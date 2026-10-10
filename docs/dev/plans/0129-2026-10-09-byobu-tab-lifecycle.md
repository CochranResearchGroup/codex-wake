# Plan 0129 — Open and close exact Byobu tabs

State: CLOSED
Workflow: DONE
Owner: primary agent lane
Branch: feat/native-workflows
Parent: docs/dev/plans/0127-2026-10-09-native-codex-wake-product-boundary.md
Blocked by: None

## Current State

Installed candidate acceptance passed new/exact resume/reuse/explicit extra attachment, active/pending close guards, ordinary idle close, force preservation, and identity mismatch refusal. Signal and mailbox authorities are inspected alongside JSON records.975 candidate tests and affected regression checks passed. See [acceptance](../evidence/plan0127/0129-acceptance.md) and exact source hashes. Released v0.9.0 adds normal installed lifecycle/close evidence and983 frozen installed tests; parent completion-audit.md records final qualification and retained failed samples.

## What to Build

Open and close exact Byobu tabs, as one complete user-visible slice under the parent product contract.

## Acceptance Criteria

- [x] Open explicitly creates a conversation with a chosen directory or resumes one exact thread; return thread and tab identities.
- [x] Reuse an existing attachment unless another is explicitly requested; do not create implicit worktrees.
- [x] Closing active or pending-work tabs refuses; force-close preserves conversations and records and reports affected work.
- [x] A disposable real session proves new, resume, reuse, close and identity mismatch handling.

## Scope and Non-goals

Only this slice and its required behavior validation. Do not expand trigger classes, alter unrelated projects, claim exactly-once delivery or remove unqualified legacy paths.

## Validation and Definition of Done

Verify public CLI behavior and exact durable/native outcomes with focused regression checks and a bounded disposable live run where applicable. Retain failures, review standards/spec independently, and bind evidence to source and installed versions before closing.
