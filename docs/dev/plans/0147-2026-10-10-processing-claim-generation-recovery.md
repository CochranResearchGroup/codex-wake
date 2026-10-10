# Ticket0147 — Recover processing ownership across generations

State: PLANNED
Workflow: READY
Owner: primary
Lane: P71
Branch: docs/a2a-completion-stream
Target: origin/main
Integration: governed_by_plan0141
Work-Item: docs/dev/plans/0147-2026-10-10-processing-claim-generation-recovery.md
Parent: docs/dev/plans/0141-2026-10-10-a2a-completion-stream.md
Depends-On: Plan0146

## What it delivers

After a worker generation ends, the same recipient can determine whether work is already owned/completed or needs explicit reconciliation, without duplicate processing or fabricated completion.

## Blocked by

[0146](0146-2026-10-10-held-recovery-disposition.md)

## Acceptance criteria

- [ ] Public mailbox/worker regression freezes accepted claim, generation change and terminal/unknown cases; stale actors cannot release, steal or complete a claim.
- [ ] New generation observes prior acceptance and completion receipts; explicit recovery/reconciliation handles orphaned ownership without granting extra task rights.
- [ ] An already-owned claim never grants permission to start again merely because read or notification is repeated; uncertain prior processing remains held.
- [ ] Installed fresh-process control proves same-thread attribution, fencing and cleanup; no old live message is manually completed or replayed.

## Test seam and bound

Public accepted-work claim and reconciliation seams under disposable generation transitions. One smallest red loop per ownership gap; no provider effects.

## Owned write surface

Processing claim/recovery semantics and necessary guards/tests/evidence; no automatic business-task replay.

## Execution and terminal condition

One primary owner; obey Plan0141 authority, evidence and no-replay rules. Before
implementation, register the actual branch/checkpoint and update this header.
READY means refined and unblocked, not implemented. DONE requires all acceptance
checks, attributable source/evidence, integration or explicit non-code completion,
and owned cleanup. BLOCKED records a missing dependency/evidence, not approval
inferred from elapsed time. Planning alone does not satisfy a behavior criterion.
