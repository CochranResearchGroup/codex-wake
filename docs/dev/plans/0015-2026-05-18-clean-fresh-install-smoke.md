# Clean Fresh Install Smoke

State: CLOSED
Lane: P15

## Scope

Verify the published release install path from a clean environment, independent of the local source checkout.

## Non-Goals

- Do not add new features.
- Do not target a human active Codex pane.
- Do not require PyPI publication.

## Current State

Local source, user-scoped installs, and the public `v0.3.0` tag install path are validated.

## Acceptance Criteria

- Install from the GitHub release tag into a clean tool or temporary environment.
- Verify `codex-wake`, `codex-waked`, and `codex-wake-hook`.
- Run `codex-wake doctor`.
- Run `codex-wake hook install/check` against a temporary repo.
- Optionally run service install/status/uninstall with a temporary service name if user systemd is available.
- Record evidence.

## Definition Of Done

Closed by `docs/dev/verification/0008-2026-05-18-clean-fresh-install-smoke.md`.
