# Codex Wake Runbook

## Turn 1 | 2026-05-18

Policy bootstrap for the new wake-timer repo.

- Created `AGENTS.md` as the repo entrypoint.
- Selected a custom policy composition: `repo-product-engineering` base with `runtime-state-governance` and `subagent-runtime-governance` overrides.
- Added repo-local policy files under `docs/dev/policies/`.
- Added canonical roadmap, runbook, and initial design plan surfaces.
- Wired active P01 work to `docs/dev/plans/0001-2026-05-18-initial-wake-timer-design.md`.

Next checkpoint: design the wake-record contract, trigger vocabulary, runtime state storage boundary, and first CLI/API surface.

## Turn 2 | 2026-05-18

Roadmapped the wake-spooler design from the supplied design note.

- Expanded `ROADMAP.md` into implementation lanes for architecture, CLI, daemon, tmux injection, Codex hook ack, runtime state safety, app-server mode, and installed verification.
- Updated the active P01 plan to reflect the narrow wake-spooler shape.
- Verified current Codex docs for `UserPromptSubmit`, hook timeout/async behavior, `codex exec resume`, remote TUI mode, and app-server `thread/resume` plus `turn/start`.

Next checkpoint: write the source-backed design brief and first wake-record contract under `docs/dev/`.

## Turn 3 | 2026-05-18

Started execution on P01 and moved the repo into the first implementation slice.

- Added `docs/dev/0001-wake-spooler-design.md` with the accepted architecture, schema, status vocabulary, event records, hook ack contract, retry policy, CLI contract, and validation requirements.
- Closed P01 in `ROADMAP.md`.
- Opened P02 in `ROADMAP.md`.
- Added `docs/dev/plans/0002-2026-05-18-agent-facing-cli.md` as the active implementation plan.

Next checkpoint: implement the `codex-wake` CLI and tests for wake-record creation, listing, showing, and cancellation.

## Turn 4 | 2026-05-18

Implemented and validated the P02 CLI slice.

- Added Python package metadata and a `codex-wake` console entry point.
- Added `after`, `at`, `file`, `list`, `show`, and `cancel` command support.
- Added wake-record helpers for duration parsing, timestamp normalization, tmux target capture, atomic JSON writes, record lookup, and cancellation.
- Added focused standard-library tests for records and CLI behavior.
- Closed P02 in `ROADMAP.md`.
- Opened P03 with `docs/dev/plans/0003-2026-05-18-wake-daemon-trigger-engine.md`.

Validation:

- `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`
- `PYTHONPATH=src python -m codex_wake.cli --help`
- `TMUX_PANE='%11' TMUX='/tmp/tmux-1000/default,123,0' PYTHONPATH=src python -m codex_wake.cli --wake-root /tmp/codex-wake-smoke after 1m -- 'Smoke wake'`

Next checkpoint: implement `codex-waked` predicate polling and `pending -> firing` movement for `not_before` and `file_exists`.

## Turn 5 | 2026-05-18

Implemented and validated the P03 daemon slice.

- Added `codex-waked` as a console entry point.
- Added one-shot and polling daemon modes.
- Added predicate evaluation for `not_before` and `file_exists`.
- Added deterministic movement from `pending` to `firing`.
- Added invalid-predicate movement from `pending` to `failed`.
- Added stable transition events and `last_error` support.
- Closed P03 in `ROADMAP.md`.
- Opened P04 with `docs/dev/plans/0004-2026-05-18-tmux-injection-mvp.md`.

Validation:

- `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`
- `PYTHONPATH=src python -m codex_wake.daemon --once --wake-root /tmp/codex-wake-daemon-smoke`
- create an already-due wake through `codex-wake`, then run `codex-waked --once` and verify the record moved to `firing`.

Next checkpoint: implement the tmux injector, per-pane locking, unsafe pane checks, and bounded missing-ack behavior.

## Turn 6 | 2026-05-18

Implemented and validated the P04 tmux injector slice.

- Added `codex_wake.injector` with canonical prompt construction, tmux subprocess runner, pane capture, prompt paste, per-pane locks, ack waiting, and bounded requeue/fail behavior.
- Wired `codex-waked` to dispatch `firing` records by default, with `--no-dispatch` and `--ack-timeout` controls.
- Ensured injected text contains only `WAKE_TRIGGER_ID=<id>` and the short resume instruction.
- Added tests for canonical prompt construction, unsafe pane detection, lock contention, submitted ack behavior, missing-ack requeue, and full-prompt exclusion from injected text.
- Closed P04 in `ROADMAP.md`.
- Opened P05 with `docs/dev/plans/0005-2026-05-18-codex-hook-ack-context-loader.md`.

Validation:

- `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`
- `python -m compileall -q src tests`

Next checkpoint: implement the `UserPromptSubmit` hook that writes ack files and injects wake context into Codex.

## Turn 7 | 2026-05-18

Implemented and validated the P05 Codex hook slice.

- Added `codex_wake.hook` with wake id extraction, ack writing, trigger lookup, missing-trigger warnings, and hook-specific JSON output.
- Added `.codex/hooks/wake_user_prompt_submit.py` as the repo-local command hook wrapper.
- Added `docs/dev/codex-hooks.example.json` with a sample `UserPromptSubmit` hook configuration.
- Added tests for no-match, found-record, missing-record, and direct hook output behavior.
- Verified official Codex hook docs for `UserPromptSubmit` matcher behavior and `hookSpecificOutput.additionalContext`.
- Closed P05 in `ROADMAP.md`.
- Opened P06 with `docs/dev/plans/0006-2026-05-18-runtime-state-retention-safety.md`.

Validation:

- `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`
- direct `.codex/hooks/wake_user_prompt_submit.py` smoke with a generated JSON payload
- `python -m compileall -q src tests .codex/hooks`

Next checkpoint: specify and implement runtime-state retention, archive, and cleanup behavior.

## Turn 8 | 2026-05-18

Implemented and validated the P06 runtime-state retention slice.

- Added `docs/dev/runtime-state.md` documenting runtime directory classes, retention rules, safety rules, and archive commands.
- Added `codex-wake archive <wake-id>`.
- Added `codex-wake archive --all-terminal`.
- Added `codex-wake list --archived`.
- Added archive helpers that only move terminal records and preserve JSON with `previous_status`, `archived_at`, and an `archived` event.
- Added tests for single-record archive, archive-all-terminal, CLI archive, and archived listing.
- Closed P06 in `ROADMAP.md`.
- Opened P07 with `docs/dev/plans/0007-2026-05-18-app-server-controlled-mode.md`.

Validation:

- `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`
- `python -m compileall -q src tests .codex/hooks`

Next checkpoint: verify current Codex app-server contract and decide whether P07 can implement controlled dispatch now or should record a precise blocker.

## Turn 9 | 2026-05-18

Implemented and validated the P07 app-server controlled mode slice.

- Verified official Codex docs for app-server transports and WebSocket safety boundaries.
- Verified local Codex CLI 0.130.0 supports `codex app-server --listen stdio://`, schema generation, and TypeScript generation.
- Generated local app-server schemas and confirmed `thread/resume` and `turn/start` payload shapes.
- Added `codex_wake.app_server` with a stdio JSON-RPC client and controlled dispatch through `initialize`, `thread/resume`, and `turn/start`.
- Added app-server target support through `--app-server-thread-id`.
- Explicitly rejected non-stdio app-server endpoints in the MVP.
- Added `docs/dev/app-server-mode.md`.
- Added tests for app-server dispatch, unsupported endpoint failure, dispatcher routing, and CLI target creation.
- Closed P07 in `ROADMAP.md`.
- Opened P08 with `docs/dev/plans/0008-2026-05-18-installed-runtime-verification.md`.

