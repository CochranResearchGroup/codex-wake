"""Owner-scoped lifecycle configuration for the GitHub webhook listener.

This module deliberately owns only nonsecret listener configuration.  Secret
references are names resolved by the executable at run time; values never
enter this store, its summaries, or rendered systemd units.
"""
from __future__ import annotations

import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from ipaddress import ip_address
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import tempfile
import threading

from .executables import resolve_stable_executable
from .records import WakeError
from .service import _systemd_environment_file_path, systemctl, systemd_quote, user_state_dir, user_systemd_dir
from .signal_records import signal_journal_path
from .signal_store import JOURNAL_APPLICATION_ID, JOURNAL_SCHEMA_VERSION
from .managed_webhook_rotation import (
    ManagedWebhookRotationStore, PendingEffect, RotationPhase, RotationRecord,
)
from .managed_webhooks import ManagedWebhookBinding, ManagedWebhookStore


_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
_ENV = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_FIELDS = (
    "source_instance", "address", "port", "path", "secret_ref",
    "previous_secret_ref", "current_generation", "previous_generation",
    "enabled", "allow_non_loopback", "max_body_bytes", "max_connections",
    "request_timeout_seconds", "operation_timeout_seconds", "shutdown_timeout_seconds",
)
_V1_FIELDS = tuple(field for field in _FIELDS if field not in {"current_generation", "previous_generation"})
_MAX_GENERATION = 2**31 - 1


@dataclass(frozen=True, slots=True)
class WebhookListenerConfig:
    source_instance: str
    address: str = "127.0.0.1"
    port: int = 8820
    path: str = "/github/webhook"
    secret_ref: str = ""
    previous_secret_ref: str | None = None
    current_generation: int = 1
    previous_generation: int | None = None
    enabled: bool = False
    allow_non_loopback: bool = False
    max_body_bytes: int = 262_144
    max_connections: int = 8
    request_timeout_seconds: float = 15.0
    operation_timeout_seconds: float = 8.0
    shutdown_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        # Preserve the public v1 constructor shape while assigning the same
        # deterministic generations used when decoding a persisted v1 row.
        if self.previous_secret_ref is not None and self.current_generation == 1 and self.previous_generation is None:
            object.__setattr__(self, "current_generation", 2)
            object.__setattr__(self, "previous_generation", 1)
        if (
            type(self.source_instance) is not str or _NAME.fullmatch(self.source_instance) is None
            or type(self.address) is not str or not _valid_address(self.address, self.allow_non_loopback)
            or type(self.port) is not int or not 1 <= self.port <= 65535
            or self.path != "/github/webhook"
            or type(self.secret_ref) is not str or _ENV.fullmatch(self.secret_ref) is None
            or self.previous_secret_ref is not None and (
                type(self.previous_secret_ref) is not str
                or _ENV.fullmatch(self.previous_secret_ref) is None
                or self.previous_secret_ref == self.secret_ref
            )
            or type(self.current_generation) is not int
            or not 1 <= self.current_generation <= _MAX_GENERATION
            or self.previous_generation is not None and (
                type(self.previous_generation) is not int
                or not 1 <= self.previous_generation < self.current_generation
            )
            or (self.previous_secret_ref is None) != (self.previous_generation is None)
            or type(self.enabled) is not bool
            or type(self.allow_non_loopback) is not bool
            or type(self.max_body_bytes) is not int or not 1_024 <= self.max_body_bytes <= 1_048_576
            or type(self.max_connections) is not int or not 1 <= self.max_connections <= 256
            or type(self.request_timeout_seconds) not in {int, float}
            or not 0 < self.request_timeout_seconds <= 60
            or type(self.shutdown_timeout_seconds) not in {int, float}
            or not 0 < self.shutdown_timeout_seconds <= 60
            or type(self.operation_timeout_seconds) not in {int, float}
            or not 0 < self.operation_timeout_seconds <= min(
                self.request_timeout_seconds, self.shutdown_timeout_seconds
            )
        ):
            raise ValueError("webhook listener configuration is invalid")


def _valid_address(value: str, allow_non_loopback: bool) -> bool:
    """Allow only a concrete IP; wildcard exposure stays unsupported."""
    try:
        address = ip_address(value)
    except ValueError:
        return False
    return not address.is_unspecified and (address.is_loopback or allow_non_loopback)


