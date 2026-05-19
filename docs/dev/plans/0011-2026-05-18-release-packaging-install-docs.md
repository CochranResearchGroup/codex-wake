# Release Packaging And Install Docs

State: OPEN
Lane: P11

## Scope

Prepare the first operator-facing release surface for the verified wake spooler MVP.

## Non-Goals

- Do not add new trigger types.
- Do not change app-server dispatch behavior.
- Do not automate global hook trust decisions for users.

## Current State

The MVP has verified CLI lifecycle, daemon predicate movement, hook ack behavior, app-server target creation, and disposable live tmux wake dispatch. The repo still needs fresh-install instructions and a release-ready version boundary.

## Acceptance Criteria

- README includes install, hook setup, daemon usage, and minimal examples.
- Release notes describe the tmux/hook MVP and known trust gate.
- Package version is intentionally chosen for the first published release or patch release.
- User-scope install is refreshed after any version or injector change.
- Validation evidence is recorded.

## Definition Of Done

This lane can close when a fresh operator can install the tool, enable the hook, run a wake, and understand current limitations from tracked docs.
