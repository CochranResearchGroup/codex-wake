# Wake Spooler Design

Status: ACCEPTED
Date: 2026-05-18
Roadmap Lane: P01

## Purpose

Codex Wake is a local wake spooler for TUI-bound Codex agents. It gives an agent a narrow command surface for registering delayed follow-up work, while deterministic runtime code owns persistence, trigger evaluation, target selection, retries, and final status.

This project is not a general TUI automation controller. The first product contract is:

```text
Codex TUI agent
  -> codex-wake after/at/file ...
  -> validated trigger record
  -> codex-waked evaluates predicates
  -> tmux injector submits a short canonical prompt
  -> UserPromptSubmit hook records ack and loads full context
```

## Design Principles

- The model may request a wake, but it does not own the timer.
- Wake records are declarative data, not executable scripts.
- The daemon owns trigger evaluation, state transitions, retry policy, and target dispatch.
- The injector pastes only a short wake id prompt.
- The hook loads full context after Codex accepts the wake prompt.
- Every wake prompt must be idempotent and must first verify whether the work is already complete.
- Missing ack, unsafe pane state, timeout, cancellation, and duplicate dispatch are explicit outcomes.

## MVP Transport

The MVP transport is tmux.

At trigger creation, `codex-wake` captures:

- current working directory
- `TMUX_PANE`
- tmux socket or enough environment to resolve it
- creation timestamp
- trigger predicate
- continuation prompt

At trigger firing, `codex-waked` uses a tmux injector to:

- acquire a per-pane lock
- capture the pane before injection
- reject obvious unsafe pane states
- paste the canonical wake prompt
- press Enter
- wait for a hook ack file

The canonical prompt is:

```text
WAKE_TRIGGER_ID=<wake-id>
Resume the scheduled wake task.
```

The full continuation text remains in the wake record and is added to model-visible context by the hook.

## Future Transport

The preferred controlled transport is Codex app-server.

That mode should:

- store an app-server thread id when available
- resume the thread with `thread/resume`
- start the wake turn with `turn/start`
- avoid terminal paste heuristics
- require localhost, SSH forwarding, or authenticated TLS for WebSocket use

`codex exec resume <session-id> ...` remains a fallback when a live TUI pane is not required.

## Runtime Root

Default runtime root:

```text
.codex/wake/
```

Initial layout:

```text
.codex/wake/
  pending/
  firing/
  submitted/
  failed/
  cancelled/
  expired/
  acks/
  logs/
  locks/
  archive/
```

The runtime root is intentionally ignored by git. Fixtures and examples belong under tracked docs or tests, not under live runtime directories.

## Wake Record Schema

Version 1 wake records are JSON objects.

Required fields:

```json
{
  "schema_version": 1,
  "id": "wake_20260518_153000_9f3a",
  "created_at": "2026-05-18T20:30:00Z",
  "updated_at": "2026-05-18T20:30:00Z",
  "cwd": "/home/user/project",
  "target": {
    "transport": "tmux",
    "tmux_socket": "/tmp/tmux-1000/default",
    "pane": "%11"
  },
  "predicate": {
    "type": "not_before",
    "due_at": "2026-05-18T21:15:00Z"
  },
  "prompt": "This is wake trigger wake_20260518_153000_9f3a. First verify whether the task is already complete. If not, continue from the recorded context.",
  "status": "pending",
  "attempts": 0,
  "max_attempts": 3,
  "ack_timeout_seconds": 30,
  "next_attempt_at": "2026-05-18T21:15:00Z",
  "events": []
}
```

Optional fields:

- `created_by_session`
- `created_by_profile`
- `expires_at`
- `last_error`
- `context_paths`
- `evidence_paths`
- `result_summary`

## Predicates

MVP predicates:

- `not_before`: fires when `due_at <= now`.
- `file_exists`: fires when the path exists relative to `cwd`, unless absolute.

Deferred predicates:

- `file_changed`: requires recording the file's registration-time stat data.
- `process_done`: requires clear ownership and stale-pid handling.
- external checks: require an explicit safety design.
- arbitrary command predicates: out of scope.

