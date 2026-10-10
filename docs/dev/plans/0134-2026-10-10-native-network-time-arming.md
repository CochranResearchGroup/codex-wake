# Plan 0134 — Native network-time arming

State: OPEN
Workflow: IN_PROGRESS
Owner: primary agent
Branch: feat/native-network-time
Work-Item: docs/dev/plans/0134-2026-10-10-native-network-time-arming.md

## Current State

Source behavior implemented and qualified in isolated Python3.12.13: comprehensive
993 tests pass; exact hosted head remains the acceptance gate. See
../evidence/plan0133/source-checkpoint.md. No installed/runtime activation claimed.

## Parent

[Plan0133](0133-2026-10-10-native-network-time-parity.md) governs scope and execution.

## What to Build

New native after/at wakes and file-trigger TTL registration use the existing
network-first provider. An unavailable-time command fails visibly with no wake.
The persisted contract identifies its time policy without corrupting schema4.

## Blocked by

None — can start immediately

## Acceptance Criteria

- [ ] Public CLI creates relative due time and TTL from the conservative upper bound; timezone-qualified absolute input retains its instant.
- [ ] Arming with unavailable, tied, stale or invalid evidence returns a useful error and leaves no partial wake or submission.
- [ ] Qualified single-source loss and healthy Windows fallback obey the existing provider policy; guest UTC does not become an implicit fallback.
- [ ] Native file registration establishes TTL using the same time domain.
- [ ] Persisted policy/version is readable across a fresh process; current native and classic records remain readable with truthful policy identity.
- [ ] Document the record/reader compatibility decision before mutation; test rejected malformed policy metadata and preserve original records.

## Scope, Non-goals and Definition of Done

Scope is the behavior above; parent non-goals apply. Record source-bound evidence
for every criterion and the applicable compatibility/review gates before marking
DONE. Expected write surface: native CLI/records/scheduler tests and documentation
for0134/0135; acceptance tooling, evidence and release projections for0136.
No isolated helper pass substitutes for the public behavior required here.
