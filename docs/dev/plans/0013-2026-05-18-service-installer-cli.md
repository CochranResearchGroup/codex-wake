# Service Installer CLI

State: OPEN
Lane: P13

## Scope

Add an operator CLI surface for managing a repo-local user service without hand-copying systemd units.

## Non-Goals

- Do not install system-level services.
- Do not manage hook trust.
- Do not support non-systemd service managers in this slice.

## Current State

P12 verified the user systemd service path and dogfood wake, but service setup still requires manual file copy and `systemctl --user` commands.

## Acceptance Criteria

- `codex-wake service install` writes a repo-specific user unit.
- `codex-wake service status` shows service state and unit path.
- `codex-wake service logs` shows recent activity.
- `codex-wake service stop` stops the service cleanly.
- `codex-wake service uninstall` disables and removes the service file.
- Tests cover unit rendering and command behavior where practical.
- Installed command validation is refreshed.

## Definition Of Done

This lane can close when an operator can manage the verified user service path through `codex-wake` itself.
