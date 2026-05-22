from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .records import WakeError


HOOK_EVENT = "UserPromptSubmit"
DEFAULT_HOOK_COMMAND = "codex-wake-hook"
DEFAULT_STATUS_MESSAGE = "Checking wake trigger"
HOOK_REVIEW_NOTE = (
    "Codex may require /hooks review before this hook can run. "
    "If /hooks does not list this repo hook source, the active TUI has not loaded it; "
    "restart or resume Codex in this repo, then review hooks before dogfooding ack behavior."
)


@dataclass(frozen=True)
class HookCheck:
    path: Path
    exists: bool
    valid_json: bool
    installed: bool
    command: str
    message: str


@dataclass(frozen=True)
class HookSourceCheck:
    scope: str
    path: Path
    exists: bool
    valid_json: bool
    installed: bool
    command: str
    message: str


@dataclass(frozen=True)
class HookSources:
    project: HookSourceCheck
    user: HookSourceCheck
    installed_scopes: tuple[str, ...]
    duplicate_installed: bool
    overlap_warning: str


@dataclass(frozen=True)
class HookRuntimeEvidence:
    ack_count: int
    active_session_loaded: str
    latest_ack_path: Path | None
    latest_ack_submitted_at: str
    latest_ack_wake_id: str
    latest_ack_session_id: str


def hook_review_note() -> str:
    return HOOK_REVIEW_NOTE


def hook_path_for_repo(repo_root: Path) -> Path:
    return repo_root.resolve() / ".codex" / "hooks.json"


def user_hook_path(codex_home: Path | None = None) -> Path:
    if codex_home is None:
        env_home = os.environ.get("CODEX_HOME")
        codex_home = Path(env_home).expanduser() if env_home else Path.home() / ".codex"
    return codex_home.expanduser().resolve() / "hooks.json"


def hook_entry(command: str = DEFAULT_HOOK_COMMAND) -> dict[str, Any]:
    return {
        "type": "command",
        "command": command,
        "timeout": 5,
        "statusMessage": DEFAULT_STATUS_MESSAGE,
    }


def load_hook_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WakeError(f"hook config is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise WakeError(f"hook config must be a JSON object: {path}")
    return data


def user_prompt_submit_entries(config: dict[str, Any]) -> list[dict[str, Any]]:
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return []
    entries = hooks.get(HOOK_EVENT)
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def contains_hook_command(config: dict[str, Any], command: str = DEFAULT_HOOK_COMMAND) -> bool:
    for entry in user_prompt_submit_entries(config):
        nested = entry.get("hooks")
        if not isinstance(nested, list):
            continue
        for hook in nested:
            if isinstance(hook, dict) and hook.get("type") == "command" and hook.get("command") == command:
                return True
    return False


def install_hook_config(repo_root: Path, command: str = DEFAULT_HOOK_COMMAND) -> Path:
    return install_hook_file(hook_path_for_repo(repo_root), command)


def install_user_hook_config(codex_home: Path | None = None, command: str = DEFAULT_HOOK_COMMAND) -> Path:
    return install_hook_file(user_hook_path(codex_home), command)


def install_hook_file(path: Path, command: str = DEFAULT_HOOK_COMMAND) -> Path:
    config = load_hook_config(path)
    if contains_hook_command(config, command):
        return path
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
        config["hooks"] = hooks
    entries = hooks.get(HOOK_EVENT)
    if not isinstance(entries, list):
        entries = []
        hooks[HOOK_EVENT] = entries
    entries.append({"hooks": [hook_entry(command)]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def check_hook_config(repo_root: Path, command: str = DEFAULT_HOOK_COMMAND) -> HookCheck:
    path = hook_path_for_repo(repo_root)
    check = check_hook_file(path, command, scope="project")
    return HookCheck(
        path=check.path,
        exists=check.exists,
        valid_json=check.valid_json,
        installed=check.installed,
        command=check.command,
        message=check.message,
    )


def check_user_hook_config(codex_home: Path | None = None, command: str = DEFAULT_HOOK_COMMAND) -> HookSourceCheck:
    return check_hook_file(user_hook_path(codex_home), command, scope="user")


def check_hook_file(path: Path, command: str = DEFAULT_HOOK_COMMAND, *, scope: str) -> HookSourceCheck:
    if not path.exists():
        return HookSourceCheck(
            scope=scope,
            path=path,
            exists=False,
            valid_json=False,
            installed=False,
            command=command,
            message="missing",
        )
    try:
        config = load_hook_config(path)
    except WakeError as exc:
        return HookSourceCheck(
            scope=scope,
            path=path,
            exists=True,
            valid_json=False,
            installed=False,
            command=command,
            message=str(exc),
        )
    installed = contains_hook_command(config, command)
    return HookSourceCheck(
        scope=scope,
        path=path,
        exists=True,
        valid_json=True,
        installed=installed,
        command=command,
        message="installed" if installed else "expected hook command missing",
    )


def check_hook_sources(
    repo_root: Path,
    command: str = DEFAULT_HOOK_COMMAND,
    *,
    codex_home: Path | None = None,
) -> HookSources:
    project = check_hook_file(hook_path_for_repo(repo_root), command, scope="project")
    user = check_hook_file(user_hook_path(codex_home), command, scope="user")
    installed_scopes = tuple(check.scope for check in (project, user) if check.installed)
    duplicate_installed = len(installed_scopes) > 1
    overlap_warning = ""
    if duplicate_installed:
        overlap_warning = (
            "codex-wake-hook is installed in both project and user hook sources; "
            "Codex may run both and inject duplicate wake context."
        )
    return HookSources(
        project=project,
        user=user,
        installed_scopes=installed_scopes,
        duplicate_installed=duplicate_installed,
        overlap_warning=overlap_warning,
    )


def hook_runtime_evidence(wake_root: Path) -> HookRuntimeEvidence:
    ack_dir = wake_root / "acks"
    ack_paths = sorted(ack_dir.glob("*.submitted")) if ack_dir.exists() else []
    latest_path: Path | None = None
    latest_data: dict[str, Any] = {}
    latest_sort_key = ""
    for path in ack_paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        submitted_at = data.get("submitted_at")
        sort_key = submitted_at if isinstance(submitted_at, str) else ""
        if latest_path is None or sort_key >= latest_sort_key:
            latest_path = path
            latest_data = data if isinstance(data, dict) else {}
            latest_sort_key = sort_key
    if latest_path is None:
        return HookRuntimeEvidence(
            ack_count=0,
            active_session_loaded="unknown_without_ack",
            latest_ack_path=None,
            latest_ack_submitted_at="",
            latest_ack_wake_id="",
            latest_ack_session_id="",
        )
    submitted_at = latest_data.get("submitted_at")
    wake_id = latest_data.get("wake_id")
    session_id = latest_data.get("session_id")
    return HookRuntimeEvidence(
        ack_count=len(ack_paths),
        active_session_loaded="observed_ack",
        latest_ack_path=latest_path,
        latest_ack_submitted_at=submitted_at if isinstance(submitted_at, str) else "",
        latest_ack_wake_id=wake_id if isinstance(wake_id, str) else "",
        latest_ack_session_id=session_id if isinstance(session_id, str) else "",
    )
