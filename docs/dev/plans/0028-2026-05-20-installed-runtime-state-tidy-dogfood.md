# Installed Runtime State Tidy Dogfood

Date: 2026-05-20

## Scope

Dogfood the installed cleanup surface against the repo wake root after live-dispatch testing left historical terminal records visible in `status --json`.

## Non-Goals

- Do not add product code unless the dogfood reveals a concrete gap.
- Do not delete archived records.
- Do not hide or rewrite wake evidence.
- Do not change schema, status vocabulary, or retention semantics.

## Current State

Closed by `docs/dev/verification/0032-2026-05-20-installed-runtime-state-tidy-dogfood.md`. After refreshing the user-scoped installed tool from v0.4.7 to v0.4.8, `cleanup --archive-terminal --json` archived four terminal records without deleting evidence and final `status --json` reported `active_total=0` and `terminal_total=0`.

## Plan

- Capture baseline `status --json`.
- Run installed `codex-wake cleanup --archive-terminal --json` without `--delete`.
- Confirm terminal records move into `.codex/wake/archive/`.
- Confirm final `status --json` reports `active_total=0`, `terminal_total=0`, and no next attempt.
- Record whether the current cleanup surface is sufficient or if a follow-on product change is needed.

## Acceptance Criteria

- The command is run through the installed `codex-wake` surface with global flags before the subcommand.
- Cleanup output is structured JSON and records archived terminal wake ids.
- No archived wake record is deleted.
- Runtime status is tidier after the command, with active and terminal totals at zero.
- Verification records before/after counts and the exact command.

## Definition Of Done

This lane can close when the runtime state is tidied or the failure is recorded as a product gap, with no ambiguous active dogfood wake left behind.
