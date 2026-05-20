# Status Summary Dogfood

Date: 2026-05-20

## Scope

Dogfood the released `status --json` surface against the repo-local wake root with a bounded short wake trigger, then record whether the compact summary is useful for supervising wake lifecycle state.

## Non-Goals

- Do not add new product behavior.
- Do not rely on tracked fixtures for runtime state.
- Do not claim live TUI wake success unless dispatch and hook ack evidence are observed.
- Do not leave a long-lived pending wake behind.

## Current State

Closed by [Status Summary Dogfood](../verification/0028-2026-05-20-status-dogfood.md).

## Plan

- Refresh the user-scoped installed `codex-wake` runtime to `v0.4.7`.
- Capture baseline `doctor --json` and `status --json`.
- Register a short repo-local tmux-targeted wake with a dogfood-specific prompt.
- Use `status --json` to verify the pending summary.
- Run or start the repo-scoped daemon long enough to evaluate the due trigger.
- Inspect wake record movement, hook ack evidence, and `status --json` after evaluation.
- Clean up or archive the dogfood wake if it reaches a terminal state.

## Acceptance Criteria

- Installed `codex-wake` exposes `status`.
- A dogfood wake is created in `.codex/wake/pending`.
- `status --json` shows the expected active count while the wake is pending.
- Trigger evaluation moves the wake deterministically or records a clear failure/requeue state.
- Closeout records whether hook ack was observed.
- No dogfood wake is left ambiguously pending.

## Definition Of Done

This lane can close when the dogfood wake lifecycle evidence is recorded in verification docs, and the repo is left in a clean source state.
