from __future__ import annotations

import argparse
import json
import os
import re
import select
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from urllib import request
from urllib.error import URLError

from . import __version__
from .compatibility import compatibility_status, launcher_safety_issues, preflight_issues, requires_compatibility_gate, write_compatibility_receipt
from .config import Settings, account_environment, load_settings
from .layout import ActiveProfileGuard, ClosedSession, MigrationAction, ProjectionAction, apply_migration, ensure_directory, ensure_layout, plan_migration, profile_snapshot, project_profile, unproject_profile, validate_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-profiles",
        description="Manage isolated Codex homes with selectively shared local state.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(os.environ.get("CODEX_PROFILES_CONFIG", "profiles.toml")),
        help="Optional TOML config file for layout policy.",
    )
    parser.add_argument(
        "--state-root",
        type=Path,
        default=None,
        help="Root directory containing shared and per-profile Codex homes.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="Existing singleton Codex root used to seed shared state.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    sessions_parser = subparsers.add_parser("sessions", help="Browse selected tenants and resume the exact owning conversation.")
    sessions_parser.add_argument("history_args", nargs=argparse.REMAINDER)
    upgrades_parser = subparsers.add_parser("upgrades", help="Check, stage and explicitly select qualified builds.")
    upgrades_parser.add_argument("upgrade_args", nargs=argparse.REMAINDER)
    continue_parser = subparsers.add_parser("continue", help="Prepare an explicit linked conversation under another account.")
    continue_parser.add_argument("continuation_args", nargs=argparse.REMAINDER)

    init_parser = subparsers.add_parser("init", help="Create the shared layout root.")
    init_parser.add_argument("--profile", help="Optional profile or alias to provision during init.")
    init_parser.set_defaults(_subparser=init_parser)

    add_parser = subparsers.add_parser("add", help="Provision a profile directory.")
    add_parser.add_argument("profile", nargs="?", help="Profile name to create, with or without the codex- prefix.")
    add_parser.add_argument("--alias", help="Optional alias to add to the config for the new profile.")
    add_parser.set_defaults(_subparser=add_parser)

    aliases_parser = subparsers.add_parser("aliases", help="List configured profile aliases.")
    aliases_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    list_parser = subparsers.add_parser("list", help="List managed profiles.")
    list_parser.add_argument("--absolute", action="store_true", help="Show absolute paths.")
    list_parser.add_argument("--names", action="store_true", help="Show completable profile names and aliases.")

    inspect_parser = subparsers.add_parser("inspect", help="Show resolved paths for a profile.")
    inspect_parser.add_argument("profile", nargs="?", help="Profile name or alias to inspect.")
    inspect_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    which_parser = subparsers.add_parser("which", help="Resolve the active or named profile.")
    which_parser.add_argument("profile", nargs="?", help="Optional profile name or alias to resolve.")
    which_parser.add_argument("--shell", action="store_true", help="Print shell exports for the resolved profile.")
    which_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    use_parser = subparsers.add_parser("use", help="Persist the current profile selection.")
    use_parser.add_argument("profile", help="Profile name or alias to persist as the current profile.")
    use_parser.add_argument(
        "--close-open-sessions",
        action="store_true",
        help="Terminate tracked Codex sessions from other profiles before switching the persisted profile.",
    )
    use_parser.add_argument("--shell", action="store_true", help="Also print shell exports for the selected profile.")
    use_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    project_parser = subparsers.add_parser("project", help="Project a profile into the stock ~/.codex path.")
    project_parser.add_argument("profile", nargs="?", help="Profile name or alias to project. Uses current/default profile when omitted.")
    project_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    unproject_parser = subparsers.add_parser("unproject", help="Materialize managed ~/.codex projection symlinks back to stock files.")
    unproject_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    run_parser = subparsers.add_parser("run", help="Run codex with CODEX_HOME set for a profile.")
    run_parser.add_argument("--build-manifest", type=Path, default=os.environ.get("CODEX_BUILD_MANIFEST"), help="Pinned stock/modded build registry.")
    run_parser.add_argument("--channel", choices=("stock", "modded"))
    run_parser.add_argument("--sudo", "--su", action="store_true", help="Run codex through sudo while preserving the selected profile environment.")
    run_parser.add_argument("--sudo-user", help="User to pass to sudo -u. Defaults to sudo's configured target user.")
    run_parser.add_argument("profile", nargs="?", help="Profile name or alias to run. Uses default_profile when omitted.")
    run_parser.add_argument("codex_args", nargs=argparse.REMAINDER, help="Arguments passed through to codex.")

    doctor_parser = subparsers.add_parser("doctor", help="Validate the current layout.")
    doctor_parser.add_argument("profile", nargs="?", help="Optional profile name or alias to validate.")
    doctor_parser.add_argument("--mcp", action="append", default=[], help="Also smoke-check a configured MCP server by name.")
    doctor_parser.add_argument(
        "--mcp-required-tool",
        action="append",
        default=[],
        help="Tool name that must be present in every --mcp tools/list response.",
    )
    doctor_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    status_parser = subparsers.add_parser("status", help="Show summary status for managed profiles.")
    status_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    compatibility_parser = subparsers.add_parser("compatibility", help="Check or accept the current Codex/tool/profile-policy combination.")
    compatibility_parser.add_argument("--accept", action="store_true", help="Accept the current combination after preflight checks pass.")
    compatibility_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    completion_parser = subparsers.add_parser("completion", help="Emit shell completion script.")
    completion_parser.add_argument("shell", choices=("zsh", "bash"), help="Shell to generate completions for.")

    shell_init_parser = subparsers.add_parser("shell-init", help="Emit shell integration that routes plain codex through the selected profile.")
    shell_init_parser.add_argument("shell", choices=("zsh", "bash"), help="Shell integration flavor to emit.")

    install_parser = subparsers.add_parser("install", help="Install local helper artifacts for this repo checkout.")
    install_parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local" / "bin", help="Directory for launcher scripts.")
    install_parser.add_argument(
        "--completion-dir",
        type=Path,
        default=None,
        help="Optional completion directory. Defaults to ~/.zsh/completions for zsh and ~/.local/share/bash-completion/completions for bash.",
    )
    install_parser.add_argument("--shell", choices=("zsh", "bash"), default="zsh", help="Shell completion flavor to install.")
    install_parser.add_argument("--repo-path", type=Path, default=Path.cwd(), help="Repo checkout to target.")
    install_parser.add_argument("--print-only", action="store_true", help="Print the install plan without writing files.")

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove local helper artifacts and revert the stock ~/.codex projection.")
    uninstall_parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local" / "bin", help="Directory containing launcher scripts.")
    uninstall_parser.add_argument(
        "--completion-dir",
        type=Path,
        default=None,
        help="Optional completion directory. Defaults to ~/.zsh/completions for zsh and ~/.local/share/bash-completion/completions for bash.",
    )
    uninstall_parser.add_argument("--shell", choices=("zsh", "bash"), default="zsh", help="Shell completion flavor to remove.")
    uninstall_parser.add_argument("--keep-projection", action="store_true", help="Do not materialize managed ~/.codex projection symlinks.")
    uninstall_parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    uninstall_parser.add_argument("--print-only", action="store_true", help="Print the uninstall plan without removing files.")

    migrate_parser = subparsers.add_parser("migrate", help="Plan or apply shared-state migration from an existing singleton Codex root.")
    migrate_parser.add_argument("--apply", action="store_true", help="Execute the planned migration.")
    migrate_parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without changing files.")
    migrate_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    return parser


def settings_from_args(args: argparse.Namespace) -> Settings:
    env_state_root = os.environ.get("CODEX_STATE_ROOT")
    state_root = args.state_root or (Path(env_state_root) if env_state_root else None)
    return load_settings(args.config, state_root=state_root, source_root=args.source_root)


def resolve_requested_profile(settings: Settings, profile: str | None) -> str:
    return settings.resolve_profile_name(profile, env_profile=os.environ.get("CODEX_PROFILE"))


def is_known_profile_token(settings: Settings, token: str | None) -> bool:
    if not token:
        return False
    if token in settings.aliases:
        return True
    normalized = settings.normalize_profile_name(token)
    known = {settings.normalize_profile_name(name) for name in settings.known_profiles}
    if normalized in known:
        return True
    return settings.account_root(token).exists()


def split_run_profile_and_args(settings: Settings, profile: str | None, codex_args: list[str]) -> tuple[str, list[str]]:
    cleaned_args = list(codex_args)
    if cleaned_args and cleaned_args[0] == "--":
        cleaned_args = cleaned_args[1:]

    if profile is not None and not is_known_profile_token(settings, profile):
        cleaned_args = [profile, *cleaned_args]
        profile = None

    resolved_profile = resolve_requested_profile(settings, profile)
    return resolved_profile, cleaned_args


def build_codex_command(account_root: Path, profile: str, codex_args: list[str], *, use_sudo: bool = False, sudo_user: str | None = None) -> list[str]:
    codex_path = shutil.which("codex")
    if not codex_path:
        raise FileNotFoundError("codex")

    if not use_sudo:
        return [codex_path, *codex_args]

    sudo_path = shutil.which("sudo")
    if not sudo_path:
        raise FileNotFoundError("sudo")
    env_path = shutil.which("env") or "/usr/bin/env"
    command = [sudo_path]
    if sudo_user:
        command.extend(["-u", sudo_user])
    command.extend(
        [
            env_path,
            f"CODEX_HOME={account_root}",
            f"CODEX_PROFILE_NAME={profile}",
            codex_path,
            *codex_args,
        ]
    )
    return command


def print_migration_actions(actions: list[MigrationAction]) -> None:
    for action in actions:
        source = str(action.source) if action.source is not None else "-"
        print(f"{action.status:7} {action.kind:6} {source} -> {action.destination}")
        print(f"detail={action.detail}")


def render_completion(shell: str) -> str:
    if shell == "zsh":
        return """#compdef codex-profiles codex-profile

_codex_profiles_names() {
  local -a names
  names=(${(f)$(codex-profiles list --names 2>/dev/null)})
  print -l -- $names
}

_codex_profiles() {
  local -a commands
    commands=(
      'init:Create the shared layout root'
      'add:Provision a profile directory'
      'aliases:List configured profile aliases'
      'list:List managed profiles'
    'inspect:Show resolved paths for a profile'
    'which:Resolve the active or named profile'
      'use:Persist the current profile selection'
    'project:Project a profile into the stock ~/.codex path'
    'unproject:Materialize stock ~/.codex projection symlinks'
    'status:Show summary status for managed profiles'
    'compatibility:Check or accept the current Codex/tool/profile policy'
    'doctor:Validate the current layout'
    'completion:Emit shell completion script'
    'shell-init:Route plain codex through the selected profile'
    'install:Install local helper artifacts'
    'uninstall:Remove local helper artifacts'
    'migrate:Plan or apply shared-state migration'
    'run:Run codex with CODEX_HOME set for a profile'
  )
  _arguments \
    '1:command:->command' \
    '*::args:->args'

  case $state in
    command)
      _describe 'command' commands
      ;;
    args)
      case $words[2] in
        add|inspect|which|use|project|run|doctor)
          _values 'profile' $(_codex_profiles_names)
          ;;
        completion)
          _values 'shell' zsh bash
          ;;
        install)
          _arguments '--shell[shell completion flavor]:shell:(zsh bash)'
          ;;
        *)
          ;;
      esac
      ;;
  esac
}

_codex_profile() {
  _values 'profile' $(_codex_profiles_names)
}

compdef _codex_profiles codex-profiles
compdef _codex_profile codex-profile
"""
    return """_codex_profiles()
{
  local cur prev words cword
  _init_completion || return
  local commands="init add aliases list inspect which use project unproject status compatibility doctor completion shell-init install uninstall migrate run"
  if [[ ${cword} -eq 1 ]]; then
    COMPREPLY=( $(compgen -W "${commands}" -- "${cur}") )
    return
  fi
  prev="${words[cword-1]}"
  if [[ ${cword} -eq 2 && "${words[1]}" == "codex-profile" ]]; then
    COMPREPLY=( $(compgen -W "$(codex-profiles list --names 2>/dev/null)" -- "${cur}") )
    return
  fi
  if [[ ${cword} -eq 2 ]]; then
    case "${words[1]}" in
      add|inspect|which|use|project|run|doctor)
        COMPREPLY=( $(compgen -W "$(codex-profiles list --names 2>/dev/null)" -- "${cur}") )
        return
        ;;
    esac
  fi
  case "${prev}" in
    completion|shell-init|--shell)
      COMPREPLY=( $(compgen -W "zsh bash" -- "${cur}") )
      return
      ;;
  esac
}

complete -F _codex_profiles codex-profiles
complete -F _codex_profiles codex-profile
"""


def render_shell_init(shell: str) -> str:
    if shell == "zsh":
        return """# codex-profiles shell integration
codex() {
  command codex-profile --channel modded -- "$@"
}
"""
    return """# codex-profiles shell integration
codex() {
  command codex-profile --channel modded -- "$@"
}
"""


def install_payload(shell: str, repo_path: Path, bin_dir: Path, completion_dir: Path) -> dict[str, str]:
    repo_path = repo_path.resolve()
    launcher_path = bin_dir / "codex-profile"
    completion_name = "_codex_profiles" if shell == "zsh" else "codex-profiles"
    completion_path = completion_dir / completion_name
    launcher_text = "\n".join(
        [
            "#!/usr/bin/env sh",
            "set -eu",
            f'export PYTHONPATH={shlex.quote(str(repo_path / "src"))}${{PYTHONPATH:+:$PYTHONPATH}}',
            f'exec python3 -m codex_profiles.cli run "$@"',
            "",
        ]
    )
    return {
        "launcher_path": str(launcher_path),
        "launcher_text": launcher_text,
        "completion_path": str(completion_path),
        "completion_text": render_completion(shell),
    }


def migration_actions_payload(actions: list[MigrationAction]) -> list[dict[str, str | None]]:
    return [
        {
            "kind": action.kind,
            "source": str(action.source) if action.source is not None else None,
            "destination": str(action.destination),
            "status": action.status,
            "detail": action.detail,
        }
        for action in actions
    ]


def projection_actions_payload(actions: list[ProjectionAction]) -> list[dict[str, str | None]]:
    return [
        {
            "kind": action.kind,
            "source": str(action.source) if action.source is not None else None,
            "destination": str(action.destination),
            "status": action.status,
            "detail": action.detail,
        }
        for action in actions
    ]


DEFAULT_MCP_REQUIRED_TOOLS = {
    "graphiti": (
        "add_memory",
        "find_episodes",
        "get_episode",
        "get_status",
        "search_memory_facts",
        "smoke_memory_ingestion",
    ),
    "imcli": (
        "service_profile",
        "search_messages",
        "events_list",
    ),
}

DEFAULT_MCP_SMOKE_TOOLS = {
    "imcli": "service_profile",
}


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _toml_list(values: list[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def _replace_known_profiles(text: str, known_profiles: list[str]) -> str:
    replacement = f"known_profiles = {_toml_list(known_profiles)}"
    if re.search(r"^known_profiles\s*=\s*\[.*\]\s*$", text, flags=re.MULTILINE):
        return re.sub(r"^known_profiles\s*=\s*\[.*\]\s*$", replacement, text, count=1, flags=re.MULTILINE)

    marker_match = re.search(r"^\[profiles\]\s*$", text, flags=re.MULTILINE)
    if not marker_match:
        raise ValueError("config file is missing a [profiles] section")

    insert_at = marker_match.end()
    return text[:insert_at] + f"\n{replacement}" + text[insert_at:]


def _upsert_alias_mapping(text: str, alias: str, profile_name: str) -> str:
    alias_line = f'{alias} = "{profile_name}"'
    section_match = re.search(r"^\[profiles\.aliases\]\s*$", text, flags=re.MULTILINE)
    if not section_match:
        meta_match = re.search(r"^\[profiles\.meta(?:\.|\])", text, flags=re.MULTILINE)
        insert_at = meta_match.start() if meta_match else len(text)
        prefix = "" if text.endswith("\n") or insert_at == 0 else "\n"
        block = f"{prefix}[profiles.aliases]\n{alias_line}\n"
        return text[:insert_at] + block + text[insert_at:]

    section_start = section_match.end()
    next_section_match = re.search(r"^\[", text[section_start:], flags=re.MULTILINE)
    section_end = section_start + next_section_match.start() if next_section_match else len(text)
    section_text = text[section_start:section_end]
    alias_pattern = rf"^{re.escape(alias)}\s*=\s*.*$"
    if re.search(alias_pattern, section_text, flags=re.MULTILINE):
        section_text = re.sub(alias_pattern, alias_line, section_text, count=1, flags=re.MULTILINE)
    else:
        if section_text and not section_text.endswith("\n"):
            section_text += "\n"
        section_text += f"{alias_line}\n"
    return text[:section_start] + section_text + text[section_end:]


def update_profiles_config(config_path: Path, profile_name: str, alias: str | None) -> tuple[bool, bool]:
    if not config_path.exists():
        raise ValueError(f"config file does not exist: {config_path}")

    config_text = config_path.read_text(encoding="utf-8")
    config_data = load_settings(config_path)

    known_profiles = list(config_data.known_profiles)
    profile_added = False
    if profile_name not in known_profiles:
        known_profiles.append(profile_name)
        config_text = _replace_known_profiles(config_text, known_profiles)
        profile_added = True

    alias_added = False
    if alias:
        existing_target = config_data.aliases.get(alias)
        if existing_target and existing_target != profile_name:
            raise ValueError(f"alias already exists for a different profile: {alias} -> {existing_target}")
        if existing_target != profile_name:
            config_text = _upsert_alias_mapping(config_text, alias, profile_name)
            alias_added = True

    config_path.write_text(config_text, encoding="utf-8")
    return profile_added, alias_added


def prompt_for_alias(args: argparse.Namespace, profile_name: str) -> str | None:
    if args.alias is not None:
        value = args.alias.strip()
        return value or None
    if not sys.stdin.isatty():
        return None
    try:
        value = input(f"Alias for {profile_name} (optional): ").strip()
    except EOFError:
        return None
    return value or None


def configured_mcp_server(config_path: Path, name: str) -> dict[str, object] | None:
    if not config_path.exists():
        return None
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    server = data.get("mcp_servers", {}).get(name)
    return server if isinstance(server, dict) else None


def _json_rpc_request(url: str, payload: dict[str, object], session_id: str | None = None, timeout_seconds: float = 5.0) -> tuple[dict[str, object], str | None]:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    req = request.Request(url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout_seconds) as response:
        response_body = response.read().decode("utf-8")
        response_session = response.headers.get("mcp-session-id")
    return json.loads(response_body), response_session


def smoke_check_mcp_server(config_path: Path, name: str, required_tools: tuple[str, ...] = ()) -> dict[str, object]:
    server = configured_mcp_server(config_path, name)
    if not server:
        return {"name": name, "healthy": False, "issues": [f"missing MCP server config: {name}"], "tools": []}

    url = server.get("url")
    if isinstance(url, str) and url:
        return smoke_check_http_mcp_server(name, url, required_tools=required_tools)

    command = server.get("command")
    if isinstance(command, str) and command:
        args = server.get("args")
        cwd = server.get("cwd")
        env = server.get("env")
        return smoke_check_stdio_mcp_server(
            name,
            command,
            args=args if isinstance(args, list) else [],
            cwd=cwd if isinstance(cwd, str) else None,
            env=env if isinstance(env, dict) else {},
            required_tools=required_tools,
            smoke_tool=DEFAULT_MCP_SMOKE_TOOLS.get(name),
        )

    return {"name": name, "healthy": False, "issues": [f"MCP server has no supported url or command config: {name}"], "tools": []}


def smoke_check_http_mcp_server(name: str, url: str, required_tools: tuple[str, ...] = ()) -> dict[str, object]:
    try:
        initialize_payload, session_id = _json_rpc_request(
            url,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "codex-profiles-doctor", "version": "0.1"},
                },
            },
        )
        if "error" in initialize_payload:
            return {"name": name, "healthy": False, "issues": [f"initialize failed: {initialize_payload['error']}"], "tools": []}
        tools_payload, _ = _json_rpc_request(
            url,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            session_id=session_id,
        )
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"name": name, "healthy": False, "issues": [f"MCP probe failed: {exc}"], "tools": []}

    if "error" in tools_payload:
        return {"name": name, "healthy": False, "issues": [f"tools/list failed: {tools_payload['error']}"], "tools": []}

    tools = sorted(
        tool["name"]
        for tool in tools_payload.get("result", {}).get("tools", [])
        if isinstance(tool, dict) and isinstance(tool.get("name"), str)
    )
    missing_tools = [tool for tool in required_tools if tool not in tools]
    issues = [f"missing MCP tool: {tool}" for tool in missing_tools]
    return {"name": name, "transport": "streamable_http", "healthy": not issues, "issues": issues, "tools": tools}


