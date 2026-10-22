# MR-02: Preserve Codex wakes through the runtime interface

State: PLANNED
Owner: ecochran76
Work item: CW-MR-172/MR-02 (local draft; not posted)
Priority: First-release dependency order
Blocked by: MR-01
Specification: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md)

## Outcome

An existing Codex user schedules and receives the same durable wake through the new runtime interface, with unchanged exact-thread, deadline and reconciliation guarantees.

## Scope

Introduce the approved small delivery seam and its Codex adapter along the existing wake path. Expand the versioned runtime envelope only as needed; preserve legacy readers/keys. Use MR-01's real Grok variation to keep the interface useful.

## Non-goals

Do not implement a universal plugin SDK, change Codex namespace derivation, weaken owning-client checks, reset counters or alter unrelated trigger semantics.

## Acceptance Evidence

- [ ] AC6: existing Codex public-interface delivery/identity regression controls remain green.
- [ ] AC5: stale binding, expiry, cancellation, crash and uncertain submission remain conservative.
- [ ] AC7: capability/readiness results distinguish unsupported, unqualified and unavailable.
- [ ] Specify the runtime envelope compatibility and unknown-target behavior; old records keep their meaning.
- [ ] Test the seam through real callers with injected protocol dependencies, rather than wrapper-only assertions.

## Repository Surface and Risks

Wake dispatcher, exact recipient discovery, Codex runtime delivery and record compatibility; relevant native/session/identity tests.

Persistent schemas and identity admission are shared integration surfaces. Allocate any new schema version against the implementation base, not this draft.

A complete slice requires its stated evidence. Source completion, integration,
installed acceptance and external publication remain separate states.
