# Plan 0129 — Open and close exact Byobu tabs

State: PLANNED
Workflow: READY_FOR_AGENT
Owner: primary agent lane
Branch: prototype/native-session-lookup
Parent: docs/dev/plans/0127-2026-10-09-native-codex-wake-product-boundary.md
Blocked by: None

## Current State

Approved ticket; implementation not started. Execute only after every listed blocker is CLOSED with passing evidence. The parent execution contract governs this ticket; planning, mocks and prototype results alone cannot close it.

## What to Build

Open and close exact Byobu tabs, as one complete user-visible slice under the parent product contract.

## Acceptance Criteria

- [ ] Open explicitly creates a conversation with a chosen directory or resumes one exact thread; return thread and tab identities.
- [ ] Reuse an existing attachment unless another is explicitly requested; do not create implicit worktrees.
- [ ] Closing active or pending-work tabs refuses; force-close preserves conversations and records and reports affected work.
- [ ] A disposable real session proves new, resume, reuse, close and identity mismatch handling.

## Scope and Non-goals

Only this slice and its required behavior validation. Do not expand trigger classes, alter unrelated projects, claim exactly-once delivery or remove unqualified legacy paths.

## Validation and Definition of Done

Verify public CLI behavior and exact durable/native outcomes with focused regression checks and a bounded disposable live run where applicable. Retain failures, review standards/spec independently, and bind evidence to source and installed versions before closing.
