# Release Packaging And Install Docs

State: CLOSED
Lane: P11

## Scope

Prepare the first operator-facing release surface for the verified wake spooler MVP.

## Non-Goals

- Do not add new trigger types.
- Do not change app-server dispatch behavior.
- Do not automate global hook trust decisions for users.

## Current State

The MVP has verified CLI lifecycle, daemon predicate movement, hook ack behavior, app-server target creation, and disposable live tmux wake dispatch. README install docs, v0.1.0 release notes, package metadata, and refreshed user-scope install evidence are complete.

## Acceptance Criteria

- README includes install, hook setup, daemon usage, and minimal examples.
- Release notes describe the tmux/hook MVP and known trust gate.
- Package version is intentionally chosen for the first published release or patch release.
- User-scope install is refreshed after any version or injector change.
- Validation evidence is recorded.

## Definition Of Done

Closed by README install docs, `docs/releases/v0.1.0.md`, `codex-wake-hook` packaging, and `docs/dev/verification/0004-2026-05-18-release-packaging-install-docs.md`.
