from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Literal

from .signals import ArmedSignal, Eq, Resume


SIGNAL_RECORD_SCHEMA_VERSION = 2
SIGNAL_JOURNAL_SCHEMA_VERSION = 2
SIGNAL_JOURNAL_RELATIVE_PATH = Path("signals") / "journal.sqlite3"
SIGNAL_IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


def is_safe_signal_identifier(value: object) -> bool:
    """Return whether a schema-v2 identifier is one filesystem-safe segment."""

    return isinstance(value, str) and SIGNAL_IDENTIFIER_RE.fullmatch(value) is not None


def signal_journal_path(wake_root: Path) -> Path:
    """Return the one journal location owned by a resolved wake root."""

    return Path(wake_root).resolve() / SIGNAL_JOURNAL_RELATIVE_PATH


def decode_signal_record(record: object) -> dict[str, object] | None:
    """Classify and return only a structurally complete schema-v2 signal record."""

    if not isinstance(record, dict) or record.get("schema_version") != SIGNAL_RECORD_SCHEMA_VERSION:
        return None
    predicate = record.get("predicate")
    target = record.get("target")
    anchor = predicate.get("anchor") if isinstance(predicate, dict) else None
    where = predicate.get("where") if isinstance(predicate, dict) else None
    required_strings = (
        "id", "arm_id", "journal_uuid", "created_at", "updated_at", "cwd",
        "prompt", "status", "next_attempt_at",
    )
    if any(not isinstance(record.get(name), str) or not record.get(name) for name in required_strings):
        return None
    if not is_safe_signal_identifier(record.get("id")) or not is_safe_signal_identifier(record.get("arm_id")):
        return None
    if record.get("status") not in {
        "pending", "firing", "submitted", "failed", "cancelled", "expired", "archived"
    }:
        return None
    if type(record.get("record_revision")) is not int or int(record["record_revision"]) < 1:
        return None
    if type(record.get("attempts")) is not int or type(record.get("max_attempts")) is not int:
        return None
    if type(record.get("ack_timeout_seconds")) not in {int, float}:
        return None
    if not isinstance(record.get("events"), list) or not isinstance(target, dict):
        return None
    if not isinstance(predicate, dict) or predicate.get("type") != "signal":
        return None
    for name in ("arm_id", "source", "source_instance", "semantics", "kind", "subject", "condition", "verification"):
        if not isinstance(predicate.get(name), str) or not predicate.get(name):
            return None
    if predicate.get("arm_id") != record.get("arm_id") or predicate.get("contract_version") != 1:
        return None
    if not is_safe_signal_identifier(predicate.get("arm_id")):
        return None
    if predicate.get("semantics") not in {"occurrence", "state"}:
        return None
    if predicate.get("condition") not in {"occurs", "holds", "becomes"}:
        return None
    if predicate.get("verification") not in {"required", "not_required"}:
        return None
    if not isinstance(where, list) or not isinstance(anchor, dict):
        return None
    if type(anchor.get("local_after_sequence")) is not int or anchor["local_after_sequence"] < 0:
        return None
    if not isinstance(anchor.get("source_anchor"), str) or not isinstance(anchor.get("baseline"), dict):
        return None
    if anchor.get("recovery") not in {"local_journal", "source_replay", "state_recheck"}:
        return None
    for clause in where:
        if not isinstance(clause, dict) or clause.get("op") not in {"eq", "in"}:
            return None
        if not isinstance(clause.get("field"), str) or not clause.get("field"):
            return None
        if clause["op"] == "eq" and "value" not in clause:
            return None
        if clause["op"] == "in" and not isinstance(clause.get("values"), list):
            return None
    return dict(record)


@dataclass(frozen=True, slots=True)
class ManagedReaderCapability:
    wake_root: Path
    reader_id: str
    generation: int
    schema_versions: frozenset[int]
    active: bool
    pid: int | None = None
    process_start_time_ticks: int | None = None
    process_boot_id: str | None = None


@dataclass(frozen=True, slots=True)
class PublicationResult:
    outcome: Literal["applied", "missing", "conflict", "unavailable"]
    path: Path | None = None


