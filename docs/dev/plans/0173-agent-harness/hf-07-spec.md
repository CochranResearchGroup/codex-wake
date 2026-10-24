# HF-07 specification: Revisioned task briefs and assignment scope

State: APPROVED_SPEC
Owner: ecochran76
Decision authority: HF-01 and first-frontier interview records, including direct
2026-10-24 follow-up. Source baseline: origin/main f96f4c8; planning branch
4dfdc39. This spec describes proposed behavior, not implemented capability.
Public caller seams and the three-ticket breakdown were approved by the operator.

## Problem Statement

A worker needs a stable account of what it is authorized to accomplish. A mutable
prompt or worker completion report cannot establish scope, approval or acceptance.
Existing checkpoints already carry obligations and authority references; the new
brief must complement them rather than become a competing authority store.

## Solution

Pin a revisioned task brief to one assignment, including approved objective,
phase, non-goals, acceptance conditions and bounded source references. Separate
proposed revisions from approved revisions and current assignment admission.

## User Stories

1. As an operator, I want to attach an approved objective and phase to each assignment, so that I can keep execution tied to approved scope and attributable decisions.
2. As an operator, I want to pin non-goals and acceptance references so the worker knows its boundary, so that I can keep execution tied to approved scope and attributable decisions.
3. As an operator, I want to provide bounded evidence-linked context instead of copying entire transcripts, so that I can keep execution tied to approved scope and attributable decisions.
4. As an operator, I want to allow workers to propose scope revisions without approving them, so that I can keep execution tied to approved scope and attributable decisions.
5. As an operator, I want to allow an operator or explicitly delegated controller to approve a revision, so that I can keep execution tied to approved scope and attributable decisions.
6. As an operator, I want to keep an in-flight instruction on the revision admitted at its start, so that I can keep execution tied to approved scope and attributable decisions.
7. As an operator, I want to apply the next approved revision at the following instruction boundary, so that I can keep execution tied to approved scope and attributable decisions.
8. As an operator, I want to handle urgent changes through an explicit stop or steer, so that I can keep execution tied to approved scope and attributable decisions.
9. As an operator, I want to reconstruct the admitted revision after a controller restart, so that I can keep execution tied to approved scope and attributable decisions.
10. As an operator, I want to carry task obligations and allowance references through successor handoff, so that I can keep execution tied to approved scope and attributable decisions.

## Implementation Decisions

- One task-brief owner exposes propose, approve, inspect and assignment-admit
  behaviors. A task identifier is independent of managed-agent/native identities;
  HF-07 does not require HF-02 to manufacture a task identity.
- Retain immutable versioned brief revisions and approval provenance under the
  configured private Wake root. An assignment pins task ID, revision, content
  digest and approving authority reference, not a mutable latest pointer alone.
- Include objective, declared phase, non-goals, acceptance conditions and bounded
  context/evidence references. Retain existing allocation/permission references;
  the brief neither duplicates usage counters nor issues grants.
- Operator or appropriately delegated controller approval promotes a revision.
  Worker proposals remain proposals; copied approval text cannot attest the caller.
- Approval and assignment admission serialize around the selected revision so an
  assignment cannot observe half a revision. Repeated identical admission returns
  its original pin; changed intent under the same assignment key is rejected.
- A running instruction retains its admitted revision. Later approval affects
  future admission only; an urgent change uses the existing explicit stop/steer
  boundary and records the relationship. No retroactive authorization.
- Context references have explicit bounded representation and stable digests or
  revision locators where available. Changed/missing required evidence is surfaced
  before admission, without silently substituting current unrelated material.
- Expose the same brief/admission semantics through CLI and MCP and include the
  pin in existing assignment/checkpoint projections. This is not the workflow VM;
  HF-09 later consumes the pinned contract.
- Older assignments without a brief keep existing semantics and are clearly
  distinguishable. Do not invent retroactive approval. Unknown record versions
  hold; persist with current locking/private-write patterns.

## Testing Decisions

Exercise the public assignment admission and brief-management callers with
private disposable state and trusted caller/delegation fixtures. Test worker
proposal versus controller approval, out-of-scope delegated approval, concurrent
revision/admission, same-key changed intent, in-flight old revision versus next
admission, restart recovery, bounded context, missing required evidence and
successor checkpoint continuity. Existing handoff/checkpoint and assignment
receipt tests provide prior art. Assertions inspect admitted behavior and durable
pins; they do not mirror serialization helpers. No model call is necessary.

## Out of Scope

No new permission-profile engine, workflow interpreter, corpus ingestion,
automatic scope expansion, resource ledger or independent work-acceptance system.
HF-06 enforces operation profiles; HF-08 verifies acceptance; this brief declares
inputs and required evidence without implementing either feature wholesale.

## Further Notes

[Resolved interview](first-frontier-decisions.md) and [shared decisions](hf-01-decisions-and-handoffs.md) own product provenance. This document proposes the bounded build contract. The parent backlog owns wider sequencing. Public caller seams and ticket granularity were approved by the operator.

Canonical implementation work item: [#316](https://github.com/CochranResearchGroup/codex-wake/issues/316).
