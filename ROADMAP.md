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

## P23 | Doctor JSON Inspection Surface

State: CLOSED

Current State: Closed by `docs/dev/verification/0024-2026-05-20-doctor-json.md`. `codex-wake doctor --json` now emits structured command, tmux, hook config, hook runtime evidence, service, and trust fields while preserving text doctor output.

Plan: [Doctor JSON Inspection Surface](docs/dev/plans/0023-2026-05-20-doctor-json.md)

## P24 | Status JSON Summary Surface

State: CLOSED

Current State: Closed by `docs/dev/verification/0026-2026-05-20-status-json.md`. `codex-wake status` and `codex-wake status --json` now summarize wake counts by status, predicate type, and target transport.

Plan: [Status JSON Summary Surface](docs/dev/plans/0024-2026-05-20-status-json.md)

## P25 | Status Summary Dogfood

State: CLOSED

Current State: Closed by `docs/dev/verification/0028-2026-05-20-status-dogfood.md`. Bounded dogfood confirmed `status --json` exposes pending, firing, and archived summary movement for a short repo-local wake without live pane injection.

Plan: [Status Summary Dogfood](docs/dev/plans/0025-2026-05-20-status-dogfood.md)

## P26 | Cleanup JSON Surface

State: CLOSED

Current State: Closed by `docs/dev/verification/0029-2026-05-20-cleanup-json.md`. `codex-wake cleanup --json` now reports cleanup mode, terminal archives, matched archived records, deletion state, and counts without changing dry-run defaults.

Plan: [Cleanup JSON Surface](docs/dev/plans/0026-2026-05-20-cleanup-json.md)

## P27 | Controlled Live Dispatch Dogfood

State: CLOSED

Current State: Closed by `docs/dev/verification/0031-2026-05-20-live-dispatch-dogfood.md`. The installed daemon fired one live tmux dispatch, observed the `UserPromptSubmit` hook ack, moved the wake to `submitted`, and the dogfood wake was archived with `active_total=0`.

Plan: [Controlled Live Dispatch Dogfood](docs/dev/plans/0027-2026-05-20-live-dispatch-dogfood.md)

## P28 | Installed Runtime State Tidy Dogfood

State: CLOSED

Current State: Closed by `docs/dev/verification/0032-2026-05-20-installed-runtime-state-tidy-dogfood.md`. The repo-local wake root is tidy after archiving four terminal records with installed `cleanup --archive-terminal --json`; no archived evidence was deleted.

Plan: [Installed Runtime State Tidy Dogfood](docs/dev/plans/0028-2026-05-20-installed-runtime-state-tidy-dogfood.md)

## P29 | App-Server Contract Refresh

State: CLOSED

Current State: Closed by `docs/dev/verification/0033-2026-05-20-app-server-contract-refresh.md`. Codex CLI `0.131.0` still exposes the stdio app-server primitives used by codex-wake, and the source-tree stdio initialize smoke passed. No code change is required before a live disposable-thread dogfood or thread-status preflight lane.

Plan: [App-Server Contract Refresh](docs/dev/plans/0029-2026-05-20-app-server-contract-refresh.md)

## P30 | App-Server Thread Status Preflight

State: CLOSED

Current State: Closed by `docs/dev/verification/0034-2026-05-21-app-server-thread-status-preflight.md`. `codex-wake app status` reads app-server thread status without starting a turn, and app-server dispatch now starts `turn/start` only after an idle resumed-thread preflight.

Plan: [App-Server Thread Status Preflight](docs/dev/plans/0030-2026-05-21-app-server-thread-status-preflight.md)

## P31 | Disposable App-Server Dogfood

State: CLOSED

Current State: Closed by `docs/dev/verification/0036-2026-05-21-disposable-app-server-dogfood.md`. Released `v0.4.9` app-server dispatch succeeded against a disposable thread with a persisted rollout; `thread/start`-only targets are not resumable and should not be treated as valid wake targets.

Plan: [Disposable App-Server Dogfood](docs/dev/plans/0031-2026-05-21-disposable-app-server-dogfood.md)

## P32 | App Status Resume Mode

State: CLOSED

