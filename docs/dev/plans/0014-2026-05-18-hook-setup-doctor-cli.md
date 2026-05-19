# Hook Setup And Doctor CLI

State: OPEN
Lane: P14

## Scope

Add operator commands that make hook setup and environment readiness inspectable without bypassing Codex's hook trust model.

## Non-Goals

- Do not auto-trust Codex hooks.
- Do not edit global Codex config.
- Do not change wake trigger predicates.

## Current State

The installed `codex-wake-hook` command exists and README documents manual `.codex/hooks.json` setup. Operators still need a deterministic way to install/check repo hook config and diagnose missing tmux, service, wake root, or hook state.

## Acceptance Criteria

- A command can write or update repo-local `.codex/hooks.json` for `codex-wake-hook`.
- A command can report whether `.codex/hooks.json` contains the expected `UserPromptSubmit` hook.
- A doctor command reports installed command paths, tmux availability, wake root path, service status, and hook config status.
- The output clearly says Codex may still require `/hooks` trust review.
- Tests cover hook config rendering/checking and doctor output where practical.
- Installed command validation is refreshed.

## Definition Of Done

This lane can close when a fresh operator can run a command to install/check hook config and get a concise readiness report before scheduling wakes.
