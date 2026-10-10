# Ticket0147 — Recover processing ownership across generations

State: CLOSED
Workflow: DONE
Owner: primary
Lane: P74
Branch: fix/claim-reconciliation
Target: origin/main
Integration: squash_pr
Work-Item: docs/dev/plans/0147-2026-10-10-processing-claim-generation-recovery.md
Parent: docs/dev/plans/0141-2026-10-10-a2a-completion-stream.md
Depends-On: Plan0146

## What it delivers

After a worker generation ends, the same recipient can determine whether work is already owned/completed or needs explicit reconciliation, without duplicate processing or fabricated completion.

## Blocked by

[0146](0146-2026-10-10-held-recovery-disposition.md)

## Acceptance criteria

- [x] Public mailbox/worker regression freezes accepted claim, generation change and terminal/unknown cases; stale actors cannot release, steal or complete a claim.
- [x] New generation observes prior acceptance and completion receipts; explicit recovery/reconciliation handles orphaned ownership without granting extra task rights.
- [x] An already-owned claim never grants permission to start again merely because read or notification is repeated; uncertain prior processing remains held.
- [x] Installed fresh-process control proves same-thread attribution, fencing and cleanup; no old live message is manually completed or replayed.

## Test seam and bound

Public accepted-work claim and reconciliation seams under disposable generation transitions. One smallest red loop per ownership gap; no provider effects.

## Frozen claim reconciliation contract

Actor capability generation fences the accepted-work claim; a tab/client reconnect
alone does not create a new claim. Repeated acceptance returns claimed=false and
does not grant another start. A rotated or revoked actor cannot steal or complete
the original claim. No takeover/reset or invented processing outcome is added.

Public messages reconcile reports processing separately from notification:
unclaimed, already claimed by current generation, held for the original claim,
or known terminal backed by its exact immutable receipt. It reports original
claim receipt/generation and current recipient generation. A terminal receipt
remains observable across rotation; absence of terminal evidence stays unknown.
Reconciliation grants no new processing rights, reads no body and never requeues.
Metadata reconciliation must work without acquiring a clock or changing expiry;
operator inspection remains explicitly audited. Existing notification reconciliation
and its old held uncertainty retain their meaning.

Use current public Mailbox and messages CLI seams, external runtime metadata for
actor CLI qualification, fixed role-fixture clocks for non-time setup, and fresh
installed processes. No new schema or storage reset. Version0.12.0 remains the
prepared campaign version. Bound the unit to accepted/unknown, terminal, same-
generation repeat and stale authority controls; focused90s, installed60s/child10s,
FD+2/children0, zero business-task/notification effects. At most one owned empty
native tab may qualify exact actor context; preserve its fixture history and
close it after idle/ownership readback, with any pending-work refusal retained.

## Owned write surface

Processing claim/recovery semantics and necessary guards/tests/evidence; no automatic business-task replay.

## Execution and terminal condition

One primary owner; obey Plan0141 authority, evidence and no-replay rules. Before
implementation, register the actual branch/checkpoint and update this header.
READY means refined and unblocked, not implemented. DONE requires all acceptance
checks, attributable source/evidence, integration or explicit non-code completion,
and owned cleanup. BLOCKED records a missing dependency/evidence, not approval
inferred from elapsed time. Planning alone does not satisfy a behavior criterion.

## Closeout

PR236 integrated85d9f73; installed candidate/source82-file parity, actual native
context and57 installed controls PASS. Source-checkpoint/review record exact proof.
Owned clean checkout closed without force; published8c5ea4c ref retained. No test
tab created or old wake replayed. Wider0148/0149 remain mandatory.