Current State: Closed by `docs/dev/verification/0037-2026-05-21-app-status-resume-mode.md`. `codex-wake app status --resume` now mirrors the dispatch preflight path with `thread/resume` while default `app status` stays on `thread/read`.

Plan: [App Status Resume Mode](docs/dev/plans/0032-2026-05-21-app-status-resume-mode.md)

## P33 | App-Server Target Discovery

State: CLOSED

Current State: Closed by `docs/dev/verification/0039-2026-05-21-app-server-target-discovery.md`. `codex-wake app candidates` now lists recent local rollout-backed thread ids from Codex session metadata and points operators to `app status --resume` before wake registration.

Plan: [App-Server Target Discovery](docs/dev/plans/0033-2026-05-21-app-server-target-discovery.md)

## P34 | App Candidate Validation

State: CLOSED

Current State: Closed by `docs/dev/verification/0041-2026-05-21-app-candidate-validation.md`. `app candidates --validate` checks local rollout-backed thread ids with resume-backed status, and `--only-idle` filters to candidates whose resumed status is idle.

Plan: [App Candidate Validation](docs/dev/plans/0034-2026-05-21-app-candidate-validation.md)

## P35 | v0.4.12 Installed App Dogfood

State: CLOSED

Current State: Closed by `docs/dev/verification/0044-2026-05-21-v0412-installed-app-dogfood.md`. The installed public `v0.4.12` runtime created, fired, app-server-dispatched, submitted, and archived one dogfood wake.

Plan: [v0.4.12 Installed App Dogfood](docs/dev/plans/0035-2026-05-21-v0412-installed-app-dogfood.md)

## P36 | Tmux Visibility Accounting

State: CLOSED

Current State: Closed by `docs/dev/verification/0051-2026-05-23-tmux-visibility-accounting.md`. Tmux dispatch records sanitized visibility evidence so hook ack is no longer conflated with operator-visible prompt proof.

Plan: [Tmux Visibility Accounting](docs/dev/plans/0036-2026-05-23-tmux-visibility-accounting.md)

## P37 | App-Server Service Environment Skill Hardening

State: CLOSED

Current State: Closed by `docs/dev/verification/0053-2026-05-23-app-server-service-env-skill-hardening.md`. The agent skill now warns that app-server service dispatch depends on the daemon environment, not the interactive shell, and points agents to service logs and `doctor --json`.

Plan: [App-Server Service Environment Skill Hardening](docs/dev/plans/0037-2026-05-23-app-server-service-env-skill-hardening.md)

## P38 | App-Server Service Environment Product Hardening

State: CLOSED

Current State: Closed by `docs/dev/verification/0054-2026-05-23-app-server-service-env-product-hardening.md`. Service-installed app-server dispatch can persist an explicit Codex CLI command, and `doctor --json` exposes service-side Codex readiness.

Plan: [App-Server Service Environment Product Hardening](docs/dev/plans/0038-2026-05-23-app-server-service-env-product-hardening.md)

## P39 | v0.4.13 Release

State: CLOSED

Current State: Closed by `docs/dev/verification/0055-2026-05-23-v0.4.13-release.md`. Public tag `v0.4.13`, release notes, GitHub release, public tag install smoke, and refreshed user-scoped install verification are complete.

Plan: [v0.4.13 Release](docs/dev/plans/0039-2026-05-23-v0413-release.md)

## P40 | OpenClaw Gateway Wake Transport

State: CLOSED

Current State: Closed by `docs/dev/verification/0059-2026-05-25-openclaw-plugin-registration-smoke.md`. `codex-wake` can create structured `openclaw_gateway` wake records, reject placeholder session keys, dispatch through OpenClaw Gateway method `agent`, and the external OpenClaw plugin at `plugins/openclaw-codex-wake/` can register a durable wake from live OpenClaw session context. Real smokes produced Slack-visible responses for `wake_20260525_203934_201f` and plugin-created wake `wake_20260525_211551_b1f4`.

Plan: [OpenClaw Gateway Wake Transport](docs/dev/plans/0040-2026-05-25-openclaw-gateway-wake-transport.md)

