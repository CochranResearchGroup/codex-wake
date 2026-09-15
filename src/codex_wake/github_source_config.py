"""Explicit operator-owned, nonsecret GitHub source selection.

The registry takes configuration values, never ambient credentials or arbitrary
registration fields. Credential references name an injected resolver entry.
"""
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

from .github_polling import GitHubPollingConfig, _valid_config
from .signals import Degraded


_SOURCE_FIELDS = (
    "source_instance", "repository", "repository_id", "workflow_id", "refs",
    "conclusions", "credential_ref", "permissions", "page_size", "max_pages",
    "overlap_seconds", "max_history_seconds", "retry_seconds", "hostname",
    "enabled", "evidence_mode", "max_requests", "max_response_bytes",
    "max_poll_bytes", "request_timeout_seconds", "poll_timeout_seconds",
)


@dataclass(frozen=True, slots=True)
class GitHubSourceHealth:
    source_instance: str
    code: str
    retry_at: datetime | None
    observed_at: datetime


class GitHubSourceRegistry:
    def __init__(self, sources: tuple[GitHubPollingConfig, ...]):
        if type(sources) is not tuple or len(sources) > 64:
            raise ValueError("GitHub source registry is invalid")
        selected = {}
        for source in sources:
            if (not _valid_config(source) or source.evidence_mode != "positive_only"
                    or source.source_instance in selected):
                raise ValueError("GitHub source registry is invalid")
            selected[source.source_instance] = source
        self._sources = MappingProxyType(selected)

    def select(self, source_instance: str) -> GitHubPollingConfig:
        source = self._sources.get(source_instance) if type(source_instance) is str else None
        if source is None or not source.enabled:
            raise ValueError("GitHub source is not enabled")
        return source

    def enabled_sources(self) -> tuple[GitHubPollingConfig, ...]:
        return tuple(value for value in self._sources.values() if value.enabled)


