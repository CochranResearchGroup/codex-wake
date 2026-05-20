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

State: CLOSED

Current State: Closed by the stdio app-server controlled dispatch path. Wake records can target app-server threads, dispatch uses `initialize`, `thread/resume`, and `turn/start`, and WebSocket mode remains explicitly deferred behind the documented experimental/auth boundary.

Plan: [App-Server Controlled Mode](docs/dev/plans/0007-2026-05-18-app-server-controlled-mode.md)

Planned behavior:

- Support Codex app-server as a target transport.
- Store app-server thread id and target cwd when available.
- Use `thread/resume` followed by `turn/start` for controlled wake dispatch.
- Treat WebSocket mode as localhost or SSH-forwarding first; require auth/TLS before non-local exposure.
- Keep `codex exec resume <session-id> ...` as a fallback when a live TUI pane is not required.

## P08 | Installed Runtime Verification

State: CLOSED

Current State: Closed by `docs/dev/verification/0001-2026-05-18-installed-runtime-verification.md`. Installed console scripts, CLI lifecycle, daemon predicate movement, hook ack behavior, and app-server target creation were verified from a temporary virtualenv.

Plan: [Installed Runtime Verification](docs/dev/plans/0008-2026-05-18-installed-runtime-verification.md)

Acceptance target:

- A wake request can be created from a tmux-hosted Codex TUI.
- The daemon observes the predicate and moves the wake through expected states.
- The injector sends only the canonical wake prompt.
- The `UserPromptSubmit` hook records ack and supplies context.
- The resumed agent can inspect the trigger and referenced log/event files.
- Failed ack, unsafe pane, cancellation, timeout, and duplicate wake attempts are observable.

## P09 | User-Scope Install And Operator Smoke

State: CLOSED

Current State: Closed by `docs/dev/verification/0002-2026-05-18-user-scope-install-operator-smoke.md`. `codex-wake` and `codex-waked` are installed as uv user tools and verified through PATH-resolved operator smokes.

Plan: [User-Scope Install And Operator Smoke](docs/dev/plans/0009-2026-05-18-user-scope-install-operator-smoke.md)

## P10 | Disposable Live Tmux Wake Smoke

State: CLOSED

Current State: Closed by `docs/dev/verification/0003-2026-05-18-disposable-live-tmux-wake-smoke.md`. A disposable tmux-hosted Codex TUI wake was verified with repo-local hook trust, delayed multiline submit, daemon-observed ack, and a submitted wake record.

Plan: [Disposable Live Tmux Wake Smoke](docs/dev/plans/0010-2026-05-18-disposable-live-tmux-wake-smoke.md)

## P11 | Release Packaging And Install Docs

State: CLOSED

Current State: Closed by `docs/dev/verification/0004-2026-05-18-release-packaging-install-docs.md`. README install docs, v0.1.0 release notes, installed `codex-wake-hook`, clean package build, and refreshed user-scope install evidence are complete.

Plan: [Release Packaging And Install Docs](docs/dev/plans/0011-2026-05-18-release-packaging-install-docs.md)

## P12 | User Daemon Service And Dogfood Wake

State: CLOSED

Current State: Closed by `docs/dev/verification/0005-2026-05-18-user-daemon-service-dogfood-wake.md`. A user-scoped systemd path is documented, the daemon logs non-empty poll results, and a real dogfood wake resolved through the running service.

Plan: [User Daemon Service And Dogfood Wake](docs/dev/plans/0012-2026-05-18-user-daemon-service-dogfood-wake.md)

## P13 | Service Installer CLI

State: CLOSED

Current State: Closed by `docs/dev/verification/0006-2026-05-18-service-installer-cli.md`. Operators can now manage a repo-local user systemd service with `codex-wake service install/status/logs/stop/uninstall`.

Plan: [Service Installer CLI](docs/dev/plans/0013-2026-05-18-service-installer-cli.md)

## P14 | Hook Setup And Doctor CLI

State: CLOSED