class WebhookListenerStore:
    """One immutable listener authority set below one owner wake root."""

    _thread_locks: dict[str, threading.RLock] = {}
    _thread_locks_guard = threading.Lock()

    def __init__(self, wake_root: Path):
        self.wake_root = Path(wake_root).resolve()
        self.path = self.wake_root / "github" / "webhook-listeners.json"
        self._lock_path = self.wake_root / "github" / ".webhook-listeners.lock"

    @contextmanager
    def locked(self) -> Iterator[None]:
        key = str(self._lock_path)
        with self._thread_locks_guard:
            lock = self._thread_locks.setdefault(key, threading.RLock())
        with lock:
            handle = None
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                parent_meta = self.path.parent.lstat()
                if (
                    self.path.parent.is_symlink() or not stat.S_ISDIR(parent_meta.st_mode)
                    or parent_meta.st_uid != os.getuid()
                ):
                    raise ValueError("webhook listener configuration is unavailable")
                os.chmod(self.path.parent, 0o700)
                descriptor = os.open(
                    self._lock_path,
                    os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                )
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
                    os.close(descriptor)
                    raise ValueError("webhook listener configuration is unavailable")
                os.fchmod(descriptor, 0o600)
                handle = os.fdopen(descriptor, "a+", encoding="utf-8")
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                yield
            except OSError:
                raise ValueError("webhook listener configuration is unavailable") from None
            finally:
                if handle is not None:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    finally:
                        handle.close()

    def listeners(self) -> tuple[WebhookListenerConfig, ...]:
        with self.locked():
            return self._listeners_unlocked()

    def _listeners_unlocked(self) -> tuple[WebhookListenerConfig, ...]:
        if self.path.is_symlink():
            raise ValueError("webhook listener configuration is invalid")
        if not self.path.exists():
            return ()
        try:
            metadata = self.path.stat()
            if (self.path.is_symlink() or not self.path.is_file() or metadata.st_size > 131_072
                    or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077):
                raise ValueError
            payload = json.loads(self.path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
            if type(payload) is not dict or set(payload) != {"schema_version", "listeners"}:
                raise ValueError
            rows = payload["listeners"]
            schema_version = payload["schema_version"]
            if schema_version not in {1, 2} or type(rows) is not list or len(rows) > 16:
                raise ValueError
            listeners = tuple(_decode(row, schema_version=schema_version) for row in rows)
            if tuple(item.source_instance for item in listeners) != tuple(sorted(item.source_instance for item in listeners)):
                raise ValueError
            if len({item.source_instance for item in listeners}) != len(listeners):
                raise ValueError
            return listeners
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("webhook listener configuration is invalid") from None

    def select(self, source_instance: str) -> WebhookListenerConfig:
        for listener in self.listeners():
            if listener.source_instance == source_instance:
                return listener
        raise ValueError("webhook listener is not configured")

    def configure(self, listener: WebhookListenerConfig) -> WebhookListenerConfig:
        if type(listener) is not WebhookListenerConfig:
            raise ValueError("webhook listener configuration is invalid")
        with self.locked():
            if listener.enabled:
                from .managed_webhook_cleanup import ManagedWebhookCleanupStore
                cleanup_store = ManagedWebhookCleanupStore(self.wake_root)
                with cleanup_store.locked():
                    if any(
                        item.source_instance == listener.source_instance
                        for item in cleanup_store._records_unlocked()
                    ):
                        raise ValueError("webhook listener enable is blocked while cleanup authority exists")
            selected = {item.source_instance: item for item in self._listeners_unlocked()}
            current = selected.get(listener.source_instance)
            if current == listener:
                return listener
            if current is not None:
                before, after = _encode(current), _encode(listener)
                before.pop("enabled")
                after.pop("enabled")
                if before != after:
                    raise ValueError("material webhook listener changes require a new source_instance")
            selected[listener.source_instance] = listener
            self._write_unlocked(selected)
            return listener

    def transition_rotation_secrets(
        self,
        *,
        expected: WebhookListenerConfig,
        replacement: WebhookListenerConfig,
        rotation: RotationRecord,
        binding: ManagedWebhookBinding,
    ) -> WebhookListenerConfig:
        """Apply one intent-bound secret-reference transition under an exact CAS."""
        if not all(type(value) is expected_type for value, expected_type in (
            (expected, WebhookListenerConfig), (replacement, WebhookListenerConfig),
            (rotation, RotationRecord), (binding, ManagedWebhookBinding),
        )):
            raise ValueError("webhook listener rotation authority is invalid")
        self._validate_rotation_authority(expected, replacement, rotation, binding)
        rotation_store = ManagedWebhookRotationStore(self.wake_root)
        binding_store = ManagedWebhookStore(self.wake_root)
        # Freeze all three authorities in one fixed lock order.  This prevents
        # a rollback or binding revision from landing between validation and
        # the listener CAS even though the stores remain separately durable.
        with rotation_store.locked():
            with binding_store.locked():
                with self.locked():
                    if rotation_store._load_unlocked(rotation.owner_id) != rotation:
                        raise ValueError("webhook listener rotation authority is stale")
                    if binding_store._load_unlocked(binding.owner_id) != binding:
                        raise ValueError("webhook listener binding authority is stale")
                    selected = {item.source_instance: item for item in self._listeners_unlocked()}
                    if selected.get(expected.source_instance) != expected:
                        raise ValueError("webhook listener rotation preimage is stale")
                    selected[replacement.source_instance] = replacement
                    self._write_unlocked(selected)
        return replacement

    def _validate_rotation_authority(
        self,
        expected: WebhookListenerConfig,
        replacement: WebhookListenerConfig,
        rotation: RotationRecord,
        binding: ManagedWebhookBinding,
    ) -> None:
        source = expected.source_instance
        if (
            replacement.source_instance != source
            or rotation.owner_id != binding.owner_id
            or not (rotation.canonical_root == binding.canonical_root == str(self.wake_root))
            or rotation.owner_uid != binding.owner_uid
            or rotation.owner_uid != os.getuid()
            or rotation.source_instance != binding.source_instance
            or rotation.source_instance != source
            or rotation.service_id != binding.service_id
            or rotation.service_id != webhook_service_name(source)
            or rotation.binding_revision != binding.generation
            or rotation.previous_generation != binding.secret_generation
        ):
            raise ValueError("webhook listener rotation authority is invalid")
        before, after = _encode(expected), _encode(replacement)
        for field in ("secret_ref", "previous_secret_ref", "current_generation", "previous_generation"):
            before.pop(field)
            after.pop(field)
        if before != after:
            raise ValueError("webhook listener rotation changes unrelated configuration")
        if rotation.phase is RotationPhase.PREPARED and rotation.pending_effect is PendingEffect.RESTART_DUAL:
            valid = (
                expected.current_generation == rotation.previous_generation
                and expected.previous_generation is None
                and replacement.current_generation == rotation.target_generation
                and replacement.previous_generation == rotation.previous_generation
                and replacement.previous_secret_ref == expected.secret_ref
                and replacement.secret_ref != expected.secret_ref
            )
        elif (
            rotation.phase is RotationPhase.AWAITING_DELIVERY
            and rotation.pending_effect is PendingEffect.RESTART_TARGET_ONLY
        ):
            valid = (
                expected.current_generation == rotation.target_generation
                and expected.previous_generation == rotation.previous_generation
                and replacement.current_generation == rotation.target_generation
                and replacement.previous_generation is None
                and replacement.secret_ref == expected.secret_ref
                and replacement.previous_secret_ref is None
            )
        else:
            raise ValueError("webhook listener rotation phase is invalid")
        if not valid:
            raise ValueError("webhook listener rotation shape is invalid")

    def _write_unlocked(self, selected: dict[str, WebhookListenerConfig]) -> None:
        _atomic_write(self.path, {
            "schema_version": 2,
            "listeners": [_encode(item) for item in sorted(selected.values(), key=lambda item: item.source_instance)],
        })

    def enabled(self, source_instance: str) -> WebhookListenerConfig:
        listener = self.select(source_instance)
        if not listener.enabled:
            raise ValueError("webhook listener is not enabled")
        return listener


def listener_summary(listener: WebhookListenerConfig, *, include_references: bool = True) -> dict[str, object]:
    result: dict[str, object] = {
        "source_instance": listener.source_instance,
        "address": listener.address,
        "port": listener.port,
        "path": listener.path,
        "enabled": listener.enabled,
        "current_generation": listener.current_generation,
        "previous_generation": listener.previous_generation,
        "max_body_bytes": listener.max_body_bytes,
        "allow_non_loopback": listener.allow_non_loopback,
        "max_connections": listener.max_connections,
        "request_timeout_seconds": listener.request_timeout_seconds,
        "operation_timeout_seconds": listener.operation_timeout_seconds,
        "shutdown_timeout_seconds": listener.shutdown_timeout_seconds,
    }
    if include_references:
        result["secret_ref"] = listener.secret_ref
        result["previous_secret_ref"] = listener.previous_secret_ref
    return result


def webhook_http_config_kwargs(listener: WebhookListenerConfig) -> dict[str, object]:
    """The narrow #105 transport construction packet; worker/queue are fixed."""
    return {
        "host": listener.address,
        "port": listener.port,
        "path": listener.path,
        "max_body_bytes": listener.max_body_bytes,
        "max_connections": listener.max_connections,
        "max_workers": 1,
        "request_timeout": listener.request_timeout_seconds,
        "shutdown_timeout": listener.shutdown_timeout_seconds,
        "allow_non_loopback": listener.allow_non_loopback,
    }


def _encode(listener: WebhookListenerConfig) -> dict[str, object]:
    return {field: getattr(listener, field) for field in _FIELDS}


def _decode(payload: object, *, schema_version: int) -> WebhookListenerConfig:
    fields = _V1_FIELDS if schema_version == 1 else _FIELDS
    if type(payload) is not dict or set(payload) != set(fields):
        raise ValueError
    if schema_version == 1:
        previous = payload["previous_secret_ref"]
        payload = dict(payload)
        payload["current_generation"] = 1 if previous is None else 2
        payload["previous_generation"] = None if previous is None else 1
    return WebhookListenerConfig(**payload)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _atomic_write(path: Path, payload: dict[str, object]) -> None:
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise ValueError
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".webhook-", delete=False) as handle:
            temporary = Path(handle.name)
            os.chmod(temporary, 0o600)
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except OSError:
        raise ValueError("webhook listener configuration is unavailable") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@dataclass(frozen=True, slots=True)
