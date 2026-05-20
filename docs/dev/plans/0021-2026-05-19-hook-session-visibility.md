# Hook Session Visibility

State: CLOSED
Lane: P21

## Scope

Improve diagnostics that distinguish hook config on disk from runtime evidence that the active Codex TUI has loaded and run the hook.

## Non-Goals

- Do not automate Codex `/hooks` trust review.
- Do not scrape private TUI transcript content.
- Do not infer hook success from tmux injection alone.
- Do not require a live dogfood wake to run source tests.

## Current State

`codex-wake hook check` reports whether `.codex/hooks.json` contains `codex-wake-hook`. `doctor` reports the same config state. This does not clearly separate config-on-disk from active-session hook execution, which caused confusion during dogfooding when the hook was visible under `UserPromptHooks` rather than by command name.

## Design

Add runtime ack evidence to `hook check` and `doctor`:

- count of `.codex/wake/acks/*.submitted`
- latest ack path
- latest ack submitted timestamp
- latest ack wake id
- latest ack session id when present
- explicit active-session loaded state:
  - `unknown_without_ack` when no ack has been observed
  - `observed_ack` when an ack exists

The output should continue to say that `/hooks` lists hook sources under `UserPromptHooks`, and that ack evidence is proof of hook execution only after a wake prompt is submitted.

Closed by [Hook Session Visibility](../verification/0020-2026-05-19-hook-session-visibility.md).

## Acceptance Criteria

- `codex-wake hook check` reports config state and runtime ack evidence.
- `codex-wake doctor` reports the same runtime ack evidence.
- Missing ack evidence is reported as unknown, not failure of tmux injection.
- README or runtime docs explain the diagnostic boundary.
- Source and installed CLI smokes cover the output shape.

## Definition Of Done

This lane can close when tests and CLI smokes verify hook config state, no-ack state, and latest-ack evidence.