Validation:

- `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`
- `python -m compileall -q src tests .codex/hooks`

Next checkpoint: verify installed executables and hook behavior end to end from a temporary install.

## Turn 10 | 2026-05-18

Completed P08 installed runtime verification.

- Installed the package into `/tmp/codex-wake-venv`.
- Verified installed `codex-wake --help`.
- Verified installed `codex-waked --once --no-dispatch`.
- Verified installed CLI create, list, cancel, and archive lifecycle.
- Verified installed daemon predicate movement for an already-due wake with `--no-dispatch`.
- Verified the repo-local hook wrapper writes an ack and returns hook-specific output from a JSON payload.
- Verified installed app-server-targeted wake creation and JSON listing.
- Recorded verification details in `docs/dev/verification/0001-2026-05-18-installed-runtime-verification.md`.
- Closed P08 in `ROADMAP.md`.

Known limits:

- Live tmux dispatch was not attempted without a disposable Codex TUI pane target.
- Live app-server dispatch was not attempted without a real target thread id.
- WebSocket app-server dispatch remains intentionally unimplemented.

Next checkpoint: open PR for review and merge planning.

## Turn 11 | 2026-05-18

Merged PR #1 and started the next operator-useful lane.

- Merged `p02-agent-facing-cli` into `main` with merge commit `4c8d38c`.
- Verified post-merge tests and planning audit on local `main`.
- Added P09 for user-scope install and operator smoke.

Next checkpoint: install Codex Wake with `python -m pip install --user .` and verify the actual PATH-resolved commands.

## Turn 12 | 2026-05-18

Completed P09 user-scope install and operator smoke.

- Direct `python -m pip install --user .` was blocked by the uv-managed Python environment.
- Installed safely with `uv tool install --force .`.
- Verified PATH-resolved `/home/ecochran76/.local/bin/codex-wake`.
- Verified PATH-resolved `/home/ecochran76/.local/bin/codex-waked`.
- Verified CLI create, list, cancel, and archive lifecycle.
- Verified daemon predicate movement with `--no-dispatch`.
- Verified hook wrapper ack behavior.
- Verified app-server-targeted wake creation.
- Closed `docs/dev/plans/0009-2026-05-18-user-scope-install-operator-smoke.md`.
- Opened `docs/dev/plans/0010-2026-05-18-disposable-live-tmux-wake-smoke.md`.
- Recorded details in `docs/dev/verification/0002-2026-05-18-user-scope-install-operator-smoke.md`.
- Closed P09 in `ROADMAP.md`.
- Opened P10 for a disposable live tmux wake smoke.

Best next turn option: run P10 against a disposable tmux session, not a human active Codex pane.

## Turn 13 | 2026-05-18

Completed P10 disposable live tmux wake smoke.

- Installed `.codex/hooks.json` so the repo-local `UserPromptSubmit` hook is available to Codex.
- Created a disposable tmux session running `codex -C /home/ecochran76/workspace.local/codex-wake --no-alt-screen`.
- Observed the Codex hook trust gate and trusted the hook inside the disposable pane.
- Found that immediate submit after paste left the two-line wake prompt in the Codex composer.
- Updated the tmux injector to wait after paste and send delayed `C-m` submit keys.
- Verified daemon-owned live dispatch with `checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0`.
- Verified the hook wrote `.codex/wake/acks/wake_20260519_003526_bfaa.submitted`.
- Refreshed the user-scoped `uv tool install --force .` after the injector submit timing fix.
- Recorded evidence in `docs/dev/verification/0003-2026-05-18-disposable-live-tmux-wake-smoke.md`.
- Closed P10 in `ROADMAP.md`.
- Opened P11 with `docs/dev/plans/0011-2026-05-18-release-packaging-install-docs.md` for release packaging and install docs.

Best next turn option: complete P11 by writing operator install docs, choosing the first release version boundary, refreshing the user-scope install, and tagging the release.

## Turn 14 | 2026-05-18

Completed P11 release packaging and install docs.

- Chose `v0.1.0` as the initial MVP release boundary.
- Rewrote `README.md` with requirements, install, hook setup, usage examples, daemon commands, runtime state, limits, and development commands.
- Added installed `codex-wake-hook` console script for operator hook configs.
- Added `docs/releases/v0.1.0.md` release notes.
- Updated package license metadata to the non-deprecated SPDX string form.
- Built source and wheel artifacts cleanly with `uv build`.
- Refreshed the user-scoped install and verified `codex-wake`, `codex-waked`, and `codex-wake-hook`.
- Recorded evidence in `docs/dev/verification/0004-2026-05-18-release-packaging-install-docs.md`.
- Closed P11 in `ROADMAP.md`.
- Opened P12 with `docs/dev/plans/0012-2026-05-18-user-daemon-service-dogfood-wake.md`.

Best next turn option: commit and tag `v0.1.0`, then complete P12 by selecting a user-scoped daemon path and dogfooding a real wake.

## Turn 15 | 2026-05-18

Completed P12 user daemon service and dogfood wake.

- Added `docs/daemon-service.md` as the user-scoped systemd runbook.
- Added `docs/examples/systemd/codex-wake.service` as the repo-specific service template.
- Verified this workstation has a usable `systemctl --user` manager and `Linger=yes`.
- Installed and started `codex-wake-codex-wake.service`.
- Ran an initial dogfood wake through the service and observed ack, then found the service log was empty.
- Added continuous daemon activity logging for non-empty poll results.
- Bumped package version to `0.1.1` because the installed daemon behavior changed after the `v0.1.0` release.
- Reinstalled the user-scoped tool and verified the installed daemon contains the logging path.
- Ran a second dogfood wake through the service and observed ack plus service log activity.
- Stopped and disabled the user service after verification.
- Recorded evidence in `docs/dev/verification/0005-2026-05-18-user-daemon-service-dogfood-wake.md`.
- Closed P12 in `ROADMAP.md`.
- Opened P13 with `docs/dev/plans/0013-2026-05-18-service-installer-cli.md`.

Best next turn option: commit, tag, and publish `v0.1.1`, then implement P13 so service install/status/logs/stop/uninstall are managed by `codex-wake service`.

## Turn 16 | 2026-05-18

Completed P13 service installer CLI.

- Added `codex_wake.service` for user systemd unit rendering and lifecycle helpers.
- Added `codex-wake service install`.
- Added `codex-wake service status`.
- Added `codex-wake service logs`.
- Added `codex-wake service stop`.
- Added `codex-wake service uninstall`.
- Updated README and daemon-service docs to prefer the CLI-managed path.
- Bumped package version to `0.2.0`.
- Fixed systemd unit rendering after live validation showed quoted `WorkingDirectory` was rejected as non-absolute.
- Made `service install` verify that the unit becomes active before reporting success.
- Validated installed service lifecycle with a temporary `codex-wake-p13-smoke.service`.
- Validated `service logs` with an intentionally missing tmux pane wake, producing daemon activity without targeting a live pane.
- Recorded evidence in `docs/dev/verification/0006-2026-05-18-service-installer-cli.md`.
- Closed P13 in `ROADMAP.md`.
- Opened P14 with `docs/dev/plans/0014-2026-05-18-hook-setup-doctor-cli.md`.