class WebhookServiceConfig:
    name: str
    wake_root: Path
    source_instance: str
    executable_path: Path | None
    unit_path: Path
    log_path: Path
    source_enabled: bool = True


def webhook_service_name(source_instance: str) -> str:
    if _NAME.fullmatch(source_instance) is None:
        raise WakeError("webhook listener source is invalid")
    return f"codex-wake-github-webhook-{source_instance}.service"


def webhook_secret_environment_path(wake_root: Path) -> Path:
    return Path(wake_root).resolve() / "github" / "webhook.env"


def build_webhook_service_config(
    *, wake_root: Path, source_instance: str, name: str | None = None,
    executable_path: str | None = None, unit_dir: Path | None = None,
    log_path: Path | None = None, validate_executable: bool = True,
) -> WebhookServiceConfig:
    if name is not None:
        raise WakeError("webhook listener service name is fixed by source ownership")
    listener = WebhookListenerStore(wake_root).select(source_instance)
    resolved_name = webhook_service_name(listener.source_instance)
    executable = None
    if validate_executable:
        executable = Path(resolve_stable_executable(
            executable_path, default_command="codex-wake-github-webhook",
            label="GitHub webhook listener", reject_node_versioned=True,
        ))
    unit_base = (unit_dir or user_systemd_dir()).expanduser()
    state_base = user_state_dir()
    return WebhookServiceConfig(
        name=resolved_name, wake_root=Path(wake_root).resolve(),
        source_instance=listener.source_instance, executable_path=executable,
        unit_path=unit_base / resolved_name,
        log_path=(log_path or state_base / f"{resolved_name.removesuffix('.service')}.log").expanduser(),
        source_enabled=listener.enabled,
    )