Predicate records must be declarative. They must not contain shell commands.

## Status Vocabulary

Allowed statuses:

- `pending`: created and awaiting predicate.
- `firing`: predicate matched and dispatch is in progress.
- `submitted`: Codex hook ack was observed.
- `failed`: dispatch or validation failed permanently.
- `cancelled`: user or operator cancelled the wake.
- `expired`: wake exceeded its expiry before successful submission.
- `archived`: wake was moved out of active state after retention handling.

The daemon may derive operational substate from `events`, `attempts`, `next_attempt_at`, and `last_error`; it should not create ad hoc status strings.

## Event Records

Every meaningful transition appends an event object:

```json
{
  "at": "2026-05-18T21:15:03Z",
  "type": "dispatch_attempt",
  "message": "Pasting canonical wake prompt into tmux pane %11",
  "attempt": 1
}
```

Event types should be stable enough for tests and operator inspection.

Initial event types:

- `created`
- `predicate_matched`
- `dispatch_attempt`
- `unsafe_pane`
- `ack_observed`
- `ack_timeout`
- `requeued`
- `failed`
- `cancelled`
- `expired`
- `archived`

## Hook Ack Contract

The `UserPromptSubmit` hook self-filters for:

```text
WAKE_TRIGGER_ID=<wake-id>
```

On match, it writes:

```text
.codex/wake/acks/<wake-id>.submitted
```

Ack JSON:

```json
{
  "wake_id": "wake_20260518_153000_9f3a",
  "submitted_at": "2026-05-18T21:15:05Z",
  "turn_id": "turn_...",
  "session_id": "session_..."
}
```

The hook also loads the wake JSON and adds developer context containing:

- wake id
- predicate
- original prompt
- evidence paths
- instruction to verify the predicate before editing files

If the trigger file is missing, the hook still writes an ack and adds context telling the agent to inspect `.codex/wake/` before proceeding.

## Unsafe Pane Heuristics

The MVP tmux injector should inspect captured pane text before dispatch and reject obvious unsafe states.

Initial reject patterns:

- approval or confirmation prompt
- active tool command still streaming
- shell prompt instead of Codex TUI
- existing partial input at the prompt
- pane no longer exists

These heuristics are intentionally conservative. False negatives are worse than delayed wakes.

## Retry Policy

Default policy:

- set `status=firing` before injection
- attempt dispatch
- wait up to `ack_timeout_seconds`
- if no ack, requeue with bounded backoff
- after `max_attempts`, mark `failed`

Backoff:

- attempt 1: immediate
- attempt 2: 60 seconds
- attempt 3: 300 seconds

The daemon must not retry in a tight loop.

## CLI Contract

Initial commands:

```bash
codex-wake after 45m -- "Continue the migration..."
codex-wake at "2026-05-18T17:30:00-05:00" -- "Check whether the release branch is ready."
codex-wake file .codex/events/pytest.done -- "Pytest finished. Read .codex/events/pytest.log."
codex-wake list
codex-wake show <wake-id>
codex-wake cancel <wake-id>
```

Creation commands print the wake id and trigger path.

Inspection commands must read state without mutating it, except `cancel`.

## Validation Requirements

Before MVP can be called working:

- `after` creates a valid `not_before` wake.
- `at` creates a valid UTC `not_before` wake.
- `file` creates a valid `file_exists` wake.
- daemon changes `pending -> firing -> submitted` when the hook ack appears.
- daemon changes `firing -> pending` with backoff when ack is missing.
- daemon changes `firing -> failed` after max attempts.
- cancellation is explicit and inspectable.
- trigger JSON never executes commands.
- runtime state survives process restart.

## Open Questions

- Whether v1 should use one JSON file moved between status directories, or one stable file with a status field plus indexes.
- Whether `created_by_session` can be reliably captured from current Codex TUI environment.
- Whether pane-state heuristics should be configurable per Codex version.
- Whether the app-server mode should become v2 or a parallel v1 transport.
