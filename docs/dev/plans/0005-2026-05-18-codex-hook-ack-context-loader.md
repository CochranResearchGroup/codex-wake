# Codex Hook Ack And Context Loader

State: OPEN
Lane: P05

## Scope

Implement the repo-local Codex `UserPromptSubmit` hook that acknowledges canonical wake prompts and loads full wake context into the turn.

## Non-Goals

- Do not implement app-server transport in this slice.
- Do not broaden hook behavior beyond `WAKE_TRIGGER_ID=...`.
- Do not make the hook responsible for timers, polling, or dispatch.

## Current State

The tmux injector can paste canonical wake prompts and waits for `.codex/wake/acks/<wake-id>.submitted`. No hook writes that ack or adds context yet.

## Acceptance Criteria

- `.codex/hooks/wake_user_prompt_submit.py` self-filters for `WAKE_TRIGGER_ID=...`.
- The hook writes `.codex/wake/acks/<wake-id>.submitted`.
- The ack includes wake id, submitted timestamp, turn id, and session id when present.
- If the wake record exists, the hook adds developer context with predicate, original prompt, and evidence/context paths.
- If the wake record is missing, the hook adds context telling the agent to inspect wake state before continuing.
- A sample Codex hook config fragment exists.
- Tests cover no-match, found-record, and missing-record behavior.

## Definition Of Done

The plan can close when the hook can produce ack files and hook-specific JSON output deterministically without depending on a live Codex TUI.