Acceptance target:

- `codex-wake` can store and dispatch an `openclaw_gateway` wake target with real `agent_id`, `session_key`, and channel/thread evidence.
- The daemon rejects placeholder targets and no-dispatch false positives for OpenClaw smokes.
- A real OpenClaw wake is verified through Gateway response plus Slack Mirror or transcript evidence.
- The OpenClaw plugin path can create wake records from live session context, or a precise missing SDK/core seam is documented.

## P41 | v0.4.14 Release

State: CLOSED

Current State: Closed by `docs/dev/verification/0061-2026-05-25-v0.4.14-release.md`. Public tag `v0.4.14`, GitHub release, CI, public tag install smoke, OpenClaw CLI target smoke, plugin visibility checks, installed-skill checks, and user-scoped `uv tool` refresh are complete.

Plan: [v0.4.14 Release](docs/dev/plans/0041-2026-05-25-v0414-release.md)

Acceptance target:

- `pyproject.toml`, README install docs, and release notes name `v0.4.14`.
- Source, package, plugin, installed-wheel, and installed-skill validation pass.
- Public tag, GitHub release, public tag install smoke, and user-scoped install
  refresh are recorded under `docs/dev/verification/`.

## P42 | Wake Monitor Readiness And User Supervisor

State: CLOSED

Current State: Closed by
`docs/dev/verification/0062-2026-05-26-wake-monitor-readiness-user-supervisor.md`.
The skill, CLI, and OpenClaw plugin now gate unattended wakes on monitor
readiness; `codex-wake-supervisor.service` monitors explicitly enrolled roots;
the repo-scoped service remains supported; and live Codex app-server plus
OpenClaw Gateway wakes fired from the supervisor with recorded evidence.

Plan: [Wake Monitor Readiness And User Supervisor](docs/dev/plans/0042-2026-05-25-wake-monitor-readiness-user-supervisor.md)

Acceptance target:

- The `codex-wake` skill requires monitor readiness before unattended wake
  scheduling.
- The CLI exposes monitor readiness for the selected wake root and can fail
  scheduling when a caller requires an active monitor.
- A user-scoped `codex-wake-supervisor.service` can monitor explicitly
  registered wake roots across Codex and OpenClaw transports.
- The OpenClaw plugin schedules into monitored roots by default, or returns a
  clear failure instead of implying unattended delivery.
- Real Codex app-server and OpenClaw Gateway wakes fire from monitored roots
  with recorded validation evidence.

## P43 | Productization Completion

State: CLOSED

Current State: Closed by
`docs/dev/verification/0069-2026-05-26-v050-release.md`. `v0.5.0` is tagged,
published, CI-passed, public-install-smoked, installed user-scoped from the
public tag, and live-validated through Codex app-server plus OpenClaw Gateway
wakes. Slices 1 through 5 are implemented.
`codex-wake openclaw-plugin
install|update` can materialize a public tag, install through OpenClaw's
non-linked plugin installer, prune stale linked plugin paths with a config
backup, refresh the generated registry, and survive Gateway restart from
`~/.openclaw/extensions/codex-wake`. `codex-wake product-readiness --json`
reports normalized installed readiness across CLI, hooks, skills, repo service,
supervisor roots, monitor health, app-server, OpenClaw Gateway, OpenClaw plugin,
and tmux. Runtime state classes and cleanup/archive/supervisor-unenroll effects
are documented, and stale supervisor roots now include health status plus
remediation. `scripts/product_smoke.py` and `docs/product-smoke-matrix.md`
codify safe installed/public-tag smokes, optional live Codex/OpenClaw smokes,
and the manual tmux visibility boundary. README, daemon-service docs, the
OpenClaw plugin README, the `codex-wake` skill, and
`docs/support-boundary.md` now document the public install path, monitor
selection, readiness checks, cleanup boundaries, and unsupported false
positives. Fresh Codex app-server and OpenClaw Gateway smokes through the
harness are recorded in
`docs/dev/verification/0068-2026-05-26-live-product-smokes.md`. Remaining
product risk is closed for the scoped `v0.5.0` productization DOD.