Best next turn option: commit, tag, and publish `v0.2.0`, then implement P14 so hook setup and readiness checks are available through `codex-wake`.

## Turn 17 | 2026-05-18

Completed P14 hook setup and doctor CLI.

- Added `codex_wake.hook_config` for repo-local `.codex/hooks.json` rendering and checking.
- Added `codex-wake hook install`.
- Added `codex-wake hook check`.
- Added `codex-wake doctor`.
- Updated tracked `.codex/hooks.json` and `docs/dev/codex-hooks.example.json` to use installed `codex-wake-hook`.
- Updated README hook setup to prefer `codex-wake hook install/check`.
- Bumped package version to `0.3.0`.
- Added `docs/releases/v0.3.0.md`.
- Recorded evidence in `docs/dev/verification/0007-2026-05-18-hook-setup-doctor-cli.md`.
- Closed P14 in `ROADMAP.md`.
- Opened P15 with `docs/dev/plans/0015-2026-05-18-clean-fresh-install-smoke.md`.

Best next turn option: commit, tag, and publish `v0.3.0`, then run P15 as a clean install from the public GitHub tag.

## Turn 18 | 2026-05-18

Completed P15 clean fresh install smoke.

- Installed `v0.3.0` from `git+https://github.com/CochranResearchGroup/codex-wake.git@v0.3.0` into isolated `/tmp` `UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`, and `UV_CACHE_DIR`.
- Verified isolated `codex-wake`, `codex-waked`, and `codex-wake-hook`.
- Verified `hook install` and `hook check` against a temporary repo.
- Verified `doctor` with the isolated bin directory at the front of `PATH`.
- Verified temporary user service install/status/logs/uninstall from the clean install.
- Recorded evidence in `docs/dev/verification/0008-2026-05-18-clean-fresh-install-smoke.md`.
- Closed P15 in `ROADMAP.md`.
- Opened P16 with `docs/dev/plans/0016-2026-05-18-ci-release-gates.md`.

Best next turn option: implement P16 with GitHub Actions for unit tests, package build, and lightweight CLI smoke on push and pull request.

## Turn 19 | 2026-05-18

Dogfooded a wake against this active Codex TUI pane.

- Confirmed this session exposes `TMUX_PANE=%202` and tmux socket `/tmp/tmux-1000/default`.
- Started the CLI-managed user service with `codex-wake service install`.
- Scheduled `wake_20260519_030204_9085` with a 45 second `not_before` predicate targeting this pane.
- Observed the canonical wake prompt land in this same Codex TUI, proving current-pane tmux injection works.
- Observed missing `UserPromptSubmit` ack in this already-running session, so the daemon retried and then failed closed after three attempts.
- Stopped and disabled `codex-wake-codex-wake.service` after the dogfood run.
- Recorded evidence in `docs/dev/verification/0009-2026-05-18-current-tui-dogfood.md`.

Best next turn option: run `/hooks` in this TUI to review/trust `codex-wake-hook`, then rerun a short current-pane wake to close the live-session ack gap before continuing P16 CI gates.

## Turn 20 | 2026-05-18

Repeated the current TUI dogfood after a hook-review attempt.

- Scheduled `wake_20260519_031211_5457` with a 20 second `not_before` predicate.
- Observed the canonical wake prompt land in this same TUI pane again.
- Confirmed the ack file was still missing after the ack window.
- Stopped the service and cancelled the still-firing wake to prevent later retries.
- Appended the repeat evidence to `docs/dev/verification/0009-2026-05-18-current-tui-dogfood.md`.

Best next turn option: invoke the actual Codex `/hooks` interactive review UI in this TUI and explicitly trust `codex-wake-hook`; then run one more 20 second wake and expect `status=submitted` plus an ack file.

## Turn 21 | 2026-05-18

Investigated why `codex-wake-hook` was not visible in `/hooks`.

- Confirmed `codex features list` reports `hooks` as enabled.
- Confirmed official Codex docs say repo hooks are discovered from `<repo>/.codex/hooks.json` and listed through `/hooks`.
- Confirmed this repo has `.codex/hooks.json` with `UserPromptSubmit -> codex-wake-hook`.
- Confirmed shared Codex config contains an existing hook trust-state entry for this repo path.
- Concluded this active TUI likely did not load the repo hook source for the current session, so `/hooks` cannot review it here.
- Updated `codex-wake hook check`, `codex-wake doctor`, README, service docs, and the current-TUI dogfood note to call out the missing-list case explicitly.

Best next turn option: restart or resume Codex in `/home/ecochran76/workspace.local/codex-wake`, confirm `/hooks` lists the repo `.codex/hooks.json` source, trust it if prompted, then rerun one short current-pane wake.

## Turn 22 | 2026-05-18

Retried dogfood after the operator found the hook under `UserPromptHooks`.

- Scheduled `wake_20260519_033023_e611` for a 20 second current-pane wake.
- The wake did not paste because the pane lock already existed.
- Confirmed stale lock file `.codex/wake/locks/tmp_tmux-1000_default__202.lock` contained dead PID `3672992`.
- Stopped the service and cancelled the wake.
- Patched `PaneLock` to remove dead-PID and malformed lock files before acquiring a pane lock.
- Added tests for stale dead-PID and malformed lock cleanup.
- Appended the evidence to `docs/dev/verification/0009-2026-05-18-current-tui-dogfood.md`.

Best next turn option: remove the current stale lock with the patched code path, reinstall the tool, then rerun one 20 second wake now that `UserPromptHooks` has been found.

## Turn 23 | 2026-05-19

Completed a successful current TUI dogfood wake.

- Scheduled `wake_20260519_104518_d191` for a 20 second current-pane wake.
- The stale pane lock was cleaned by the patched dispatch path.
- The daemon pasted the canonical wake prompt into pane `%202`.
- `UserPromptSubmit` ran and added the wake trigger context to this turn.
- The hook wrote `.codex/wake/acks/wake_20260519_104518_d191.submitted`.
- The daemon observed the ack and marked the wake `submitted`.
- The service log ended with `checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0`.
- Stopped and disabled `codex-wake-codex-wake.service` after the pass.
- Appended the pass evidence to `docs/dev/verification/0009-2026-05-18-current-tui-dogfood.md`.

Best next turn option: commit this dogfood pass, then continue P16 CI release gates from the now-validated current-TUI wake baseline.

## Turn 24 | 2026-05-19

Completed P16 CI release gates.

- Added `.github/workflows/ci.yml`.
- CI runs on push to `main` and pull request.
- Matrix covers Python 3.11 and 3.12.
- Each job runs compile checks, standard-library unit tests, package build, installed-wheel command smoke, non-wake hook smoke, and tmux-env-only wake creation.
- Local validation passed after moving the package-build dependency install into a temporary venv.
- First upstream run passed but warned that `actions/checkout@v4` and `actions/setup-python@v5` use Node 20.
- Updated the workflow to `actions/checkout@v6` and `actions/setup-python@v6`.
- Final upstream run `26092549749` passed both matrix jobs.
- Recorded evidence in `docs/dev/verification/0010-2026-05-19-ci-release-gates.md`.
- Closed P16 in `ROADMAP.md` and `docs/dev/plans/0016-2026-05-18-ci-release-gates.md`.

