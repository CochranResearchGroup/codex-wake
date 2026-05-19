# Clean Fresh Install Smoke

State: OPEN
Lane: P15

## Scope

Verify the published release install path from a clean environment, independent of the local source checkout.

## Non-Goals

- Do not add new features.
- Do not target a human active Codex pane.
- Do not require PyPI publication.

## Current State

Local source and user-scoped installs are validated. A clean release-tag install is still the best confirmation that README install commands work from the public upstream.

## Acceptance Criteria

- Install from the GitHub release tag into a clean tool or temporary environment.
- Verify `codex-wake`, `codex-waked`, and `codex-wake-hook`.
- Run `codex-wake doctor`.
- Run `codex-wake hook install/check` against a temporary repo.
- Optionally run service install/status/uninstall with a temporary service name if user systemd is available.
- Record evidence.

## Definition Of Done

This lane can close when the public tag install path works without relying on the local checkout.
