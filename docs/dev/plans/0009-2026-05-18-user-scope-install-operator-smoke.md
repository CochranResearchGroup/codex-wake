# User-Scope Install And Operator Smoke

State: CLOSED
Lane: P09

## Scope

Install Codex Wake into the current user's Python environment and verify the actual `PATH`-resolved `codex-wake` and `codex-waked` commands.

## Non-Goals

- Do not publish a package release in this slice.
- Do not enable an always-running daemon service in this slice.
- Do not run live tmux injection into a human Codex pane without an explicit disposable target.

## Current State

The MVP is merged to `main`. Temporary virtualenv verification passed, but the user-scoped installed commands are not present yet.

## Acceptance Criteria

- `python -m pip install --user .` succeeds.
- `command -v codex-wake` and `command -v codex-waked` resolve to user-scoped commands.
- `codex-wake --help` works without `PYTHONPATH`.
- `codex-waked --once --no-dispatch` works without `PYTHONPATH`.
- Installed CLI can create/list/cancel/archive a wake.
- Installed daemon can move an already-due wake to `firing` with `--no-dispatch`.
- A verification artifact records commands, outcomes, and remaining live-dispatch limits.

## Definition Of Done

Closed on 2026-05-18. The user-scoped install is verified and the best next live-smoke option is clear.
