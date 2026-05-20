# Controlled Live Dispatch Dogfood

Date: 2026-05-20

## Scope

Dogfood one live tmux dispatch against the current Codex TUI pane with explicit preflight checks, bounded runtime, and cleanup expectations.

## Non-Goals

- Do not add new product behavior.
- Do not run an unbounded daemon loop.
- Do not dispatch while the pane is visibly running a tool or waiting on approval.
- Do not leave a pending, firing, or requeued dogfood wake behind.

## Current State

Closed by `docs/dev/verification/0031-2026-05-20-live-dispatch-dogfood.md`. The installed daemon injected the canonical wake prompt into the active tmux pane, the hook acknowledged it, the wake record moved to `submitted`, and the dogfood record was archived with no active wake left behind.

## Plan

- Capture preflight `doctor --json`, `status --json`, tmux environment, pane snapshot, and lock state.
- Register one short tmux-targeted dogfood wake.
- Schedule one delayed `codex-waked --once` run after this turn can go idle.
- Bound ack waiting with a short timeout.
- On the wake-triggered turn, inspect the wake record, ack file, status summary, and daemon result evidence.
- Archive or otherwise clean up the dogfood wake if needed.

## Acceptance Criteria

- Preflight shows installed runtime, hook config, no active wake, and no stale lock.
- One dogfood wake is created with a tmux target for the current pane.
- Dispatch is attempted after the current turn has an opportunity to go idle.
- The outcome is recorded as submitted, requeued, failed, or explicitly cancelled.
- Hook ack is checked directly; missing ack is not treated as proof of tmux failure.
- Verification records the exact wake id and command evidence.

## Definition Of Done

This lane can close when live-dispatch evidence is recorded and no dogfood wake remains ambiguously active.