Plan: [Productization Completion](docs/dev/plans/0043-2026-05-26-productization-completion.md)

Acceptance target:

- OpenClaw plugin install/update works from a durable public tag or package
  artifact, not only from a repo-linked path.
- Installed readiness reports CLI, supervisor, monitor, hook, app-server,
  OpenClaw Gateway, plugin, and tmux status without leaking secrets.
- Runtime state cleanup and supervisor root lifecycle are documented and
  validated.
- A repeatable smoke matrix covers installed CLI, supervisor, Codex app-server,
  OpenClaw Gateway, and manual/operator-visible tmux boundaries.
- A productization release is tagged, published, public-install-smoked, and
  recorded with live wake evidence.

## P44 | App-Server Active Writer Policy

State: CLOSED

Current State: Closed on 2026-08-25. App-server preflight never calls
`turn/start` while the target is active. Active-writer contention fails by
default, including for older records without the additive target option, and
`--retry-active-writer` opts a wake into the existing bounded three-attempt
backoff policy.

Plan: [App-Server Active Writer Policy](docs/dev/plans/0044-2026-08-25-app-server-active-writer-policy.md)

Acceptance target:

- Active-writer contention never calls `turn/start`.
- Default and legacy records fail visibly when the target is active.
- Explicitly opted-in records retry with the existing bounded attempt and
  backoff policy.
- CLI, persisted schema, tests, operator docs, and agent guidance agree.

## P45 | Cross-Root Wake Hook Routing

State: CLOSED

Current State: Closed on 2026-09-04. Canonical prompts carry the absolute wake
root, the hook resolves records and retained archives against that owner, and
terminal archived wakes fail closed without resuming stale work. The redundant
project hook was removed while the user-scoped hook remains installed.

Plan: [Cross-Root Wake Hook Routing](docs/dev/plans/0045-2026-09-03-cross-root-wake-hook-routing.md)

Acceptance target:

- Every transport includes the owning absolute wake root in its canonical prompt.
- Cross-repository and archived wake submissions resolve against the owner.
- Terminal records return explicit do-not-resume context.
- Legacy id-only prompts retain the cwd fallback.
- Exactly one user-scoped hook remains installed on this workstation.

## P46 | v0.5.1 Maintenance Release

State: CLOSED

Current State: Closed by
`docs/dev/verification/0070-2026-09-04-v051-release.md`. The patch release
contains P44 and P45 plus the unpublished stable-command and removed-repository
service maintenance already present on `main`. `v0.5.1` is tagged, published,
CI-passed, public-install-smoked, and installed user-scoped; hook, skill,
supervisor, and OpenClaw plugin readbacks are complete.

Plan: [v0.5.1 Maintenance Release](docs/dev/plans/0046-2026-09-04-v051-maintenance-release.md)

Acceptance target:

- Source, package, plugin, and planning validation pass.
- The release commit and `v0.5.1` tag are pushed without rewriting history.
- GitHub CI and the GitHub release complete successfully.
- Public-tag smoke, user-scoped CLI refresh, hook/skill synchronization,
  supervisor restart, and OpenClaw plugin refresh are verified.

## P47 | Readiness Alternative Monitor Status

State: CLOSED

Current State: Closed by
`docs/dev/verification/0071-2026-09-04-v052-readiness-release.md`. Installed
`v0.5.2` reports the inactive repo service as `not_needed`, with
`required=false` and `covered_by=supervisor`, when the active enrolled
supervisor and ready monitor prove alternative coverage. Missing or unhealthy
coverage still warns.

Plan: [Readiness Alternative Monitor Status](docs/dev/plans/0047-2026-09-04-readiness-alternative-monitor-status.md)

Acceptance target:

- Healthy supervisor coverage reports the repo service as `not_needed`.
- Missing or unhealthy alternative coverage preserves the warning.
- Overall readiness treats `not_needed` as neutral.
- Source, CI, public-tag, and installed-runtime evidence agree.

## P48 | Event-Driven Wakes Product Lane

State: CLOSED

