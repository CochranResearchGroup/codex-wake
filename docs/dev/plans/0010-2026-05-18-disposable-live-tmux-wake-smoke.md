# Disposable Live Tmux Wake Smoke

State: CLOSED
Lane: P10

## Scope

Run a live wake smoke against a disposable tmux pane running Codex so the daemon can inject the canonical prompt and observe the hook ack.

## Non-Goals

- Do not target a human's active Codex pane.
- Do not leave a background daemon running after the smoke.
- Do not broaden trigger types or app-server behavior in this slice.

## Current State

`codex-wake` and `codex-waked` are installed in user scope and verified through PATH-resolved commands. Live tmux injection has been verified against a disposable Codex TUI pane in `docs/dev/verification/0003-2026-05-18-disposable-live-tmux-wake-smoke.md`.

## Acceptance Criteria

- A disposable tmux session/pane is created and clearly identified.
- Codex runs in that pane with the repo-local hook configured or a documented equivalent.
- A wake is registered against that pane.
- `codex-waked --once` dispatches the wake.
- The hook ack file appears.
- The disposable tmux session is cleaned up.
- Any live limitation is recorded in a verification artifact.

## Definition Of Done

Closed after a disposable live tmux wake was verified. The final daemon-owned smoke observed `checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0` and the `UserPromptSubmit` hook wrote `.codex/wake/acks/wake_20260519_003526_bfaa.submitted`.
