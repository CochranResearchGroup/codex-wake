# Wake Daemon And Trigger Engine

State: OPEN
Lane: P03

## Scope

Implement `codex-waked`, a small polling daemon that reads pending wake records, evaluates MVP predicates, and moves records through deterministic status transitions.

## Non-Goals

- Do not implement tmux paste injection in this slice.
- Do not implement Codex hooks in this slice.
- Do not implement app-server transport in this slice.
- Do not implement arbitrary command predicates.

## Current State

The `codex-wake` CLI can create, list, show, and cancel declarative wake records. No daemon evaluates predicates yet.

## Acceptance Criteria

- `codex-waked` polls a wake root.
- `not_before` records fire when `due_at <= now`.
- `file_exists` records fire when the referenced path exists relative to the creating cwd unless absolute.
- Predicate matches append stable event records.
- Matching records move from `pending` to `firing`.
- Records with invalid predicates move to `failed` with a clear error.
- Focused tests cover predicate evaluation and status movement.

## Definition Of Done

The plan can close when `codex-waked` can deterministically move eligible records into `firing` and tests cover both MVP predicates.
