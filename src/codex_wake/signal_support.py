"""Read-only signal readiness and bounded support exports."""
from __future__ import annotations

import bisect
import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .monitor import health_is_recent, read_monitor_health
from .github_source_config import GitHubSourceStore
from .records import ACTIVE_STATUS_DIRS
from .signal_records import decode_signal_record, signal_journal_path
from .signal_store import JOURNAL_APPLICATION_ID, JOURNAL_SCHEMA_VERSION


MAX_SUPPORT_WAKES = 100
MAX_SUPPORT_BYTES = 1_048_576
MAX_SUPPORT_INPUT_FILES = 512
MAX_SUPPORT_SCANNED_ENTRIES = 2_048
MAX_SUPPORT_RECORD_BYTES = 65_536
MAX_SUPPORT_SOURCES = 128

_RUNTIME_HEALTH_BY_CODE = {
    "RUNTIME_NOT_OBSERVED": "unobserved", "RUNTIME_READY": "ready",
    "RUNTIME_SOURCE_UNSUPPORTED": "unsupported", "RUNTIME_AUTHORIZATION_DENIED": "invalidated",
    "RUNTIME_OBSERVATION_UNAVAILABLE": "unavailable", "RUNTIME_OBSERVATION_AMBIGUOUS": "invalidated",
    "RUNTIME_BASELINE_MATCHES": "invalidated", "RUNTIME_RESOURCE_LIMIT": "unavailable",
    "RUNTIME_ANCHOR_INVALID": "invalidated", "RUNTIME_REQUEST_INVALID": "invalidated",
    "RUNTIME_CHECKPOINT_UNAVAILABLE": "unavailable", "RUNTIME_CHECKPOINT_INVALID": "invalidated",
    "RUNTIME_INGEST_UNAVAILABLE": "unavailable", "RUNTIME_PUBLICATION_UNAVAILABLE": "unavailable",
}
_SYSTEMD_HEALTH_BY_CODE = {
    "SYSTEMD_READY": "ready", "SYSTEMD_SOURCE_UNSUPPORTED": "unsupported",
    "SYSTEMD_CAPABILITY_DENIED": "invalidated", "SYSTEMD_AUTHORIZATION_DENIED": "invalidated",
    "SYSTEMD_SIGNAL_NOT_ALLOWED": "invalidated", "SYSTEMD_BASELINE_MATCHES": "invalidated",
    "SYSTEMD_OBSERVATION_UNAVAILABLE": "unavailable", "SYSTEMD_UNIT_UNAVAILABLE": "unavailable",
    "SYSTEMD_RESOURCE_LIMIT": "unavailable", "SYSTEMD_CHECKPOINT_UNAVAILABLE": "unavailable",
    "SYSTEMD_CHECKPOINT_INVALID": "invalidated", "SYSTEMD_INGEST_UNAVAILABLE": "unavailable",
    "SYSTEMD_ANCHOR_INVALID": "invalidated",
}
_ALLOWED_HEALTH_CODES = frozenset(_RUNTIME_HEALTH_BY_CODE) | frozenset(_SYSTEMD_HEALTH_BY_CODE) | {
    "GITHUB_RATE_LIMITED", "GITHUB_AUTH_UNAVAILABLE", "GITHUB_SOURCE_UNAVAILABLE",
    "GITHUB_POLL_BUDGET_EXHAUSTED", "GITHUB_HISTORY_GAP", "GITHUB_COVERAGE_UNPROVEN",
    "GITHUB_PAGINATION_INVALID", "GITHUB_RESPONSE_INVALID", "GITHUB_VERIFICATION_FAILED", "CONFIG_INVALID",
}