Current State: Closed at checkpoint `P48-G1-C05`. Issues #4 through #10 are
accepted on `origin/main` through `0f917719f8a50f55f76d33262c3ca639c7f515c4`.
The provider-neutral signal module, v1 compatibility, filesystem wakes, GitHub
polling, signed webhook convergence, lifecycle productization, disposable
package proof, and bounded routing calibration are integrated. The calibration
was honestly inconclusive and retained `balanced` defaults. Provider access,
public ingress, live dispatch, installed-runtime mutation, deployment, tag,
and release were not performed.

Plan: [Event-Driven Wakes Product Lane](docs/dev/plans/0048-2026-09-14-event-driven-wakes-product-lane.md)

Goal campaign: [Event-driven wakes goal campaign](docs/dev/plans/0049-2026-09-14-event-driven-wakes-goal-campaign.md)

Vision: [Event-driven wakes](docs/event-driven-wakes.md)

Acceptance target:

- A provider-neutral signal module arms, ingests, evaluates, and explains
  filesystem and GitHub events without provider logic leaking into dispatch.
- Durable receipts, deduplication, checkpoints, reservations, and recovery
  prevent missed or duplicate wake transitions across restarts.
- Existing wake predicates and target transports retain their documented
  behavior through a versioned compatibility path.
- GitHub Issues, short-lived branches, pull requests, CI, and the active-lane
  catalog provide shared coordination and custody evidence.
- Bounded subagent use and measured model routing reduce accepted-slice cost
  without weakening correctness, safety, or delivery evidence.

## P49 | Installed Filesystem Wake Canary

State: CLOSED

Current State: Issue #30 is ready for one isolated installed-candidate service
and one live tmux dispatch. The global `0.5.2` uv-tool installation and normal
repo wake root are observation-only. The candidate service, wake root, marker,
and venv use exact P49-only identities and must be removed after evidence
capture. Provider access, public ingress, deployment, tag, and release remain
excluded. A pre-effect review found that schema-v2 filesystem registration
must first gain a supported one-attempt bound; the same lane will implement and
validate that prerequisite before any installed mutation.

Closure: Candidate `86291bf` completed the isolated live canary with one
verified filesystem match, one dispatch, hook acknowledgement, and
`visible_prompt_observed`. The canary found and repaired stale pending
republication after terminal submission. Verification 0073 records the test,
receipt, archive, complete rollback, and unchanged global/normal runtime state.

Plan: [Installed Filesystem Wake Canary](docs/dev/plans/0057-2026-09-14-installed-filesystem-canary.md)

Acceptance target:

- Bind the candidate source and wheel to one isolated active user service.
- Persist and enforce `max_attempts: 1` through the supported CLI and
  journal-authoritative record path.
- Arm `file.created` while absent and dispatch exactly once after the initiating
  turn becomes idle.
- Recover the same pending wake across a controlled service restart before the
  marker is created.
- Prove submitted status, hook acknowledgement, and visible prompt evidence.
- Archive and roll back the canary without global install, normal wake-root,
  supervisor, or unrelated service drift.

## P50 | GitHub CI Wake Productization And Installed Canary

State: CLOSED

Current State: Checkpoint `P50-G1-C12` accepts issues #34 through #37 and #45.
The production source is fixed-origin, bounded, read-only, positive-only, and
explicitly reports `GITHUB_COVERAGE_UNPROVEN`; it never promotes list exhaustion
or mutable `updated_at` into complete-history or completion-time evidence. The
supported CLI, daemon recovery, readiness, support, and installed-wheel paths
are canonical. Installed retry 3 observed successful run `34984194234`, matched
once, dispatched once with `visible_prompt_observed`, archived, and rolled back
without global-runtime drift. PR #56 merged its verified receipt at
`30c6f2d721d48cedcb12d0e55374369ece7645a4`; no P50 live effect remains.

Plan: [GitHub CI wake productization goal campaign](docs/dev/plans/0058-2026-09-14-github-ci-wake-productization.md)

Acceptance target:

- An explicit enabled-source registry and fixed-origin read-only client enforce
  repository, workflow, ref, conclusion, credential, and resource limits.
- Positive run-attempt evidence and history coverage are independently truthful;
  missing or delayed provider evidence never advances a false checkpoint.
