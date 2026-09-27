"""Bounded configuration for generic read-only HTTP/JSON completion sources."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
_ENV = re.compile(r"[A-Z][A-Z0-9_]{0,127}")
_FIELDS = (
    "source_instance", "url", "state_pointer", "event_id_pointer",
    "terminal_values", "selectors", "completed_at_pointer", "credential_ref",
    "allow_non_loopback", "enabled", "request_timeout_seconds",
    "max_response_bytes",
)


def _valid_pointer(value: str | None) -> bool:
    if value is None:
        return True
    if type(value) is not str or len(value.encode("utf-8")) > 256:
        return False
    if value == "":
        return True
    if not value.startswith("/"):
        return False
    parts = value[1:].split("/")
    return all(
        part != "" and re.search(r"~(?![01])", part) is None
        for part in parts
    )


def _safe_scalar(value: str) -> bool:
    return (
        type(value) is str
        and 0 < len(value.encode("utf-8")) <= 128
        and value.isprintable()
        and "\n" not in value
        and "\r" not in value
    )


@dataclass(frozen=True, slots=True)
class HTTPJSONSourceConfig:
    source_instance: str
    url: str
    state_pointer: str
    event_id_pointer: str | None
    terminal_values: frozenset[str]
    selectors: tuple[tuple[str, str], ...] = ()
    completed_at_pointer: str | None = None
    credential_ref: str | None = None
    allow_non_loopback: bool = False
    enabled: bool = True
    request_timeout_seconds: int = 10
    max_response_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        parsed = urlsplit(self.url) if type(self.url) is str else None
        valid_url = bool(
            parsed
            and parsed.scheme in {"http", "https"}
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
            and len(self.url.encode("utf-8")) <= 2048
        )
        if (
            type(self.source_instance) is not str
            or _NAME.fullmatch(self.source_instance) is None
            or not valid_url
            or not _valid_pointer(self.state_pointer)
            or not self.state_pointer
            or not _valid_pointer(self.event_id_pointer)
            or not _valid_pointer(self.completed_at_pointer)
            or type(self.terminal_values) is not frozenset
            or not 1 <= len(self.terminal_values) <= 16
            or any(not _safe_scalar(value) for value in self.terminal_values)
            or type(self.selectors) is not tuple
            or len(self.selectors) > 16
            or any(
                type(item) is not tuple
                or len(item) != 2
                or not _valid_pointer(item[0])
                or not item[0]
                or not _safe_scalar(item[1])
                for item in self.selectors
            )
            or len({item[0] for item in self.selectors}) != len(self.selectors)
            or self.credential_ref is not None
            and (type(self.credential_ref) is not str or _ENV.fullmatch(self.credential_ref) is None)
            or type(self.allow_non_loopback) is not bool
            or type(self.enabled) is not bool
            or type(self.request_timeout_seconds) is not int
            or not 1 <= self.request_timeout_seconds <= 60
            or type(self.max_response_bytes) is not int
            or not 1_024 <= self.max_response_bytes <= 8_388_608
        ):
            raise ValueError("HTTP JSON source configuration is invalid")
        object.__setattr__(self, "terminal_values", frozenset(self.terminal_values))
        object.__setattr__(self, "selectors", tuple(sorted(self.selectors)))


class HTTPJSONSourceStore:
    """Owner-only source allowlist below one wake root."""

    def __init__(self, wake_root: Path) -> None:
        self.wake_root = Path(wake_root).resolve()
        self.path = self.wake_root / "http-json" / "sources.json"

    def sources(self) -> tuple[HTTPJSONSourceConfig, ...]:
        if not self.path.exists():
            return ()
        try:
            meta = self.path.lstat()
            if (
                self.path.is_symlink()
                or not self.path.is_file()
                or meta.st_size > 262_144
                or meta.st_uid != os.geteuid()
                or meta.st_mode & 0o077
            ):
                raise ValueError
            payload = json.loads(self.path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
            if type(payload) is not dict or set(payload) != {"schema_version", "sources"}:
                raise ValueError
            rows = payload["sources"]
            if payload["schema_version"] != 1 or type(rows) is not list or len(rows) > 64:
                raise ValueError
            sources = tuple(_decode(row) for row in rows)
            if tuple(item.source_instance for item in sources) != tuple(sorted(item.source_instance for item in sources)):
                raise ValueError
            if len({item.source_instance for item in sources}) != len(sources):
                raise ValueError
            return sources
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("HTTP JSON source configuration is invalid") from None

    def select(self, source_instance: str) -> HTTPJSONSourceConfig:
        selected = next((item for item in self.sources() if item.source_instance == source_instance), None)
        if selected is None or not selected.enabled:
            raise ValueError("HTTP JSON source is not enabled")
        return selected

    def configure(self, source: HTTPJSONSourceConfig) -> HTTPJSONSourceConfig:
        if type(source) is not HTTPJSONSourceConfig:
            raise ValueError("HTTP JSON source configuration is invalid")
        selected = {item.source_instance: item for item in self.sources()}
        existing = selected.get(source.source_instance)
        if existing is not None and existing != source:
            old = _encode(existing)
            new = _encode(source)
            old.pop("enabled")
            new.pop("enabled")
            if old != new:
                raise ValueError("material HTTP JSON source changes require a new source_instance")
        selected[source.source_instance] = source
        self._write(tuple(sorted(selected.values(), key=lambda item: item.source_instance)))
        return source

    def remove(self, source_instance: str) -> bool:
        selected = {item.source_instance: item for item in self.sources()}
        if source_instance not in selected:
            return False
        del selected[source_instance]
        self._write(tuple(sorted(selected.values(), key=lambda item: item.source_instance)))
        return True

    def _write(self, sources: tuple[HTTPJSONSourceConfig, ...]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.parent.is_symlink():
            raise ValueError("HTTP JSON source configuration is invalid")
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent, prefix=".sources-", delete=False
            ) as handle:
                temp_path = Path(handle.name)
                os.chmod(temp_path, 0o600)
                json.dump(
                    {"schema_version": 1, "sources": [_encode(item) for item in sources]},
                    handle,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
            os.chmod(self.path, 0o600)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()


def _encode(source: HTTPJSONSourceConfig) -> dict[str, object]:
    return {
        "source_instance": source.source_instance,
        "url": source.url,
        "state_pointer": source.state_pointer,
        "event_id_pointer": source.event_id_pointer,
        "terminal_values": sorted(source.terminal_values),
        "selectors": [[pointer, value] for pointer, value in source.selectors],
        "completed_at_pointer": source.completed_at_pointer,
        "credential_ref": source.credential_ref,
        "allow_non_loopback": source.allow_non_loopback,
        "enabled": source.enabled,
        "request_timeout_seconds": source.request_timeout_seconds,
        "max_response_bytes": source.max_response_bytes,
    }


def _decode(value: object) -> HTTPJSONSourceConfig:
    if type(value) is not dict or set(value) != set(_FIELDS):
        raise ValueError
    data = dict(value)
    terminal_values = data["terminal_values"]
    selectors = data["selectors"]
    if type(terminal_values) is not list or any(type(item) is not str for item in terminal_values):
        raise ValueError
    if type(selectors) is not list or any(
        type(item) is not list or len(item) != 2 or any(type(part) is not str for part in item)
        for item in selectors
    ):
        raise ValueError
    data["terminal_values"] = frozenset(terminal_values)
    data["selectors"] = tuple((item[0], item[1]) for item in selectors)
    return HTTPJSONSourceConfig(**data)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result