def _safe_health(value: object) -> dict[str, Any]:
    """Keep only bounded health counters and capability labels."""
    if not isinstance(value, dict):
        return {}
    allowed = {"scanned", "observed", "degraded", "checked_at", "credential_capability",
               "credential_status", "checkpoint_present", "replay_lag_seconds",
               "lag_seconds", "max_replay_lag_seconds", "failure_code", "terminal_failure",
               "code", "retry_at", "observed_at"}
    result: dict[str, Any] = {}
    for key in allowed:
        item = value.get(key)
        if key in {"scanned", "observed", "degraded", "checkpoint_present"} and type(item) not in {bool, int}:
            continue
        if key in {"replay_lag_seconds", "lag_seconds", "max_replay_lag_seconds"} and type(item) not in {int, float}:
            continue
        if key in {"credential_capability", "credential_status", "failure_code", "terminal_failure", "code", "retry_at", "observed_at", "checked_at"}:
            if not isinstance(item, str) or len(item) > 128 or not item.isascii():
                continue
            if key in {"failure_code", "terminal_failure", "code"} and item not in _ALLOWED_HEALTH_CODES:
                continue
        result[key] = item
    return result


def _runtime_source_health(
    source: str, health: dict[str, Any] | None, *, now: datetime,
) -> tuple[str, str]:
    """Classify only fresh, exact runtime-instance health."""
    observed = _safe_health(health)
    if not health_is_recent({"checked_at": observed.get("observed_at")}, now=now):
        return "unobserved", ""
    code = observed.get("code") if isinstance(observed.get("code"), str) else ""
    mapping = _RUNTIME_HEALTH_BY_CODE if source == "runtime" else _SYSTEMD_HEALTH_BY_CODE
    if code in mapping:
        return mapping[code], code
    if int(observed.get("degraded", 0) or 0) > 0:
        return "unavailable", ""
    return "ready", ""


