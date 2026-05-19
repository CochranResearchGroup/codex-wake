# Service Installer CLI

State: CLOSED
Lane: P13

## Scope

Add an operator CLI surface for managing a repo-local user service without hand-copying systemd units.

## Non-Goals

- Do not install system-level services.
- Do not manage hook trust.
- Do not support non-systemd service managers in this slice.

## Current State

P12 verified the user systemd service path and dogfood wake. P13 adds `codex-wake service` commands for unit install, status, logs, stop, and uninstall.

## Acceptance Criteria

- `codex-wake service install` writes a repo-specific user unit.
- `codex-wake service status` shows service state and unit path.
- `codex-wake service logs` shows recent activity.
- `codex-wake service stop` stops the service cleanly.
- `codex-wake service uninstall` disables and removes the service file.
- Tests cover unit rendering and command behavior where practical.
- Installed command validation is refreshed.

## Definition Of Done

Closed by `docs/dev/verification/0006-2026-05-18-service-installer-cli.md`.
