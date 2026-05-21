# App Status Resume Mode

Date: 2026-05-21

## Scope

Clarify app-server wake target requirements and add a read-only resume-backed status check for app-server threads that are not currently loaded in a fresh app-server process.

## Non-Goals

- Do not start app-server turns.
- Do not implement thread discovery.
- Do not change dispatch semantics.
- Do not implement WebSocket app-server support.

## Current State

Closed by `docs/dev/verification/0037-2026-05-21-app-status-resume-mode.md`. `codex-wake app status --resume` now reports resume-backed status without starting a turn, while default `app status` remains a non-loading `thread/read` check.

## Plan

- Add `codex-wake app status --resume <thread-id>`.
- Keep default `app status` as a non-loading `thread/read` check.
- Implement the resume-backed status path with `thread/resume`, not `turn/start`.
- Document that app-server wake targets must be resumable rollout-backed threads.
- Record validation evidence with focused and full tests.

## Acceptance Criteria

- `app status --resume --json <thread-id>` reports status from `thread/resume`.
- `app status --json <thread-id>` continues to use `thread/read`.
- Tests distinguish read-backed and resume-backed status calls.
- Docs explain the `notLoaded` vs resumable-thread behavior.

## Definition Of Done

This lane can close when the status UX and docs match the P31 dogfood evidence and validation passes without starting a live turn.