def github_source_readiness(
    config: object | None = None,
    *,
    health: dict[str, Any] | None = None,
    checkpoint: object | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Project GitHub source support state without reading credentials.

    ``health`` is an adapter-owned, already sanitized summary.  Only scalar
    capability fields are copied; provider payloads and credential values are
    never part of this projection.
    """
    observed = _safe_health(health)
    enabled = bool(getattr(config, "enabled", False)) if config is not None else False
    supported = config is not None and getattr(config, "hostname", "github.com") == "github.com"
    configuration_status = "ready" if supported and enabled else "disabled" if supported else "unsupported"
    credential_state = str(observed.get("credential_capability") or observed.get("credential_status") or ("configured_reference" if getattr(config, "credential_ref", "") else "unknown"))
    if credential_state not in {"ready", "configured_reference", "missing", "unavailable", "unknown"}:
        credential_state = "unknown"
    failure = observed.get("terminal_failure") or observed.get("failure_code") or observed.get("code") or ""
    failure = str(failure) if isinstance(failure, (str, int)) else ""
    allowed_codes = {"GITHUB_RATE_LIMITED", "GITHUB_AUTH_UNAVAILABLE", "GITHUB_SOURCE_UNAVAILABLE", "GITHUB_POLL_BUDGET_EXHAUSTED", "GITHUB_HISTORY_GAP", "GITHUB_COVERAGE_UNPROVEN", "GITHUB_PAGINATION_INVALID", "GITHUB_RESPONSE_INVALID", "GITHUB_VERIFICATION_FAILED", "CONFIG_INVALID"}
    failure = failure[:80] if failure.isascii() and failure in allowed_codes else ""
    degraded = bool(observed.get("degraded", 0))
    transient = failure in {"GITHUB_RATE_LIMITED", "GITHUB_AUTH_UNAVAILABLE", "GITHUB_SOURCE_UNAVAILABLE", "GITHUB_POLL_BUDGET_EXHAUSTED", "GITHUB_HISTORY_GAP", "GITHUB_COVERAGE_UNPROVEN", "GITHUB_PAGINATION_INVALID"}
    expected_warning = failure in {"GITHUB_COVERAGE_UNPROVEN", "GITHUB_HISTORY_GAP"}
    auth_unavailable = failure == "GITHUB_AUTH_UNAVAILABLE"
    if auth_unavailable:
        credential_state = "unavailable"
    health_status = "warning" if transient and not auth_unavailable else "blocked" if degraded or failure else "warning" if observed.get("checked_at") is None else "ready"
    checkpoint_present = checkpoint is not None or bool(observed.get("checkpoint_present"))
    lag_value = observed.get("replay_lag_seconds", observed.get("lag_seconds"))
    if lag_value is None and isinstance(observed.get("observed_at"), str):
        try:
            observed_time = datetime.fromisoformat(observed["observed_at"].replace("Z", "+00:00"))
            current = now if isinstance(now, datetime) and now.tzinfo else datetime.now(UTC)
            lag_value = max(0.0, (current.astimezone(UTC) - observed_time.astimezone(UTC)).total_seconds())
        except (TypeError, ValueError):
            lag_value = None
    lag = lag_value if type(lag_value) in {int, float} and lag_value >= 0 else None
    ceiling = observed.get("max_replay_lag_seconds", 300)
    if type(ceiling) not in {int, float} or ceiling < 0:
        ceiling = 300
    lag_status = "ready" if lag is not None and lag <= ceiling else "warning" if lag is not None else "unknown"
    if configuration_status == "unsupported":
        overall = "unsupported"
    elif configuration_status == "disabled":
        overall = "disabled"
    elif auth_unavailable or credential_state in {"missing", "unavailable"}:
        overall = "blocked"
    elif expected_warning or transient:
        overall = "warning"
    elif (failure and not transient) or degraded:
        overall = "blocked"
    elif health_status == "warning" or not checkpoint_present or lag_status in {"warning", "unknown"}:
        overall = "warning"
    else:
        overall = "ready"
    return {
        "status": overall,
        "configuration": {"status": configuration_status, "enabled": enabled},
        "credential_capability": {"status": credential_state},
        "health": {"status": health_status, "degraded": degraded},
        "checkpoint": {"status": "ready" if checkpoint_present else "warning", "present": checkpoint_present},
        "replay_lag": {"status": lag_status, "seconds": lag},
        "terminal_failure": {"status": "not_present" if not failure or transient else "blocked", "code": "" if transient else failure},
        "health_code": failure,
        "retry_at": observed.get("retry_at"),
        "observed_at": observed.get("observed_at", observed.get("checked_at")),
        "disabled": configuration_status == "disabled",
        "unsupported": configuration_status == "unsupported",
    }


@dataclass(frozen=True, slots=True)
class SupportExportResult:
    path: Path
    size_bytes: int
    sha256: str
    included_wakes: int
    omitted_wakes: int


def _outcome(status: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, "message": message, **extra}


def signal_readiness(
    wake_root: Path,
    *,
    health: dict[str, Any] | None = None,
    github_store: GitHubSourceStore | None = None,
    max_journal_schema: int = JOURNAL_SCHEMA_VERSION,
    max_sources: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Inspect signal capability without creating or migrating runtime state."""

    root = Path(wake_root).resolve()
    journal_path = signal_journal_path(root)
    capability = _outcome(
        "ready",
        "signal records and provider-free source reconciliation are available",
        record_schema_versions=[2],
        journal_schema_versions=[1, 2],
        sources_enabled_by_default=False,
    )
    dispatch = {
        "included": False,
        "message": "dispatch-target readiness is reported separately",
    }
    captured_now = now or datetime.now(UTC)
    configured_github: list[dict[str, Any]] = []
    config_error = ""
    health_error = False
    store = github_store or GitHubSourceStore(root)
    try:
        configured = store.sources()
        health_rows = {}
        try:
            for source in configured:
                item = store.source_health(source.source_instance)
                if item is not None:
                    health_rows[source.source_instance] = {"code": item.code, "retry_at": item.retry_at.isoformat() if item.retry_at else None, "observed_at": item.observed_at.isoformat()}
        except ValueError:
            config_error = "GitHub source health is invalid"
            health_error = True
        for source in configured:
            health_item = health_rows.get(source.source_instance, {})
            projection = github_source_readiness(source, health=health_item, now=captured_now)
            projection["source_instance"] = source.source_instance
            projection["repository"] = source.repository
            projection["workflow_id"] = source.workflow_id
            projection["credential_ref"] = source.credential_ref
            configured_github.append(projection)
        if health_error:
            for projection in configured_github:
                projection["status"] = "blocked"
                projection["health"] = {"status": "blocked", "degraded": True}
                projection["terminal_failure"] = {
                    "status": "blocked",
                    "code": "HEALTH_INVALID",
                }
                projection["diagnostic"] = "GitHub source health is invalid"
    except ValueError as exc:
        config_error = str(exc)
        configured_github.append({"status": "blocked", "source_instance": "", "configuration": {"status": "invalid", "enabled": None}, "credential_capability": {"status": "unknown"}, "health": {"status": "blocked"}, "checkpoint": {"status": "unknown", "present": False}, "replay_lag": {"status": "unknown", "seconds": None}, "terminal_failure": {"status": "blocked", "code": "CONFIG_INVALID"}, "disabled": False, "unsupported": False, "diagnostic": "GitHub source configuration is invalid"})
    if not journal_path.is_file():
        source_entries = [
            {"source": "github", "source_instance": item.get("source_instance", ""),
             "status": item.get("status", "blocked"),
             "message": "configured GitHub source has no signal journal or active arm",
             "active_arms": 0, "checkpoint_present": False, "checkpoint_order": None,
             "observed_through": "", "latest_reconcile": {}, "health_scope": "none",
             "support": item}
            for item in configured_github
        ]
        source_statuses = {str(item.get("status")) for item in configured_github}
        aggregate_status = "blocked" if config_error or "blocked" in source_statuses else "warning" if "warning" in source_statuses else "ready"
        return {
            "status": aggregate_status,
            "capability": capability,
            "journal": _outcome(
                "not_needed",
                (
                    "no signal journal exists; configured sources have no active arm"
                    if configured_github
                    else "no signal journal exists because no signal source is configured"
                ),
                exists=False,
                path=str(journal_path),
                schema_version=None,
                repair="",
            ),
            "sources": source_entries,
            "sources_omitted": 0,
            "dispatch_readiness": dispatch,
        }

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            journal_path.resolve().as_uri() + "?mode=ro", uri=True
        )
        connection.row_factory = sqlite3.Row
        application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
        schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if application_id != JOURNAL_APPLICATION_ID:
            raise sqlite3.DatabaseError("unexpected application id")
        if schema_version > max_journal_schema:
            journal = _outcome(
                "blocked",
                f"signal journal schema {schema_version} is newer than this runtime supports",
                exists=True,
                path=str(journal_path),
                schema_version=schema_version,
                repair=(
                    "downgrade is blocked; restore a pre-upgrade journal backup or use a runtime "
                    f"supporting schema {schema_version}"
                ),
            )
            return {
                "status": "blocked",
                "capability": capability,
                "journal": journal,
                "sources": [],
                "sources_omitted": 0,
                "dispatch_readiness": dispatch,
            }
        source_count = int(
            connection.execute("SELECT COUNT(*) FROM source_instances").fetchone()[0]
        )
        if max_sources is not None and (
            type(max_sources) is not int or not 0 <= max_sources <= MAX_SUPPORT_SOURCES
        ):
            raise ValueError("max_sources exceeds the supported bound")
        query = """
            SELECT i.source, i.source_instance, s.checkpoint,
                   s.checkpoint_order, s.observed_through,
                   SUM(CASE WHEN a.state != 'tombstoned' THEN 1 ELSE 0 END) AS active_arms
            FROM source_instances AS i
            LEFT JOIN source_state AS s
              ON s.source = i.source AND s.source_instance = i.source_instance
            LEFT JOIN arms AS a
              ON a.source = i.source AND a.source_instance = i.source_instance
            GROUP BY i.source, i.source_instance, s.checkpoint,
                     s.checkpoint_order, s.observed_through
            ORDER BY i.source, i.source_instance
            """
        parameters: tuple[int, ...] = ()
        if max_sources is not None:
            query += " LIMIT ?"
            parameters = (max_sources,)
        rows = connection.execute(query, parameters).fetchall()
        sources_omitted = source_count - len(rows)
    except Exception:
        return {
            "status": "blocked",
            "capability": capability,
            "journal": _outcome(
                "blocked",
                "signal journal cannot be read safely",
                exists=True,
                path=str(journal_path),
                schema_version=None,
                repair=(
                    "stop signal writers, preserve the journal and WAL files, then restore a "
                    "known-good backup or run SQLite integrity repair on a copy"
                ),
            ),
            "sources": [],
            "sources_omitted": 0,
            "dispatch_readiness": dispatch,
        }
    finally:
        if connection is not None:
            connection.close()

    source_health = health if health is not None else read_monitor_health(root)
    observed_health = (
        source_health.get("signal_sources", [])
        if isinstance(source_health, dict)
        and isinstance(source_health.get("signal_sources"), list)
        else []
    )
    by_source_instance = {
        (str(item.get("source")), str(item.get("source_instance"))): item
        for item in observed_health
        if isinstance(item, dict) and item.get("source") and item.get("source_instance")
    }
    aggregate_by_source = {
        str(item.get("source")): item
        for item in observed_health
        if isinstance(item, dict) and item.get("source") and not item.get("source_instance")
    }
    sources: list[dict[str, Any]] = []
    for row in rows:
        active_arms = int(row["active_arms"] or 0)
        source_key = (str(row["source"]), str(row["source_instance"]))
        latest = by_source_instance.get(source_key)
        aggregate = aggregate_by_source.get(source_key[0])
        runtime_source = source_key[0] in {"runtime", "systemd"}
        runtime_code = ""
        if active_arms == 0:
            status = "not_needed"
            message = "source has no active arms"
        elif runtime_source:
            status, runtime_code = _runtime_source_health(
                source_key[0], latest, now=captured_now
            )
            if latest is None and aggregate is not None:
                message = "aggregate source health cannot establish this instance's readiness"
            elif latest is None:
                message = "source is configured but not yet observed"
            elif status == "ready":
                message = "source has fresh exact-instance reconciliation health"
            elif status == "unobserved":
                message = "source health is stale or does not establish this instance"
            else:
                message = "the latest exact-instance reconciliation is not ready"
        elif latest is None and aggregate is not None and int(aggregate.get("degraded", 0) or 0) > 0:
            status = "blocked"
            message = "aggregate source reconciliation degraded; instance health is unavailable"
        elif latest is None and aggregate is not None:
            status = "warning"
            message = "aggregate source health cannot establish this instance's readiness"
        elif latest is None and row["observed_through"] is None:
            status = "warning"
            message = "source is configured but not yet observed"
        elif latest is not None and int(latest.get("degraded", 0) or 0) > 0:
            status = "blocked"
            message = "the latest source reconciliation degraded"
        else:
            status = "ready"
            message = "source has durable reconciliation state"
        sources.append(
            {
                "source": str(row["source"]),
                "source_instance": str(row["source_instance"]),
                "status": status,
                "message": message,
                "active_arms": active_arms,
                "checkpoint_present": row["checkpoint"] is not None,
                "checkpoint_order": row["checkpoint_order"],
                "observed_through": row["observed_through"] or "",
                "latest_reconcile": _safe_health(latest or aggregate or {}),
                "health_scope": "instance" if latest is not None else "aggregate" if aggregate is not None else "none",
                "support": (
                    {"status": "configured_for_journal",
                     "configuration": {"status": "unknown", "enabled": None},
                     "credential_capability": {"status": "unknown"},
                     "health": {"status": status},
                     "checkpoint": {"status": "ready" if row["checkpoint"] is not None else "warning", "present": row["checkpoint"] is not None},
                     "replay_lag": {"status": "unknown", "seconds": None},
                     "terminal_failure": {"status": "not_present", "code": ""},
                     "disabled": False, "unsupported": False}
                    if str(row["source"]) == "github"
                    else {"status": status,
                          "configuration": {"status": "unknown"},
                          "credential_capability": {"status": "not_applicable"},
                          "health": {"status": status},
                          "checkpoint": {"status": "ready" if row["checkpoint"] is not None else "warning", "present": row["checkpoint"] is not None},
                          "replay_lag": {"status": "unknown", "seconds": None},
                          "terminal_failure": {
                              "status": "blocked" if status in {"unavailable", "invalidated", "unsupported"} else "not_present",
                              "code": runtime_code if status in {"unavailable", "invalidated", "unsupported"} else "",
                          },
                          "disabled": False, "unsupported": status == "unsupported"}
                    if runtime_source
                    else {"status": "ready" if status in {"ready", "not_needed"} else status,
                          "configuration": {"status": "ready"},
                          "credential_capability": {"status": "not_applicable"},
                          "health": {"status": status},
                          "checkpoint": {"status": "ready" if row["checkpoint"] is not None else "warning", "present": row["checkpoint"] is not None},
                          "replay_lag": {"status": "unknown", "seconds": None},
                          "terminal_failure": {"status": "not_present", "code": ""},
                          "disabled": False, "unsupported": False}
                ),
            }
        )
    journal = _outcome(
        "ready",
        "signal journal is readable and compatible",
        exists=True,
        path=str(journal_path),
        schema_version=schema_version,
        repair="",
    )
    configured_by_instance = {item.get("source_instance"): item for item in configured_github if item.get("source_instance")}
    seen_instances = set()
    for item in sources:
        if item.get("source") != "github":
            continue
        instance = item.get("source_instance")
        seen_instances.add(instance)
        configured_item = configured_by_instance.get(instance)
        if configured_item is not None:
            item["support"] = dict(configured_item)
            item["support"]["checkpoint"] = {"status": "ready" if item.get("checkpoint_present") else "warning", "present": bool(item.get("checkpoint_present"))}
    for item in configured_github:
        if item.get("source_instance") not in seen_instances:
            sources.append({"source": "github", "source_instance": item.get("source_instance", ""), "status": item.get("status", "blocked"), "message": "configured GitHub source has no active signal arm", "active_arms": 0, "checkpoint_present": False, "checkpoint_order": None, "observed_through": "", "latest_reconcile": {}, "health_scope": "none", "support": item})
    support_statuses = {str(item.get("support", {}).get("status")) for item in sources}
    if config_error or support_statuses & {"blocked", "unavailable", "invalidated", "unsupported"}:
        overall = "blocked"
    elif support_statuses & {"warning", "unobserved"}:
        overall = "warning"
    else:
        overall = "blocked" if any(item["status"] == "blocked" for item in sources) else "ready"
    return {
        "status": overall,
        "capability": capability,
        "journal": journal,
        "sources": sources,
        "sources_omitted": sources_omitted,
        "dispatch_readiness": dispatch,
    }


