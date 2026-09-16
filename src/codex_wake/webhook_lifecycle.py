"""Owner-scoped lifecycle configuration for the GitHub webhook listener.

This module deliberately owns only nonsecret listener configuration.  Secret
references are names resolved by the executable at run time; values never
enter this store, its summaries, or rendered systemd units.
"""
from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from ipaddress import ip_address
from dataclasses import dataclass
from pathlib import Path

from .executables import resolve_stable_executable
from .records import WakeError
from .service import systemctl, systemd_environment_assignment, systemd_quote, user_state_dir, user_systemd_dir
from .signal_records import signal_journal_path


_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
_ENV = re.compile(r"[A-Z][A-Z0-9_]{0,127}")
_FIELDS = (
    "source_instance", "address", "port", "path", "secret_ref",
    "previous_secret_ref", "enabled", "allow_non_loopback", "max_body_bytes", "max_connections",
    "request_timeout_seconds", "shutdown_timeout_seconds",
)


@dataclass(frozen=True, slots=True)
class WebhookListenerConfig:
    source_instance: str
    address: str = "127.0.0.1"
    port: int = 8820
    path: str = "/github/webhook"
    secret_ref: str = ""
    previous_secret_ref: str | None = None
    enabled: bool = False
    allow_non_loopback: bool = False
    max_body_bytes: int = 262_144
    max_connections: int = 8
    request_timeout_seconds: float = 15.0
    shutdown_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
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
            or type(self.enabled) is not bool
            or type(self.allow_non_loopback) is not bool
            or type(self.max_body_bytes) is not int or not 1 <= self.max_body_bytes <= 1_048_576
            or type(self.max_connections) is not int or not 1 <= self.max_connections <= 256
            or type(self.request_timeout_seconds) not in {int, float}
            or not 0 < self.request_timeout_seconds <= 60
            or type(self.shutdown_timeout_seconds) not in {int, float}
            or not 0 < self.shutdown_timeout_seconds <= 60
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

    def __init__(self, wake_root: Path):
        self.wake_root = Path(wake_root).resolve()
        self.path = self.wake_root / "github" / "webhook-listeners.json"

    def listeners(self) -> tuple[WebhookListenerConfig, ...]:
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
            if payload["schema_version"] != 1 or type(rows) is not list or len(rows) > 16:
                raise ValueError
            listeners = tuple(_decode(row) for row in rows)
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
        selected = {item.source_instance: item for item in self.listeners()}
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
        _atomic_write(self.path, {"schema_version": 1, "listeners": [_encode(item) for item in sorted(selected.values(), key=lambda item: item.source_instance)]})
        return listener

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
        "max_body_bytes": listener.max_body_bytes,
        "allow_non_loopback": listener.allow_non_loopback,
        "max_connections": listener.max_connections,
        "request_timeout_seconds": listener.request_timeout_seconds,
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


def _decode(payload: object) -> WebhookListenerConfig:
    if type(payload) is not dict or set(payload) != set(_FIELDS):
        raise ValueError
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


def webhook_service_name(source_instance: str) -> str:
    if _NAME.fullmatch(source_instance) is None:
        raise WakeError("webhook listener source is invalid")
    return f"codex-wake-github-webhook-{source_instance}.service"


def build_webhook_service_config(
    *, wake_root: Path, source_instance: str, name: str | None = None,
    executable_path: str | None = None, unit_dir: Path | None = None,
    log_path: Path | None = None, validate_executable: bool = True,
) -> WebhookServiceConfig:
    listener = WebhookListenerStore(wake_root).select(source_instance)
    resolved_name = name or webhook_service_name(listener.source_instance)
    if not resolved_name.endswith(".service"):
        resolved_name += ".service"
    if "/" in resolved_name:
        raise WakeError("webhook listener service name must not contain '/'")
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
    )


