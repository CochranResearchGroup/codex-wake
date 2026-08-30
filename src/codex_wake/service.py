from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .app_server import APP_SERVER_CODEX_ENV, resolve_codex_cmd
from .executables import resolve_stable_executable
from .records import WakeError, default_wake_root


DEFAULT_INTERVAL = 1.0


class CommandRunner(Protocol):
    def run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        ...


class SubprocessRunner:
    def run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, check=check, text=True, capture_output=True)


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    repo_root: Path
    wake_root: Path
    interval: float
    daemon_path: Path | None
    unit_path: Path
    log_path: Path
    codex_path: Path | None = None


@dataclass(frozen=True)
class ServiceAppServerReadiness:
    codex_cmd_ready: bool
    codex_cmd_source: str
    codex_cmd: str
    unit_codex_cmd: str
    user_manager_codex_cmd: str
    interactive_codex_cmd: str
    message: str


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-_.").lower()
    return slug or "repo"


def default_service_name(repo_root: Path) -> str:
    return f"codex-wake-{slugify(repo_root.name)}.service"


def user_systemd_dir(env: dict[str, str] | None = None) -> Path:
    source = env if env is not None else os.environ
    base = source.get("XDG_CONFIG_HOME")
    if base:
        return Path(base).expanduser() / "systemd" / "user"
    return Path.home() / ".config" / "systemd" / "user"


def user_state_dir(env: dict[str, str] | None = None) -> Path:
    source = env if env is not None else os.environ
    base = source.get("XDG_STATE_HOME")
    if base:
        return Path(base).expanduser() / "codex-wake"
    return Path.home() / ".local" / "state" / "codex-wake"


def resolve_daemon_path(raw: str | None = None) -> Path:
    return Path(
        resolve_stable_executable(
            raw,
            default_command="codex-waked",
            label="codex-waked",
        )
    )


def build_service_config(
    *,
    repo_root: Path | None = None,
    wake_root: Path | None = None,
    name: str | None = None,
    interval: float = DEFAULT_INTERVAL,
    daemon_path: str | None = None,
    codex_path: str | None = None,
    resolve_default_codex: bool = False,
    unit_dir: Path | None = None,
    log_path: Path | None = None,
    validate_executables: bool = True,
) -> ServiceConfig:
    resolved_repo = (repo_root or Path.cwd()).resolve()
    resolved_name = name or default_service_name(resolved_repo)
    if not resolved_name.endswith(".service"):
        resolved_name = f"{resolved_name}.service"
    if "/" in resolved_name:
        raise WakeError("service name must not contain '/'")
    if interval <= 0:
        raise WakeError("--interval must be greater than zero")
    resolved_codex = ""
    if validate_executables and codex_path:
        resolved_codex = resolve_stable_executable(
            codex_path,
            default_command="codex",
            label="Codex CLI",
            reject_node_versioned=True,
        )
    elif validate_executables and resolve_default_codex:
        resolved_codex = resolve_stable_executable(
            None,
            default_command="codex",
            label="Codex CLI",
            required=False,
            reject_node_versioned=True,
        )
    resolved_unit_dir = (unit_dir or user_systemd_dir()).expanduser()
    resolved_log_path = (log_path or (user_state_dir() / f"{resolved_name.removesuffix('.service')}.log")).expanduser()
    return ServiceConfig(
        name=resolved_name,
        repo_root=resolved_repo,
        wake_root=(wake_root or default_wake_root(resolved_repo)).resolve(),
        interval=interval,
        daemon_path=resolve_daemon_path(daemon_path) if validate_executables else None,
        unit_path=resolved_unit_dir / resolved_name,
        log_path=resolved_log_path,
        codex_path=Path(resolved_codex) if resolved_codex else None,
    )


