# Plan 0136 — Installed native network-time acceptance

State: CLOSED
Workflow: COMPLETE
Owner: primary agent
Branch: feat/native-network-time
Work-Item: docs/dev/plans/0136-2026-10-10-native-network-time-installed-acceptance.md

## Current State

Complete: integrated PR230 commit17b4d9833d33588bea1fd9987224561f7cca0953,
published v0.10.0, active immutable0.10.0-17b4d98 installation. Real unattended
native after/at and installed controls qualify; release assets/module parity,
quiescent supervisor rollout and unrelated-unit preservation verified.
Final hosted CI waiting explicitly waived by user: "skip CI". Prior source CI
and local/installed evidence retained; final CI success is not inferred.
See ../evidence/plan0133/installed-acceptance.md and installed/release-activation.json.
Disposable tab closed preserving conversation; no migration or unrelated rollout.

## Parent

[Plan0133](0133-2026-10-10-native-network-time-parity.md) governs scope and execution.

## What to Build

Qualify an immutable installed candidate through the normal scheduler and a
real disposable Codex recipient, including deadline holds, restart and rollback.
Record source, release and installed identities before claiming product readiness.

## Blocked by

0135-2026-10-10-native-network-time-recovery.md

## Acceptance Criteria

- [x] Complete native after and at runs through the installed CLI/normal supervisor; initiating turn ends before real exact-thread follow-up completes, with no controller reply or manual replay.
- [x] Record admitted live source readback and controlled single-loss behavior; distinguish deterministic outage/expiry controls from actual live evidence.
- [x] Installed outage/conflict controls preserve deadlines and block effects; recovery and worker restart complete or expire according to those original deadlines.
- [x] Installed file TTL, cancellation, missing/busy recipient and uncertainty/no-resend controls pass with raw receipts.
- [x] Compatibility and rollback restore the prior installation without mutating live imports or destroying new-policy records; unsupported readers hold visibly.
- [x] Run required source/installed/hosted checks, adjudicate Standards and Spec separately, and retain failures with invalidation limits.
- [x] Before parent closure verify exact integrated/released/installed identities, owned-client cleanup and preserved conversations; unrelated roots, services and protected state remain unchanged.

## Scope, Non-goals and Definition of Done

Scope is the behavior above; parent non-goals apply. Record source-bound evidence
for every criterion and the applicable compatibility/review gates before marking
DONE. Expected write surface: native CLI/records/scheduler tests and documentation
for0134/0135; acceptance tooling, evidence and release projections for0136.
No isolated helper pass substitutes for the public behavior required here.
