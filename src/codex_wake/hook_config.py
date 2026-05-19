from __future__ import annotations

import json
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


def hook_review_note() -> str:
    return HOOK_REVIEW_NOTE


def hook_path_for_repo(repo_root: Path) -> Path:
    return repo_root.resolve() / ".codex" / "hooks.json"


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
    path = hook_path_for_repo(repo_root)
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
    if not path.exists():
        return HookCheck(path=path, exists=False, valid_json=False, installed=False, command=command, message="missing")
    try:
        config = load_hook_config(path)
    except WakeError as exc:
        return HookCheck(path=path, exists=True, valid_json=False, installed=False, command=command, message=str(exc))
    installed = contains_hook_command(config, command)
    return HookCheck(
        path=path,
        exists=True,
        valid_json=True,
        installed=installed,
        command=command,
        message="installed" if installed else "expected hook command missing",
    )
