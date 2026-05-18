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
