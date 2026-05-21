# Disposable App-Server Dogfood

Date: 2026-05-21

## Scope

Dogfood the released app-server wake path against one disposable app-server thread, using the P30 status preflight before `turn/start`.

## Non-Goals

- Do not target the active TUI thread.
- Do not use WebSocket app-server dispatch.
- Do not add new product behavior unless the dogfood exposes a concrete bug.
- Do not leave an active dogfood wake behind.

## Current State

Closed by `docs/dev/verification/0036-2026-05-21-disposable-app-server-dogfood.md`. The released app-server wake path succeeded against a disposable thread with a persisted rollout, recording idle preflight and `turn/start` acceptance. A `thread/start`-only target failed because no rollout existed for later resume.

## Plan

- Create one disposable app-server thread through local `codex app-server --listen stdio://`.
- Verify `codex-wake app status <thread-id> --json` reports the thread and status.
- Register a short `codex-wake app after <thread-id>` wake in a temporary dogfood wake root.
- Run `codex-waked --once` against that wake root.
- Verify the wake record moved through `predicate_matched`, `dispatch_attempt`, `app_server_preflight`, and `ack_observed`.
- Archive the submitted wake.
- Record whether `turn/start` was accepted and whether any operator cleanup is needed.

## Acceptance Criteria

- The target thread id is created by the current dogfood and is not the active TUI session.
- The app-server status helper runs before dispatch.
- Dispatch evidence shows an idle preflight before `turn/start`.
- The wake reaches `submitted` or a first-class failure/requeue state.
- No pending or firing dogfood wake remains.

## Definition Of Done

This lane can close when one disposable app-server wake is registered, evaluated, dispatched or explicitly failed, cleaned up, and documented with command evidence.
