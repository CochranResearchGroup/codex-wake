# Plan 0132 — Migrate and retire redundant delivery paths

State: CLOSED
Workflow: DONE
Owner: primary agent lane
Branch: feat/native-workflows
Parent: docs/dev/plans/0127-2026-10-09-native-codex-wake-product-boundary.md
Blocked by: docs/dev/plans/0131-2026-10-09-native-agent-lifecycle-acceptance.md — Prove the complete native agent lifecycle

## Current State

Installed0.9.0 migration source gates pass: native schema4 and metadata-only
promotion preserve uncertainty; installed oldreader holds and restored reader
executes; implicit basic tmux capture retires with explicit compatibility
retained.983 comprehensive tests, installed wheel smoke and real native turn
readback pass. See [acceptance](../evidence/plan0127/0132-acceptance.md).
Migration/capability documentation is published at remote source27bd7af. All
child criteria pass; parent integration, release and normal installation remain
unproven.

## What to Build

Migrate and retire redundant delivery paths, as one complete user-visible slice under the parent product contract.

## Acceptance Criteria

- [x] Inventory each legacy path and its callers, persisted formats and qualified replacement before proposing removal.
- [x] Prove existing state remains readable and recovery and rollback supported with disposable copies.
- [x] Retire only paths whose replacement contract passes; retain explicitly required compatibility without silent fallback.
- [x] Publish migration, capability and product-boundary documentation; no unapproved destructive state cleanup.

## Scope and Non-goals

Only this slice and its required behavior validation. Do not expand trigger classes, alter unrelated projects, claim exactly-once delivery or remove unqualified legacy paths.

## Validation and Definition of Done

Verify public CLI behavior and exact durable/native outcomes with focused regression checks and a bounded disposable live run where applicable. Retain failures, review standards/spec independently, and bind evidence to source and installed versions before closing.

## Migration contract fixed before implementation

Retire implicit tmux capture for the qualified basic time/file registration
verbs. Require `--legacy-tmux` for that compatibility path; prefer the explicit
`native after|at|file THREAD TRIGGER` interface. Existing persisted tmux records
continue to dispatch. Advanced signal and tracked-mailbox paths retain their
existing interfaces because replacement parity has not been qualified.

Native records use schema4, restricted to exact native targets and basic time
or file predicates. Current readers also accept the earlier candidate schema1
native records; an explicit metadata-only migration promotes them to schema4,
preserving identifiers, prompts, events, status and uncertainty. Migration does
not submit work. Older releases hold unknown schema4 rather than interpreting
native work as tmux. Rollback retains those records until a capable reader is
restored; no conversion to legacy delivery is implied.