Best next turn option: decide the next release boundary after the stale-lock fix and CI gates, likely a `v0.3.1` patch release with release notes and clean tag install smoke.

## Turn 25 | 2026-05-19

Started the `v0.3.1` patch release boundary.

- Selected `v0.3.1` for stale pane-lock cleanup, hook visibility diagnostics, current-TUI dogfood proof, and CI release gates.
- Bumped package version to `0.3.1`.
- Added `docs/releases/v0.3.1.md`.

Best next turn option: run local release validation, commit, tag `v0.3.1`, publish the GitHub release, and verify a clean install from the public tag.

## Turn 26 | 2026-05-19

Published and verified `v0.3.1`.

- Ran local release validation: compileall, `44` unit tests, package build, installed-wheel command smoke, non-wake hook smoke, and tmux-env-only wake creation.
- Committed `aad1be4` with the `0.3.1` version bump and release notes.
- Tagged and pushed `v0.3.1`.
- Published GitHub release `https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.3.1`.
- Verified clean public tag install with isolated `UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`, and `UV_CACHE_DIR`.
- Verified installed tag commands, hook install/check, wake creation, and doctor output.
- Confirmed upstream CI run `26102171944` passed on the release commit.
- Recorded evidence in `docs/dev/verification/0011-2026-05-19-v0.3.1-release.md`.

Best next turn option: open a new roadmap lane for either `file_changed`/`process_done` predicates or app-server-controlled wake hardening.

## Turn 27 | 2026-05-19

Opened P17 for event predicates.

- Selected `file_changed` and `process_done` as the next runtime slice.
- Added `docs/dev/plans/0017-2026-05-19-event-predicates.md`.
- Opened P17 in `ROADMAP.md`.
- Started implementation with `codex-wake changed <path>` and `codex-wake pid <pid>`.

Best next turn option: finish predicate implementation, run source and CLI validation, record evidence, and close P17.

## Turn 28 | 2026-05-19

Completed P17 event predicates.

- Added `codex-wake changed <path> -- <prompt>` for file creation or mtime/size changes.
- Added `codex-wake pid <pid> -- <prompt>` for process-exit waits.
- Added daemon evaluation for `file_changed` and `process_done`.
- Kept both predicates declarative; wake records still do not execute shell commands.
- Documented examples and PID-reuse limit in `README.md`.
- Added focused CLI and daemon tests.
- Ran source validation: `51` tests passed.
- Ran CLI smoke with `--no-dispatch`, confirming both predicates move from `pending` to `firing`.
- Recorded evidence in `docs/dev/verification/0012-2026-05-19-event-predicates.md`.
- Closed P17 in `ROADMAP.md` and `docs/dev/plans/0017-2026-05-19-event-predicates.md`.

Best next turn option: cut `v0.4.0` for the new predicate surface, with clean tag install smoke and release notes.

## Turn 29 | 2026-05-19

Started the `v0.4.0` release boundary.

- Selected `v0.4.0` because P17 adds new CLI commands and predicate semantics.
- Bumped package version to `0.4.0`.
- Added `docs/releases/v0.4.0.md`.

Best next turn option: run local release validation, commit, tag `v0.4.0`, publish the GitHub release, and verify a clean install from the public tag.

## Turn 30 | 2026-05-19

Published and verified `v0.4.0`.

- Ran local release validation: compileall, `51` unit tests, package build, installed-wheel command smoke, non-wake hook smoke, and installed-wheel `changed`/`pid` predicate smokes.
- Committed `63ccd12` with the `0.4.0` version bump and release notes.
- Tagged and pushed `v0.4.0`.
- Published GitHub release `https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.4.0`.
- Verified clean public tag install with isolated `UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`, and `UV_CACHE_DIR`.
- Verified clean tag commands, daemon no-dispatch, `changed` predicate movement, `pid` predicate movement, and doctor output.
- Confirmed upstream CI run `26126484154` passed on the release commit.
- Recorded evidence in `docs/dev/verification/0013-2026-05-19-v0.4.0-release.md`.

Best next turn option: open a new roadmap lane for app-server controlled wake hardening or PID-reuse-safe process predicates.

## Turn 31 | 2026-05-19

Opened P18 for app-server hardening.

- Selected app-server hardening over PID-reuse safety because it advances the preferred controlled wake transport.
- Added `docs/dev/plans/0018-2026-05-19-app-server-hardening.md`.
- Opened P18 in `ROADMAP.md`.
- Added explicit `codex-wake app after` and `codex-wake app at` commands.
- Added app-server dispatch metadata capture for accepted `thread_id` and `turn_id`.
- Updated README and app-server docs.

Best next turn option: run source and CLI validation, record P18 evidence, close the lane, then consider a release boundary.

## Turn 32 | 2026-05-19

Completed P18 app-server hardening.

- Added explicit `codex-wake app after <thread-id> <duration> -- <prompt>`.
- Added explicit `codex-wake app at <thread-id> <timestamp> -- <prompt>`.
- Kept non-stdio app-server endpoints rejected.
- App-server dispatch now records a `dispatch_attempt` event before requests.
- App-server dispatch now stores accepted `thread_id` and `turn_id` metadata in `dispatch_result` when available.
- Added focused CLI and app-server dispatch tests.
- Ran source validation: `53` tests passed.
- Ran CLI smoke creating both app-server `after` and `at` wakes.
- Recorded evidence in `docs/dev/verification/0014-2026-05-19-app-server-hardening.md`.
- Closed P18 in `ROADMAP.md` and `docs/dev/plans/0018-2026-05-19-app-server-hardening.md`.

Best next turn option: cut `v0.4.1` for the app-server CLI and dispatch metadata hardening, or continue to a PID-reuse-safety lane before releasing.

## Turn 33 | 2026-05-19

Started the `v0.4.1` release for P18 app-server hardening.

- Selected release over a new PID-reuse-safety lane because P18 is already closed and changes installed agent-facing CLI behavior.
- Bumped package version to `0.4.1`.
- Added `docs/releases/v0.4.1.md`.

Best next turn option: run source and installed-package release validation, then tag and publish `v0.4.1` if validation passes.

## Turn 34 | 2026-05-19

Published and verified `v0.4.1`.

- Ran source validation: compileall and `53` unit tests.
- Built and installed the local wheel in temporary virtual environments.
- Smoked installed `codex-wake`, `codex-waked`, and `codex-wake-hook`.
- Smoked installed-wheel `app after` and `app at` wake creation.
- Committed `2f53ea9`, tagged and pushed `v0.4.1`, and published the GitHub release.
- Verified clean public tag installation with isolated `uv` tool/cache directories.
- Confirmed upstream CI run `26127180628` passed on the release commit.
- Recorded evidence in `docs/dev/verification/0015-2026-05-19-v0.4.1-release.md`.

Best next turn option: open a PID-reuse-safety lane for `process_done`, because it is the main known correctness gap left in the event predicate surface.

## Turn 35 | 2026-05-19

Opened P19 for PID reuse safety.

- Selected PID reuse safety because `process_done` was the main known correctness gap after `v0.4.1`.
- Added `docs/dev/plans/0019-2026-05-19-pid-reuse-safety.md`.
- Opened P19 in `ROADMAP.md`.

Best next turn option: implement process identity capture and daemon identity comparison, then validate source and installed CLI behavior.

## Turn 36 | 2026-05-19

Implemented P19 PID reuse safety.