class GitHubSourceStore:
    """Own the bounded, nonsecret GitHub configuration below one wake root."""

    def __init__(self, wake_root: Path):
        self.wake_root = Path(wake_root).resolve()
        self.path = self.wake_root / "github" / "sources.json"
        self.health_path = self.wake_root / "github" / "source-health.json"

    def sources(self) -> tuple[GitHubPollingConfig, ...]:
        if self.path.is_symlink():
            raise ValueError("GitHub source configuration is invalid")
        if not self.path.exists():
            return ()
        try:
            if self.path.is_symlink() or not self.path.is_file() or self.path.stat().st_size > 262_144:
                raise ValueError
            payload = json.loads(
                self.path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
            )
            if type(payload) is not dict or set(payload) != {"schema_version", "sources"}:
                raise ValueError
            rows = payload["sources"]
            if payload["schema_version"] != 1 or type(rows) is not list or len(rows) > 64:
                raise ValueError
            sources = tuple(_decode_source(row) for row in rows)
            GitHubSourceRegistry(sources)
            if tuple(item.source_instance for item in sources) != tuple(
                sorted(item.source_instance for item in sources)
            ):
                raise ValueError
            return sources
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("GitHub source configuration is invalid") from None

    def registry(self) -> GitHubSourceRegistry:
        return GitHubSourceRegistry(self.sources())

    def configure(self, source: GitHubPollingConfig) -> GitHubPollingConfig:
        GitHubSourceRegistry((source,))
        selected = {item.source_instance: item for item in self.sources()}
        existing = selected.get(source.source_instance)
        if existing == source:
            return source
        if existing is not None:
            existing_authority = _encode_source(existing)
            requested_authority = _encode_source(source)
            existing_authority.pop("enabled")
            requested_authority.pop("enabled")
            if existing_authority != requested_authority:
                raise ValueError(
                    "material GitHub source changes require a new source_instance"
                )
        selected[source.source_instance] = source
        configured = tuple(sorted(selected.values(), key=lambda item: item.source_instance))
        GitHubSourceRegistry(configured)
        _atomic_write_json(
            self.path,
            {"schema_version": 1, "sources": [_encode_source(item) for item in configured]},
        )
        return source

    def record_health(
        self,
        source_instance: str,
        health: Degraded,
        *,
        observed_at: datetime,
    ) -> None:
        if (
            type(source_instance) is not str
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", source_instance) is None
            or not isinstance(health, Degraded)
            or health.wake_id is not None
            or health.evidence_ref is not None
            or health.code not in {
                "GITHUB_AUTH_UNAVAILABLE", "GITHUB_RATE_LIMITED",
                "GITHUB_SOURCE_UNAVAILABLE", "GITHUB_VERIFICATION_FAILED",
                "GITHUB_RESPONSE_INVALID", "GITHUB_POLL_BUDGET_EXHAUSTED",
                "GITHUB_COVERAGE_UNPROVEN", "GITHUB_HISTORY_GAP",
                "GITHUB_PAGINATION_INVALID", "STORE_UNAVAILABLE",
            }
            or not _aware_time(observed_at)
            or (health.retry_at is not None and not _aware_time(health.retry_at))
        ):
            raise ValueError("GitHub source health is invalid")
        rows = self._health_rows()
        rows[source_instance] = {
            "source": "github",
            "source_instance": source_instance,
            "code": health.code,
            "retry_at": _format_time(health.retry_at) if health.retry_at else None,
            "observed_at": _format_time(observed_at),
        }
        _atomic_write_json(
            self.health_path,
            {"schema_version": 1, "sources": [rows[name] for name in sorted(rows)]},
        )

    def retry_failure(self, source_instance: str) -> Degraded | None:
        health = self.source_health(source_instance)
        if health is None or health.retry_at is None:
            return None
        retry_codes = {
            "GITHUB_AUTH_UNAVAILABLE", "GITHUB_RATE_LIMITED",
            "GITHUB_SOURCE_UNAVAILABLE", "GITHUB_VERIFICATION_FAILED",
            "GITHUB_RESPONSE_INVALID", "GITHUB_POLL_BUDGET_EXHAUSTED",
        }
        if health.code not in retry_codes:
            return None
        return Degraded(None, health.code, health.retry_at)

    def source_health(self, source_instance: str) -> GitHubSourceHealth | None:
        row = self._health_rows().get(source_instance)
        if row is None:
            return None
        return GitHubSourceHealth(
            source_instance=source_instance,
            code=str(row["code"]),
            retry_at=_parse_time(row["retry_at"]) if row["retry_at"] else None,
            observed_at=_parse_time(str(row["observed_at"])),
        )

    def _health_rows(self) -> dict[str, dict[str, object]]:
        if self.health_path.is_symlink():
            raise ValueError("GitHub source health is invalid")
        if not self.health_path.exists():
            return {}
        try:
            if (self.health_path.is_symlink() or not self.health_path.is_file()
                    or self.health_path.stat().st_size > 262_144):
                raise ValueError
            payload = json.loads(
                self.health_path.read_text(encoding="utf-8"),
                object_pairs_hook=_unique_object,
            )
            if type(payload) is not dict or set(payload) != {"schema_version", "sources"}:
                raise ValueError
            rows = payload["sources"]
            if payload["schema_version"] != 1 or type(rows) is not list or len(rows) > 64:
                raise ValueError
            decoded: dict[str, dict[str, object]] = {}
            for row in rows:
                if type(row) is not dict or set(row) != {
                    "source", "source_instance", "code", "retry_at", "observed_at"
                }:
                    raise ValueError
                name = row["source_instance"]
                if (row["source"] != "github" or type(name) is not str
                        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", name) is None
                        or name in decoded or type(row["code"]) is not str
                        or row["retry_at"] is not None and type(row["retry_at"]) is not str
                        or type(row["observed_at"]) is not str):
                    raise ValueError
                _parse_time(row["observed_at"])
                if row["retry_at"] is not None:
                    _parse_time(row["retry_at"])
                decoded[name] = row
            return decoded
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("GitHub source health is invalid") from None


def _encode_source(source: GitHubPollingConfig) -> dict[str, object]:
    return {
        name: sorted(getattr(source, name))
        if name in {"refs", "conclusions", "permissions"}
        else getattr(source, name)
        for name in _SOURCE_FIELDS
    }


def _decode_source(payload: object) -> GitHubPollingConfig:
    if type(payload) is not dict or set(payload) != set(_SOURCE_FIELDS):
        raise ValueError
    values = dict(payload)
    for name in ("refs", "conclusions", "permissions"):
        value = values[name]
        if type(value) is not list or any(type(item) is not str for item in value):
            raise ValueError
        values[name] = frozenset(value)
    source = GitHubPollingConfig(**values)
    if not _valid_config(source) or source.evidence_mode != "positive_only":
        raise ValueError
    return source


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    temp_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise ValueError("GitHub source configuration is invalid")
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=".sources-", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            os.chmod(temp_path, 0o600)
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except ValueError:
        raise
    except OSError:
        raise ValueError("GitHub source configuration is unavailable") from None
    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def _aware_time(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not _aware_time(parsed):
        raise ValueError
    return parsed


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result
