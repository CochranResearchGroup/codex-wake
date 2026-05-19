# Hook Setup And Doctor CLI

State: CLOSED
Lane: P14

## Scope

Add operator commands that make hook setup and environment readiness inspectable without bypassing Codex's hook trust model.

## Non-Goals

- Do not auto-trust Codex hooks.
- Do not edit global Codex config.
- Do not change wake trigger predicates.

## Current State

The installed `codex-wake-hook` command exists, `codex-wake hook install/check` can manage repo-local hook config, and `codex-wake doctor` reports command, tmux, wake-root, hook, and service readiness.

## Acceptance Criteria

- A command can write or update repo-local `.codex/hooks.json` for `codex-wake-hook`.
- A command can report whether `.codex/hooks.json` contains the expected `UserPromptSubmit` hook.
- A doctor command reports installed command paths, tmux availability, wake root path, service status, and hook config status.
- The output clearly says Codex may still require `/hooks` trust review.
- Tests cover hook config rendering/checking and doctor output where practical.
- Installed command validation is refreshed.

## Definition Of Done

Closed by `docs/dev/verification/0007-2026-05-18-hook-setup-doctor-cli.md`.