class WakeRecordPublisher:
    """Durably projects exact signal-record bytes into one managed wake root."""

    def __init__(
        self,
        wake_root: Path,
        capability: ManagedReaderCapability | None = None,
        *,
        capability_probe: Callable[[], ManagedReaderCapability | None] | None = None,
        checkpoint: Callable[[str], None] | None = None,
    ) -> None:
        self.wake_root = Path(wake_root).resolve()
        self.capability = capability
        self._capability_probe = capability_probe
        self._checkpoint = checkpoint or (lambda _name: None)

    def capability_code(self) -> str | None:
        capability = self._capability_probe() if self._capability_probe is not None else self.capability
        if capability is None:
            return "READER_CAPABILITY_UNAVAILABLE"
        try:
            capability_root = Path(capability.wake_root).resolve()
        except OSError:
            return "READER_CAPABILITY_UNAVAILABLE"
        if (
            capability_root != self.wake_root
            or not capability.active
            or not capability.reader_id
            or capability.generation < 1
            or SIGNAL_RECORD_SCHEMA_VERSION not in capability.schema_versions
        ):
            return "READER_CAPABILITY_UNAVAILABLE"
        if capability.pid is not None:
            from .process import boot_id_value, process_exists, process_identity

            if not process_exists(capability.pid):
                return "READER_CAPABILITY_UNAVAILABLE"
            identity = process_identity(capability.pid)
            if identity is None:
                return "READER_CAPABILITY_UNAVAILABLE"
            if (
                capability.process_start_time_ticks is not None
                and identity.get("start_time_ticks") != capability.process_start_time_ticks
            ):
                return "READER_CAPABILITY_UNAVAILABLE"
            if (
                capability.process_boot_id is not None
                and boot_id_value() != capability.process_boot_id
            ):
                return "READER_CAPABILITY_UNAVAILABLE"
        return None

    @classmethod
    def for_managed_reader(
        cls,
        wake_root: Path,
        *,
        state_dir: Path | None = None,
        checkpoint: Callable[[str], None] | None = None,
    ) -> WakeRecordPublisher:
        root = Path(wake_root).resolve()
        return cls(
            root,
            capability_probe=lambda: probe_managed_reader_capability(root, state_dir=state_dir),
            checkpoint=checkpoint,
        )

    def apply(self, payload_json: str, payload_sha256: str) -> PublicationResult:
        if self.capability_code() is not None:
            return PublicationResult("unavailable")
        try:
            payload = json.loads(payload_json)
            wake_id = payload["id"]
            status = payload["status"]
            if (
                not isinstance(wake_id, str)
                or not wake_id
                or status not in {"pending", "firing", "cancelled", "expired"}
                or decode_signal_record(payload) is None
            ):
                return PublicationResult("conflict")
            expected = (payload_json + "\n").encode("utf-8")
            if hashlib.sha256(expected).hexdigest() != payload_sha256:
                return PublicationResult("conflict")
            final_path = self.wake_root / status / f"{wake_id}.json"
            if final_path.exists():
                if final_path.read_bytes() != expected:
                    return PublicationResult("conflict", final_path)
                self._remove_superseded_source(payload, final_path)
                return PublicationResult("applied", final_path)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=final_path.parent,
                    prefix=f".{wake_id}.",
                    suffix=".json.tmp",
                    delete=False,
                ) as handle:
                    temp_path = Path(handle.name)
                    handle.write(expected)
                    handle.flush()
                    self._checkpoint("after_temp_write")
                    os.fsync(handle.fileno())
                    self._checkpoint("after_file_fsync")
                if self.capability_code() is not None:
                    return PublicationResult("unavailable")
                os.replace(temp_path, final_path)
                temp_path = None
                self._checkpoint("after_replace")
                if status == "firing":
                    self._checkpoint("after_firing_replace")
                directory_fd = os.open(
                    final_path.parent,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
                )
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
                self._checkpoint("after_directory_fsync")
                self._remove_superseded_source(payload, final_path)
                return PublicationResult("applied", final_path)
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
        except (OSError, TypeError, ValueError, KeyError):
            return PublicationResult("unavailable")

    def _remove_superseded_source(self, payload: dict[str, object], final_path: Path) -> None:
        if payload.get("status") not in {"firing", "cancelled", "expired"}:
            return
        wake_id = payload["id"]
        source_path = self.wake_root / "pending" / f"{wake_id}.json"
        if source_path == final_path or not source_path.exists():
            return
        try:
            source = json.loads(source_path.read_text(encoding="utf-8"))
            decoded = decode_signal_record(source)
            if (
                decoded is None
                or decoded.get("id") != wake_id
                or decoded.get("journal_uuid") != payload.get("journal_uuid")
                or int(decoded["record_revision"]) > int(payload["record_revision"])
            ):
                return
            self._checkpoint("before_pending_unlink")
            source_path.unlink()
            directory_fd = os.open(
                source_path.parent,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            self._checkpoint("after_pending_unlink")
        except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
            return

    def inspect(self, payload_json: str, payload_sha256: str) -> PublicationResult:
        if self.capability_code() is not None:
            return PublicationResult("unavailable")
        try:
            payload = json.loads(payload_json)
            if decode_signal_record(payload) is None:
                return PublicationResult("conflict")
            wake_id = payload["id"]
            status = payload["status"]
            final_path = self.wake_root / status / f"{wake_id}.json"
            if not final_path.exists():
                return PublicationResult("missing", final_path)
            expected = (payload_json + "\n").encode("utf-8")
            if hashlib.sha256(expected).hexdigest() != payload_sha256:
                return PublicationResult("conflict", final_path)
            return PublicationResult(
                "applied" if final_path.read_bytes() == expected else "conflict",
                final_path,
            )
        except (OSError, TypeError, ValueError, KeyError):
            return PublicationResult("conflict")


def build_signal_record(
    armed: ArmedSignal,
    resume: Resume,
    *,
    journal_uuid: str,
    revision: int,
    max_attempts: int = 3,
) -> tuple[str, str]:
    timestamp = _format_time(armed.registered_at)
    predicate = {
        "type": "signal",
        "contract_version": armed.spec.contract_version,
        "arm_id": str(armed.arm_id),
        "source": armed.spec.source,
        "source_instance": armed.spec.source_instance,
        "semantics": armed.spec.semantics,
        "kind": armed.spec.kind,
        "subject": armed.spec.subject,
        "condition": armed.spec.condition,
        "where": [
            {"op": "eq", **asdict(clause)}
            if isinstance(clause, Eq)
            else {"op": "in", **asdict(clause)}
            for clause in armed.spec.where
        ],
        "verification": armed.spec.verification,
        "anchor": {
            "local_after_sequence": armed.anchor.local_after_sequence,
            "source_anchor": armed.anchor.source_anchor,
            "baseline": dict(armed.anchor.baseline),
            "recovery": armed.anchor.recovery,
        },
    }
    payload = {
        "schema_version": SIGNAL_RECORD_SCHEMA_VERSION,
        "id": str(armed.wake_id),
        "arm_id": str(armed.arm_id),
        "journal_uuid": journal_uuid,
        "record_revision": revision,
        "created_at": timestamp,
        "updated_at": timestamp,
        "cwd": str(resume.cwd.resolve()),
        "target": dict(resume.target),
        "predicate": predicate,
        "prompt": resume.prompt,
        "status": "pending",
        "attempts": 0,
        "max_attempts": max_attempts,
        "ack_timeout_seconds": 30,
        "next_attempt_at": timestamp,
        "events": [
            {
                "at": timestamp,
                "type": "created",
                "message": "Signal wake record created",
            }
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256((encoded + "\n").encode("utf-8")).hexdigest()
    return encoded, digest


def probe_managed_reader_capability(
    wake_root: Path,
    *,
    state_dir: Path | None = None,
    expected_reader_id: str | None = None,
    expected_generation: int | None = None,
    now: datetime | None = None,
) -> ManagedReaderCapability | None:
    """Read and verify the currently advertised managed reader without mutation."""

    from .monitor import health_is_recent, read_monitor_health

    root = Path(wake_root).resolve()
    health = read_monitor_health(root, state_dir)
    if not health_is_recent(health, now=now) or health is None:
        return None
    try:
        advertised_root = Path(str(health["wake_root"])).resolve()
        reader_id = health["reader_id"]
        generation = health["reader_generation"]
        versions = health["reader_schema_versions"]
        capabilities = health["reader_capabilities"]
        pid = health["pid"]
        start = health["process_start_time_ticks"]
        boot_id = health["process_boot_id"]
    except (KeyError, OSError, TypeError, ValueError):
        return None
    if (
        advertised_root != root
        or not isinstance(reader_id, str)
        or not reader_id
        or type(generation) is not int
        or generation < 1
        or not isinstance(versions, list)
        or any(type(value) is not int for value in versions)
        or not isinstance(capabilities, list)
        or "signal_records_v2" not in capabilities
        or type(pid) is not int
        or pid < 1
        or type(start) is not int
        or not isinstance(boot_id, str)
        or not boot_id
    ):
        return None
    if expected_reader_id is not None and reader_id != expected_reader_id:
        return None
    if expected_generation is not None and generation != expected_generation:
        return None
    capability = ManagedReaderCapability(
        root,
        reader_id,
        generation,
        frozenset(versions),
        True,
        pid,
        start,
        boot_id,
    )
    publisher = WakeRecordPublisher(root, capability)
    return capability if publisher.capability_code() is None else None


def current_reader_capability(
    wake_root: Path,
    *,
    reader_id: str | None = None,
) -> ManagedReaderCapability:
    from .process import boot_id_value, process_identity

    pid = os.getpid()
    identity = process_identity(pid) or {}
    start = identity.get("start_time_ticks")
    boot_id = identity.get("boot_id") or boot_id_value()
    return ManagedReaderCapability(
        Path(wake_root).resolve(),
        reader_id or f"codex-waked:{pid}",
        start if isinstance(start, int) and start > 0 else pid,
        frozenset({1, 2}),
        True,
        pid if isinstance(start, int) and isinstance(boot_id, str) else None,
        start if isinstance(start, int) else None,
        boot_id if isinstance(boot_id, str) else None,
    )


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
