# App-Server Contract Refresh

Date: 2026-05-20

## Scope

Refresh the app-server controlled-dispatch design against the currently installed Codex CLI and generated app-server schema.

## Non-Goals

- Do not expose WebSocket app-server dispatch.
- Do not start a live wake turn in an existing user thread.
- Do not replace the proven tmux path.
- Do not add OAuth or token acquisition logic; local stdio app-server uses the local Codex CLI auth boundary.

## Current State

P07 implemented a stdio app-server dispatch path using `initialize`, `thread/resume`, and `turn/start`. The design doc was last verified with Codex CLI `0.130.0`. The current local Codex CLI is `0.131.0`, and `codex app-server generate-json-schema` now requires `--out <DIR>` and emits v2 protocol schema files.

## Plan

- Verify local `codex app-server --help` for transports and auth options.
- Generate the current JSON schema and inspect `ThreadResumeParams`, `TurnStartParams`, and `TurnStartResponse`.
- Smoke the existing stdio `initialize` path without starting a user turn.
- Update `docs/dev/app-server-mode.md` with the current local contract and safety boundary.
- Record verification evidence and any follow-on product slice.

## Acceptance Criteria

- The plan records the exact local Codex CLI version used for contract refresh.
- App-server schema evidence confirms `thread/resume` and `turn/start` still exist.
- The existing stdio client can initialize against local `codex app-server`.
- The design doc clearly says WebSocket dispatch remains deferred behind auth and live operator need.
- The next implementation lane is explicit.

## Definition Of Done

This lane can close when the design doc reflects current local app-server behavior and the repo records whether code changes are required now.
