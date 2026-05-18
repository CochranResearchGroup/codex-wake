# Codex Wake Roadmap

## P01 | Wake Spooler Architecture

State: CLOSED

Current State: Closed by `docs/dev/0001-wake-spooler-design.md`. The accepted architecture direction is a wake spooler: agents request wakes through `codex-wake`, deterministic runtime code owns trigger persistence and firing, and the MVP targets a live Codex TUI through tmux plus a `UserPromptSubmit` hook ack.

Plan: [Initial Wake Timer Design](docs/dev/plans/0001-2026-05-18-initial-wake-timer-design.md)

Deliverables:

- Source-backed design brief for the MVP and preferred future mode.
- Wake-record JSON contract.
- Trigger/status vocabulary.
- Runtime state layout under a user-scoped wake root.
- Explicit split between model-requested wake intent and daemon-owned execution.

## P02 | Agent-Facing CLI

State: CLOSED

Current State: Closed by the first Python package and CLI implementation. `codex-wake` can create `after`, `at`, and `file` wake records, list records, show a record, and cancel pending or firing records.

Plan: [Agent-Facing CLI](docs/dev/plans/0002-2026-05-18-agent-facing-cli.md)

Planned surface:

- `codex-wake after <duration> -- <prompt>`
- `codex-wake at <timestamp> -- <prompt>`
- `codex-wake file <path> -- <prompt>`
- `codex-wake list`
- `codex-wake show <wake-id>`
- `codex-wake cancel <wake-id>`

Acceptance target:

- The CLI captures cwd, `TMUX_PANE`, tmux socket, trigger predicate, prompt text, and creation metadata.
- Relative file predicates are stored with the creating cwd and validated before write.
- Time triggers store absolute UTC timestamps, not only relative expressions.
- Trigger JSON never contains shell commands to execute.

## P03 | Wake Daemon And Trigger Engine

State: CLOSED

Current State: Closed by the first `codex-waked` implementation. The daemon can poll pending records, evaluate `not_before` and `file_exists`, move ready records into `firing`, and fail records with invalid predicates.

Plan: [Wake Daemon And Trigger Engine](docs/dev/plans/0003-2026-05-18-wake-daemon-trigger-engine.md)

Planned behavior:

- Poll pending wake records.
- Support `not_before` and `file_exists` first.
- Add `file_changed` and `process_done` only after the base state machine is stable.
- Mark triggers `firing` before injection.
- Use per-pane locks so concurrent wakes cannot paste into the same TUI.
- Require ack before marking a trigger `submitted`.
- Requeue with bounded backoff when ack is missing.

## P04 | Tmux Injection MVP

State: CLOSED

Current State: Closed by the first tmux injector implementation. Firing records can be dispatched through a testable injector path, canonical prompts are generated from wake id only, unsafe panes are rejected, per-pane locks are enforced, and missing ack requeues with backoff.

Plan: [Tmux Injection MVP](docs/dev/plans/0004-2026-05-18-tmux-injection-mvp.md)

Planned behavior:

- Capture target pane from `TMUX_PANE` at trigger creation time.
- Resolve tmux socket from the environment or tmux introspection.
- Before injection, use tmux capture heuristics to reject obvious unsafe states such as approval prompts, active tool output, or non-Codex shell prompts.
- Inject only:

```text
WAKE_TRIGGER_ID=<wake-id>
Resume the scheduled wake task.
```

- Keep full wake context in the trigger record and hook-added context, not in the pasted prompt.

## P05 | Codex Hook Ack And Context Loader

State: CLOSED

Current State: Closed by the repo-local `UserPromptSubmit` hook. The hook self-filters for `WAKE_TRIGGER_ID=...`, writes ack files, and returns wake context through `hookSpecificOutput.additionalContext`.

Plan: [Codex Hook Ack And Context Loader](docs/dev/plans/0005-2026-05-18-codex-hook-ack-context-loader.md)

Planned behavior:

- Self-filter for `WAKE_TRIGGER_ID=...` because Codex ignores `matcher` for `UserPromptSubmit`.
- Write an ack file when the wake prompt is submitted.
- Load the trigger JSON and add the full wake context as developer context.
- If the trigger file is missing, add context that instructs the agent to inspect wake state before continuing.
- Keep the hook short and bounded by a small timeout.

## P06 | Runtime State, Retention, And Safety

State: CLOSED

Current State: Closed by runtime-state documentation and the terminal-record archive command. Operators can inspect active and archived wakes, and terminal wake records can be archived without touching active `pending` or `firing` records.

Plan: [Runtime State, Retention, And Safety](docs/dev/plans/0006-2026-05-18-runtime-state-retention-safety.md)

Planned state layout:

- `.codex/wake/pending/`
- `.codex/wake/firing/` or status-bearing records
- `.codex/wake/acks/`
- `.codex/wake/logs/`
- `.codex/wake/archive/`
- `.codex/wake/locks/`

Safety requirements:

- Never store secrets or raw private transcripts in trigger JSON.
- Require idempotent prompts: every wake should first verify whether the task is already complete.
- Define cleanup and archival semantics before broad use.
- Treat missed, failed, expired, cancelled, and submitted wakes as distinct inspectable outcomes.

## P07 | App-Server Controlled Mode

State: OPEN

Current State: The tmux MVP path exists. This is the preferred long-term mode and should now be designed against the current Codex app-server contract before implementation.

Plan: [App-Server Controlled Mode](docs/dev/plans/0007-2026-05-18-app-server-controlled-mode.md)

Planned behavior:

- Support Codex app-server as a target transport.
- Store app-server thread id and target cwd when available.
- Use `thread/resume` followed by `turn/start` for controlled wake dispatch.
- Treat WebSocket mode as localhost or SSH-forwarding first; require auth/TLS before non-local exposure.
- Keep `codex exec resume <session-id> ...` as a fallback when a live TUI pane is not required.

## P08 | Installed Runtime Verification

State: PLANNED

Current State: No installed command, hook, or daemon exists yet. This lane opens once there is an executable surface.

Acceptance target:

- A wake request can be created from a tmux-hosted Codex TUI.
- The daemon observes the predicate and moves the wake through expected states.
- The injector sends only the canonical wake prompt.
- The `UserPromptSubmit` hook records ack and supplies context.
- The resumed agent can inspect the trigger and referenced log/event files.
- Failed ack, unsafe pane, cancellation, timeout, and duplicate wake attempts are observable.
