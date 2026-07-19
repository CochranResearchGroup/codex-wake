from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from .hook_config import DEFAULT_HOOK_COMMAND, check_hook_sources, hook_runtime_evidence
from .monitor import DEFAULT_HEALTH_STALE_AFTER_SECONDS, monitor_readiness
from .openclaw_plugin import DEFAULT_PLUGIN_ID, default_openclaw_config_path, package_version
from .records import format_utc, utc_now
from .service import build_service_config, service_app_server_readiness, service_status
from .supervisor import build_supervisor_config, supervisor_status


STATUS_READY = "ready"
STATUS_WARNING = "warning"
STATUS_MANUAL_ONLY = "manual_only"
STATUS_BLOCKED = "blocked"
STATUS_ORDER = {
    STATUS_READY: 0,
    STATUS_MANUAL_ONLY: 1,
    STATUS_WARNING: 2,
    STATUS_BLOCKED: 3,
}
DEFAULT_OPENCLAW_TIMEOUT_SECONDS = 30.0


class CommandRunner(Protocol):
    def run(
        self,
        args: list[str],
        *,
        check: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        ...


class SubprocessRunner:
    def run(
        self,
        args: list[str],
        *,
        check: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, check=check, text=True, capture_output=True, timeout=timeout)


def outcome(status: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {"status": status, "message": message}
    payload.update(extra)
    return payload


def overall_status(items: list[dict[str, Any]]) -> str:
    if not items:
        return STATUS_READY
    return max((str(item.get("status") or STATUS_READY) for item in items), key=lambda status: STATUS_ORDER.get(status, 0))


def command_paths() -> dict[str, str]:
    names = ("codex-wake", "codex-waked", "codex-wake-hook", "codex", "tmux", "openclaw")
    return {name.replace("-", "_"): shutil.which(name) or "" for name in names}


def cli_readiness(commands: dict[str, str] | None = None) -> dict[str, Any]:
    resolved = commands or command_paths()
    missing = [name for name in ("codex_wake", "codex_waked") if not resolved.get(name)]
    status = STATUS_BLOCKED if missing else STATUS_READY
    message = "required CLI commands are installed" if not missing else "missing required CLI commands: " + ", ".join(missing)
    return {
        **outcome(status, message),
        "version": package_version(),
        "commands": resolved,
    }


def skill_install_readiness(home: Path | None = None) -> dict[str, Any]:
    root = home or Path.home()
    candidates = [
        ("agents", root / ".agents" / "skills" / "codex-wake" / "SKILL.md"),
        ("codex_shared", root / ".codex" / "shared" / "skills" / "codex-wake" / "SKILL.md"),
        ("openclaw", root / ".openclaw" / "skills" / "codex-wake" / "SKILL.md"),
    ]
    installs = [{"scope": scope, "path": str(path), "exists": path.exists()} for scope, path in candidates]
    present = [item for item in installs if item["exists"]]
    status = STATUS_READY if present else STATUS_WARNING
    message = "codex-wake skill is installed" if present else "codex-wake skill was not found in standard user-scope locations"
    return {**outcome(status, message), "installations": installs}


def hook_readiness(repo_root: Path, wake_root: Path, command: str = DEFAULT_HOOK_COMMAND) -> dict[str, Any]:
    sources = check_hook_sources(repo_root, command)
    evidence = hook_runtime_evidence(wake_root)
    if sources.duplicate_installed:
        status = STATUS_WARNING
        message = sources.overlap_warning
    elif sources.installed_scopes:
        status = STATUS_READY
        message = "codex-wake hook is installed"
    else:
        status = STATUS_WARNING
        message = "codex-wake hook is not installed in project or user scope"
    return {
        **outcome(status, message),
        "installed_scopes": list(sources.installed_scopes),
        "duplicate_installed": sources.duplicate_installed,
        "project": {
            "path": str(sources.project.path),
            "exists": sources.project.exists,
            "installed": sources.project.installed,
            "valid_json": sources.project.valid_json,
            "message": sources.project.message,
        },
        "user": {
            "path": str(sources.user.path),
            "exists": sources.user.exists,
            "installed": sources.user.installed,
            "valid_json": sources.user.valid_json,
            "message": sources.user.message,
        },
        "runtime": {
            "ack_count": evidence.ack_count,
            "active_session_loaded": evidence.active_session_loaded,
            "latest_ack_path": str(evidence.latest_ack_path) if evidence.latest_ack_path else "",
            "latest_ack_wake_id": evidence.latest_ack_wake_id,
            "latest_ack_session_id": evidence.latest_ack_session_id,
        },
    }


def repo_service_readiness(
    *,
    repo_root: Path,
    wake_root: Path,
    service_name: str | None = None,
    interval: float = 1.0,
    daemon_path: str | None = None,
    codex_path: str | None = None,
    log_path: Path | None = None,
    runner: Any | None = None,
) -> tuple[dict[str, Any], Any | None, str]:
    try:
        config = build_service_config(
            repo_root=repo_root,
            wake_root=wake_root,
            name=service_name,
            interval=interval,
            daemon_path=daemon_path,
            codex_path=codex_path,
            resolve_default_codex=False,
            log_path=log_path,
            validate_executables=False,
        )
    except Exception as exc:
        return {**outcome(STATUS_BLOCKED, f"repo service config could not be built: {exc}"), "config_error": str(exc)}, None, str(exc)
    try:
        active, enabled = service_status(config, runner)
    except Exception as exc:
        active, enabled = "unknown", f"unknown ({exc})"
    status = STATUS_READY if active == "active" else STATUS_WARNING
    message = "repo-scoped service is active" if active == "active" else "repo-scoped service is not active"
    return (
        {
            **outcome(status, message),
            "name": config.name,
            "active": active,
            "enabled": enabled,
            "unit": str(config.unit_path),
            "log": str(config.log_path),
        },
        config,
        "",
    )


def app_server_readiness_from_service(service_config: Any | None, runner: Any | None = None) -> dict[str, Any]:
    if service_config is None:
        return outcome(STATUS_BLOCKED, "app-server readiness cannot be checked without repo service config")
    readiness = service_app_server_readiness(service_config, runner)
    if readiness.codex_cmd_ready:
        status = STATUS_READY
    elif readiness.codex_cmd_source == "interactive_path_only":
        status = STATUS_BLOCKED
    else:
        status = STATUS_BLOCKED
    return {**outcome(status, readiness.message), **asdict(readiness)}


def monitor_product_readiness(
    *,
    wake_root: Path,
    repo_root: Path,
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
    readiness = monitor_readiness(
        wake_root=wake_root,
        repo_root=repo_root,
        service_name=service_name,
        interval=interval,
        daemon_path=daemon_path,
        codex_path=codex_path,
        log_path=log_path,
        runner=runner,
        state_dir=state_dir,
        stale_after_seconds=stale_after_seconds,
        now=now,
    )
    health = readiness.get("health") if isinstance(readiness.get("health"), dict) else {}
    if readiness.get("monitor_ready"):
        status = STATUS_READY
        message = "an active monitor owns this wake root"
    elif health.get("exists") and not health.get("recent"):
        status = STATUS_BLOCKED
        message = "monitor health exists but is stale"
    else:
        status = STATUS_BLOCKED
        message = "no active monitor owns this wake root"
    return {**outcome(status, message), **readiness}


def supervisor_product_readiness(
    *,
    wake_root: Path,
    name: str | None = None,
    interval: float = 1.0,
    codex_wake_path: str | None = None,
    registry_dir: Path | None = None,
    state_dir: Path | None = None,
    log_path: Path | None = None,
    runner: Any | None = None,
) -> dict[str, Any]:
    try:
        config = build_supervisor_config(
            name=name,
            interval=interval,
            codex_wake_path=codex_wake_path,
            registry_dir=registry_dir,
            state_dir=state_dir,
            log_path=log_path,
            validate_executable=False,
        )
    except Exception as exc:
        return {**outcome(STATUS_BLOCKED, f"supervisor config could not be built: {exc}"), "config_error": str(exc)}
    summary = supervisor_status(config, runner)
    service = summary.get("service") if isinstance(summary.get("service"), dict) else {}
    roots = summary.get("roots") if isinstance(summary.get("roots"), list) else []
    current_root = str(wake_root.resolve())
    matching = [root for root in roots if root.get("wake_root") == current_root]
    if service.get("active") != "active":
        status = STATUS_BLOCKED
        message = "codex-wake supervisor service is not active"
    elif not matching:
        status = STATUS_WARNING
        message = "current wake root is not enrolled in the supervisor registry"
    else:
        status = STATUS_READY
        message = "codex-wake supervisor is active and this wake root is enrolled"
    return {**outcome(status, message), **summary, "current_root_enrolled": bool(matching)}


def env_ref(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    match = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", value.strip())
    return match.group(1) if match else ""


def secret_source(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "missing"
    if env_ref(value):
        return "env_ref"
    return "literal"


def openclaw_auth_readiness(
    *,
    config_path: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_env = env if env is not None else os.environ
    path = (config_path or default_openclaw_config_path()).expanduser()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {**outcome(STATUS_WARNING, "OpenClaw config was not found"), "config_path": str(path), "missing_env": []}
    except json.JSONDecodeError as exc:
        return {**outcome(STATUS_BLOCKED, f"OpenClaw config is invalid JSON: {exc}"), "config_path": str(path), "missing_env": []}
    gateway = payload.get("gateway") if isinstance(payload, dict) else {}
    auth = gateway.get("auth") if isinstance(gateway, dict) else {}
    mode = str(auth.get("mode") or "none") if isinstance(auth, dict) else "none"
    token_value = auth.get("token") if isinstance(auth, dict) else None
    password_value = auth.get("password") if isinstance(auth, dict) else None
    token_env = env_ref(token_value)
    password_env = env_ref(password_value)
    missing_env: list[str] = []
    if mode == "token" and token_env and not source_env.get(token_env):
        missing_env.append(token_env)
    if mode == "password" and password_env and not source_env.get(password_env):
        missing_env.append(password_env)
    if mode == "token" and secret_source(token_value) == "missing":
        missing_env.append("token")
    if mode == "password" and secret_source(password_value) == "missing":
        missing_env.append("password")
    status = STATUS_BLOCKED if missing_env else STATUS_READY
    message = "OpenClaw Gateway auth environment is available" if not missing_env else "OpenClaw Gateway auth environment is missing"
    return {
        **outcome(status, message),
        "config_path": str(path),
        "mode": mode,
        "token_source": secret_source(token_value),
        "token_env": token_env,
        "token_env_present": bool(token_env and source_env.get(token_env)),
        "password_source": secret_source(password_value),
        "password_env": password_env,
        "password_env_present": bool(password_env and source_env.get(password_env)),
        "missing_env": missing_env,
    }


def _json_command(
    args: list[str],
    *,
    runner: CommandRunner | None = None,
    timeout: float = DEFAULT_OPENCLAW_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any] | None, str, int]:
    command_runner = runner or SubprocessRunner()
    try:
        result = command_runner.run(args, check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f"command timed out after {timeout:g}s", 124
    except Exception as exc:
        return None, str(exc), 1
    if result.returncode != 0:
        return None, (result.stderr or result.stdout).strip(), result.returncode
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON output: {exc}", 1
    if not isinstance(payload, dict):
        return None, "JSON output was not an object", 1
    return payload, "", 0


def openclaw_gateway_readiness(
    *,
    openclaw_cmd: str,
    auth: dict[str, Any],
    runner: CommandRunner | None = None,
    timeout: float = DEFAULT_OPENCLAW_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if not openclaw_cmd:
        return outcome(STATUS_BLOCKED, "OpenClaw CLI was not found on PATH", openclaw_cmd="")
    if auth.get("status") == STATUS_BLOCKED:
        return {**outcome(STATUS_BLOCKED, "OpenClaw Gateway auth is not available; skipping RPC probe"), "openclaw_cmd": openclaw_cmd, "auth": auth, "rpc_ok": False}
    payload, error, returncode = _json_command(
        [openclaw_cmd, "gateway", "status", "--require-rpc", "--json", "--timeout", str(int(timeout * 1000))],
        runner=runner,
        timeout=timeout,
    )
    if error or payload is None:
        return {**outcome(STATUS_BLOCKED, error or "OpenClaw Gateway status failed"), "openclaw_cmd": openclaw_cmd, "auth": auth, "returncode": returncode, "rpc_ok": False}
    rpc = payload.get("rpc") if isinstance(payload.get("rpc"), dict) else {}
    rpc_ok = bool(rpc.get("ok"))
    status = STATUS_READY if rpc_ok else STATUS_BLOCKED
    message = "OpenClaw Gateway RPC is ready" if rpc_ok else "OpenClaw Gateway RPC probe failed"
    return {
        **outcome(status, message),
        "openclaw_cmd": openclaw_cmd,
        "auth": auth,
        "rpc_ok": rpc_ok,
        "url": str(rpc.get("url") or payload.get("url") or ""),
        "server_version": str((rpc.get("server") or {}).get("version") or rpc.get("version") or ""),
    }


def openclaw_plugin_readiness(
    *,
    openclaw_cmd: str,
    runner: CommandRunner | None = None,
    timeout: float = DEFAULT_OPENCLAW_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if not openclaw_cmd:
        return outcome(STATUS_BLOCKED, "OpenClaw CLI was not found on PATH", openclaw_cmd="")
    payload, error, returncode = _json_command(
        [openclaw_cmd, "plugins", "inspect", DEFAULT_PLUGIN_ID, "--runtime", "--json"],
        runner=runner,
        timeout=timeout,
    )
    if error or payload is None:
        return {**outcome(STATUS_BLOCKED, error or "OpenClaw plugin inspect failed"), "openclaw_cmd": openclaw_cmd, "returncode": returncode}
    plugin = payload.get("plugin") if isinstance(payload.get("plugin"), dict) else {}
    tool_names = plugin.get("toolNames") if isinstance(plugin.get("toolNames"), list) else []
    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), list) else []
    has_tool = "codex_wake_schedule" in tool_names
    activated = bool(plugin.get("activated"))
    if has_tool and activated and not diagnostics:
        status = STATUS_READY
        message = "OpenClaw codex-wake plugin is active"
    elif has_tool and activated:
        status = STATUS_WARNING
        message = "OpenClaw codex-wake plugin is active with diagnostics"
    else:
        status = STATUS_BLOCKED
        message = "OpenClaw codex-wake plugin is missing codex_wake_schedule or is inactive"
    install = payload.get("install") if isinstance(payload.get("install"), dict) else {}
    return {
        **outcome(status, message),
        "openclaw_cmd": openclaw_cmd,
        "id": str(plugin.get("id") or ""),
        "version": str(plugin.get("version") or ""),
        "source": str(plugin.get("source") or ""),
        "origin": str(plugin.get("origin") or ""),
        "activated": activated,
        "status_text": str(plugin.get("status") or ""),
        "tool_names": [str(name) for name in tool_names],
        "config_schema": bool(plugin.get("configSchema")),
        "diagnostic_count": len(diagnostics),
        "install": {
            "source": str(install.get("source") or ""),
            "sourcePath": str(install.get("sourcePath") or ""),
            "installPath": str(install.get("installPath") or ""),
            "version": str(install.get("version") or ""),
            "installedAt": str(install.get("installedAt") or ""),
        },
    }


def tmux_readiness(commands: dict[str, str] | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    resolved = commands or command_paths()
    source_env = env if env is not None else os.environ
    tmux_cmd = resolved.get("tmux", "")
    if not tmux_cmd:
        return outcome(STATUS_BLOCKED, "tmux command is missing", tmux_cmd="")
    if source_env.get("TMUX_PANE") and source_env.get("TMUX"):
        return outcome(STATUS_READY, "current shell has tmux target environment", tmux_cmd=tmux_cmd, tmux_pane_present=True)
    return outcome(
        STATUS_MANUAL_ONLY,
        "tmux command is installed, but current shell has no TMUX_PANE/TMUX target",
        tmux_cmd=tmux_cmd,
        tmux_pane_present=bool(source_env.get("TMUX_PANE")),
    )


def product_readiness_summary(
    *,
    wake_root: Path,
    repo_root: Path | None = None,
    hook_command: str = DEFAULT_HOOK_COMMAND,
    service_name: str | None = None,
    supervisor_name: str | None = None,
    interval: float = 1.0,
    daemon_path: str | None = None,
    codex_path: str | None = None,
    codex_wake_path: str | None = None,
    log_path: Path | None = None,
    supervisor_log_path: Path | None = None,
    registry_dir: Path | None = None,
    state_dir: Path | None = None,
    openclaw_path: str | None = None,
    openclaw_config: Path | None = None,
    stale_after_seconds: int = DEFAULT_HEALTH_STALE_AFTER_SECONDS,
    openclaw_timeout: float = DEFAULT_OPENCLAW_TIMEOUT_SECONDS,
    runner: Any | None = None,
    openclaw_runner: CommandRunner | None = None,
    env: dict[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    resolved_repo = (repo_root or Path.cwd()).resolve()
    resolved_root = wake_root.resolve()
    source_env = env if env is not None else os.environ
    commands = command_paths()
    if openclaw_path:
        commands["openclaw"] = openclaw_path
    cli = cli_readiness(commands)
    hooks = hook_readiness(resolved_repo, resolved_root, hook_command)
    skills = skill_install_readiness()
    repo_service, service_config, _ = repo_service_readiness(
        repo_root=resolved_repo,
        wake_root=resolved_root,
        service_name=service_name,
        interval=interval,
        daemon_path=daemon_path,
        codex_path=codex_path,
        log_path=log_path,
        runner=runner,
    )
    app_server = app_server_readiness_from_service(service_config, runner)
    monitor_state_dir = state_dir.parent / "monitors" if state_dir else None
    monitor = monitor_product_readiness(
        wake_root=resolved_root,
        repo_root=resolved_repo,
        service_name=service_name,
        interval=interval,
        daemon_path=daemon_path,
        codex_path=codex_path,
        log_path=log_path,
        runner=runner,
        state_dir=monitor_state_dir,
        stale_after_seconds=stale_after_seconds,
        now=now,
    )
    supervisor = supervisor_product_readiness(
        wake_root=resolved_root,
        name=supervisor_name,
        interval=interval,
        codex_wake_path=codex_wake_path,
        registry_dir=registry_dir,
        state_dir=state_dir,
        log_path=supervisor_log_path,
        runner=runner,
    )
    auth = openclaw_auth_readiness(config_path=openclaw_config, env=source_env)
    openclaw_cmd = commands.get("openclaw", "")
    openclaw_gateway = openclaw_gateway_readiness(
        openclaw_cmd=openclaw_cmd,
        auth=auth,
        runner=openclaw_runner,
        timeout=openclaw_timeout,
    )
    openclaw_plugin = openclaw_plugin_readiness(
        openclaw_cmd=openclaw_cmd,
        runner=openclaw_runner,
        timeout=openclaw_timeout,
    )
    tmux = tmux_readiness(commands, source_env)
    checks = {
        "cli": cli,
        "hooks": hooks,
        "skills": skills,
        "repo_service": repo_service,
        "supervisor": supervisor,
        "monitor": monitor,
        "app_server": app_server,
        "openclaw_gateway": openclaw_gateway,
        "openclaw_plugin": openclaw_plugin,
        "tmux": tmux,
    }
    return {
        "schema_version": 1,
        "generated_at": format_utc(now or utc_now()),
        "repo_root": str(resolved_repo),
        "wake_root": str(resolved_root),
        "overall_status": overall_status(list(checks.values())),
        "status_vocabulary": [STATUS_READY, STATUS_WARNING, STATUS_MANUAL_ONLY, STATUS_BLOCKED],
        "checks": checks,
    }
