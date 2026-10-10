# Plan 0125 — Keep mailbox deadlines usable through time uncertainty

State: CLOSED
Workflow: DONE
Owner: primary agent lane
Branch: feature/network-time-consensus
Parent: docs/dev/plans/0122-2026-10-08-network-first-time-provider.md
Blocked by: docs/dev/plans/0123-2026-10-08-network-time-inspection.md

## Current State

Completed explicit schema-3 mailbox migration, retryable uncertain admission, time-independent inspection/cancellation and bounded expiry/delivery recovery. Disposable tests prove interrupted commits, concurrent admission, fresh-process persistence, preserved deadlines and intact legacy guards. Acceptance mapping, two-axis review, installed identity and final validation: `docs/dev/evidence/plan0126/acceptance-review.md`.

## What to Build

Agents using a disposable mailbox can create, inspect and cancel during time uncertainty; deadline-dependent effects pause and recover automatically without moving existing deadlines.

## Required Inputs

Plan0122, its committed decision core and tests, and the primary-source production qualification note under `docs/dev/evidence/plan0122/production-requirements.md`. Read current repo policy and applicable TDD/code-review skills before implementation.

## Acceptance Criteria

- [x] Define creation semantics when no trusted time exists: preserve explicit deadlines; retain relative intent as visibly pending or return a specific retryable error, never fabricate UTC.
- [x] Demonstrate inspection and cancellation during uncertainty without mutating guarded time anchors.
- [x] Hold expiration and time-dependent delivery until accepted bounds settle the original deadline; recover automatically when trusted evidence returns.
- [x] Document state versioning, compatibility, migration and rollback before changing persisted data. Preserve original deadlines and attributable anomaly evidence.
- [x] Use disposable stores to prove cross-process persistence, interrupted writes, concurrent evaluation, foreign boot/round rejection and recovery.
- [x] Prove no early release at interval boundaries and no accidental clearing/bypass of the existing live mailbox guard.

## Expected Write Surface

Mailbox API/CLI behavior, deadline/state handling, migration fixtures and integration tests using temporary state.

## Validation and Definition of Done

Record meaningful failing controls before behavior fixes, focused passing tests, entrypoint readback and standards/spec review. Commit the bounded slice with acceptance evidence, reconcile dependency status, and close only when every criterion is supported. Documentation publication alone is not implementation completion.

## Non-goals

No live checkpoint reset, production store migration, real agent messages, session notifications or installed runtime activation.
