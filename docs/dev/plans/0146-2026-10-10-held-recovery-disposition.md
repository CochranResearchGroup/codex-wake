# Ticket0146 — Make held recovery disposition explicit and safe

State: OPEN
Workflow: IN_PROGRESS
Owner: primary
Lane: P71
Branch: docs/a2a-completion-stream
Target: origin/main
Integration: governed_by_plan0141
Work-Item: docs/dev/plans/0146-2026-10-10-held-recovery-disposition.md
Parent: docs/dev/plans/0141-2026-10-10-a2a-completion-stream.md
Depends-On: none

## What it delivers

An operator on an isolated recovered bus can inspect missing-state uncertainty, explicitly dispose of gaps and, only when gates pass, begin fresh-authority work without reviving legacy notifications.

## Blocked by

None; priority ordering still applies.

## Acceptance criteria

- [ ] Derive the exact unresolved gap/hold obligations from verification0110 and original Plan0101; retain quarantine, snapshot hash, unavailable outcomes and immutable receipts.
- [ ] Freeze a disposition contract before code: unknown prior effects never become absent/completed by inference, and releasing the hold never queues a legacy attempt.
- [ ] Public CLI red-green and installed fresh-process controls prove old operator/actor/scheduler and legacy notifications fenced, fresh authority required, audited deliberate disposition and explicit release/refusal.
- [ ] Interruption/repeated disposition is attributable and idempotent or visibly held; ambiguous writes reconcile before retry.
- [ ] Only disposable recovery stores are mutated. Production recovery/hold release requires an exact separately authorized store and concrete reviewed operation; this plan does not grant it.

## Test seam and bound

Public recovery/reconciliation/operator commands with isolated damaged-source fixtures, then installed fresh processes. One bounded contract and smallest fault loop per demonstrated obligation; no transport on legacy intent.

## Owned write surface

Recovery hold/disposition public contract, necessary state/CLI/tests and installed evidence. Preserve original quarantines and uncertain Plan0139 bus.

## Execution and terminal condition

One primary owner; obey Plan0141 authority, evidence and no-replay rules. Before
implementation, register the actual branch/checkpoint and update this header.
READY means refined and unblocked, not implemented. DONE requires all acceptance
checks, attributable source/evidence, integration or explicit non-code completion,
and owned cleanup. BLOCKED records a missing dependency/evidence, not approval
inferred from elapsed time. Planning alone does not satisfy a behavior criterion.
