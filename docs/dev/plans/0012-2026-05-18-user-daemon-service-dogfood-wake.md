# User Daemon Service And Dogfood Wake

State: OPEN
Lane: P12

## Scope

Define and verify a user-scoped way to keep `codex-waked` running for a repo, then schedule a real dogfood wake that proves the operator path works outside a one-shot smoke.

## Non-Goals

- Do not install a system-level service.
- Do not target a human active Codex pane without an explicit disposable or consenting pane.
- Do not add new trigger predicates in this lane.

## Current State

`codex-waked --once` and foreground polling are verified. Operators still need a durable daemon-running pattern for repo-local wake roots.

## Acceptance Criteria

- A user-scoped service, launcher, or documented foreground runbook is selected.
- The selected path records logs and can be stopped cleanly.
- A dogfood wake is registered and resolved through the selected path.
- Failure and cleanup commands are documented.
- Validation evidence is recorded.

## Definition Of Done

This lane can close when a repo-local wake daemon can be started, observed, stopped, and used to resolve at least one dogfood wake.
