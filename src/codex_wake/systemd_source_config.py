"""Durable, exact configuration for read-only user-systemd signals.

This module deliberately stores no bus address, command, credential, or
method/property selector.  The adapter receives its fixed read boundary by
dependency injection; configuration only chooses a canonical unit and the
small target-state vocabulary supported by ``runtime_signals``.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .runtime_signals import RuntimeSourceDescriptor


_SOURCE_FIELDS = (
    "source_instance", "unit", "owner_uid", "target_states", "enabled",
    "poll_timeout_seconds",
)
_TARGET_STATES = frozenset({"active", "inactive", "failed"})
_INSTANCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")


@dataclass(frozen=True, slots=True)
class SystemdSourceConfig:
    source_instance: str
    unit: str
    owner_uid: int
    target_states: frozenset[str]
    enabled: bool = True
    poll_timeout_seconds: int = 5

    def __post_init__(self) -> None:
        if not _valid_config(self):
            raise ValueError("systemd source configuration is invalid")

    def descriptor(self, target_state: str) -> RuntimeSourceDescriptor:
        if type(target_state) is not str or target_state not in self.target_states:
            raise ValueError("systemd target state is not configured")
        return RuntimeSourceDescriptor(
            1,
            "systemd.unit",
            {"manager": "user", "owner_uid": self.owner_uid, "unit": self.unit},
            target_state,
        )


class SystemdSourceRegistry:
    """An exact, bounded operator allowlist; disabled entries never select."""

    def __init__(self, sources: tuple[SystemdSourceConfig, ...]) -> None:
        if type(sources) is not tuple or len(sources) > 64:
            raise ValueError("systemd source registry is invalid")
        selected: dict[str, SystemdSourceConfig] = {}
        for source in sources:
            if type(source) is not SystemdSourceConfig or source.source_instance in selected:
                raise ValueError("systemd source registry is invalid")
            selected[source.source_instance] = source
        self._sources = MappingProxyType(selected)

    def select(self, source_instance: str) -> SystemdSourceConfig:
        source = self._sources.get(source_instance) if type(source_instance) is str else None
        if source is None or not source.enabled:
            raise ValueError("systemd source is not enabled")
        return source

    def enabled_sources(self) -> tuple[SystemdSourceConfig, ...]:
        return tuple(source for source in self._sources.values() if source.enabled)


class SystemdSourceStore:
    """Own bounded, nonsecret source selection below a wake root."""

    def __init__(self, wake_root: Path) -> None:
        self.wake_root = Path(wake_root).resolve()
        self.path = self.wake_root / "systemd" / "sources.json"

    def sources(self) -> tuple[SystemdSourceConfig, ...]:
        if self.path.is_symlink():
            raise ValueError("systemd source configuration is invalid")
        if not self.path.exists():
            return ()
        try:
            metadata = self.path.stat()
            if (self.path.is_symlink() or not self.path.is_file() or metadata.st_size > 262_144
                    or metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077):
                raise ValueError
            payload = json.loads(self.path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
            if type(payload) is not dict or set(payload) != {"schema_version", "sources"}:
                raise ValueError
            rows = payload["sources"]
            if payload["schema_version"] != 1 or type(rows) is not list or len(rows) > 64:
                raise ValueError
            sources = tuple(_decode_source(row) for row in rows)
            SystemdSourceRegistry(sources)
            if tuple(source.source_instance for source in sources) != tuple(sorted(source.source_instance for source in sources)):
                raise ValueError
            return sources
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("systemd source configuration is invalid") from None

    def registry(self) -> SystemdSourceRegistry:
        return SystemdSourceRegistry(self.sources())

    def configure(self, source: SystemdSourceConfig) -> SystemdSourceConfig:
        SystemdSourceRegistry((source,))
        selected = {item.source_instance: item for item in self.sources()}
        existing = selected.get(source.source_instance)
        if existing == source:
            return source
        if existing is not None:
            prior = _encode_source(existing)
            requested = _encode_source(source)
            prior.pop("enabled")
            requested.pop("enabled")
            if prior != requested:
                raise ValueError("material systemd source changes require a new source_instance")
        selected[source.source_instance] = source
        configured = tuple(sorted(selected.values(), key=lambda item: item.source_instance))
        SystemdSourceRegistry(configured)
        _atomic_write_json(self.path, {"schema_version": 1, "sources": [_encode_source(item) for item in configured]})
        return source


def _valid_config(config: object) -> bool:
    try:
        if type(config) is not SystemdSourceConfig:
            return False
        if (_INSTANCE.fullmatch(config.source_instance) is None or type(config.unit) is not str
                or type(config.owner_uid) is not int or isinstance(config.owner_uid, bool)
                or type(config.target_states) is not frozenset or not config.target_states
                or not config.target_states <= _TARGET_STATES or not all(type(state) is str for state in config.target_states)
                or type(config.enabled) is not bool or type(config.poll_timeout_seconds) is not int
                or isinstance(config.poll_timeout_seconds, bool) or not 1 <= config.poll_timeout_seconds <= 60):
            return False
        for state in config.target_states:
            config.descriptor(state)
        return True
    except (TypeError, ValueError):
        return False


def _encode_source(source: SystemdSourceConfig) -> dict[str, object]:
    return {
        "source_instance": source.source_instance,
        "unit": source.unit,
        "owner_uid": source.owner_uid,
        "target_states": sorted(source.target_states),
        "enabled": source.enabled,
        "poll_timeout_seconds": source.poll_timeout_seconds,
    }


def _decode_source(payload: object) -> SystemdSourceConfig:
    if type(payload) is not dict or set(payload) != set(_SOURCE_FIELDS):
        raise ValueError
    values = dict(payload)
    target_states = values["target_states"]
    if type(target_states) is not list or not target_states or any(type(state) is not str for state in target_states):
        raise ValueError
    values["target_states"] = frozenset(target_states)
    return SystemdSourceConfig(**values)


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise ValueError("systemd source configuration is invalid")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".sources-", delete=False) as handle:
            temporary = Path(handle.name)
            os.chmod(temporary, 0o600)
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except ValueError:
        raise
    except OSError:
        raise ValueError("systemd source configuration is unavailable") from None
    finally:
        if temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


def _unique_object(pairs: object) -> dict[object, object]:
    result: dict[object, object] = {}
    for key, value in pairs:  # type: ignore[union-attr]
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result
