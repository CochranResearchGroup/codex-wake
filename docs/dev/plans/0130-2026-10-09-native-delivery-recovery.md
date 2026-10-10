# Plan 0130 — Recover interrupted native delivery

State: PLANNED
Workflow: READY_FOR_AGENT
Owner: primary agent lane
Branch: prototype/native-session-lookup
Parent: docs/dev/plans/0127-2026-10-09-native-codex-wake-product-boundary.md
Blocked by: docs/dev/plans/0128-2026-10-09-native-durable-delivery.md — Deliver an existing durable wake natively

## Current State

Approved ticket; implementation not started. Execute only after every listed blocker is CLOSED with passing evidence. The parent execution contract governs this ticket; planning, mocks and prototype results alone cannot close it.

## What to Build

Recover interrupted native delivery, as one complete user-visible slice under the parent product contract.

## Acceptance Criteria

- [ ] Inject interruption before submission, after acceptance and before recording; retain attribution and reconcile exact native evidence.
- [ ] Never blindly resend ambiguous work; unresolved submission remains inspectable.
- [ ] Qualify busy, detached and restarted-client cases individually; unsupported cases remain explicit pending/expiry outcomes.
- [ ] Demonstrate scheduler-process restart with disposable state; host or shared-daemon restart requires separately bounded authority.

## Scope and Non-goals

Only this slice and its required behavior validation. Do not expand trigger classes, alter unrelated projects, claim exactly-once delivery or remove unqualified legacy paths.

## Validation and Definition of Done

Verify public CLI behavior and exact durable/native outcomes with focused regression checks and a bounded disposable live run where applicable. Retain failures, review standards/spec independently, and bind evidence to source and installed versions before closing.
