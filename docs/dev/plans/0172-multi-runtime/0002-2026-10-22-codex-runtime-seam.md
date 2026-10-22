# MR-02: Preserve Codex wakes through the runtime interface

State: CLOSED
Ticket state: DONE
Owner: ecochran76
Work item: CW-MR-172/MR-02 (local draft; not posted)
Priority: First-release dependency order
Blocked by: MR-01
Readiness gate: Satisfied by MR-01's managed-launch terminal-observed route; native live control remains unqualified
Lane: P172-MR02
Branch: feat/mr02-runtime-seam
Base: 9618a58
Target: origin/main
Integration: squash_pr
Specification: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md)

## Outcome

An existing Codex user schedules and receives the same durable wake through the new runtime interface, with unchanged exact-thread, deadline and reconciliation guarantees.

## Current State

Source slice complete: version1 runtime interface and Codex adapter preserve the
existing public dispatcher, trusted-time, exact-recipient and durable no-resend
controls. Final full suite: 1428 tests, 1 skipped, PASS. Isolated installed
wheel:94 tests PASS; changed module bytes match source. No persisted schema
change, production installation, live provider prompt or main integration.

[MR-02 verification](../../verification/0172-2026-10-22-mr02-runtime-seam.md) and
[version1 contract](runtime-delivery-contract.md) own compatibility and evidence.
The intermediate legacy-helper regression and its passing repair are retained.
Only MR-02 was ready; primary worked it with zero independent nonblocked tickets
and zero subagents. MR-03 is READY from this source checkpoint. MR-04/MR-05
remain blocked on MR-03; MR-06 remains blocked on MR-04/MR-05.

## Scope

Introduce the approved small delivery seam and its Codex adapter along the existing wake path. Expand the versioned runtime envelope only as needed; preserve legacy readers/keys. Use MR-01's real Grok variation to keep the interface useful.

## Non-goals

Do not implement a universal plugin SDK, change Codex namespace derivation, weaken owning-client checks, reset counters or alter unrelated trigger semantics.

## Acceptance Evidence

- [x] AC6: existing Codex public-interface delivery/identity regression controls remain green.
- [x] AC5: stale binding, expiry, cancellation, crash and uncertain submission remain conservative.
- [x] AC7: capability/readiness results distinguish unsupported, unqualified and unavailable.
- [x] Specify the runtime envelope compatibility and unknown-target behavior; old records keep their meaning.
- [x] Test the seam through real callers with injected protocol dependencies, rather than wrapper-only assertions.

## Repository Surface and Risks

Wake dispatcher, exact recipient discovery, Codex runtime delivery and record compatibility; relevant native/session/identity tests.

Persistent schemas and identity admission are shared integration surfaces. Allocate any new schema version against the implementation base, not this draft.

A complete slice requires its stated evidence. Source completion, integration,
installed acceptance and external publication remain separate states.
