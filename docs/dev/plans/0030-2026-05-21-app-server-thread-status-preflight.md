# App-Server Thread Status Preflight

Date: 2026-05-21

## Scope

Add a bounded app-server thread-status preflight so future app-server wake dispatch does not blindly call `turn/start` against an active or unhealthy thread.

## Non-Goals

- Do not dogfood live app-server dispatch in this slice.
- Do not implement WebSocket dispatch.
- Do not add OAuth or credential bootstrap.
- Do not change tmux dispatch behavior.

## Current State

Closed by `docs/dev/verification/0034-2026-05-21-app-server-thread-status-preflight.md`. App-server dispatch now records resumed-thread status before `turn/start`, submits only idle threads, and requeues active threads with backoff. `codex-wake app status <thread-id>` provides a read-only thread status helper.

## Plan

- Add a read-only app-server client method for `thread/read`.
- Add `codex-wake app status <thread-id>` with JSON and text output.
- Inspect resumed-thread status before `turn/start`.
- Allow dispatch only when status is `idle`.
- Requeue active threads with backoff and fail malformed or unhealthy non-idle status.
- Cover the preflight with focused unit tests.
- Update app-server docs and record verification.

## Acceptance Criteria

- `codex-wake app status <thread-id> --json` reports thread id and status without starting a turn.
- App-server dispatch records status preflight evidence before `turn/start`.
- Active threads are not submitted to `turn/start`.
- Tests cover idle dispatch, active-thread requeue, and CLI status output.
- Validation includes source tests for app-server behavior.

## Definition Of Done

This lane can close when the app-server preflight is implemented, documented, validated, and no live app-server turn has been started by the verification process.