def render_webhook_unit(config: WebhookServiceConfig) -> str:
    if config.executable_path is None:
        raise WakeError("GitHub webhook listener executable must be resolved before rendering")
    # The owner-only environment file carries values for configured references.
    # Its path is nonsecret; no reference name or secret value enters the unit.
    environment_file = _systemd_environment_file_path(
        webhook_secret_environment_path(config.wake_root)
    )
    return (
        "[Unit]\n"
        "Description=Codex Wake GitHub webhook listener for one source\n"
        "Documentation=https://github.com/CochranResearchGroup/codex-wake\n"
        "After=default.target\n"
        f"ConditionPathIsDirectory={config.wake_root}\n\n"
        "[Service]\nType=simple\n"
        f"EnvironmentFile={environment_file}\n"
        f"ExecStart={systemd_quote(config.executable_path)} --wake-root {systemd_quote(config.wake_root)} --source {config.source_instance}\n"
        "Restart=on-failure\nRestartSec=5\nTimeoutStopSec=15\n"
        "NoNewPrivileges=yes\nPrivateTmp=yes\n"
        f"StandardOutput=append:{config.log_path}\nStandardError=append:{config.log_path}\n\n"
        "[Install]\nWantedBy=default.target\n"
    )


def install_webhook_service(config: WebhookServiceConfig, runner=None, *, start: bool = True) -> None:
    if not config.source_enabled:
        raise WakeError("webhook listener service requires an enabled source")
    _require_secret_environment(config)
    rendered = render_webhook_unit(config)
    if config.unit_path.exists():
        try:
            metadata = config.unit_path.lstat()
            if (config.unit_path.is_symlink() or not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077
                    or config.unit_path.read_text(encoding="utf-8") != rendered):
                raise WakeError("webhook listener service ownership is invalid")
        except OSError:
            raise WakeError("webhook listener service ownership is invalid") from None
    config.unit_path.parent.mkdir(parents=True, exist_ok=True)
    config.log_path.parent.mkdir(parents=True, exist_ok=True)
    config.unit_path.write_text(rendered, encoding="utf-8")
    os.chmod(config.unit_path, 0o600)
    systemctl(["daemon-reload"], runner)
    if start:
        start_webhook_service(config, runner)