def _sanitized_wake(record: object) -> dict[str, Any] | None:
    decoded = decode_signal_record(record)
    if decoded is None or not isinstance(record, dict):
        return None
    predicate = record.get("predicate")
    if not isinstance(predicate, dict):
        return None
    result: dict[str, Any] = {
        "wake_id": str(decoded["id"]),
        "status": str(decoded["status"]),
        "record_revision": int(decoded["record_revision"]),
        "source": str(predicate.get("source") or ""),
        "source_instance": str(predicate.get("source_instance") or ""),
        "kind": str(predicate.get("kind") or ""),
        "subject": "" if predicate.get("source") == "systemd" else str(predicate.get("subject") or ""),
    }
    match = record.get("trigger_match")
    if isinstance(match, dict):
        result["match"] = {
            "receipt_id": str(match.get("receipt_id") or ""),
            "local_sequence": match.get("local_sequence"),
            "evidence_ref": str(match.get("evidence_ref") or ""),
            "evidence_digest": str(match.get("evidence_digest") or ""),
            "verification": match.get("verification") if isinstance(match.get("verification"), dict) else {},
        }
    return result


def _encode(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _bounded_record_paths(root: Path) -> tuple[list[Path], int, int, bool]:
    """Select deterministic record paths with bounded retained memory."""

    selected: list[tuple[str, Path]] = []
    discovered = 0
    scanned = 0
    scan_truncated = False
    for directory_name in (*ACTIVE_STATUS_DIRS, "archive"):
        directory = root / directory_name
        if not directory.is_dir() or directory.is_symlink():
            continue
        try:
            entries = os.scandir(directory)
        except OSError:
            continue
        with entries:
            for entry in entries:
                if scanned >= MAX_SUPPORT_SCANNED_ENTRIES:
                    scan_truncated = True
                    break
                scanned += 1
                try:
                    is_record = (
                        entry.name.endswith(".json")
                        and entry.is_file(follow_symlinks=False)
                    )
                except OSError:
                    continue
                if not is_record:
                    continue
                discovered += 1
                key = f"{directory_name}/{entry.name}"
                bisect.insort(selected, (key, Path(entry.path)))
                if len(selected) > MAX_SUPPORT_INPUT_FILES:
                    selected.pop()
        if scan_truncated:
            break
    return [path for _key, path in selected], discovered, scanned, scan_truncated


def _read_sanitized_record(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_SUPPORT_RECORD_BYTES + 1)
    except OSError:
        return None, "unreadable"
    if len(raw) > MAX_SUPPORT_RECORD_BYTES:
        return None, "oversized"
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None, "invalid"
    sanitized = _sanitized_wake(record)
    return (sanitized, "included") if sanitized is not None else (None, "invalid")


def export_signal_support(
    wake_root: Path,
    output_path: Path,
    *,
    max_wakes: int = 50,
    max_bytes: int = 262_144,
) -> SupportExportResult:
    """Write a deterministic, sanitized, size-bounded JSON support artifact."""

    root = Path(wake_root).resolve()
    destination = Path(output_path).expanduser().resolve(strict=False)
    try:
        destination.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("support export destination must be outside the wake root")
    if type(max_wakes) is not int or not 0 <= max_wakes <= MAX_SUPPORT_WAKES:
        raise ValueError(f"max_wakes must be between 0 and {MAX_SUPPORT_WAKES}")
    if type(max_bytes) is not int or not 1024 <= max_bytes <= MAX_SUPPORT_BYTES:
        raise ValueError(f"max_bytes must be between 1024 and {MAX_SUPPORT_BYTES}")

    record_paths, discovered_records, scanned_entries, scan_truncated = _bounded_record_paths(root)
    candidates: list[dict[str, Any]] = []
    read_counts = {"oversized": 0, "invalid": 0, "unreadable": 0}
    for record_path in record_paths:
        candidate, outcome = _read_sanitized_record(record_path)
        if candidate is not None:
            candidates.append(candidate)
        elif outcome in read_counts:
            read_counts[outcome] += 1
    candidates.sort(key=lambda item: item["wake_id"])
    selected: list[dict[str, Any]] = []
    payload: dict[str, Any] = {
        "schema_version": 1,
        "signal_readiness": signal_readiness(
            root, health={}, max_sources=MAX_SUPPORT_SOURCES
        ),
        "wakes": selected,
        "included_wakes": 0,
        "omitted_wakes": discovered_records,
        "bounds": {"max_wakes": max_wakes, "max_bytes": max_bytes},
        "input": {
            "discovered_records": discovered_records,
            "record_count_complete": not scan_truncated,
            "scanned_entries": scanned_entries,
            "scan_truncated": scan_truncated,
            "read_records": len(record_paths),
            "omitted_before_read": discovered_records - len(record_paths),
            "oversized_records": read_counts["oversized"],
            "invalid_records": read_counts["invalid"],
            "unreadable_records": read_counts["unreadable"],
            "max_input_files": MAX_SUPPORT_INPUT_FILES,
            "max_scanned_entries": MAX_SUPPORT_SCANNED_ENTRIES,
            "max_record_bytes": MAX_SUPPORT_RECORD_BYTES,
            "max_sources": MAX_SUPPORT_SOURCES,
        },
    }
    for candidate in candidates[:max_wakes]:
        selected.append(candidate)
        payload["included_wakes"] = len(selected)
        payload["omitted_wakes"] = discovered_records - len(selected)
        if len(_encode(payload)) > max_bytes:
            selected.pop()
            payload["included_wakes"] = len(selected)
            payload["omitted_wakes"] = discovered_records - len(selected)
            break
    encoded = _encode(payload)
    if len(encoded) > max_bytes:
        raise ValueError("support export metadata exceeds max_bytes")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, destination)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return SupportExportResult(
        destination,
        len(encoded),
        hashlib.sha256(encoded).hexdigest(),
        len(selected),
        discovered_records - len(selected),
    )