def _stdio_mcp_env(extra_env: dict[object, object]) -> dict[str, str]:
    env = os.environ.copy()
    for key, value in extra_env.items():
        if isinstance(key, str) and isinstance(value, str):
            env[key] = value
    return env


def _stdio_json_rpc_send(process: subprocess.Popen[str], payload: dict[str, object]) -> None:
    if process.stdin is None:
        raise RuntimeError("stdio MCP process has no stdin")
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.flush()


def _stdio_json_rpc_read(process: subprocess.Popen[str], expected_id: int, timeout_seconds: float = 10.0) -> dict[str, object]:
    if process.stdout is None:
        raise RuntimeError("stdio MCP process has no stdout")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"stdio MCP process exited with code {process.returncode}")
        ready, _, _ = select.select([process.stdout], [], [], 0.1)
        if not ready:
            continue
        line = process.stdout.readline()
        if not line:
            continue
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("id") == expected_id:
            return payload
    raise TimeoutError(f"timed out waiting for MCP response id {expected_id}")


def _stdio_json_rpc_request(process: subprocess.Popen[str], payload: dict[str, object], timeout_seconds: float = 10.0) -> dict[str, object]:
    expected_id = payload.get("id")
    if not isinstance(expected_id, int):
        raise ValueError("stdio JSON-RPC request requires an integer id")
    _stdio_json_rpc_send(process, payload)
    return _stdio_json_rpc_read(process, expected_id, timeout_seconds=timeout_seconds)


