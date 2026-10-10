# Plan 0132 — Migrate and retire redundant delivery paths

State: PLANNED
Workflow: READY_FOR_AGENT
Owner: primary agent lane
Branch: feat/native-workflows
Parent: docs/dev/plans/0127-2026-10-09-native-codex-wake-product-boundary.md
Blocked by: docs/dev/plans/0131-2026-10-09-native-agent-lifecycle-acceptance.md — Prove the complete native agent lifecycle

## Current State

Approved ticket; implementation not started. Execute only after every listed blocker is CLOSED with passing evidence. The parent execution contract governs this ticket; planning, mocks and prototype results alone cannot close it.

## What to Build

Migrate and retire redundant delivery paths, as one complete user-visible slice under the parent product contract.

## Acceptance Criteria

- [ ] Inventory each legacy path and its callers, persisted formats and qualified replacement before proposing removal.
- [ ] Prove existing state remains readable and recovery and rollback supported with disposable copies.
- [ ] Retire only paths whose replacement contract passes; retain explicitly required compatibility without silent fallback.
- [ ] Publish migration, capability and product-boundary documentation; no unapproved destructive state cleanup.

## Scope and Non-goals

Only this slice and its required behavior validation. Do not expand trigger classes, alter unrelated projects, claim exactly-once delivery or remove unqualified legacy paths.

## Validation and Definition of Done

Verify public CLI behavior and exact durable/native outcomes with focused regression checks and a bounded disposable live run where applicable. Retain failures, review standards/spec independently, and bind evidence to source and installed versions before closing.
