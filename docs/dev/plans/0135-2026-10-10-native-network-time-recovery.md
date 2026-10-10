# Plan 0135 — Safe native deadline evaluation and recovery

State: PLANNED
Workflow: BLOCKED
Owner: primary agent
Branch: docs/native-time-parity
Work-Item: docs/dev/plans/0135-2026-10-10-native-network-time-recovery.md

## Current State

Approved ticket; implementation and acceptance have not run.

## Parent

[Plan0133](0133-2026-10-10-native-network-time-parity.md) governs scope and execution.

## What to Build

An armed native wake holds during time uncertainty, resumes on trustworthy
evidence, and reaches its exact recipient without early dispatch or premature
expiry. Its original due time and expiry survive worker restart.

## Blocked by

0134-2026-10-10-native-network-time-arming.md

## Acceptance Criteria

- [ ] Public scheduler evaluates due, retry eligibility and expiry in the persisted network domain; guest clock skew cannot release or expire the wake.
- [ ] Boundary-crossing intervals hold; accepted lower bounds govern due/expiry and expiration takes precedence when both have elapsed.
- [ ] Provider loss and conflict visibly hold new effects; inspection and cancellation remain available.
- [ ] Outage/recovery and worker restart retain original due/expiry; fresh boot/round evidence is required and deadlines are never rebased.
- [ ] Busy/missing recipients and optional exact-thread resume retain their guards within trustworthy TTL evaluation.
- [ ] Crash before/after native submission retains one durable intent and attempts count; reconciliation never resends an ambiguous effect.
- [ ] Legacy native records are neither silently reinterpreted nor replayed; any opt-in migration preserves original bytes, deadlines and transport identity.

## Scope, Non-goals and Definition of Done

Scope is the behavior above; parent non-goals apply. Record source-bound evidence
for every criterion and the applicable compatibility/review gates before marking
DONE. Expected write surface: native CLI/records/scheduler tests and documentation
for0134/0135; acceptance tooling, evidence and release projections for0136.
No isolated helper pass substitutes for the public behavior required here.
