#!/usr/bin/env bash
# Supported user installation: package install followed by completion activation.
set -euo pipefail
source_spec="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
shell_name=all
completion_home=
completion_enabled=true
while (($#)); do
  case "$1" in
    --source) source_spec="${2:?--source requires a package or source path}"; shift 2 ;;
    --shell) shell_name="${2:?--shell requires bash, zsh or all}"; shift 2 ;;
    --home) completion_home="${2:?--home requires a user home}"; shift 2 ;;
    --no-completion) completion_enabled=false; shift ;;
    --help|-h)
      printf '%s\n' 'Usage: scripts/install.sh [--source PACKAGE] [--shell bash|zsh|all] [--home PATH] [--no-completion]' 'Installs with uv and configures shell completion by default. Reload existing shells afterward.'
      exit 0 ;;
    *) printf 'Unknown installation option: %s\n' "$1" >&2; exit 2 ;;
  esac
done
case "$shell_name" in bash|zsh|all) ;; *) printf 'Unsupported shell: %s\n' "$shell_name" >&2; exit 2 ;; esac
uv tool install --force --reinstall "$source_spec"
if "$completion_enabled"; then
  tool_bin="$(uv tool dir --bin)"
  arguments=(completion install --shell "$shell_name")
  if [[ -n "$completion_home" ]]; then arguments+=(--home "$completion_home"); fi
  if ! "$tool_bin/codex-wake" "${arguments[@]}"; then
    printf '%s\n' 'Package installed, but completion setup failed. Existing shell configuration was preserved where ownership was uncertain. Resolve the reported conflict and run codex-wake completion install.' >&2
    exit 2
  fi
fi
printf '%s\n' 'Codex Wake installation completed.'
