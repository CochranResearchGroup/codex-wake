# Plan 0134 — Native network-time arming

State: CLOSED
Workflow: COMPLETE
Owner: primary agent
Branch: feat/native-network-time
Work-Item: docs/dev/plans/0134-2026-10-10-native-network-time-arming.md

## Current State

Source acceptance qualified at f3a72e80c8383c98172230d6242fa3e5b6f7de08.
Hosted Python3.11/3.12 gates passed in run38061083627. Source regressions,
reader compatibility and primary Standards/Spec adjudication are recorded in
../evidence/plan0133/. LitScout repair is preserved; 11 combined focused tests
passed. Installed acceptance belongs to ticket0136 and is not claimed here.

## Parent

[Plan0133](0133-2026-10-10-native-network-time-parity.md) governs scope and execution.

## What to Build

New native after/at wakes and file-trigger TTL registration use the existing
network-first provider. An unavailable-time command fails visibly with no wake.
The persisted contract identifies its time policy without corrupting schema4.

## Blocked by

None — can start immediately

## Acceptance Criteria

- [x] Public CLI creates relative due time and TTL from the conservative upper bound; timezone-qualified absolute input retains its instant.
- [x] Arming with unavailable, tied, stale or invalid evidence returns a useful error and leaves no partial wake or submission.
- [x] Qualified single-source loss and healthy Windows fallback obey the existing provider policy; guest UTC does not become an implicit fallback.
- [x] Native file registration establishes TTL using the same time domain.
- [x] Persisted policy/version is readable across a fresh process; current native and classic records remain readable with truthful policy identity.
- [x] Document the record/reader compatibility decision before mutation; test rejected malformed policy metadata and preserve original records.

## Scope, Non-goals and Definition of Done

Scope is the behavior above; parent non-goals apply. Record source-bound evidence
for every criterion and the applicable compatibility/review gates before marking
DONE. Expected write surface: native CLI/records/scheduler tests and documentation
for0134/0135; acceptance tooling, evidence and release projections for0136.
No isolated helper pass substitutes for the public behavior required here.
