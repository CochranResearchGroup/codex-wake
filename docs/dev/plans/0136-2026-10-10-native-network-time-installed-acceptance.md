# Plan 0136 — Installed native network-time acceptance

State: OPEN
Workflow: IN_PROGRESS
Owner: primary agent
Branch: feat/native-network-time
Work-Item: docs/dev/plans/0136-2026-10-10-native-network-time-installed-acceptance.md

## Current State

Source dependency0135 accepted. Separate immutable candidate installed; unattended
after/at checks armed. See ../evidence/plan0133/installed-checkpoint.md.
Acceptance remains incomplete.

## Parent

[Plan0133](0133-2026-10-10-native-network-time-parity.md) governs scope and execution.

## What to Build

Qualify an immutable installed candidate through the normal scheduler and a
real disposable Codex recipient, including deadline holds, restart and rollback.
Record source, release and installed identities before claiming product readiness.

## Blocked by

0135-2026-10-10-native-network-time-recovery.md

## Acceptance Criteria

- [ ] Complete native after and at runs through the installed CLI/normal supervisor; initiating turn ends before real exact-thread follow-up completes, with no controller reply or manual replay.
- [ ] Record admitted live source readback and controlled single-loss behavior; distinguish deterministic outage/expiry controls from actual live evidence.
- [ ] Installed outage/conflict controls preserve deadlines and block effects; recovery and worker restart complete or expire according to those original deadlines.
- [ ] Installed file TTL, cancellation, missing/busy recipient and uncertainty/no-resend controls pass with raw receipts.
- [ ] Compatibility and rollback restore the prior installation without mutating live imports or destroying new-policy records; unsupported readers hold visibly.
- [ ] Run required source/installed/hosted checks, adjudicate Standards and Spec separately, and retain failures with invalidation limits.
- [ ] Before parent closure verify exact integrated/released/installed identities, owned-client cleanup and preserved conversations; unrelated roots, services and protected state remain unchanged.

## Scope, Non-goals and Definition of Done

Scope is the behavior above; parent non-goals apply. Record source-bound evidence
for every criterion and the applicable compatibility/review gates before marking
DONE. Expected write surface: native CLI/records/scheduler tests and documentation
for0134/0135; acceptance tooling, evidence and release projections for0136.
No isolated helper pass substitutes for the public behavior required here.
