# Installed Runtime Verification

State: OPEN
Lane: P08

## Scope

Verify the installed Codex Wake executable surface end to end from a user/operator perspective.

## Non-Goals

- Do not add new trigger types in this slice.
- Do not expose app-server WebSocket mode in this slice.
- Do not merge or release without a clean installed smoke.

## Current State

The feature branch includes CLI creation/inspection/cancel/archive commands, `codex-waked`, tmux injection, Codex hook ack/context loading, and stdio app-server dispatch. Validation has mostly used source-tree and temporary package-target runs.

## Acceptance Criteria

- Installed `codex-wake --help` works.
- Installed `codex-waked --once --no-dispatch` works.
- Installed CLI can create, list, cancel, and archive a wake.
- Installed hook wrapper can write an ack from a JSON payload.
- A daemon smoke can move an already-due wake to `firing` with `--no-dispatch`.
- A dry/testable dispatch path is documented for tmux and app-server modes.
- Any live tmux or app-server limitation is recorded before opening a PR.

## Definition Of Done

The plan can close when the installed runtime surface has been verified and the branch is ready for PR review or merge.
