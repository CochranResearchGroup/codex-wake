# Ticket0146 — Make held recovery disposition explicit and safe

State: CLOSED
Workflow: DONE
Owner: primary
Lane: P73
Branch: fix/recovery-disposition
Target: origin/main
Integration: squash_pr
Work-Item: docs/dev/plans/0146-2026-10-10-held-recovery-disposition.md
Parent: docs/dev/plans/0141-2026-10-10-a2a-completion-stream.md
Depends-On: none

## Current State

PR235 integrated8548265879534762c2cf205d88688b263c6604f6. Reviewed228source,
86installed and9changed fixture controls PASS; actual fresh-process disposition,
release, old-reader refusal and cleanup PASS. All82package files match reviewed
candidate and merged source. Owned clean published checkout closed normally;
branch1f79e4d retained. Candidate0.12.0 is prepared; global0.11.2 stays active until
final release. See docs/dev/evidence/plan0146/source-checkpoint.md and review.md.

## What it delivers

An operator on an isolated recovered bus can inspect missing-state uncertainty, explicitly dispose of gaps and, only when gates pass, begin fresh-authority work without reviving legacy notifications.

## Blocked by

None; priority ordering still applies.

## Acceptance criteria

- [x] Derive the exact unresolved gap/hold obligations from verification0110 and original Plan0101; retain quarantine, snapshot hash, unavailable outcomes and immutable receipts.
- [x] Freeze a disposition contract before code: unknown prior effects never become absent/completed by inference, and releasing the hold never queues a legacy attempt.
- [x] Public CLI red-green and installed fresh-process controls prove old operator/actor/scheduler and legacy notifications fenced, fresh authority required, audited deliberate disposition and explicit release/refusal.
- [x] Interruption/repeated disposition is attributable and idempotent or visibly held; ambiguous writes reconcile before retry.
- [x] Only disposable recovery stores are mutated. Production recovery/hold release requires an exact separately authorized store and concrete reviewed operation; this plan does not grant it.

## Test seam and bound

Public recovery/reconciliation/operator commands with isolated damaged-source fixtures, then installed fresh processes. One bounded contract and smallest fault loop per demonstrated obligation; no transport on legacy intent.

## Frozen disposition contract

Missing post-snapshot outcomes stay unknown permanently in this recovery epoch.
The only disposition is retain-unknown: preserve quarantine, original receipts,
claims, message states and bodies; prohibit processing/reply/notification of every
snapshot-era message. No inferred completion, cancellation or replay.

Public operator recovery-status reports epoch, pinned snapshot SHA, hold,
disposition and legacy boundary/counts without bodies. dispose-recovery requires
fresh operator, exact epoch/SHA, bounded nonsecret reason and idempotency key plus
explicit accept-missing-state-unknown. One SQLite transaction records disposition,
fences legacy outbox, retains outcome uncertainty and upgrades recovered bus to
schema3 so older executables refuse it. Repeated same key returns its original
receipt; conflicting intent refuses. Interrupted writes reconcile by the same
key/status, with no filesystem transition or transport.

release-recovery separately requires the committed disposition, exact epoch/SHA,
fresh operator and still-paused bus. Release only clears the recovery hold; it
does not resume, re-enroll roots, rotate actors or deliver work. Fresh grants and
explicit actor rotation/enrollment are required before a new manual intent.
Legacy message IDs stay inspectable as operator history and are never processing
inputs under fresh credentials. Schema1/2 ordinary buses remain unchanged; old
binary rollback refuses schema3, and no in-place downgrade is offered.

Version0.12.0 declares this compatibility boundary. Qualification uses disposable
stores only, zero actual transports, existing pinned legacy0.11.2 installation
and fresh installed candidate processes. Initial public CLI tracer proves the
held recovered bus can deliberately retain unknown history and release into
paused fresh-authority-only operation; subsequent vertical slices cover fence,
refusal and commit-interruption risks. Two attempts per unit, focused gate120s;
installed workload60s, child10s, FD+2/children0/transport0.

## Owned write surface

Recovery hold/disposition public contract, necessary state/CLI/tests and installed evidence. Preserve original quarantines and uncertain Plan0139 bus.

## Execution and terminal condition

One primary owner; obey Plan0141 authority, evidence and no-replay rules. Before
implementation, register the actual branch/checkpoint and update this header.
READY means refined and unblocked, not implemented. DONE requires all acceptance
checks, attributable source/evidence, integration or explicit non-code completion,
and owned cleanup. BLOCKED records a missing dependency/evidence, not approval
inferred from elapsed time. Planning alone does not satisfy a behavior criterion.