- A supported `github-ci` recipe and daemon runner persist and recover the same
  wake, anchor, checkpoint, retry state, and source health across restart.
- Operator readiness and support surfaces remain bounded, sanitized, and
  explicit about recovery strength and degradation.
- One isolated installed candidate observes one exact post-anchor workflow
  completion, dispatches once with visibility evidence, archives, and rolls
  back without global or normal-runtime drift.
- Issues #34 through #37 integrate through pull requests and required CI; no
  webhook ingress, provider mutation, global refresh, deployment, tag, or
  release occurs.

## P51 | Local Runtime Event Wakes

State: CLOSED

Current State: Checkpoint `P51-G1-C11` accepts the runtime contract, exact
same-user process-exit wake, read-only user-systemd transition wake, shared
product lifecycle, and installed canary through issues #59 through #63 and PRs
#67, #71, #73, #77, and #79. The final installed receipt proves one exact
restart-recovered systemd transition, one acknowledged and visibly observed
tmux wake, archive, and complete isolated rollback without global or normal
runtime drift. The active-lane projection is empty and parent issue #58 closes
with the final coordination merge.

Plan: [Local runtime event wakes goal campaign](docs/dev/plans/0059-2026-09-15-local-runtime-event-wakes.md)

Acceptance target:

- Exact process and user-unit identities are authorization-bound and cannot be
  widened through a wake request.
- Runtime observations are read-only, bounded, restart-correct, deduplicated,
  and fail closed on ambiguity or backend loss.
- Process wakes never attach to PID reuse or claim unavailable exit code/time;
  systemd wakes never claim unseen transitions or acquire unit-control power.
- Supported CLI, daemon, readiness, status, support, packaging, and legacy
  compatibility surfaces remain truthful and tested.
- One isolated installed candidate produces one bounded visible wake, archives,
  and rolls back without global or unrelated runtime drift.

Completion evidence:

- Process wake canonical commit:
  `54311f35f9e3b6dd0c21be3d0beaa2eb443616a3`.
- User-systemd wake canonical commit:
  `f41ef0ba6d5b37ab85bea7a1cebbc9bd6b0ad748`.
- Productization canonical commit:
  `08447afdfe0384b23d73079e4579ca050dffe2c0`.
- Installed canary canonical commit:
  `00af8fa2142ce5adb102f48ba651c6a09c02df1b` and verification receipt
  [0077](docs/dev/verification/0077-2026-09-15-installed-runtime-wake-canary.md).

## P52 | Event Source Extension Framework

State: CLOSED

Current State: PR #89 accepted issue #82 at canonical `f8059cd`, freezing the
closed built-in source-family registry plus provider-free conformance fixture.
PR #93 accepted local-source migration #83 at canonical `3c30947`; PR #95
accepted GitHub migration #84 at canonical `e0d8862`. PR #99 accepted
productization #85 at canonical `2929d93`. Its shared catalogue inventory,
additive readiness/support projection, maintainer docs, and provider-free
installed-wheel conformance pass both Python 3.11/3.12 release gates. All four
child issues and implementation lanes are closed. No new source, provider
effect, live dispatch, arbitrary plugin loading, release, deployment, or global
installation refresh occurred.

Plan: [Event source extension framework goal campaign](docs/dev/plans/0065-2026-09-15-event-source-extension-framework.md)

Acceptance target:

- One immutable built-in source-family catalogue replaces source-specific
  daemon reconstruction branches without changing source semantics.
- A provider-free fixture proves extension, collision rejection, ordering,
  batching, failure isolation, recovery, and side-effect-free introspection.
- Filesystem, process, user-systemd, and GitHub CI sources preserve their exact
  configuration, authorization, anchors, retry, health, and recovery behavior.
- Readiness/support, documentation, and an isolated dispatch-disabled installed
  wheel agree with runtime registration.
- GitHub issues, short-lived branches, pull requests, CI, and canonical-main
  readback provide custody and acceptance evidence.

## P53 | Signed GitHub Webhook Ingress

State: CLOSED

