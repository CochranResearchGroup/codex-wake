# Disposable Live Tmux Wake Smoke

State: OPEN
Lane: P10

## Scope

Run a live wake smoke against a disposable tmux pane running Codex so the daemon can inject the canonical prompt and observe the hook ack.

## Non-Goals

- Do not target a human's active Codex pane.
- Do not leave a background daemon running after the smoke.
- Do not broaden trigger types or app-server behavior in this slice.

## Current State

`codex-wake` and `codex-waked` are installed in user scope and verified through PATH-resolved commands. Live tmux injection has not yet been attempted.

## Acceptance Criteria

- A disposable tmux session/pane is created and clearly identified.
- Codex runs in that pane with the repo-local hook configured or a documented equivalent.
- A wake is registered against that pane.
- `codex-waked --once` dispatches the wake.
- The hook ack file appears.
- The disposable tmux session is cleaned up.
- Any live limitation is recorded in a verification artifact.

## Definition Of Done

The plan can close when a disposable live tmux wake is verified or a precise blocker is recorded with the exact command and failure output.
