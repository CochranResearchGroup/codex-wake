# Wake Spooler Design Input

## Summary

The accepted design direction is a narrow wake spooler, not a general TUI controller.

Flow:

```text
Codex TUI agent
  -> codex-wake after/at/file ...
  -> validated trigger record
  -> wake daemon waits for predicate
  -> tmux injector submits a short wake prompt
  -> UserPromptSubmit hook records ack and loads full wake context
```

The model may request a wake, but deterministic runtime code owns the timer, event predicate, target pane, retry policy, validation, and final status.

## Current Source Checks

Official Codex docs checked on 2026-05-18:

- `UserPromptSubmit` receives the prompt, ignores matcher filters, and can add `hookSpecificOutput.additionalContext`.
- Codex hook config supports command hooks with timeouts; `async: true` handlers are parsed but skipped today.
- `codex exec resume` supports resuming non-interactive automation while preserving transcript, plan history, and approvals.
- Remote TUI mode can connect to `codex app-server --listen ws://127.0.0.1:4500`.
- Codex app-server supports `thread/resume` and `turn/start`.
- WebSocket app-server transport is experimental; localhost or SSH forwarding is the first safe target, and non-local exposure needs WebSocket auth and TLS.

Sources:

- https://developers.openai.com/codex/hooks
- https://developers.openai.com/codex/cli/features
- https://developers.openai.com/codex/app-server

## MVP Decision

Build first:

- `codex-wake` CLI
- `codex-waked` polling daemon
- declarative trigger JSON files
- tmux pane targeting and short-prompt injection
- `UserPromptSubmit` hook ack and context loader

Defer:

- app-server controlled mode
- systemd transient timers
- `at`
- inotify/entr event backends
- process completion predicates beyond simple polling
- multi-host wake dispatch

## Guardrails

- Trigger records must be declarative.
- Trigger JSON must not contain shell commands.
- Wake prompts must be idempotent.
- Mark triggers `firing` before injection.
- Require ack before `submitted`.
- Requeue missing-ack wakes with bounded backoff.
- Use per-pane locks.
- Reject obvious unsafe pane states before injecting.