def systemd_quote(value: Path | str) -> str:
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def systemd_environment_assignment(key: str, value: str) -> str:
    escaped = f"{key}={value}".replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_unit(config: ServiceConfig) -> str:
    if config.daemon_path is None:
        raise WakeError("codex-waked must be resolved before rendering a service unit")
    environment = ""
    if config.codex_path:
        environment = f"Environment={systemd_environment_assignment(APP_SERVER_CODEX_ENV, str(config.codex_path))}\n"
    return (
        "[Unit]\n"
        "Description=Codex Wake daemon for one repository\n"
        "Documentation=https://github.com/CochranResearchGroup/codex-wake\n"
        "After=default.target\n"
        f"ConditionPathIsDirectory={config.repo_root}\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={config.repo_root}\n"
        f"{environment}"
        f"ExecStart={systemd_quote(config.daemon_path)} --wake-root {systemd_quote(config.wake_root)} --interval {config.interval:g}\n"
        "Restart=on-failure\n"
        "RestartPreventExitStatus=200\n"
        "RestartSec=5\n"
        f"StandardOutput=append:{config.log_path}\n"
        f"StandardError=append:{config.log_path}\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def systemctl(args: list[str], runner: CommandRunner | None = None, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    command_runner = runner or SubprocessRunner()
    return command_runner.run(["systemctl", "--user", *args], check=check)


def install_service(config: ServiceConfig, runner: CommandRunner | None = None, *, start: bool = True) -> None:
    config.unit_path.parent.mkdir(parents=True, exist_ok=True)
    config.log_path.parent.mkdir(parents=True, exist_ok=True)
    config.unit_path.write_text(render_unit(config), encoding="utf-8")
    systemctl(["daemon-reload"], runner)
    if start:
        systemctl(["enable", "--now", config.name], runner)
        active = systemctl(["is-active", config.name], runner, check=False).stdout.strip()
        if active != "active":
            raise WakeError(f"service did not become active: {config.name} ({active or 'unknown'})")


def stop_service(config: ServiceConfig, runner: CommandRunner | None = None) -> None:
    systemctl(["disable", "--now", config.name], runner, check=False)


def uninstall_service(config: ServiceConfig, runner: CommandRunner | None = None) -> None:
    stop_service(config, runner)
    config.unit_path.unlink(missing_ok=True)
    systemctl(["daemon-reload"], runner)


def service_status(config: ServiceConfig, runner: CommandRunner | None = None) -> tuple[str, str]:
    active = systemctl(["is-active", config.name], runner, check=False).stdout.strip() or "unknown"
    enabled = systemctl(["is-enabled", config.name], runner, check=False).stdout.strip() or "unknown"
    return active, enabled


def parse_unit_environment(unit_path: Path) -> dict[str, str]:
    if not unit_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in unit_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("Environment="):
            continue
        try:
            assignments = shlex.split(stripped.removeprefix("Environment="))
        except ValueError:
            continue
        for assignment in assignments:
            if "=" not in assignment:
                continue
            key, value = assignment.split("=", 1)
            values[key] = value
    return values


def user_manager_environment(runner: CommandRunner | None = None) -> dict[str, str]:
    try:
        result = systemctl(["show-environment"], runner, check=False)
    except Exception:
        return {}
    if result.returncode != 0:
        return {}
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def service_app_server_readiness(
    config: ServiceConfig,
    runner: CommandRunner | None = None,
) -> ServiceAppServerReadiness:
    unit_env = parse_unit_environment(config.unit_path)
    unit_codex_cmd = unit_env.get(APP_SERVER_CODEX_ENV, "")
    manager_env = user_manager_environment(runner)
    manager_path = manager_env.get("PATH") or None
    user_manager_codex_cmd = ""
    if APP_SERVER_CODEX_ENV in manager_env:
        user_manager_codex_cmd = resolve_codex_cmd(env=manager_env, path=manager_path or "")
    elif manager_path:
        user_manager_codex_cmd = resolve_codex_cmd(env={}, path=manager_path)
    interactive_codex_cmd = resolve_codex_cmd()

    if unit_codex_cmd:
        try:
            resolved_unit = resolve_codex_cmd(unit_codex_cmd, env={}, path=manager_path or "", required=True)
        except WakeError as exc:
            return ServiceAppServerReadiness(
                codex_cmd_ready=False,
                codex_cmd_source="unit_environment",
                codex_cmd=unit_codex_cmd,
                unit_codex_cmd=unit_codex_cmd,
                user_manager_codex_cmd=user_manager_codex_cmd,
                interactive_codex_cmd=interactive_codex_cmd,
                message=str(exc),
            )
        return ServiceAppServerReadiness(
            codex_cmd_ready=True,
            codex_cmd_source="unit_environment",
            codex_cmd=resolved_unit,
            unit_codex_cmd=unit_codex_cmd,
            user_manager_codex_cmd=user_manager_codex_cmd,
            interactive_codex_cmd=interactive_codex_cmd,
            message=f"service unit sets {APP_SERVER_CODEX_ENV}",
        )

    if user_manager_codex_cmd:
        return ServiceAppServerReadiness(
            codex_cmd_ready=True,
            codex_cmd_source="user_manager_path",
            codex_cmd=user_manager_codex_cmd,
            unit_codex_cmd="",
            user_manager_codex_cmd=user_manager_codex_cmd,
            interactive_codex_cmd=interactive_codex_cmd,
            message="user-systemd manager PATH can resolve codex",
        )

    if interactive_codex_cmd:
        return ServiceAppServerReadiness(
            codex_cmd_ready=False,
            codex_cmd_source="interactive_path_only",
            codex_cmd="",
            unit_codex_cmd="",
            user_manager_codex_cmd="",
            interactive_codex_cmd=interactive_codex_cmd,
            message=(
                "interactive shell can resolve codex, but the service unit and "
                "user-systemd manager environment do not expose it"
            ),
        )

    return ServiceAppServerReadiness(
        codex_cmd_ready=False,
        codex_cmd_source="missing",
        codex_cmd="",
        unit_codex_cmd="",
        user_manager_codex_cmd="",
        interactive_codex_cmd="",
        message=(
            f"Codex CLI not found for app-server dispatch; set {APP_SERVER_CODEX_ENV} "
            "or reinstall the service with --codex-path"
        ),
    )


def read_log_tail(path: Path, lines: int) -> str:
    if lines <= 0:
        raise WakeError("--lines must be greater than zero")
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])
