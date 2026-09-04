# App-Server Active Writer Policy

Date: 2026-08-25

Status: CLOSED

## Scope

Make Codex app-server wake behavior explicit when dispatch preflight finds that
the target thread already has an active writer.

The default is fail-fast with durable status evidence. Operators may opt into
bounded retry at wake creation time; retry uses the existing attempt limit and
app-server backoff schedule.

## Current State

Implemented and validated. App-server dispatch still avoids `turn/start` for
an active thread, now fails active-writer contention by default, and requeues
only when the wake target explicitly carries `retry_active_writer: true`.
CLI registration exposes that opt-in as `--retry-active-writer` on both the
dedicated app-server commands and the compatibility target options.

## Non-Goals

- Do not start a second turn while app-server reports the thread as active.
- Do not infer whether an active writer is safe to interrupt.
- Do not add unbounded retries or a daemon-global retry switch.
- Do not change retry behavior for tmux or OpenClaw Gateway transports.
- Do not run a live app-server wake as part of this source-level contract
  change.

## Implementation Slice

- Persist an additive app-server target policy selected by CLI registration.
- Fail active-writer contention by default with an actionable error.
- Add an explicit CLI opt-in that requeues under the existing bounded retry
  schedule.
- Cover legacy/default records and opted-in records with focused tests.
- Update the schema, operator docs, and agent skill guidance.

## Acceptance Criteria

- An app-server wake without an active-writer retry option becomes `failed`
  when preflight reports `active`, and it does not call `turn/start`.
- An app-server wake created with the retry option persists that choice and
  requeues on `active` using the existing `max_attempts` and backoff behavior.
- Older records without the additive option receive the default fail-fast
  behavior.
- Both `codex-wake app after|at` and compatibility
  `after|at --app-server-thread-id` creation surfaces support the opt-in.
- Focused tests, the complete source suite, compile checks, planning audit, and
  `git diff --check` pass.

## Definition Of Done

Code, tests, schema documentation, app-server operator guidance, README, and
the installed skill source describe one consistent default/optional retry
contract; P44 and this plan are closed with validation evidence in the
runbook.