- Added Linux `/proc` process identity helpers.
- Updated `codex-wake pid` to record process start time and boot id when available.
- Updated daemon `process_done` evaluation to fire when a live PID no longer matches the registered identity.
- Preserved liveness fallback for old records and platforms without process identity data.
- Updated README process predicate behavior and limits.

Best next turn option: run source validation and installed CLI smokes, then record P19 verification and close the lane if validation passes.

## Turn 37 | 2026-05-19

Completed P19 PID reuse safety.

- Ran source validation: compileall and `61` unit tests.
- Ran source CLI smoke with a live `sleep` process.
- Confirmed source `codex-wake pid` recorded process start time and boot id on this host.
- Confirmed source daemon kept the wake pending while the process lived and moved it to `firing` after exit.
- Built and installed a local wheel in temporary virtual environments.
- Confirmed installed `codex-wake` and `codex-waked` produced the same PID wake behavior.
- Recorded evidence in `docs/dev/verification/0016-2026-05-19-pid-reuse-safety.md`.
- Closed P19 in `ROADMAP.md` and `docs/dev/plans/0019-2026-05-19-pid-reuse-safety.md`.

Best next turn option: commit and push P19, wait for CI, then cut `v0.4.2` if the branch remains green.

## Turn 38 | 2026-05-19

Started the `v0.4.2` release for P19 PID reuse safety.

- Selected release because P19 changes runtime wake predicate behavior and installed CLI output.
- Bumped package version to `0.4.2`.
- Added `docs/releases/v0.4.2.md`.

Best next turn option: run source and installed-package release validation, then tag and publish `v0.4.2` if validation passes.

## Turn 39 | 2026-05-19

Published and verified `v0.4.2`.

- Ran source validation: compileall and `61` unit tests.
- Built and installed the local wheel in temporary virtual environments.
- Smoked installed `codex-wake`, `codex-waked`, and `codex-wake-hook`.
- Smoked installed-wheel PID wake identity capture and `pending -> firing` after process exit.
- Committed `e6c91dd`, tagged and pushed `v0.4.2`, and published the GitHub release.
- Verified clean public tag installation with isolated `uv` tool/cache directories.
- Confirmed clean public tag PID wake identity capture and `pending -> firing` after process exit.
- Confirmed upstream CI run `26130628026` passed on the release commit.
- Recorded evidence in `docs/dev/verification/0017-2026-05-19-v0.4.2-release.md`.

Best next turn option: open a retention/cleanup policy lane for wake runtime state, because active trigger behavior is now solid enough to revisit archive defaults and operator cleanup ergonomics.

## Turn 40 | 2026-05-19

Opened P20 for runtime retention cleanup.

- Selected retention cleanup because active trigger behavior is stable and archived wake records currently have no pruning command.
- Added `docs/dev/plans/0020-2026-05-19-runtime-retention-cleanup.md`.
- Opened P20 in `ROADMAP.md`.
- Chose a conservative cleanup shape: dry-run by default, delete only archived records, and optionally archive terminal records first.

Best next turn option: implement `codex-wake cleanup`, test dry-run/delete behavior, and validate installed CLI cleanup smokes.

## Turn 41 | 2026-05-19

Completed P20 runtime retention cleanup.

- Added `codex-wake cleanup`.
- Kept cleanup dry-run by default.
- Limited deletion to records already under `.codex/wake/archive/`.
- Added `--delete`, `--older-than`, and `--archive-terminal`.
- Updated README and runtime-state docs.
- Ran source validation: compileall and `65` unit tests.
- Ran source CLI cleanup smoke.
- Built and installed a local wheel in temporary virtual environments.
- Ran installed CLI cleanup smoke.
- Recorded evidence in `docs/dev/verification/0018-2026-05-19-runtime-retention-cleanup.md`.
- Closed P20 in `ROADMAP.md` and `docs/dev/plans/0020-2026-05-19-runtime-retention-cleanup.md`.

Best next turn option: commit and push P20, wait for CI, then cut `v0.4.3` if the branch remains green.

## Turn 42 | 2026-05-19

Started the `v0.4.3` release for P20 runtime retention cleanup.

- Selected release because P20 adds an installed operator command for runtime state cleanup.
- Bumped package version to `0.4.3`.
- Added `docs/releases/v0.4.3.md`.

Best next turn option: run source and installed-package release validation, then tag and publish `v0.4.3` if validation passes.

## Turn 43 | 2026-05-19

Published and verified `v0.4.3`.

- Ran source validation: compileall and `65` unit tests.
- Built and installed the local wheel in temporary virtual environments.
- Smoked installed `codex-wake`, `codex-waked`, and `codex-wake-hook`.
- Smoked installed-wheel cleanup archive, dry-run, and delete behavior.
- Committed `279c975`, tagged and pushed `v0.4.3`, and published the GitHub release.
- Verified clean public tag installation with isolated `uv` tool/cache directories.
- Confirmed clean public tag cleanup archive, dry-run, and delete behavior.
- Confirmed upstream CI run `26135597539` passed on the release commit.
- Recorded evidence in `docs/dev/verification/0019-2026-05-19-v0.4.3-release.md`.

Best next turn option: open a hook/session visibility lane so `doctor` can better distinguish hook config on disk from hooks loaded in the active Codex TUI.

## Turn 44 | 2026-05-19

Opened P21 for hook session visibility.

- Selected hook visibility because current diagnostics still blur `.codex/hooks.json` config state with active-TUI hook execution.
- Added `docs/dev/plans/0021-2026-05-19-hook-session-visibility.md`.
- Opened P21 in `ROADMAP.md`.
- Chose ack evidence diagnostics instead of TUI transcript scraping.

Best next turn option: add latest-ack runtime evidence to `hook check` and `doctor`, then validate source and installed CLI output.

## Turn 45 | 2026-05-19

Completed P21 hook session visibility.

- Added hook runtime ack evidence.
- Updated `codex-wake hook check` to report ack count, latest ack metadata, and active-session hook evidence state.
- Updated `codex-wake doctor` to report the same hook runtime evidence.
- Documented that no ack means active-session hook state is unknown, not that tmux injection failed.
- Ran source validation: compileall and `68` unit tests.
- Ran source CLI smoke for no-ack and observed-ack states.
- Built and installed a local wheel in temporary virtual environments.
- Ran installed CLI smoke for no-ack and observed-ack states.
- Recorded evidence in `docs/dev/verification/0020-2026-05-19-hook-session-visibility.md`.
- Closed P21 in `ROADMAP.md` and `docs/dev/plans/0021-2026-05-19-hook-session-visibility.md`.

Best next turn option: commit and push P21, wait for CI, then cut `v0.4.4` if the branch remains green.

## Turn 46 | 2026-05-19

Started the `v0.4.4` release for P21 hook session visibility.

- Selected release because P21 changes installed operator diagnostics in `hook check` and `doctor`.
- Bumped package version to `0.4.4`.
- Added `docs/releases/v0.4.4.md`.

Best next turn option: run source and installed-package release validation, then tag and publish `v0.4.4` if validation passes.

## Turn 47 | 2026-05-19

Published and verified `v0.4.4`.

- Ran source validation: compileall and `68` unit tests.
- Built and installed the local wheel in temporary virtual environments.
- Smoked installed `codex-wake`, `codex-waked`, and `codex-wake-hook`.
- Smoked installed-wheel hook diagnostics for no-ack and observed-ack states.
- Committed `a357c0b`, tagged and pushed `v0.4.4`, and published the GitHub release.
- Verified clean public tag installation with isolated `uv` tool/cache directories.
- Confirmed clean public tag hook diagnostics output.
- Confirmed upstream CI run `26137262586` passed on the release commit.
- Recorded evidence in `docs/dev/verification/0021-2026-05-19-v0.4.4-release.md`.

