# Ticket0148 — Finish remaining fault and session-isolation proof

State: OPEN
Workflow: IN_PROGRESS
Owner: primary
Lane: P71
Branch: docs/a2a-completion-stream
Target: origin/main
Integration: governed_by_plan0141
Work-Item: docs/dev/plans/0148-2026-10-10-remaining-fault-and-ancestry-proof.md
Parent: docs/dev/plans/0141-2026-10-10-a2a-completion-stream.md
Depends-On: Plan0142, Plan0146, Plan0147

## What it delivers

Remaining original fault, compatibility and parent/child isolation requirements have attributable evidence, with wrong-recipient and duplicate effects refused.

## Blocked by

[0142](0142-2026-10-10-native-live-submission.md); [0146](0146-2026-10-10-held-recovery-disposition.md); [0147](0147-2026-10-10-processing-claim-generation-recovery.md)

## Acceptance criteria

- [ ] Produce a row for every original verification0106 requirement family, map later receipts and identify only still-unproved cuts; freeze the finite matrix before executing it.
- [ ] Each remaining ancestry/reparent/restart case uses disposable process/session identities; foreign or changed owner cannot retarget a message, receipt arm or claim.
- [ ] Remaining interruption, writer-fencing and version/schema cases prove preservation or explicit hold, never silent replay or state loss; installed commands cover required process boundaries.
- [ ] Reuse valid multiroot, retention, backup, rollback and resource receipts; document source/freshness relevance rather than pretending old installed versions are current.
- [ ] If matrix scope exceeds one context-sized packet, split this ticket into named bounded children with blockers and identical inherited obligations before execution; parent stays open until every required child has proof.
- [ ] Clean owned processes/tabs and record fresh OS/resource readback. No autonomous unrelated agents, production-store faults or broad service restarts.

## Test seam and bound

Public APIs/CLI and disposable OS identity fixtures; provider-free fault cuts followed only by required installed boundaries. Each case has predeclared expected result, original intent and stop condition.

## Owned write surface

Finite acceptance matrix and reproduced corrections; no speculative fuzz/soak expansion.

## Execution and terminal condition

One primary owner; obey Plan0141 authority, evidence and no-replay rules. Before
implementation, register the actual branch/checkpoint and update this header.
READY means refined and unblocked, not implemented. DONE requires all acceptance
checks, attributable source/evidence, integration or explicit non-code completion,
and owned cleanup. BLOCKED records a missing dependency/evidence, not approval
inferred from elapsed time. Planning alone does not satisfy a behavior criterion.

## Frozen execution

See evidence/plan0148/finite-matrix.md: all32 original families, three bounded
serial packets A1/F1/C1 and exact runtime/time/resource stops. No new delegation
turns; metadata-only owned fork/process fixtures. Parent remains OPEN.
