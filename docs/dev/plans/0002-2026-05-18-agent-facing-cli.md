# Agent-Facing CLI

State: CLOSED
Lane: P02

## Scope

Implement the first `codex-wake` command-line surface for creating and inspecting declarative wake records.

## Non-Goals

- Do not implement tmux injection in this slice.
- Do not implement a long-running daemon in this slice.
- Do not implement app-server transport in this slice.
- Do not execute commands from trigger records.

## Current State

P01 produced the accepted wake-spooler design in `docs/dev/0001-wake-spooler-design.md`. The repo does not yet have source code, package metadata, tests, or an executable CLI.

## Acceptance Criteria

- `codex-wake after <duration> -- <prompt>` writes a schema-versioned `not_before` wake.
- `codex-wake at <timestamp> -- <prompt>` writes a schema-versioned `not_before` wake with UTC `due_at`.
- `codex-wake file <path> -- <prompt>` writes a schema-versioned `file_exists` wake.
- `codex-wake list` lists active wakes without mutating state.
- `codex-wake show <wake-id>` prints a wake record.
- `codex-wake cancel <wake-id>` marks a wake cancelled.
- Unit tests cover duration parsing, timestamp normalization, wake id generation shape, and JSON schema basics.

## Definition Of Done

Closed on 2026-05-18. The CLI exists, focused tests pass, and `ROADMAP.md` has opened the daemon lane.
