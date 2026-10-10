# Plan 0131 — Prove the complete native agent lifecycle

State: CLOSED
Workflow: DONE
Owner: primary agent lane
Branch: feat/native-workflows
Parent: docs/dev/plans/0127-2026-10-09-native-codex-wake-product-boundary.md
Blocked by: docs/dev/plans/0128-2026-10-09-native-durable-delivery.md — Deliver an existing durable wake natively; docs/dev/plans/0129-2026-10-09-byobu-tab-lifecycle.md — Open and close exact Byobu tabs; docs/dev/plans/0130-2026-10-09-native-delivery-recovery.md — Recover interrupted native delivery

## Current State

Installed two-agent lifecycle passed at sourcec579ebe. A assigned B natively, armed a file condition and ended its turn; the independent installed scheduler resumed A17 seconds later, read result42 and displayed the exact response. Guard, separate cancellation and ordinary close preserved B conversation. Current-source0130 receipts cover expiry and explicit same-thread resume. See [acceptance](../evidence/plan0127/0131-acceptance.md). Candidate release/migration remain0132; parent staysopen.

## What to Build

Prove the complete native agent lifecycle, as one complete user-visible slice under the parent product contract.

## Acceptance Criteria

- [x] Open recipient tab, assign ordinary work natively, arm a condition follow-up, end the sender turn, observe due execution and reply, then close the tab preserving the conversation.
- [x] Real tab, native transcript and durable record evidence agree on exact identities and outcome.
- [x] Exercise guarded close with pending work, cancellation separate from close, expiry and per-workflow same-thread resume.
- [x] Record installed/source versions and limitations; code review evaluates standards and spec independently.

## Scope and Non-goals

Only this slice and its required behavior validation. Do not expand trigger classes, alter unrelated projects, claim exactly-once delivery or remove unqualified legacy paths.

## Validation and Definition of Done

Verify public CLI behavior and exact durable/native outcomes with focused regression checks and a bounded disposable live run where applicable. Retain failures, review standards/spec independently, and bind evidence to source and installed versions before closing.