def start_webhook_service(config: WebhookServiceConfig, runner=None) -> None:
    if not config.source_enabled:
        raise WakeError("webhook listener service requires an enabled source")
    _require_secret_environment(config)
    _require_owned_unit(config)
    systemctl(["enable", "--now", config.name], runner)
    active, enabled = webhook_service_status(config, runner)
    if (active, enabled) != ("active", "enabled"):
        raise WakeError(f"webhook listener service did not become active and enabled: {config.name} ({active}, {enabled})")


def stop_webhook_service(config: WebhookServiceConfig, runner=None) -> None:
    _require_owned_unit(config)
    systemctl(["disable", "--now", config.name], runner, check=False)
    active, enabled = webhook_service_status(config, runner)
    if (active, enabled) != ("inactive", "disabled"):
        raise WakeError(f"webhook listener service did not stop and disable: {config.name} ({active}, {enabled})")


def uninstall_webhook_service(config: WebhookServiceConfig, runner=None) -> None:
    stop_webhook_service(config, runner)
    config.unit_path.unlink(missing_ok=True)
    systemctl(["daemon-reload"], runner)


def webhook_service_status(config: WebhookServiceConfig, runner=None) -> tuple[str, str]:
    active = systemctl(["is-active", config.name], runner, check=False).stdout.strip() or "unknown"
    enabled = systemctl(["is-enabled", config.name], runner, check=False).stdout.strip() or "unknown"
    return active, enabled


def disable_webhook_listener(
    store: WebhookListenerStore,
    listener: WebhookListenerConfig,
    runner=None,
    *,
    unit_dir: Path | None = None,
) -> WebhookListenerConfig:
    """Stop the exact active owner before persisting its disabled authority."""
    if listener.enabled:
        raise ValueError("webhook listener disable request is invalid")
    current = store.select(listener.source_instance)
    before, after = _encode(current), _encode(listener)
    before.pop("enabled")
    after.pop("enabled")
    if before != after:
        raise ValueError("material webhook listener changes require a new source_instance")
    config = build_webhook_service_config(
        wake_root=store.wake_root, source_instance=current.source_instance,
        unit_dir=unit_dir, validate_executable=False,
    )
    active, enabled = webhook_service_status(config, runner)
    if (active, enabled) != ("inactive", "disabled"):
        stop_webhook_service(config, runner)
        active, enabled = webhook_service_status(config, runner)
        if (active, enabled) != ("inactive", "disabled"):
            raise WakeError("webhook listener service remains owned; stop it before disabling source")
    return store.configure(listener)


