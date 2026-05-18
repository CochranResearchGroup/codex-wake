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
