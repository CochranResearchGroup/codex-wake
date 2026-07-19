from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .records import WakeError, format_utc, utc_now
from .service import (
    ServiceConfig,
    build_service_config,
    service_app_server_readiness,
    service_status,
    user_state_dir,
)


DEFAULT_HEALTH_STALE_AFTER_SECONDS = 120


def root_key(wake_root: Path) -> str:
    return hashlib.sha1(str(wake_root.resolve()).encode("utf-8")).hexdigest()[:12]


def monitor_state_dir(state_dir: Path | None = None) -> Path:
    return (state_dir or (user_state_dir() / "monitors")).expanduser()


def monitor_health_path(wake_root: Path, state_dir: Path | None = None) -> Path:
    return monitor_state_dir(state_dir) / f"{root_key(wake_root)}.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)


def write_monitor_health(
    *,
    wake_root: Path,
    source: str,
    mode: str,
    poll_result: dict[str, Any] | None = None,
    repo_root: Path | None = None,
    state_dir: Path | None = None,
    now: datetime | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    current = now or utc_now()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "root_key": root_key(wake_root),
        "wake_root": str(wake_root.resolve()),
        "repo_root": str(repo_root.resolve()) if repo_root else "",
        "source": source,
        "mode": mode,
        "pid": os.getpid(),
        "checked_at": format_utc(current),
        "poll_result": poll_result or {},
    }
    if extra:
        payload.update(extra)
    path = monitor_health_path(wake_root, state_dir)
    _atomic_write_json(path, payload)
    return path


def read_monitor_health(wake_root: Path, state_dir: Path | None = None) -> dict[str, Any] | None:
    path = monitor_health_path(wake_root, state_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    payload.setdefault("path", str(path))
    return payload


def parse_health_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def health_is_recent(
    health: dict[str, Any] | None,
    *,
    stale_after_seconds: int = DEFAULT_HEALTH_STALE_AFTER_SECONDS,
    now: datetime | None = None,
) -> bool:
    if not health:
        return False
    checked_at = parse_health_time(health.get("checked_at"))
    if checked_at is None:
        return False
    current = now or utc_now()
    return (current.astimezone(UTC) - checked_at).total_seconds() <= stale_after_seconds


def parse_unit_exec_start_wake_root(unit_path: Path) -> str:
    if not unit_path.exists():
        return ""
    for raw_line in unit_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("ExecStart="):
            continue
        command_text = stripped.removeprefix("ExecStart=")
        try:
            parts = shlex.split(command_text)
        except ValueError:
            return ""
        for index, part in enumerate(parts):
            if part == "--wake-root" and index + 1 < len(parts):
                return str(Path(parts[index + 1]).expanduser().resolve())
            if part.startswith("--wake-root="):
                return str(Path(part.split("=", 1)[1]).expanduser().resolve())
    return ""


def transport_readiness(config: ServiceConfig) -> dict[str, Any]:
    app_server = service_app_server_readiness(config)
    return {
        "app_server": {
            "codex_cmd_ready": app_server.codex_cmd_ready,
            "codex_cmd_source": app_server.codex_cmd_source,
            "codex_cmd": app_server.codex_cmd,
            "unit_codex_cmd": app_server.unit_codex_cmd,
            "user_manager_codex_cmd": app_server.user_manager_codex_cmd,
            "interactive_codex_cmd": app_server.interactive_codex_cmd,
            "message": app_server.message,
        },
        "openclaw_gateway": {
            "interactive_openclaw_cmd": shutil.which("openclaw") or "",
            "message": "OpenClaw Gateway dispatch can also use target.openclaw_cmd from individual wake records",
        },
        "tmux": {
            "interactive_tmux_cmd": shutil.which("tmux") or "",
            "message": "tmux dispatch also requires a valid target pane and socket in the wake record",
        },
    }


def monitor_readiness(
    *,
    wake_root: Path,
    repo_root: Path | None = None,
    service_name: str | None = None,
    interval: float = 1.0,
    daemon_path: str | None = None,
    codex_path: str | None = None,
    log_path: Path | None = None,
    runner: Any | None = None,
    state_dir: Path | None = None,
    stale_after_seconds: int = DEFAULT_HEALTH_STALE_AFTER_SECONDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    resolved_root = wake_root.resolve()
    resolved_repo = (repo_root or Path.cwd()).resolve()
    config_error = ""
    try:
        config = build_service_config(
            repo_root=resolved_repo,
            wake_root=resolved_root,
            name=service_name,
            interval=interval,
            daemon_path=daemon_path,
            codex_path=codex_path,
            resolve_default_codex=False,
            log_path=log_path,
            validate_executables=False,
        )
    except Exception as exc:
        config = None
        config_error = str(exc)
    service_active = "unknown"
    service_enabled = "unknown"
    service_wake_root = ""
    service_matches_root = False
    service_unit = ""
    service_log = ""
    service = {
        "name": service_name or "",
        "active": service_active,
        "enabled": service_enabled,
        "unit": service_unit,
        "log": service_log,
        "wake_root": service_wake_root,
        "matches_wake_root": service_matches_root,
        "config_error": config_error,
    }
    transports: dict[str, Any] = {}
    if config is not None:
        service_unit = str(config.unit_path)
        service_log = str(config.log_path)
        try:
            service_active, service_enabled = service_status(config, runner)
        except Exception as exc:
            service_active, service_enabled = "unknown", f"unknown ({exc})"
        service_wake_root = parse_unit_exec_start_wake_root(config.unit_path)
        service_matches_root = service_wake_root == str(resolved_root)
        service = {
            "name": config.name,
            "active": service_active,
            "enabled": service_enabled,
            "unit": service_unit,
            "log": service_log,
            "wake_root": service_wake_root,
            "matches_wake_root": service_matches_root,
            "config_error": "",
        }
        transports = transport_readiness(config)
    health = read_monitor_health(resolved_root, state_dir)
    recent_health = health_is_recent(health, stale_after_seconds=stale_after_seconds, now=now)
    persistent_health = bool(health and health.get("mode") == "loop")
    service_ready = service_active == "active" and service_matches_root
    health_ready = recent_health and persistent_health
    monitor_ready = service_ready or health_ready
    source = ""
    if service_ready:
        source = "repo_service"
    elif health_ready and health:
        source = str(health.get("source") or "health")
    return {
        "wake_root": str(resolved_root),
        "repo_root": str(resolved_repo),
        "monitor_ready": monitor_ready,
        "monitor_source": source,
        "service": service,
        "health": {
            "path": str(monitor_health_path(resolved_root, state_dir)),
            "exists": health is not None,
            "recent": recent_health,
            "persistent": persistent_health,
            "source": str(health.get("source") or "") if health else "",
            "mode": str(health.get("mode") or "") if health else "",
            "checked_at": str(health.get("checked_at") or "") if health else "",
            "pid": health.get("pid", "") if health else "",
        },
        "transports": transports,
    }


def require_monitor_ready(readiness: dict[str, Any]) -> None:
    if readiness.get("monitor_ready"):
        return
    service = readiness.get("service") if isinstance(readiness.get("service"), dict) else {}
    health = readiness.get("health") if isinstance(readiness.get("health"), dict) else {}
    raise WakeError(
        "no active monitor owns this wake root; "
        f"wake_root={readiness.get('wake_root')} "
        f"service={service.get('name', '')} active={service.get('active', '')} "
        f"service_wake_root={service.get('wake_root', '') or 'missing'} "
        f"health_recent={health.get('recent', False)}"
    )
