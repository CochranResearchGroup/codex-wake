# Plan 0128 — Deliver an existing durable wake natively

State: PLANNED
Workflow: READY_FOR_AGENT
Owner: primary agent lane
Branch: prototype/native-session-lookup
Parent: docs/dev/plans/0127-2026-10-09-native-codex-wake-product-boundary.md
Blocked by: None

## Current State

Approved ticket; implementation not started. Execute only after every listed blocker is CLOSED with passing evidence. The parent execution contract governs this ticket; planning, mocks and prototype results alone cannot close it.

## What to Build

Deliver an existing durable wake natively, as one complete user-visible slice under the parent product contract.

## Acceptance Criteria

- [ ] A real installed scheduler submits one due wake to an exact idle thread without TUI injection or an originating agent turn.
- [ ] Record native acceptance identity separately from recipient execution and acknowledgment.
- [ ] Busy/unavailable recipients remain pending until expiry; ordinary direct-send failure creates no implicit mailbox record.
- [ ] Transport selection is explicit; uncertain native submission never automatically falls back.

## Scope and Non-goals

Only this slice and its required behavior validation. Do not expand trigger classes, alter unrelated projects, claim exactly-once delivery or remove unqualified legacy paths.

## Validation and Definition of Done

Verify public CLI behavior and exact durable/native outcomes with focused regression checks and a bounded disposable live run where applicable. Retain failures, review standards/spec independently, and bind evidence to source and installed versions before closing.
