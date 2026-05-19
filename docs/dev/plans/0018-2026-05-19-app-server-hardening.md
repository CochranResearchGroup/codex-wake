# App-Server Hardening

State: CLOSED
Lane: P18

## Scope

Harden the existing stdio app-server wake path.

## Non-Goals

- Do not implement unauthenticated WebSocket app-server dispatch.
- Do not remove or weaken the tmux path.
- Do not require a live Codex app-server thread in CI.

## Current State

P07 implemented a stdio app-server dispatch path and target record support, but the agent-facing CLI still exposed app-server targeting mostly as an option on time commands. P18 adds explicit app-server CLI commands and preserves accepted dispatch metadata.

Validation evidence: [App-Server Hardening](../verification/0014-2026-05-19-app-server-hardening.md)

## Acceptance Criteria

- Add explicit app-server CLI commands for time-based wakes.
- Preserve `thread_id` and `turn_id` metadata from accepted `thread/resume` and `turn/start` results when available.
- Add dispatch attempt evidence before app-server requests.
- Keep non-stdio endpoints rejected.
- Update app-server docs and README examples.
- Validate with source tests and CLI smokes without requiring a live app-server thread.

## Definition Of Done

This lane can close when app-server wake creation is explicit, dispatch records accepted turn metadata, and tests cover the new behavior.