Current State: Closed by `docs/dev/verification/0007-2026-05-18-hook-setup-doctor-cli.md`. Operators can run `codex-wake hook install/check` and `codex-wake doctor` to set up and inspect wake readiness without bypassing Codex hook trust review.

Live note: `docs/dev/verification/0009-2026-05-18-current-tui-dogfood.md` confirmed that tmux injection can resume the active TUI pane, but an already-running TUI session still needs `/hooks` review before the installed `codex-wake-hook` ack path should be expected to fire.

Plan: [Hook Setup And Doctor CLI](docs/dev/plans/0014-2026-05-18-hook-setup-doctor-cli.md)

## P15 | Clean Fresh Install Smoke

State: CLOSED

Current State: Closed by `docs/dev/verification/0008-2026-05-18-clean-fresh-install-smoke.md`. The public `v0.3.0` tag installs into an isolated `uv tool` path and passes command, hook, doctor, and temporary service lifecycle smokes without relying on the local checkout.

Plan: [Clean Fresh Install Smoke](docs/dev/plans/0015-2026-05-18-clean-fresh-install-smoke.md)

## P16 | CI Release Gates

State: CLOSED

Current State: Closed by `docs/dev/verification/0010-2026-05-19-ci-release-gates.md`. GitHub Actions now runs compile checks, unit tests, package build, and installed-wheel CLI smoke checks for Python 3.11 and 3.12 on push and pull request.

Plan: [CI Release Gates](docs/dev/plans/0016-2026-05-18-ci-release-gates.md)

## P17 | Event Predicates

State: CLOSED

Current State: Closed by `docs/dev/verification/0012-2026-05-19-event-predicates.md`. `codex-wake changed <path>` and `codex-wake pid <pid>` now create declarative predicates, and the daemon can move ready `file_changed` and `process_done` records to `firing`.

Plan: [Event Predicates](docs/dev/plans/0017-2026-05-19-event-predicates.md)

## P18 | App-Server Hardening

State: CLOSED

Current State: Closed by `docs/dev/verification/0014-2026-05-19-app-server-hardening.md`. `codex-wake app after` and `codex-wake app at` now create explicit app-server wakes, and accepted app-server dispatch stores available `thread_id` and `turn_id` metadata.

Plan: [App-Server Hardening](docs/dev/plans/0018-2026-05-19-app-server-hardening.md)

## P19 | PID Reuse Safety

State: CLOSED

Current State: Closed by `docs/dev/verification/0016-2026-05-19-pid-reuse-safety.md`. `codex-wake pid` now records best-effort process identity on Linux, and the daemon fires when a live PID no longer matches the registered process.

Plan: [PID Reuse Safety](docs/dev/plans/0019-2026-05-19-pid-reuse-safety.md)

## P20 | Runtime Retention Cleanup

State: CLOSED

Current State: Closed by `docs/dev/verification/0018-2026-05-19-runtime-retention-cleanup.md`. `codex-wake cleanup` now previews old archived records by default, deletes them only with `--delete`, and can archive terminal records first with `--archive-terminal`.

Plan: [Runtime Retention Cleanup](docs/dev/plans/0020-2026-05-19-runtime-retention-cleanup.md)

## P21 | Hook Session Visibility

State: CLOSED

Current State: Closed by `docs/dev/verification/0020-2026-05-19-hook-session-visibility.md`. `hook check` and `doctor` now report hook ack evidence and explicitly mark active-session hook state as unknown until an ack is observed.

Plan: [Hook Session Visibility](docs/dev/plans/0021-2026-05-19-hook-session-visibility.md)

## P22 | Wake Record Schema Versioning

State: CLOSED

Current State: Closed by `docs/dev/verification/0022-2026-05-19-wake-record-schema-versioning.md`. Schema version `1` is now documented as an additive optional-field contract, and `codex-wake schema` exposes the compatibility policy.

Plan: [Wake Record Schema Versioning](docs/dev/plans/0022-2026-05-19-wake-record-schema-versioning.md)