def _journal_is_safe(path: Path) -> bool:
    """Inspect a disposable WAL-aware snapshot without touching the journal."""
    try:
        metadata = path.stat()
        if not (path.is_file() and not path.is_symlink() and metadata.st_uid == os.getuid()
                and not stat.S_IMODE(metadata.st_mode) & 0o077):
            return False
        with tempfile.TemporaryDirectory(prefix="codex-wake-journal-read-") as temporary:
            snapshot = Path(temporary) / path.name
            for suffix in ("", "-wal", "-shm"):
                source = path.with_name(path.name + suffix)
                if not source.exists():
                    continue
                sidecar = source.lstat()
                if (not stat.S_ISREG(sidecar.st_mode) or source.is_symlink()
                        or sidecar.st_uid != os.getuid()
                        or stat.S_IMODE(sidecar.st_mode) & 0o077):
                    return False
                shutil.copyfile(source, snapshot.with_name(snapshot.name + suffix))
            connection = sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True, isolation_level=None)
            try:
                application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
                user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if application_id != JOURNAL_APPLICATION_ID or user_version != JOURNAL_SCHEMA_VERSION:
                    return False
                row = connection.execute(
                    "SELECT schema_version, journal_uuid FROM journal_meta WHERE singleton = 1"
                ).fetchone()
                return row is not None and int(row[0]) == JOURNAL_SCHEMA_VERSION and isinstance(row[1], str) and bool(row[1])
            finally:
                connection.close()
    except (OSError, sqlite3.Error, ValueError):
        return False


def _unit_is_safe(config: WebhookServiceConfig) -> bool:
    try:
        metadata = config.unit_path.stat()
        if (not config.unit_path.is_file() or config.unit_path.is_symlink()
                or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077):
            return False
        text = config.unit_path.read_text(encoding="utf-8")
        return (f"--wake-root {systemd_quote(config.wake_root)} --source {config.source_instance}" in text
                and f"EnvironmentFile={_systemd_environment_file_path(webhook_secret_environment_path(config.wake_root))}" in text
                and "Restart=on-failure" in text and "TimeoutStopSec=15" in text)
    except (OSError, WakeError):
        return False


def _require_owned_unit(config: WebhookServiceConfig) -> None:
    if not _unit_is_safe(config):
        raise WakeError("webhook listener service ownership is invalid")


def _secret_environment_is_safe(config: WebhookServiceConfig) -> bool:
    path = webhook_secret_environment_path(config.wake_root)
    try:
        metadata = path.lstat()
        return (
            stat.S_ISREG(metadata.st_mode)
            and not path.is_symlink()
            and metadata.st_uid == os.getuid()
            and not stat.S_IMODE(metadata.st_mode) & 0o077
            and metadata.st_size <= 16_384
        )
    except OSError:
        return False


def _require_secret_environment(config: WebhookServiceConfig) -> None:
    if not _secret_environment_is_safe(config):
        raise WakeError("webhook listener secret environment file must be an owner-only regular file")


def required_secret_references(listener: WebhookListenerConfig, source) -> frozenset[str]:
    refs = {listener.secret_ref}
    if source.credential_ref != "GH_CLI":
        refs.add(source.credential_ref)
    if listener.previous_secret_ref:
        refs.add(listener.previous_secret_ref)
    return frozenset(refs)


def secret_environment_has_references(config: WebhookServiceConfig, listener: WebhookListenerConfig, source) -> bool:
    if not _secret_environment_is_safe(config):
        return False
    try:
        values = _parse_secret_environment(webhook_secret_environment_path(config.wake_root))
        return all(values.get(reference, "") for reference in required_secret_references(listener, source))
    except (OSError, ValueError):
        return False


def _parse_secret_environment(path: Path) -> dict[str, str]:
    """Accept only unquoted KEY=value lines; all richer systemd syntax is unsafe here."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("unsupported environment syntax")
        key, value = line.split("=", 1)
        if (_ENV.fullmatch(key) is None or key in values or not value
                or value != value.strip() or any(char in value for char in "'\"\\\r\n")):
            raise ValueError("unsupported environment syntax")
        values[key] = value
    return values


def _proc_address(value: str, *, ipv6: bool) -> str:
    packed = ip_address(value).packed
    if not ipv6:
        return packed[::-1].hex().upper()
    return "".join(packed[index:index + 4][::-1].hex() for index in range(0, 16, 4)).upper()


def _service_main_pid(config: WebhookServiceConfig, runner=None) -> int | None:
    try:
        value = systemctl(["show", config.name, "--property=MainPID", "--value"], runner, check=False).stdout.strip()
        return int(value) if value.isdigit() and int(value) > 0 else None
    except Exception:
        return None


def linux_service_bind_probe(
    config: WebhookServiceConfig, runner=None, *, proc_root: Path = Path("/proc"),
    expected_pid: int | None = None,
    listener: WebhookListenerConfig | None = None,
) -> bool:
    """Read-only proof that this unit's MainPID owns the exact listening inode."""
    pid = _service_main_pid(config, runner)
    if pid is None or expected_pid is not None and pid != expected_pid:
        return False
    try:
        selected = listener or WebhookListenerStore(config.wake_root).select(
            config.source_instance
        )
        if selected.source_instance != config.source_instance:
            return False
        inodes = {
            target.removeprefix("socket:[").removesuffix("]")
            for item in (proc_root / str(pid) / "fd").iterdir()
            if (target := os.readlink(item)).startswith("socket:[") and target.endswith("]")
        }
        address = ip_address(selected.address)
        table = "tcp6" if address.version == 6 else "tcp"
        expected = _proc_address(str(address), ipv6=address.version == 6)
        for line in (proc_root / "net" / table).read_text(encoding="utf-8").splitlines()[1:]:
            fields = line.split()
            if len(fields) < 10 or fields[3] != "0A" or fields[9] not in inodes:
                continue
            local = fields[1].split(":", 1)
            if (
                len(local) == 2
                and local[0].upper() == expected
                and int(local[1], 16) == selected.port
            ):
                return True
    except (OSError, ValueError):
        return False
    return False


