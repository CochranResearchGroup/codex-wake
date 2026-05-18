# Initial Wake Timer Design

State: CLOSED
Lane: P01

## Scope

Design the first durable product shape for a wake spooler that TUI-bound Codex agents can use to register delayed work, inspect wake state, and resume from a deterministic handoff.

## Non-Goals

- Do not implement scheduler code in this slice.
- Do not implement scheduler code in this slice.
- Do not commit to systemd, cron, `at`, inotify, or SQLite before the MVP state contract is defined.
- Do not store raw private transcripts or credentials in tracked fixtures.
- Do not build a general TUI controller; the intended shape is a narrow wake spooler.

## Current State

The repo has an accepted P01 design artifact at `docs/dev/0001-wake-spooler-design.md`. No source tree, package manifest, CLI, runtime state schema implementation, or tests exist yet.

## Design Questions

- What is the minimum wake-record schema?
- Which trigger types belong in the first version?
- What is the status vocabulary for pending, fired, failed, expired, cancelled, and acknowledged wake requests?
- What is the agent-facing command surface?
- Where does user-scoped runtime state live?
- What evidence does a future agent need to trust that a wake fired or failed?
- What pane-state heuristics are sufficient for MVP tmux injection?
- What transition path should exist from tmux MVP to app-server controlled mode?

## Acceptance Criteria

- A written wake-record contract exists.
- A first trigger vocabulary exists.
- Runtime state boundaries are explicit.
- The first CLI/API surface is specified.
- Validation expectations are defined before implementation begins.
- The roadmap lanes distinguish CLI, daemon, tmux injection, hook ack, runtime state safety, app-server mode, and installed verification.

## Definition Of Done

Closed on 2026-05-18. The next active slice is P02, tracked in `docs/dev/plans/0002-2026-05-18-agent-facing-cli.md`.
