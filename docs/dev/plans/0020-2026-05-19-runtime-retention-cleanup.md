# Runtime Retention Cleanup

State: CLOSED
Lane: P20

## Scope

Improve operator cleanup ergonomics for wake runtime state without weakening active wake safety.

## Non-Goals

- Do not delete active `pending` or `firing` wake records.
- Do not delete terminal records before they are archived.
- Do not delete ack files, logs, locks, or event files in this slice.
- Do not add background automatic cleanup to the daemon.

## Current State

Operators can archive terminal wake records with `codex-wake archive <wake-id>` or `codex-wake archive --all-terminal`. Archived records remain under `.codex/wake/archive/` indefinitely. There is no command to preview or prune old archived records.

## Design

Add a `codex-wake cleanup` command that:

- Defaults to dry-run.
- Prunes only records already in `archive/`.
- Uses `--older-than <duration>` with a conservative default of `30d`.
- Requires `--delete` before removing files.
- Optionally runs `archive --all-terminal` first with `--archive-terminal`.
- Prints per-record action lines and a summary.

The command uses `archived_at`, then `updated_at`, then `created_at` as the retention timestamp. Records without a parseable timestamp are skipped rather than deleted.

Closed by [Runtime Retention Cleanup](../verification/0018-2026-05-19-runtime-retention-cleanup.md).

## Acceptance Criteria

- `codex-wake cleanup` previews old archived records without deleting them.
- `codex-wake cleanup --delete` deletes only eligible archived records.
- `codex-wake cleanup --archive-terminal` archives terminal records before cleanup evaluation.
- Active and non-archived terminal records are never deleted directly.
- README and runtime-state docs describe the retention behavior.
- Source and installed CLI smokes cover dry-run and delete behavior.

## Definition Of Done

This lane can close when tests and CLI smokes verify dry-run, deletion, active-record protection, and optional terminal archival.