Best next turn option: open a wake-record schema/versioning lane to document compatibility for optional predicate and diagnostic fields before adding more runtime metadata.

## Turn 48 | 2026-05-19

Opened P22 for wake record schema versioning.

- Selected schema/versioning because optional predicate, dispatch, archive, and diagnostic fields have accumulated while `schema_version` remains `1`.
- Added `docs/dev/plans/0022-2026-05-19-wake-record-schema-versioning.md`.
- Added `docs/dev/wake-record-schema.md`.
- Added `codex-wake schema` and `codex-wake schema --json`.
- Opened P22 in `ROADMAP.md`.

Best next turn option: validate the schema command from source and installed wheel, record evidence, close P22, and push if validation passes.

## Turn 49 | 2026-05-19

Completed P22 wake record schema versioning.

- Documented schema version `1` in `docs/dev/wake-record-schema.md`.
- Defined the compatibility policy as additive optional fields.
- Documented required fields, status vocabulary, target variants, predicate variants, optional fields, derived ack files, and schema bump triggers.
- Added `codex-wake schema`.
- Added `codex-wake schema --json`.
- Ran source validation: compileall and `70` unit tests.
- Ran source CLI schema smoke.
- Built and installed a local wheel in temporary virtual environments.
- Ran installed CLI schema smoke.
- Recorded evidence in `docs/dev/verification/0022-2026-05-19-wake-record-schema-versioning.md`.
- Closed P22 in `ROADMAP.md` and `docs/dev/plans/0022-2026-05-19-wake-record-schema-versioning.md`.

Best next turn option: commit and push P22, wait for CI, then cut `v0.4.5` if the branch remains green.

## Turn 50 | 2026-05-19

Started the `v0.4.5` release for P22 wake record schema versioning.

- Bumped package version to `0.4.5`.
- Added `docs/releases/v0.4.5.md`.

Best next turn option: run source and installed-package release validation, then tag and publish `v0.4.5` if validation passes.

## Turn 51 | 2026-05-19

Published and verified `v0.4.5`.

- Ran source validation: compileall and `70` unit tests.
- Built `codex_wake-0.4.5.tar.gz` and `codex_wake-0.4.5-py3-none-any.whl`.
- Ran installed-wheel schema command smoke.
- Committed `e4aabf2`, tagged and pushed `v0.4.5`, and published the GitHub release.
- Ran clean public tag install smoke from `git+https://github.com/CochranResearchGroup/codex-wake.git@v0.4.5`.
- Verified public CI run `26139110324` passed.
- Recorded evidence in `docs/dev/verification/0023-2026-05-19-v0.4.5-release.md`.

Best next turn option: open P23 for a user-facing `doctor --json` or `list --json` inspection surface so wake state can be consumed reliably by automation.

## Turn 52 | 2026-05-20

Opened P23 for a machine-readable doctor inspection surface.

- Selected `doctor --json` first because runtime readiness already aggregates command, tmux, hook, ack, and service state.
- Added `docs/dev/plans/0023-2026-05-20-doctor-json.md`.
- Marked P23 active in `ROADMAP.md`.

Best next turn option: implement `doctor --json` over the same structured summary as text `doctor`, then validate source and installed CLI output.

## Turn 53 | 2026-05-20

Completed P23 doctor JSON inspection.

- Added `doctor --json`.
- Factored doctor data collection into a shared structured summary for text and JSON output.
- Preserved existing text `doctor` keys.
- Added tests for JSON shape and text compatibility.
- Updated README usage.
- Ran source validation: compileall and `71` unit tests.
- Built and installed a local working-tree wheel.
- Ran installed CLI smokes for `doctor` and `doctor --json`, including a venv-first `PATH` check for command path fields.
- Recorded evidence in `docs/dev/verification/0024-2026-05-20-doctor-json.md`.
- Closed P23 in `ROADMAP.md` and `docs/dev/plans/0023-2026-05-20-doctor-json.md`.

Best next turn option: commit and push P23, wait for CI, then cut `v0.4.6` if the branch remains green.

## Turn 54 | 2026-05-20

Started the `v0.4.6` release for P23 doctor JSON inspection.

- Bumped package version to `0.4.6`.
- Added `docs/releases/v0.4.6.md`.

Best next turn option: run source and installed-package release validation, then tag and publish `v0.4.6` if validation passes.

## Turn 55 | 2026-05-20

Published and verified `v0.4.6`.

- Ran source validation: compileall and `71` unit tests.
- Built `codex_wake-0.4.6.tar.gz` and `codex_wake-0.4.6-py3-none-any.whl`.
- Ran installed-wheel smokes for text `doctor` and `doctor --json`.
- Committed `b61670f`, tagged and pushed `v0.4.6`, and published the GitHub release.
- Ran clean public tag install smoke from `git+https://github.com/CochranResearchGroup/codex-wake.git@v0.4.6`.
- Verified public CI run `26176601988` passed.
- Recorded evidence in `docs/dev/verification/0025-2026-05-20-v0.4.6-release.md`.

Best next turn option: open P24 for `list --json` enrichment or a compact `status --json` command that summarizes wake counts by state for supervisor automation.

## Turn 56 | 2026-05-20

Opened P24 for a compact status JSON summary surface.

- Selected `status --json` over `list --json` enrichment because `list --json` already exposes full records.
- Added `docs/dev/plans/0024-2026-05-20-status-json.md`.
- Marked P24 active in `ROADMAP.md`.

Best next turn option: implement `codex-wake status` and `codex-wake status --json`, then validate source and installed CLI output.

## Turn 57 | 2026-05-20

Completed P24 status JSON summary.

- Added record-layer `status_summary()`.
- Added `codex-wake status`.
- Added `codex-wake status --json`.
- Updated README usage.
- Added tests for summary logic and CLI text/JSON output.
- Ran source validation: compileall and `73` unit tests.
- Built and installed a local working-tree wheel.
- Ran installed CLI smokes for `status` and `status --json`.
- Recorded evidence in `docs/dev/verification/0026-2026-05-20-status-json.md`.
- Closed P24 in `ROADMAP.md` and `docs/dev/plans/0024-2026-05-20-status-json.md`.

Best next turn option: commit and push P24, wait for CI, then cut `v0.4.7` if the branch remains green.

## Turn 58 | 2026-05-20

Started the `v0.4.7` release for P24 status JSON summaries.

- Bumped package version to `0.4.7`.
- Added `docs/releases/v0.4.7.md`.

Best next turn option: run source and installed-package release validation, then tag and publish `v0.4.7` if validation passes.

## Turn 59 | 2026-05-20

Published and verified `v0.4.7`.

- Ran source validation: compileall and `73` unit tests.
- Built `codex_wake-0.4.7.tar.gz` and `codex_wake-0.4.7-py3-none-any.whl`.
- Ran installed-wheel smokes for `status` and `status --json`.
- Committed `5aa3f61`, tagged and pushed `v0.4.7`, and published the GitHub release.
- Ran clean public tag install smoke from `git+https://github.com/CochranResearchGroup/codex-wake.git@v0.4.7`.
- Verified public CI run `26179270632` passed.
- Recorded evidence in `docs/dev/verification/0027-2026-05-20-v0.4.7-release.md`.

