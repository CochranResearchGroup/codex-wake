# Plan 0131 — Prove the complete native agent lifecycle

State: PLANNED
Workflow: READY_FOR_AGENT
Owner: primary agent lane
Branch: prototype/native-session-lookup
Parent: docs/dev/plans/0127-2026-10-09-native-codex-wake-product-boundary.md
Blocked by: docs/dev/plans/0128-2026-10-09-native-durable-delivery.md — Deliver an existing durable wake natively; docs/dev/plans/0129-2026-10-09-byobu-tab-lifecycle.md — Open and close exact Byobu tabs; docs/dev/plans/0130-2026-10-09-native-delivery-recovery.md — Recover interrupted native delivery

## Current State

Approved ticket; implementation not started. Execute only after every listed blocker is CLOSED with passing evidence. The parent execution contract governs this ticket; planning, mocks and prototype results alone cannot close it.

## What to Build

Prove the complete native agent lifecycle, as one complete user-visible slice under the parent product contract.

## Acceptance Criteria

- [ ] Open recipient tab, assign ordinary work natively, arm a condition follow-up, end the sender turn, observe due execution and reply, then close the tab preserving the conversation.
- [ ] Real tab, native transcript and durable record evidence agree on exact identities and outcome.
- [ ] Exercise guarded close with pending work, cancellation separate from close, expiry and per-workflow same-thread resume.
- [ ] Record installed/source versions and limitations; code review evaluates standards and spec independently.

## Scope and Non-goals

Only this slice and its required behavior validation. Do not expand trigger classes, alter unrelated projects, claim exactly-once delivery or remove unqualified legacy paths.

## Validation and Definition of Done

Verify public CLI behavior and exact durable/native outcomes with focused regression checks and a bounded disposable live run where applicable. Retain failures, review standards/spec independently, and bind evidence to source and installed versions before closing.