def webhook_readiness(*, wake_root: Path, source_instance: str, runner=None,
                      bind_probe=None, journal_probe=None, runtime_available: bool | None = None) -> dict[str, object]:
    """Read nonsecret local ownership state; never contacts GitHub or dispatches."""
    try:
        listener = WebhookListenerStore(wake_root).enabled(source_instance)
        from .github_source_config import GitHubSourceStore
        source = GitHubSourceStore(wake_root).registry().select(listener.source_instance)
        config = build_webhook_service_config(
            wake_root=wake_root, source_instance=source_instance, validate_executable=False,
        )
    except (ValueError, WakeError) as exc:
        return {"status": "blocked", "message": str(exc), "provider_delivery": "unproven", "dispatch": "not_included"}
    unit_ok = _unit_is_safe(config)
    try:
        active, enabled = webhook_service_status(config, runner)
    except Exception:
        active, enabled = "unknown", "unknown"
    if runtime_available is None:
        try:
            import importlib.util
            runtime_available = importlib.util.find_spec("codex_wake.github_webhook_runtime") is not None
        except (ImportError, ValueError):
            runtime_available = False
    journal_path = signal_journal_path(wake_root)
    journal_ok = journal_probe(journal_path) if journal_probe is not None else _journal_is_safe(journal_path)
    secret_environment_ok = secret_environment_has_references(config, listener, source)
    bind_ok = bind_probe(listener.address, listener.port) if bind_probe is not None else linux_service_bind_probe(config, runner)
    status = "ready" if unit_ok and active == "active" and runtime_available and journal_ok and bind_ok and secret_environment_ok else "blocked"
    if not runtime_available:
        message = "canonical #105 webhook runtime is unavailable"
    elif not unit_ok or active != "active":
        message = "webhook listener service is not locally active and owned"
    elif not bind_ok:
        message = "webhook listener bind ownership is unproven"
    elif not journal_ok:
        message = "webhook listener journal is inaccessible or unsafe"
    elif not secret_environment_ok:
        message = "webhook listener secret environment file is inaccessible or unsafe"
    else:
        message = "webhook listener ownership is locally ready"
    return {
        "status": status,
        "message": message,
        "source_instance": listener.source_instance, "address": listener.address,
        "port": listener.port, "path": listener.path, "active": active, "enabled": enabled,
        "unit": str(config.unit_path), "runtime_available": runtime_available,
        "bind_ownership": "proven" if bind_ok else "unproven",
        "journal": str(journal_path), "journal_access": "safe" if journal_ok else "unsafe",
        "secret_environment_access": "safe" if secret_environment_ok else "unsafe",
        "provider_delivery": "unproven", "dispatch": "not_included",
    }


def webhook_support(*, wake_root: Path, source_instance: str, runner=None,
                    bind_probe=None, journal_probe=None, runtime_available: bool | None = None) -> dict[str, object]:
    readiness = webhook_readiness(wake_root=wake_root, source_instance=source_instance, runner=runner,
                                  bind_probe=bind_probe, journal_probe=journal_probe,
                                  runtime_available=runtime_available)
    # Do not include even opaque reference names in portable support output.
    return {"webhook_listener": readiness, "repair": "configure an enabled listener, install its user service, then join canonical #105 before runtime qualification"}
