# Event Predicates

State: CLOSED
Lane: P17

## Scope

Add two non-shell event predicates:

- `file_changed`: fire when a watched path is created or changes mtime/size from registration time.
- `process_done`: fire when a registered positive PID no longer exists.

## Non-Goals

- Do not execute shell commands from wake records.
- Do not add inotify, entr, systemd timers, or platform-specific event loops.
- Do not solve PID reuse robustly in this slice.
- Do not require live tmux dispatch to validate predicate evaluation.

## Current State

The daemon previously supported `not_before` and `file_exists`. P17 adds `file_changed` and `process_done` through CLI creation, daemon evaluation, docs, and tests.

Validation evidence: [Event Predicates](../verification/0012-2026-05-19-event-predicates.md)

## Acceptance Criteria

- `codex-wake changed <path> -- <prompt>` creates a `file_changed` predicate with registration-time file state.
- Missing paths can be registered and fire when created.
- Existing paths fire when mtime or size changes.
- `codex-wake pid <pid> -- <prompt>` creates a `process_done` predicate for a live positive PID.
- The daemon moves ready records from `pending` to `firing` deterministically.
- Invalid predicate records fail with an inspectable `last_error`.
- README documents the new commands and limits.
- Validation evidence is recorded.

## Definition Of Done

This lane can close when source tests and CLI smokes cover creation and daemon evaluation for both predicates, with no live dispatch requirement.
