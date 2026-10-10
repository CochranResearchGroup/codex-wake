# Plan 0128 — Deliver an existing durable wake natively

State: CLOSED
Workflow: DONE
Owner: primary agent lane
Branch: feat/native-workflows
Parent: docs/dev/plans/0127-2026-10-09-native-codex-wake-product-boundary.md
Blocked by: None

## Current State

Installed isolated candidate delivered a real due wake, held a busy recipient then delivered after idle, and held an unavailable exact thread until expiry. Evidence: docs/dev/evidence/plan0127/0128-acceptance.md. Native acceptance is explicitly distinct from execution/ack; no full-plan completion claim.

## What to Build

Deliver an existing durable wake natively, as one complete user-visible slice under the parent product contract.

## Acceptance Criteria

- [x] A real installed scheduler submits one due wake to an exact idle thread without TUI injection or an originating agent turn.
- [x] Record native acceptance identity separately from recipient execution and acknowledgment.
- [x] Busy/unavailable recipients remain pending until expiry; ordinary direct-send failure creates no implicit mailbox record.
- [x] Transport selection is explicit; uncertain native submission never automatically falls back.

## Scope and Non-goals

Only this slice and its required behavior validation. Do not expand trigger classes, alter unrelated projects, claim exactly-once delivery or remove unqualified legacy paths.

## Validation and Definition of Done

Verify public CLI behavior and exact durable/native outcomes with focused regression checks and a bounded disposable live run where applicable. Retain failures, review standards/spec independently, and bind evidence to source and installed versions before closing.
