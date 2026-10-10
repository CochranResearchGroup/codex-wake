# Plan 0130 — Recover interrupted native delivery

State: CLOSED
Workflow: DONE
Owner: primary agent lane
Branch: feat/native-workflows
Parent: docs/dev/plans/0127-2026-10-09-native-codex-wake-product-boundary.md
Blocked by: docs/dev/plans/0128-2026-10-09-native-durable-delivery.md — Deliver an existing durable wake natively

## Current State

Installed recovery acceptance passed exact native reconciliation, safe pre-submission restart, unresolved intent holds, busy/expiry, default detached hold, explicit same-thread headless resume and visible-client restart.978 comprehensive tests pass. See [acceptance](../evidence/plan0127/0130-acceptance.md), retained failed assumptions, source hashes and actual native/systemd receipts. Shared daemon and host were not restarted. Candidate remains unreleased.

## What to Build

Recover interrupted native delivery, as one complete user-visible slice under the parent product contract.

## Acceptance Criteria

- [x] Inject interruption before submission, after acceptance and before recording; retain attribution and reconcile exact native evidence.
- [x] Never blindly resend ambiguous work; unresolved submission remains inspectable.
- [x] Qualify busy, detached and restarted-client cases individually; unsupported cases remain explicit pending/expiry outcomes.
- [x] Demonstrate scheduler-process restart with disposable state; host or shared-daemon restart requires separately bounded authority.

## Scope and Non-goals

Only this slice and its required behavior validation. Do not expand trigger classes, alter unrelated projects, claim exactly-once delivery or remove unqualified legacy paths.

## Validation and Definition of Done

Verify public CLI behavior and exact durable/native outcomes with focused regression checks and a bounded disposable live run where applicable. Retain failures, review standards/spec independently, and bind evidence to source and installed versions before closing.