def _extract_tools(tools_payload: dict[str, object]) -> list[str]:
    return sorted(
        tool["name"]
        for tool in tools_payload.get("result", {}).get("tools", [])  # type: ignore[union-attr]
        if isinstance(tool, dict) and isinstance(tool.get("name"), str)
    )


def _extract_first_version(candidate: object) -> str | None:
    if isinstance(candidate, dict):
        version = candidate.get("version")
        if isinstance(version, str):
            return version
        for value in candidate.values():
            found = _extract_first_version(value)
            if found:
                return found
    if isinstance(candidate, list):
        for value in candidate:
            found = _extract_first_version(value)
            if found:
                return found
    if isinstance(candidate, str):
        text = candidate.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                return _extract_first_version(json.loads(text))
            except json.JSONDecodeError:
                return None
    return None


def _command_version(command: str) -> str | None:
    try:
        completed = subprocess.run(
            [command, "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (completed.stdout or completed.stderr).strip()
    return output.splitlines()[0].strip() if output else None


def projection_compatibility_error(settings: Settings) -> str | None:
    codex_version = _command_version("codex")
    if not codex_version:
        return "compatibility check failed: codex is not available or did not report a version"
    status = compatibility_status(settings, codex_version=codex_version, tool_version=__version__)
    runtime_issues = compatibility_preflight_issues(settings)
    if status.compatible and not runtime_issues:
        return None
    issues = [*status.issues, *runtime_issues]
    return (
        "compatibility acceptance required before mutating legacy shared or projected Codex state: "
        f"{'; '.join(issues)}. Run 'codex-profiles compatibility --accept' after review."
    )


def compatibility_preflight_issues(settings: Settings) -> tuple[str, ...]:
    guard = ActiveProfileGuard(settings, "__compatibility__")
    issues: list[str] = []
    if guard.active_profiles():
        issues.append("Managed Codex profile sessions are running")
    if guard.codex_processes():
        issues.append("Codex processes are running")
    if issues:
        return tuple(issues)
    issues.extend(preflight_issues(settings))
    return tuple(issues)


def smoke_check_stdio_mcp_server(
    name: str,
    command: str,
    args: list[object],
    cwd: str | None,
    env: dict[object, object],
    required_tools: tuple[str, ...] = (),
    smoke_tool: str | None = None,
) -> dict[str, object]:
    command_args = [str(arg) for arg in args if isinstance(arg, (str, int, float))]
    issues: list[str] = []
    tools: list[str] = []
    smoke: dict[str, object] | None = None
    cli_version = _command_version(command)

    try:
        process = subprocess.Popen(
            [command, *command_args],
            cwd=cwd,
            env=_stdio_mcp_env(env),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        return {"name": name, "transport": "stdio", "healthy": False, "issues": [f"MCP launch failed: {exc}"], "tools": [], "cliVersion": cli_version}

    try:
        initialize_payload = _stdio_json_rpc_request(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "codex-profiles-doctor", "version": "0.1"},
                },
            },
        )
        if "error" in initialize_payload:
            issues.append(f"initialize failed: {initialize_payload['error']}")
        else:
            _stdio_json_rpc_send(process, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            tools_payload = _stdio_json_rpc_request(
                process,
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )
            if "error" in tools_payload:
                issues.append(f"tools/list failed: {tools_payload['error']}")
            else:
                tools = _extract_tools(tools_payload)
                issues.extend(f"missing MCP tool: {tool}" for tool in required_tools if tool not in tools)
                if smoke_tool:
                    if smoke_tool not in tools:
                        issues.append(f"missing MCP smoke tool: {smoke_tool}")
                    else:
                        smoke_payload = _stdio_json_rpc_request(
                            process,
                            {
                                "jsonrpc": "2.0",
                                "id": 3,
                                "method": "tools/call",
                                "params": {"name": smoke_tool, "arguments": {}},
                            },
                        )
                        if "error" in smoke_payload:
                            issues.append(f"{smoke_tool} failed: {smoke_payload['error']}")
                        else:
                            smoke_version = _extract_first_version(smoke_payload.get("result"))
                            smoke = {"tool": smoke_tool}
                            if smoke_version:
                                smoke["version"] = smoke_version
                            if cli_version and smoke_version and cli_version != smoke_version:
                                issues.append(f"version drift: cli={cli_version}, mcp={smoke_version}")
    except (RuntimeError, TimeoutError, ValueError) as exc:
        issues.append(f"MCP probe failed: {exc}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)

    record: dict[str, object] = {
        "name": name,
        "transport": "stdio",
        "healthy": not issues,
        "issues": issues,
        "tools": tools,
        "cliVersion": cli_version,
    }
    if smoke:
        record["smoke"] = smoke
    return record


def mcp_config_path_for_server(settings: Settings, preferred_config_path: Path, name: str) -> Path:
    if configured_mcp_server(preferred_config_path, name):
        return preferred_config_path
    return settings.shared_root / "config.toml"


def profile_record(settings: Settings, resolved_profile: str, requested_profile: str | None = None) -> dict[str, object]:
    snapshot = profile_snapshot(settings, resolved_profile)
    details = settings.profile_details(resolved_profile)
    issues = validate_profile(settings, resolved_profile) if settings.account_root(resolved_profile).exists() else []
    record: dict[str, object] = {
        **snapshot,
        "label": details.label,
        "owner": details.owner,
        "notes": details.notes,
        "default_profile": settings.resolve_profile_name(settings.default_profile) if settings.default_profile else None,
        "current_profile": settings.current_profile_resolved(),
        "issues": issues,
        "healthy": len(issues) == 0 if snapshot["exists"] == "yes" else False,
    }
    try:
        record["configuration"] = settings.configuration_view(resolved_profile)
    except (OSError, ValueError):
        record["configuration"] = {"status": "unavailable", "reason": "effective configuration cannot be read or parsed"}
    if requested_profile and requested_profile in settings.aliases:
        record["alias"] = requested_profile
        record["alias_target"] = settings.aliases[requested_profile]
    return record


def configured_and_discovered_profiles(settings: Settings) -> list[str]:
    configured = [settings.resolve_profile_name(name) for name in settings.known_profiles]
    discovered = [p.name for p in settings.state_root.glob(f"{settings.account_prefix}*")] if settings.state_root.exists() else []
    return sorted(set(configured + discovered))


def cmd_init(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    ensure_directory(settings.shared_root)
    ensure_directory(settings.shared_root / "log")
    if args.config and not args.config.exists():
        print(f"Config file not found, using defaults: {args.config}", file=sys.stderr)
    if args.profile:
        if requires_compatibility_gate(settings):
            compatibility_error = projection_compatibility_error(settings)
            if compatibility_error:
                print(compatibility_error, file=sys.stderr)
                return 1
        ensure_layout(settings, args.profile)
    print(f"Initialized shared root at {settings.shared_root}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    if not args.profile:
        args._subparser.print_help()
        return 1

    settings = settings_from_args(args)
    if args.profile in settings.aliases:
        print(f"cannot add profile using an existing alias name: {args.profile}", file=sys.stderr)
        return 1

    profile_name = settings.denormalize_profile_name(settings.normalize_profile_name(args.profile))
    alias = prompt_for_alias(args, profile_name)
    if alias and alias == profile_name:
        print("alias cannot be the same as the profile name", file=sys.stderr)
        return 1

    if alias and alias in settings.aliases and settings.aliases[alias] != profile_name:
        print(f"alias already exists for a different profile: {alias} -> {settings.aliases[alias]}", file=sys.stderr)
        return 1

    if requires_compatibility_gate(settings):
        compatibility_error = projection_compatibility_error(settings)
        if compatibility_error:
            print(compatibility_error, file=sys.stderr)
            return 1

    account_root = ensure_layout(settings, profile_name)
    profile_added = False
    alias_added = False
    if args.config:
        try:
            profile_added, alias_added = update_profiles_config(args.config, profile_name, alias)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    print(f"account_root={account_root}")
    print(f"profile={settings.normalize_profile_name(profile_name)}")
    if args.config:
        print(f"config={args.config}")
        print(f"config_profile_added={str(profile_added).lower()}")
        print(f"config_alias_added={str(alias_added).lower()}")
    if alias:
        print(f"alias={alias}")
    return 0


def cmd_aliases(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    payload = {
        alias: settings.resolve_profile_name(target)
        for alias, target in sorted(settings.aliases.items())
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    for alias, target in payload.items():
        print(f"{alias}={target}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    seen: set[str] = set()
    name_values: set[str] = set(settings.aliases.keys()) if args.names else set()

    for profile in settings.known_profiles:
        resolved = settings.resolve_profile_name(profile)
        if resolved in seen:
            continue
        seen.add(resolved)
        if args.names:
            name_values.add(settings.denormalize_profile_name(resolved))
            continue
        path = settings.state_root / resolved
        print(path if args.absolute else resolved)

    if not settings.state_root.exists():
        if args.names:
            for value in sorted(name_values):
                print(value)
        return 0
    for path in sorted(settings.state_root.iterdir()):
        if not path.is_dir():
            continue
        if path.name == settings.shared_dir_name:
            continue
        if not path.name.startswith(settings.account_prefix):
            continue
        if path.name in seen:
            continue
        if args.names:
            continue
        print(path if args.absolute else path.name)
    if args.names:
        for value in sorted(name_values):
            print(value)
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    try:
        resolved_profile = resolve_requested_profile(settings, args.profile)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    record = profile_record(settings, resolved_profile, requested_profile=args.profile)
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True))
        return 0
    for key, value in record.items():
        if value is None or key in {"issues", "healthy"}:
            continue
        print(f"{key}={value}")
    print(f"healthy={str(record['healthy']).lower()}")
    if record["issues"]:
        for issue in record["issues"]:
            print(f"issue={issue}")
    return 0


def cmd_which(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    try:
        resolved_profile = resolve_requested_profile(settings, args.profile)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    account_root = settings.account_root(resolved_profile)
    if args.shell:
        print(f"export CODEX_PROFILE={settings.denormalize_profile_name(resolved_profile)}")
        if settings.selection_mode == "launcher":
            print(f"export CODEX_HOME={shlex.quote(str(account_root))}")
            print(f"export CODEX_PROFILE_NAME={shlex.quote(resolved_profile)}")
        else:
            print("unset CODEX_HOME")
            print("unset CODEX_PROFILE_NAME")
        return 0
    if args.json:
        print(
            json.dumps(
                {
                    "profile": resolved_profile,
                    "selection_mode": settings.selection_mode,
                    "codex_home": str(account_root if settings.selection_mode == "launcher" else settings.source_root),
                    "profile_home": str(account_root),
                    "current_profile": settings.current_profile_resolved(),
                    "default_profile": settings.resolve_profile_name(settings.default_profile) if settings.default_profile else None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    print(f"profile={resolved_profile}")
    print(f"selection_mode={settings.selection_mode}")
    print(f"codex_home={account_root if settings.selection_mode == 'launcher' else settings.source_root}")
    print(f"profile_home={account_root}")
    current = settings.current_profile_resolved()
    if current:
        print(f"current_profile={current}")
    if settings.default_profile:
        print(f"default_profile={settings.resolve_profile_name(settings.default_profile)}")
    return 0


def cmd_use(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    try:
        resolved_profile = resolve_requested_profile(settings, args.profile)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    ensure_directory(settings.shared_root)
    closed_sessions: list[ClosedSession] = []
    if args.close_open_sessions:
        guard = ActiveProfileGuard(settings, resolved_profile)
        active_profiles = guard.active_profiles()
        profiles_to_close = tuple(profile for profile in active_profiles if profile != resolved_profile)
        closed_sessions = guard.close_profiles(profiles_to_close)
        closed_sessions.extend(guard.close_stock_codex_processes())

    if settings.selection_mode == "projection":
        compatibility_error = projection_compatibility_error(settings)
        if compatibility_error:
            print(compatibility_error, file=sys.stderr)
            return 1

    settings.current_profile_path.write_text(f"{settings.denormalize_profile_name(resolved_profile)}\n", encoding="utf-8")
    projection_actions = (
        project_profile(settings, resolved_profile)
        if settings.selection_mode == "projection"
        else []
    )

    if args.shell:
        print(f"export CODEX_PROFILE={settings.denormalize_profile_name(resolved_profile)}")
        if settings.selection_mode == "launcher":
            print(f"export CODEX_HOME={shlex.quote(str(settings.account_root(resolved_profile)))}")
            print(f"export CODEX_PROFILE_NAME={shlex.quote(resolved_profile)}")
        else:
            print("unset CODEX_HOME")
            print("unset CODEX_PROFILE_NAME")
        return 0
    if args.json:
        print(
            json.dumps(
                {
                    "current_profile": resolved_profile,
                    "selection_mode": settings.selection_mode,
                    "codex_home": str(settings.source_root),
                    "profile_home": str(settings.account_root(resolved_profile)),
                    "projection": projection_actions_payload(projection_actions),
                    "closed_sessions": [
                        {
                            "profile": session.profile,
                            "pid": session.pid,
                            "pid_file": str(session.pid_file),
                            "status": session.status,
                        }
                        for session in closed_sessions
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    print(f"current_profile={resolved_profile}")
    for action in projection_actions:
        if action.status == "applied":
            print(f"projection={action.kind}:{action.destination}")
    for session in closed_sessions:
        print(
            "closed_session="
            f"profile={session.profile},pid={session.pid},status={session.status}"
        )
    return 0


def cmd_project(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    if settings.selection_mode != "projection":
        print(
            "stock-home projection is disabled; set profiles.selection_mode = 'projection' only if legacy projection is required",
            file=sys.stderr,
        )
        return 1
    compatibility_error = projection_compatibility_error(settings)
    if compatibility_error:
        print(compatibility_error, file=sys.stderr)
        return 1
    try:
        resolved_profile = resolve_requested_profile(settings, args.profile)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    actions = project_profile(settings, resolved_profile)
    if args.json:
        print(
            json.dumps(
                {
                    "profile": resolved_profile,
                    "codex_home": str(settings.source_root),
                    "profile_home": str(settings.account_root(resolved_profile)),
                    "actions": projection_actions_payload(actions),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(f"profile={resolved_profile}")
    print(f"codex_home={settings.source_root}")
    for action in actions:
        print(f"{action.status:7} {action.kind:9} {action.source or '-'} -> {action.destination}")
        print(f"detail={action.detail}")
    return 0


def cmd_unproject(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    actions = unproject_profile(settings)
    if args.json:
        print(
            json.dumps(
                {
                    "codex_home": str(settings.source_root),
                    "actions": projection_actions_payload(actions),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(f"codex_home={settings.source_root}")
    for action in actions:
        print(f"{action.status:7} {action.kind:9} {action.source or '-'} -> {action.destination}")
        print(f"detail={action.detail}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    if args.profile:
        try:
            profiles = [resolve_requested_profile(settings, args.profile)]
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    else:
        profiles = configured_and_discovered_profiles(settings)
    if not profiles:
        print("No managed profiles found.")
        return 0

    records: list[dict[str, object]] = []
    failures = 0
    for profile in profiles:
        issues = validate_profile(settings, profile)
        record = {
            "profile": profile,
            "healthy": len(issues) == 0,
            "issues": issues,
        }
        records.append(record)
        if args.json:
            failures += len(issues)
            continue
        print(f"[{profile}]")
        if not issues:
            print("ok")
            continue
        for issue in issues:
            print(issue)
        print("issues found")
        failures += len(issues)
    mcp_records: list[dict[str, object]] = []
    for mcp_name in args.mcp:
        required_tools = tuple(args.mcp_required_tool) or DEFAULT_MCP_REQUIRED_TOOLS.get(mcp_name, ())
        mcp_config_path = mcp_config_path_for_server(settings, args.config, mcp_name)
        record = smoke_check_mcp_server(mcp_config_path, mcp_name, required_tools=required_tools)
        record["config"] = str(mcp_config_path)
        mcp_records.append(record)
        failures += len(record["issues"])
        if args.json:
            continue
        print(f"[mcp:{mcp_name}]")
        if record["healthy"]:
            print("ok")
        else:
            for issue in record["issues"]:
                print(issue)
            print("issues found")
        if record["tools"]:
            print(f"tools={','.join(record['tools'])}")
        if record.get("cliVersion"):
            print(f"cli_version={record['cliVersion']}")
        if isinstance(record.get("smoke"), dict):
            smoke = record["smoke"]
            smoke_text = ",".join(f"{key}={value}" for key, value in smoke.items())
            print(f"smoke={smoke_text}")
    if args.json:
        print(json.dumps({"profiles": records, "mcp": mcp_records, "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


def cmd_status(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    profiles = configured_and_discovered_profiles(settings)
    records = [profile_record(settings, profile) for profile in profiles]
    active_profiles = list(ActiveProfileGuard(settings, "__status__").active_profiles())
    payload = {
        "state_root": str(settings.state_root),
        "source_root": str(settings.source_root),
        "shared_root": str(settings.shared_root),
        "selection_mode": settings.selection_mode,
        "default_profile": settings.resolve_profile_name(settings.default_profile) if settings.default_profile else None,
        "current_profile": settings.current_profile_resolved(),
        "active_profiles": active_profiles,
        "profiles": records,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(f"state_root={payload['state_root']}")
    print(f"shared_root={payload['shared_root']}")
    print(f"selection_mode={payload['selection_mode']}")
    if payload["current_profile"]:
        print(f"current_profile={payload['current_profile']}")
    if payload["default_profile"]:
        print(f"default_profile={payload['default_profile']}")
    if payload["active_profiles"]:
        print(f"active_profiles={','.join(payload['active_profiles'])}")
    for record in records:
        print(f"[{record['profile']}]")
        print(f"exists={record['exists']}")
        print(f"healthy={str(record['healthy']).lower()}")
        if record["label"]:
            print(f"label={record['label']}")
        for issue in record["issues"]:
            print(f"issue={issue}")
    return 0


def cmd_compatibility(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    codex_version = _command_version("codex")
    if not codex_version:
        print("codex is not available or did not report a version", file=sys.stderr)
        return 1

    preflight = compatibility_preflight_issues(settings)
    if args.accept and not preflight:
        write_compatibility_receipt(settings, codex_version=codex_version, tool_version=__version__)
    status = compatibility_status(settings, codex_version=codex_version, tool_version=__version__)
    issues = [*preflight, *status.issues]
    payload = {
        "compatible": status.compatible and not preflight,
        "issues": issues,
        "codex_version": status.current.codex_version,
        "tool_version": status.current.tool_version,
        "policy_fingerprint": status.current.policy_fingerprint,
        "accepted_at": status.accepted.accepted_at if status.accepted else None,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"compatible={str(status.compatible).lower()}")
        print(f"codex_version={payload['codex_version']}")
        print(f"tool_version={payload['tool_version']}")
        print(f"policy_fingerprint={payload['policy_fingerprint']}")
        for issue in issues:
            print(f"issue={issue}")
    return 0 if payload["compatible"] else 1


def cmd_completion(args: argparse.Namespace) -> int:
    print(render_completion(args.shell), end="")
    return 0


def cmd_shell_init(args: argparse.Namespace) -> int:
    print(render_shell_init(args.shell), end="")
    return 0


def completion_dir_for_shell(shell: str, completion_dir: Path | None) -> Path:
    if completion_dir is not None:
        return completion_dir.expanduser()
    if shell == "zsh":
        return Path.home() / ".zsh" / "completions"
    return Path.home() / ".local" / "share" / "bash-completion" / "completions"


def cmd_install(args: argparse.Namespace) -> int:
    shell = args.shell
    bin_dir = args.bin_dir.expanduser()
    completion_dir = completion_dir_for_shell(shell, args.completion_dir)

    payload = install_payload(shell, args.repo_path, bin_dir, completion_dir)
    if args.print_only:
        print(f"launcher_path={payload['launcher_path']}")
        print(f"completion_path={payload['completion_path']}")
        print("shell_hint=add the bin dir to PATH and initialize your shell with 'eval \"$(codex-profiles shell-init zsh)\"' or the bash equivalent")
        return 0

    bin_dir.mkdir(parents=True, exist_ok=True)
    completion_dir.mkdir(parents=True, exist_ok=True)

    launcher_path = Path(payload["launcher_path"])
    launcher_path.write_text(payload["launcher_text"], encoding="utf-8")
    launcher_path.chmod(0o755)

    completion_path = Path(payload["completion_path"])
    completion_path.write_text(payload["completion_text"], encoding="utf-8")

    print(f"installed_launcher={launcher_path}")
    print(f"installed_completion={completion_path}")
    if shell == "zsh":
        print(f"shell_hint=ensure {bin_dir} is on PATH")
        print(f"shell_hint=add 'fpath=({completion_dir} $fpath)' before compinit in ~/.zshrc")
        print("shell_hint=add 'eval \"$(codex-profiles shell-init zsh)\"' to ~/.zshrc so plain codex follows codex-profiles use")
    else:
        print(f"shell_hint=ensure {bin_dir} is on PATH")
        print(f"shell_hint=source {completion_path} or place it in a bash-completion searched directory")
        print("shell_hint=add 'eval \"$(codex-profiles shell-init bash)\"' to ~/.bashrc so plain codex follows codex-profiles use")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    shell = args.shell
    bin_dir = args.bin_dir.expanduser()
    completion_dir = completion_dir_for_shell(shell, args.completion_dir)
    payload = install_payload(shell, Path.cwd(), bin_dir, completion_dir)
    paths = [Path(payload["launcher_path"]), Path(payload["completion_path"])]
    projection_actions: list[ProjectionAction] = []

    if args.print_only:
        print(f"launcher_path={payload['launcher_path']}")
        print(f"completion_path={payload['completion_path']}")
        print(f"keep_projection={str(args.keep_projection).lower()}")
        return 0

    if not args.keep_projection:
        settings = settings_from_args(args)
        projection_actions = unproject_profile(settings)

    removed: list[str] = []
    skipped: list[str] = []
    for path in paths:
        if path.exists() or path.is_symlink():
            path.unlink()
            removed.append(str(path))
        else:
            skipped.append(str(path))

    if args.json:
        print(
            json.dumps(
                {
                    "removed": removed,
                    "skipped": skipped,
                    "projection": projection_actions_payload(projection_actions),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    for path in removed:
        print(f"removed={path}")
    for path in skipped:
        print(f"skipped={path}")
    for action in projection_actions:
        if action.status == "applied":
            print(f"projection={action.kind}:{action.destination}")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    actions = plan_migration(settings)
    if not actions:
        print("No migration actions needed.")
        return 0

    if args.apply and args.dry_run:
        print("--apply and --dry-run cannot be used together", file=sys.stderr)
        return 1

    if args.apply:
        if requires_compatibility_gate(settings):
            compatibility_error = projection_compatibility_error(settings)
            if compatibility_error:
                print(compatibility_error, file=sys.stderr)
                return 1
        actions = apply_migration(settings, actions)
        if not args.json:
            print("Applied migration plan.")
    else:
        if not args.json:
            print("Planned migration only. Re-run with --apply to execute.")

    if args.json:
        print(
            json.dumps(
                {
                    "applied": args.apply,
                    "state_root": str(settings.state_root),
                    "shared_root": str(settings.shared_root),
                    "actions": migration_actions_payload(actions),
                    "rollback_notes": [] if args.apply else [
                        "planned link actions point back to source_root; copy actions only affect shared_root",
                        "review destination paths under shared_root before applying",
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    print_migration_actions(actions)
    if not args.apply:
        print("rollback_note=planned link actions point back to source_root; copy actions only affect shared_root")
        print("rollback_note=review destination paths under shared_root before applying")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if args.sudo_user and not args.sudo:
        print("--sudo-user requires --sudo", file=sys.stderr)
        return 1

    settings = settings_from_args(args)
    if not getattr(args, "build_manifest", None) and (settings.shared_root / "builds.json").is_file():
        args.build_manifest = settings.shared_root / "builds.json"
    if getattr(args, "channel", None) and not getattr(args, "build_manifest", None):
        print("explicit stock/modded selection requires a pinned build manifest", file=sys.stderr)
        return 2
    try:
        profile, codex_args = split_run_profile_and_args(settings, args.profile, list(args.codex_args))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    safety_issues = launcher_safety_issues(settings)
    if safety_issues:
        for issue in safety_issues:
            print(f"safety check failed: {issue}", file=sys.stderr)
        return 1
    if requires_compatibility_gate(settings):
        compatibility_error = projection_compatibility_error(settings)
        if compatibility_error:
            print(compatibility_error, file=sys.stderr)
            return 1
    account_root = ensure_layout(settings, profile)

    if getattr(args, "build_manifest", None):
        from .build_channels import BuildError, load_build, run_build
        if args.sudo:
            print("pinned build launch does not support sudo", file=sys.stderr)
            return 2
        try:
            if settings.check_upstream_releases and os.environ.get("CODEX_BUILD_UPDATE_CHECK") != "0":
                from .upgrades import schedule_check
                try:
                    checked = schedule_check(Path(args.build_manifest).parent)
                    release = checked.get("release", {})
                    message = "upstream " + release["latest_version"] if release.get("status") == "available" else checked["status"]
                except (OSError, ValueError):
                    message = "unavailable; retaining the selected build"
                print(f"[updates] {message}; activation remains explicit", file=sys.stderr)
            with ActiveProfileGuard(settings, profile, private_runtime=True):
                return run_build(load_build(Path(args.build_manifest), args.channel or "modded", account_root), account_root, profile, codex_args)
        except (BuildError, OSError, ValueError, BlockingIOError) as exc:
            print(f"build launch held: {exc}", file=sys.stderr)
            return 2

    env = account_environment(account_root, profile)

    try:
        command = build_codex_command(account_root, profile, codex_args, use_sudo=args.sudo, sudo_user=args.sudo_user)
        with ActiveProfileGuard(settings, profile):
            completed = subprocess.run(command, env=env, check=False)
    except BlockingIOError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        missing_command = exc.filename or str(exc)
        print(f"codex-profiles: '{missing_command}' is not on PATH", file=sys.stderr)
        return 1

    return completed.returncode


def profile_main() -> int:
    arguments = list(sys.argv[1:])
    if arguments and arguments[0].startswith("-") and arguments[0] not in ("--channel", "--build-manifest", "--sudo", "--sudo-user", "--"):
        arguments.insert(0, "--")
    return main(["run", *arguments])


def stock_main() -> int:
    return main(["run", "--channel", "stock", "--", *sys.argv[1:]])


def modded_main() -> int:
    return main(["run", "--channel", "modded", "--", *sys.argv[1:]])


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = list(sys.argv[1:] if argv is None else argv)
    offset = 0
    while offset < len(arguments):
        token = arguments[offset]
        if token in ("--config", "--state-root", "--source-root"):
            offset += 2
        elif token.startswith(("--config=", "--state-root=", "--source-root=")):
            offset += 1
        else:
            break
    if offset < len(arguments) and arguments[offset] in ("sessions", "upgrades", "continue"):
        header = parser.parse_args(arguments[:offset + 1])
        if header.state_root is not None or header.source_root is not None:
            parser.error("session and upgrade commands require explicit roots in their configuration or operation options")
        remaining = arguments[offset + 1:]
        if header.command == "sessions":
            from .history import main as history_main
            return history_main(["--config", str(header.config), *remaining])
        if header.command == "upgrades":
            from .upgrades import main as upgrades_main
            return upgrades_main(remaining)
        from .continuation import main as continuation_main
        return continuation_main(["--config", str(header.config), *remaining])
    args = parser.parse_args(arguments)

    commands = {
        "init": cmd_init,
        "add": cmd_add,
        "aliases": cmd_aliases,
        "list": cmd_list,
        "inspect": cmd_inspect,
        "which": cmd_which,
        "use": cmd_use,
        "project": cmd_project,
        "unproject": cmd_unproject,
        "doctor": cmd_doctor,
        "status": cmd_status,
        "compatibility": cmd_compatibility,
        "completion": cmd_completion,
        "shell-init": cmd_shell_init,
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "migrate": cmd_migrate,
        "run": cmd_run,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
