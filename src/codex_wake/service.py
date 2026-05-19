from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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
    daemon_path: Path
    unit_path: Path
    log_path: Path


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
    if raw:
        return Path(raw).expanduser().resolve()
    found = shutil.which("codex-waked")
    if not found:
        raise WakeError("codex-waked was not found on PATH; install codex-wake first")
    return Path(found).resolve()


def build_service_config(
    *,
    repo_root: Path | None = None,
    wake_root: Path | None = None,
    name: str | None = None,
    interval: float = DEFAULT_INTERVAL,
    daemon_path: str | None = None,
    unit_dir: Path | None = None,
    log_path: Path | None = None,
) -> ServiceConfig:
    resolved_repo = (repo_root or Path.cwd()).resolve()
    resolved_name = name or default_service_name(resolved_repo)
    if not resolved_name.endswith(".service"):
        resolved_name = f"{resolved_name}.service"
    if "/" in resolved_name:
        raise WakeError("service name must not contain '/'")
    if interval <= 0:
        raise WakeError("--interval must be greater than zero")
    resolved_unit_dir = (unit_dir or user_systemd_dir()).expanduser()
    resolved_log_path = (log_path or (user_state_dir() / f"{resolved_name.removesuffix('.service')}.log")).expanduser()
    return ServiceConfig(
        name=resolved_name,
        repo_root=resolved_repo,
        wake_root=(wake_root or default_wake_root(resolved_repo)).resolve(),
        interval=interval,
        daemon_path=resolve_daemon_path(daemon_path),
        unit_path=resolved_unit_dir / resolved_name,
        log_path=resolved_log_path,
    )


def systemd_quote(value: Path | str) -> str:
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_unit(config: ServiceConfig) -> str:
    return (
        "[Unit]\n"
        "Description=Codex Wake daemon for one repository\n"
        "Documentation=https://github.com/CochranResearchGroup/codex-wake\n"
        "After=default.target\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={config.repo_root}\n"
        f"ExecStart={systemd_quote(config.daemon_path)} --wake-root {systemd_quote(config.wake_root)} --interval {config.interval:g}\n"
        "Restart=on-failure\n"
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


def read_log_tail(path: Path, lines: int) -> str:
    if lines <= 0:
        raise WakeError("--lines must be greater than zero")
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])