Best next turn option: open P25 for bounded self-dogfood using `status --json` plus a short wake trigger, then record whether the runtime summary helps supervise the wake lifecycle.

## Turn 60 | 2026-05-20

Opened P25 for bounded `status --json` dogfood.

- Added `docs/dev/plans/0025-2026-05-20-status-dogfood.md`.
- Marked P25 active in `ROADMAP.md`.
- Observed that `/home/ecochran76/.local/bin/codex-wake` did not yet expose `status`, so runtime refresh is required before dogfood.
- Confirmed the active shell has `TMUX_PANE=%202`.
- Confirmed `codex-wake-codex-wake.service` exists but is inactive.

Best next turn option: refresh the installed runtime to `v0.4.7`, register a short dogfood wake, use `status --json` to supervise it, and record wake/ack evidence.

## Turn 61 | 2026-05-20

Completed bounded `status --json` dogfood.

- Refreshed the installed runtime to public tag `v0.4.7`.
- Confirmed installed `codex-wake` exposes `status`.
- Captured baseline `status --json` with `active_total=0`.
- Registered dogfood wake `wake_20260520_174316_9be6`.
- Confirmed pending `status --json` reported `active_total=1`, `pending=1`, and `earliest_next_attempt_at=2026-05-20T17:43:36Z`.
- Ran `codex-waked --once --no-dispatch` after the due time to avoid live pane injection during the turn.
- Confirmed daemon result `checked=1 fired=1 failed=0 pending=0 dispatched=0 submitted=0 requeued=0`.
- Confirmed firing `status --json` reported `pending=0` and `firing=1`.
- Cancelled and archived the dogfood wake.
- Confirmed final `status --json` reported `active_total=0`, `archived=1`, and no earliest next attempt.
- Recorded evidence in `docs/dev/verification/0028-2026-05-20-status-dogfood.md`.
- Closed P25 in `ROADMAP.md` and `docs/dev/plans/0025-2026-05-20-status-dogfood.md`.

Best next turn option: commit and push P25, wait for CI, then open P26 for a controlled live-dispatch dogfood or for cleanup UX around old terminal wake records.

## Turn 62 | 2026-05-20

Opened P26 for cleanup JSON output.

- Selected cleanup UX before live-dispatch dogfood because P25 showed historical terminal records cluttering `status --json`.
- Added `docs/dev/plans/0026-2026-05-20-cleanup-json.md`.
- Marked P26 active in `ROADMAP.md`.

Best next turn option: implement `cleanup --json` without changing dry-run defaults, then validate source and installed CLI cleanup output.

## Turn 63 | 2026-05-20

Completed P26 cleanup JSON output.

- Added `codex-wake cleanup --json`.
- Preserved existing text cleanup output and dry-run default behavior.
- JSON output reports mode, retention window, terminal archives, matched archived records, deletion state, and counts.
- Updated README cleanup usage.
- Added cleanup JSON tests.
- Ran source validation: compileall and `74` unit tests.
- Built and installed a local working-tree wheel.
- Ran installed CLI smoke for `cleanup --archive-terminal --json`.
- Recorded evidence in `docs/dev/verification/0029-2026-05-20-cleanup-json.md`.
- Closed P26 in `ROADMAP.md` and `docs/dev/plans/0026-2026-05-20-cleanup-json.md`.

Best next turn option: commit and push P26, wait for CI, then cut `v0.4.8` if the branch remains green.

## Turn 64 | 2026-05-20

Started the `v0.4.8` release for P26 cleanup JSON output.

- Bumped package version to `0.4.8`.
- Added `docs/releases/v0.4.8.md`.

Best next turn option: run source and installed-package release validation, then tag and publish `v0.4.8` if validation passes.

## Turn 65 | 2026-05-20

Published and verified `v0.4.8`.

- Ran source validation: compileall and `74` unit tests.
- Built `codex_wake-0.4.8.tar.gz` and `codex_wake-0.4.8-py3-none-any.whl`.
- Ran installed-wheel smoke for `cleanup --archive-terminal --json`.
- Committed `cebb92c`, tagged and pushed `v0.4.8`, and published the GitHub release.
- Ran clean public tag install smoke from `git+https://github.com/CochranResearchGroup/codex-wake.git@v0.4.8`.
- Verified public CI run `26183703882` passed.
- Recorded evidence in `docs/dev/verification/0030-2026-05-20-v0.4.8-release.md`.

Best next turn option: open P27 for a controlled live-dispatch dogfood with preflight checks for service state, active hook ack baseline, and stale pane locks.

## Turn 66 | 2026-05-20

Opened P27 for controlled live-dispatch dogfood.

- Added `docs/dev/plans/0027-2026-05-20-live-dispatch-dogfood.md`.
- Marked P27 active in `ROADMAP.md`.
- Re-read planning, runtime-state, and agent-runtime policies.
- Used memory guidance to re-check active hook state, avoid stale lock assumptions, and preserve correct global flag ordering.
- Captured preflight state: `active_total=0`, hook config installed, latest ack is the older `wake_20260519_104518_d191`, repo service is inactive, current tmux pane is `%202`, and no pane lock files were present.
- Pane capture showed the current turn was actively running, so live dispatch should be delayed until after the pane can go idle.

Best next turn option: schedule one short tmux wake plus a delayed one-shot daemon dispatch, then let the wake-triggered turn verify ack and record movement.

## Turn 67 | 2026-05-20

Scheduled the P27 live-dispatch dogfood wake.

- Registered `wake_20260520_214519_1ee0` with `codex-wake --wake-root .codex/wake after 45s`.
- Confirmed the wake record targets tmux pane `%202` on `/tmp/tmux-1000/default`.
- Confirmed `status --json` reports `active_total=1`, `pending=1`, and `earliest_next_attempt_at=2026-05-20T21:46:04Z`.
- Armed a bounded user-systemd one-shot timer: `codex-wake-p27-live-wake_20260520_214519_1ee0.timer`.
- The timer activates `codex-waked --wake-root /home/ecochran76/workspace.local/codex-wake/.codex/wake --once --ack-timeout 15`.

Best next turn option: let the wake-triggered prompt land, then verify the ack file and wake events before archiving or recording any failure.

## Turn 68 | 2026-05-20

Completed the P27 live-dispatch dogfood.

- Wake-triggered prompt landed for `wake_20260520_214519_1ee0`.
- Verified current UTC time `2026-05-20T21:46:37Z` was after predicate due time `2026-05-20T21:46:04Z`.
- Verified the wake record showed `predicate_matched`, `dispatch_attempt`, and `ack_observed` at `2026-05-20T21:46:18Z`.
- Verified hook ack `.codex/wake/acks/wake_20260520_214519_1ee0.submitted` with matching wake id, session id, turn id, and submitted timestamp.
- Verified transient dispatcher journal reported `checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0`.
- Archived the submitted dogfood wake.
- Confirmed final `status --json` reports `active_total=0` and no `earliest_next_attempt_at`.
- Recorded evidence in `docs/dev/verification/0031-2026-05-20-live-dispatch-dogfood.md`.
- Closed P27 in `ROADMAP.md` and `docs/dev/plans/0027-2026-05-20-live-dispatch-dogfood.md`.

Best next turn option: commit and push P27, wait for CI, then open the next roadmap lane for either installed-runtime retention cleanup or app-server-backed dispatch design.

