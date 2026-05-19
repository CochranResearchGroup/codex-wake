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
