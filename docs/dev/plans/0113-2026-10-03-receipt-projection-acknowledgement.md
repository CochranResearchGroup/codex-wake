# Operator reconciliation of durable receipt projections

State: CLOSED
Lane: P63
Owner: primary
Parent: Plan 0101 / issue #181
Branch: feat/p63-receipt-projection-ack
Target: origin/main
Integration: squash_pr

## Current State

Starting baseline b0684e3 has bounded multiroot/resource qualification. Receipt observers
commit exact occurrences but never acknowledge mailbox signal outbox rows;
retention pins therefore cannot clear through production APIs. Existing pruning
tests explicitly simulate this acknowledgement. Live disposable scope is pending.

## Scope and authority

One serialized packet adds a bounded operator acknowledgement command using an
existing independent observer grant and read-only committed signal-journal proof.
Writer authority is the independently supplied mailbox operator capability, never
the observer grant alone. Verify exact bus/root, actor generation and conversation;
acknowledge only identical committed occurrences. A checkpoint, firing record,
claimed receipt ID or missing/compacted proof cannot clear a pin. Observers remain
SQLite mode=ro. No automatic pruning, live bus writes, enrollment or provider effects.
Write surface: signal-store read API, receipt normalization/reconciliation, CLI,
focused tests, README, verification, parent plan and runbook.

## Acceptance, bounds and non-goals

At most 100 rows per call. Red executable feedback before implementation; prove
retention remains pinned before mirror, clears only committed exact projections,
retry has no duplicate acknowledgement, malformed/revoked/wrong-root/missing-proof
cases hold. Atomic mailbox commit and attributable operator receipt; uncertain
commit reports a reconciliation pointer. Two implementation attempts and one
repair; inherited review limits unchanged. Full suite and installed CLI proof.
No physical compaction/tombstone cleanup or relaxation of live delivery gates.
Current goal working checkpoint 450k, stop before 500k; preserve earlier history.

## Definition of done

Production API replaces simulated projection acknowledgement with durable exact
proof and explicit writer authority; retention can then use its existing preview/
apply guard. Hosted integration separate. Full Plan 0101 remains OPEN.

## Closeout

Locally accepted operator acknowledgement replaces simulated mailbox projection
clearing with exact committed occurrence proof. Read-only observers remain
unchanged; actual retention uses its original preview/apply guard. Initial
implementation attempt passed the primary seam; one targeted malformed-proof
repair episode normalized JSON errors and validated source-contract types.
The repair's wrong-table query failed closed and was corrected from canonical
source_instances ownership. All failures are retained in verification 0105;
no new broad review pass or allowance reset. Final: 55 focused tests on both
Python versions, 843 comprehensive and nine installed tests. FD five to five,
children zero. Hosted integration is separate; full Plan 0101 remains OPEN.