## Turn 69 | 2026-05-20

Opened P28 for installed runtime state tidy dogfood.

- Re-read planning, runtime-state, and validation policies.
- Confirmed `main` was clean and aligned with `origin/main`.
- Captured baseline `status --json`: `active_total=0`, `terminal_total=4`, `archived_total=2`, and no `earliest_next_attempt_at`.
- Added `docs/dev/plans/0028-2026-05-20-installed-runtime-state-tidy-dogfood.md`.
- Marked P28 active in `ROADMAP.md`.

Best next turn option: run installed `codex-wake --wake-root .codex/wake cleanup --archive-terminal --json`, verify terminal records were archived without deletion, then close P28 if the current cleanup surface is sufficient.

## Turn 70 | 2026-05-20

Completed P28 installed runtime state tidy dogfood.

- Attempted installed `codex-wake --wake-root .codex/wake cleanup --archive-terminal --json`.
- Found the user-scoped installed tool was stale at `codex-wake v0.4.7`, which rejected `--json`.
- Refreshed the installed tool from public tag `v0.4.8` with `uv tool install --force`.
- Verified installed cleanup help now includes `--json`.
- Ran `codex-wake --wake-root .codex/wake cleanup --archive-terminal --json`.
- Archived four terminal records: `wake_20260519_030204_9085`, `wake_20260519_031211_5457`, `wake_20260519_033023_e611`, and `wake_20260519_104518_d191`.
- Did not pass `--delete`; no archived records were deleted.
- Confirmed final `status --json` reports `active_total=0`, `terminal_total=0`, `archived_total=6`, and no `earliest_next_attempt_at`.
- Recorded evidence in `docs/dev/verification/0032-2026-05-20-installed-runtime-state-tidy-dogfood.md`.
- Closed P28 in `ROADMAP.md` and `docs/dev/plans/0028-2026-05-20-installed-runtime-state-tidy-dogfood.md`.

Best next turn option: commit and push P28, wait for CI, then open the app-server-backed dispatch design lane.

## Turn 71 | 2026-05-20

Completed P29 app-server contract refresh.

- Re-read planning, runtime-state, and agent-runtime policies.
- Used the `openai-docs` skill because this lane depends on Codex app-server behavior.
- Confirmed `main` was clean and aligned with `origin/main`.
- Checked local Codex CLI: `codex-cli 0.131.0`.
- Verified `codex app-server --help` still supports `stdio://`, Unix sockets, WebSockets, and WebSocket auth modes.
- Generated current app-server JSON schema with `codex app-server generate-json-schema --out /tmp/codex-app-schema-p29 --experimental`.
- Confirmed schema still includes `thread/resume` and `turn/start`; `ThreadResumeParams` requires `threadId`, `TurnStartParams` requires `threadId` and `input`, and `TurnStartResponse` returns `turn`.
- Ran a source-tree stdio initialize smoke with `PYTHONPATH=src`; it returned Codex home, platform, and user-agent metadata.
- Updated `docs/dev/app-server-mode.md` with the current local contract and implementation boundary.
- Recorded evidence in `docs/dev/verification/0033-2026-05-20-app-server-contract-refresh.md`.
- Closed P29 in `ROADMAP.md` and `docs/dev/plans/0029-2026-05-20-app-server-contract-refresh.md`.

Best next turn option: commit and push P29, wait for CI, then choose between disposable-thread app-server dogfood and thread-status preflight implementation.

## Turn 72 | 2026-05-20

Started P30 app-server thread status preflight.

- Re-read planning, runtime-state, agent-runtime, and validation policies.
- Used memory guidance to keep the app-server path local-auth/minimal and to distinguish source-tree work from installed runtime behavior.
- Confirmed `main` was clean and aligned with `origin/main`.
- Added `docs/dev/plans/0030-2026-05-21-app-server-thread-status-preflight.md`.
- Implemented a read-only `thread/read` client method and `codex-wake app status <thread-id>`.
- Added app-server dispatch preflight: after `thread/resume`, dispatch records thread status and starts `turn/start` only for `idle` threads.
- Active app-server threads are requeued with backoff instead of receiving a new turn.
- Added focused app-server and CLI tests for status output, idle dispatch, and active-thread requeue.
- Focused tests passed: `PYTHONPATH=src python -m unittest tests.test_app_server` and `PYTHONPATH=src python -m unittest tests.test_cli`.

Best next turn option: run full repo validation, update verification docs, then close and publish P30 if validation passes.

## Turn 73 | 2026-05-20

Completed P30 app-server thread status preflight.

- Updated `README.md` and `docs/dev/app-server-mode.md` for `codex-wake app status`.
- Ran source validation:
  - `PYTHONPATH=src python -m compileall -q src tests`
  - `PYTHONPATH=src python -m unittest tests.test_app_server`
  - `PYTHONPATH=src python -m unittest tests.test_cli`
  - `PYTHONPATH=src python -m unittest discover -s tests`
- Full suite passed with `77` tests.
- Smoked source CLI `app status --help`.
- Smoked source app-server wake record creation in a temporary wake root.
- Installed the working tree into the user-scoped uv tool with `uv tool install --force .`.
- Smoked installed `codex-wake app status --help`.
- Smoked installed app-server wake record creation in a temporary wake root.
- Recorded evidence in `docs/dev/verification/0034-2026-05-21-app-server-thread-status-preflight.md`.
- Closed P30 in `ROADMAP.md` and `docs/dev/plans/0030-2026-05-21-app-server-thread-status-preflight.md`.

Best next turn option: commit and push P30, wait for CI, then cut a `v0.4.9` release for the app-server preflight CLI/runtime change.

## Turn 74 | 2026-05-20

Started the `v0.4.9` release for P30 app-server thread status preflight.

- Re-read engineering/git/release and validation policies.
- Confirmed `main` was clean and aligned with `origin/main`.
- Bumped `pyproject.toml` to `0.4.9`.
- Added `docs/releases/v0.4.9.md`.
- Ran source validation: compileall, `77` unit tests, and `git diff --check`.
- Built `codex_wake-0.4.9.tar.gz` and `codex_wake-0.4.9-py3-none-any.whl`.
- Ran installed-wheel smoke for `codex-wake app status --help`.
- Ran installed-wheel smoke for `codex-wake --wake-root "$ROOT/wake" app after thread_abc 1m`.
- Recorded evidence in `docs/dev/verification/0035-2026-05-21-v0.4.9-release.md`.

Best next turn option: commit the release files, tag and push `v0.4.9`, wait for CI, run a clean public tag install smoke, then publish the GitHub release.

## Turn 75 | 2026-05-20

Published and verified `v0.4.9`.

- Committed release files as `72b78fa`.
- Tagged and pushed `v0.4.9`.
- Verified branch CI run `26199151140` passed on Python 3.11 and 3.12.
- Ran clean public tag install smoke from `git+https://github.com/CochranResearchGroup/codex-wake.git@v0.4.9`.
- Confirmed public tag install reports package version `0.4.9`.
- Smoked public tag `codex-wake app status --help`.
- Smoked public tag app-server wake record creation in a temporary wake root.
- Published GitHub release `https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.4.9`.
- Updated `docs/dev/verification/0035-2026-05-21-v0.4.9-release.md` with public tag and release evidence.

Best next turn option: commit and push the final release verification note, wait for CI, then open a disposable-thread app-server dogfood lane.
