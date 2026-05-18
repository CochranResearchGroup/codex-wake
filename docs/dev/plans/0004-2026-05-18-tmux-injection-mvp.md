# Tmux Injection MVP

State: OPEN
Lane: P04

## Scope

Implement the tmux injector that handles records in `firing` by submitting the canonical wake prompt into the captured Codex TUI pane.

## Non-Goals

- Do not implement the Codex `UserPromptSubmit` hook in this slice.
- Do not mark records `submitted` without an ack file.
- Do not implement app-server transport in this slice.
- Do not paste the full continuation prompt into tmux.

## Current State

`codex-waked` can evaluate pending records and move ready records to `firing`. No injection or ack waiting exists yet.

## Acceptance Criteria

- The injector builds the canonical prompt from wake id only.
- The injector uses the record's tmux socket and pane target.
- The injector writes a temporary prompt file or tmux buffer without shell-interpolating prompt text.
- Unsafe pane heuristics reject obvious non-dispatch states.
- Per-pane locks prevent concurrent dispatch into the same pane.
- Missing ack results in a bounded requeue rather than tight retry.
- Focused tests cover prompt construction, unsafe pane detection, lock behavior, and no-full-prompt injection.

## Definition Of Done

The plan can close when firing records can be safely dispatched to tmux in a dry-run/testable injector path and missing ack behavior is deterministic.