Current State: Issues #104 through #109 are accepted. The bounded listener,
durable signed-ingest join, supported lifecycle, installed qualification, and
exact Cooper/bastion route are canonical. The separately gated live successor
created one exact `workflow_run` hook, squash-merged docs-only PR #133 as
`5f21ed1`, and accepted provider delivery
`80e50480-b201-11f1-9387-9a306ef1c969` for successful run `35138287516/1`.
The durable occurrence converged `0 -> 1 -> 1`; the wake moved pending to local
firing with dispatch disabled. The hook was deleted, the successor secret
retired, and the isolated service and root removed. Fresh readback shows no
hook, unit, process, or port-8820 listener. Retained failed predecessor evidence
remains owner-only and secret-free. Verification 0081 binds the accepted
receipt. No release, global install, ingress mutation, redelivery, or live
target dispatch occurred.

Plan: [Signed GitHub webhook ingress goal campaign](docs/dev/plans/0070-2026-09-16-signed-github-webhook-ingress.md)

Acceptance target:

- A dedicated loopback-first listener rejects ambiguous HTTP framing and
  untrusted proxy claims within fixed connection, byte, time, and shutdown
  budgets.
- Signed GitHub deliveries retain authoritative attempt reads, commit-before-
  ack, durable deduplication, restart correctness, and polling convergence.
- CLI, service, readiness, status, support, packaging, and owner-only secret
  references form one supported product lifecycle.
- One installed service, one exact Cooper/bastion HTTPS route, and one exact
  live GitHub delivery are independently proven and cleaned up or retained by
  explicit receipt.
- Public ingress exposes only the HMAC-authenticated webhook path; provider
  mutation and target dispatch remain separate authorities.

Acceptance state: P53 is closed and accepted at canonical `8171220`. Movement
is `outcome_progress`. The retained ingress route and predecessor evidence
remain unchanged; no P53 hook, secret, listener service, or isolated successor
root remains.

## P54 | Managed GitHub Webhook Wakes

State: OPEN

Current State: Issue #135 and Plan 0083 own the managed-production successor to
P53. The accepted P53 route, listener, journal join, authoritative GitHub
verification, and polling convergence are reusable foundations, but the live
hook, secret, service, and isolated root were intentionally removed. P54 must
add durable exact ownership, provider reconciliation, restart-correct secret
rotation, independent health/fallback, safe rollback, one retained activation,
and one separately gated visible dispatch. The approved child graph is #138
through #142. Issue #138 and Plan 0084 own the active provider-free ownership
and reconciliation slice. Remediation checkpoint `729f4cc` implements its provider-free
binding store, ambiguity-safe reconciler, bounded GitHub.com administration
adapter, and dry-run-first CLI. Local focused, comprehensive, plugin,
compilation, and diff gates pass after addressing all eight initial independent
review findings; exact re-review and hosted integration remain. No provider,
service, secret, ingress, installation, release, or dispatch effect is
authorized by C1.

Plan: [Managed GitHub webhook wakes goal campaign](docs/dev/plans/0083-2026-09-16-managed-github-webhook-wakes.md)

Acceptance target:

- One owner-scoped, nonsecret binding and operation journal prove the exact
  repository, hook, callback, service, source, executable, desired generation,
  last observed state, and sanitized receipt history.
- Reconciliation is idempotent and crash-recoverable, classifies drift and
  collisions, and never repeats an ambiguous provider write.
- Secret rotation preserves source/journal/checkpoint identity, restarts into
  bounded dual-key acceptance, proves a new-key delivery, and safely retires or
  rolls back the prior generation.
- Local listener, provider delivery, polling coverage, and dispatch health are
  projected independently; polling remains the correctness fallback without
  duplicate occurrence or dispatch.
- One installed managed activation is intentionally retained and reversible;
  one later exact visible webhook-origin wake reaches one named target once,
  with canonical GitHub and verification custody.

Acceptance state: P54 planning and its five-child issue graph are canonical;
#138 is locally remediated and awaiting exact independent re-review. Movement is
`outcome_progress`. Next action: review and integrate the provider-free
ownership/reconciliation path through Plan 0084, then unblock #139 and #140.
Live effects remain separately gated.