def render_webhook_unit(config: WebhookServiceConfig) -> str:
    if config.executable_path is None:
        raise WakeError("GitHub webhook listener executable must be resolved before rendering")
    # Config is read from the owner wake root.  No secret ref/value is copied to
    # the unit; the executable resolves configured names from its environment.
    return (
        "[Unit]\n"
        "Description=Codex Wake GitHub webhook listener for one source\n"
        "Documentation=https://github.com/CochranResearchGroup/codex-wake\n"
        "After=default.target\n"
        f"ConditionPathIsDirectory={config.wake_root}\n\n"
        "[Service]\nType=simple\n"
        f"Environment={systemd_environment_assignment('CODEX_WAKE_WEBHOOK_CONFIG', str(config.wake_root / 'github' / 'webhook-listeners.json'))}\n"
        f"ExecStart={systemd_quote(config.executable_path)} --wake-root {systemd_quote(config.wake_root)} --source {config.source_instance}\n"
        "Restart=on-failure\nRestartSec=5\nTimeoutStopSec=15\n"
        "NoNewPrivileges=yes\nPrivateTmp=yes\n"
        f"StandardOutput=append:{config.log_path}\nStandardError=append:{config.log_path}\n\n"
        "[Install]\nWantedBy=default.target\n"
    )


def install_webhook_service(config: WebhookServiceConfig, runner=None, *, start: bool = True) -> None:
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
        systemctl(["enable", "--now", config.name], runner)
        active = systemctl(["is-active", config.name], runner, check=False).stdout.strip()
        if active != "active":
            raise WakeError(f"webhook listener service did not become active: {config.name} ({active or 'unknown'})")


def stop_webhook_service(config: WebhookServiceConfig, runner=None) -> None:
    systemctl(["disable", "--now", config.name], runner, check=False)


def uninstall_webhook_service(config: WebhookServiceConfig, runner=None) -> None:
    stop_webhook_service(config, runner)
    config.unit_path.unlink(missing_ok=True)
    systemctl(["daemon-reload"], runner)


def webhook_service_status(config: WebhookServiceConfig, runner=None) -> tuple[str, str]:
    active = systemctl(["is-active", config.name], runner, check=False).stdout.strip() or "unknown"
    enabled = systemctl(["is-enabled", config.name], runner, check=False).stdout.strip() or "unknown"
    return active, enabled


def _journal_is_safe(path: Path) -> bool:
    try:
        metadata = path.stat()
        return (path.is_file() and not path.is_symlink() and metadata.st_uid == os.getuid()
                and not stat.S_IMODE(metadata.st_mode) & 0o077)
    except OSError:
        return False


def _unit_is_safe(config: WebhookServiceConfig) -> bool:
    try:
        metadata = config.unit_path.stat()
        if (not config.unit_path.is_file() or config.unit_path.is_symlink()
                or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077):
            return False
        text = config.unit_path.read_text(encoding="utf-8")
        return (f"--wake-root {systemd_quote(config.wake_root)} --source {config.source_instance}" in text
                and "Restart=on-failure" in text and "TimeoutStopSec=15" in text)
    except OSError:
        return False


def webhook_readiness(*, wake_root: Path, source_instance: str, runner=None,
                      bind_probe=None, journal_probe=None, runtime_available: bool | None = None) -> dict[str, object]:
    """Read nonsecret local ownership state; never contacts GitHub or dispatches."""
    try:
        listener = WebhookListenerStore(wake_root).enabled(source_instance)
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
    # There is deliberately no ambient socket inspection: it cannot prove the
    # service owns the expected socket. A platform owner probe is injected by
    # the installed qualification layer; absent proof fails closed.
    bind_ok = bind_probe(listener.address, listener.port) if bind_probe is not None else False
    status = "ready" if unit_ok and active == "active" and runtime_available and journal_ok and bind_ok else "blocked"
    if not runtime_available:
        message = "canonical #105 webhook runtime is unavailable"
    elif not unit_ok or active != "active":
        message = "webhook listener service is not locally active and owned"
    elif not bind_ok:
        message = "webhook listener bind ownership is unproven"
    elif not journal_ok:
        message = "webhook listener journal is inaccessible or unsafe"
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
        "provider_delivery": "unproven", "dispatch": "not_included",
    }


def webhook_support(*, wake_root: Path, source_instance: str, runner=None,
                    bind_probe=None, journal_probe=None, runtime_available: bool | None = None) -> dict[str, object]:
    readiness = webhook_readiness(wake_root=wake_root, source_instance=source_instance, runner=runner,
                                  bind_probe=bind_probe, journal_probe=journal_probe,
                                  runtime_available=runtime_available)
    # Do not include even opaque reference names in portable support output.
    return {"webhook_listener": readiness, "repair": "configure an enabled listener, install its user service, then join canonical #105 before runtime qualification"}
