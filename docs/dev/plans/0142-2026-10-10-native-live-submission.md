# Ticket0142 — Native submission for existing live tabs

State: OPEN
Workflow: AWAITING_INTEGRATION
Owner: primary
Lane: P72
Branch: fix/native-live-submission
Target: origin/main
Integration: squash_pr
Work-Item: docs/dev/plans/0142-2026-10-10-native-live-submission.md
Parent: docs/dev/plans/0141-2026-10-10-a2a-completion-stream.md
Depends-On: none

## Current State

Source313e5aa qualified: public red-green loops, serial Standards/Spec review,
reviewed installed117PASS43.592s and81file parity. Actual owned result has one
native queue receipt and recipient claimed/completed turn; tab closed without
force and owned PIDs absent. See evidence/plan0142/installed-acceptance.md.
All behavior criteria pass; exact source integration remains before DONE.

## What it delivers

An explicitly authorized live-tab notification is submitted to its exact thread through the native queue and carries the exact returned queue receipt, independently of screen redraw or wrapping.

## Blocked by

None; priority ordering still applies.

## Acceptance criteria

- [x] Public dispatcher regression reproduces viewport loss/wrapping and then succeeds with a validated exact-thread native queue receipt; paste success alone never proves submission.
- [x] Busy, human draft, approval, unknown UI, changed identity/process generation, expiry and unavailable authority prevent queue I/O; existing pane-lock and immediate pre-submit checks remain.
- [x] Malformed response, wrong returned thread, timeout or interrupted entered submission remain uncertain; no second queue, paste fallback or automatic retry.
- [x] The notification includes exact message/attempt pointers and existing claim instructions; saved-recipient reopening and reply-arm permissions remain separate.
- [x] One installed owned live notification has exact admission/attempt/queue IDs, actual recipient claimed/completed turn and no-force tab cleanup. Original Plan0139 uncertainty is unchanged.

## Test seam and bound

Existing notification dispatcher/binding boundary; native queue external-runtime fixtures and installed owned recipient. One minimized red-green behavior loop, affected tests, one original live notification; preserve any failed/ambiguous effect and stop replay.

## Owned write surface

Live notification transport, shared pointer procedure only if needed, associated tests/evidence; no new schema or general reconciliation API.

## Execution and terminal condition

One primary owner; obey Plan0141 authority, evidence and no-replay rules. Before
implementation, register the actual branch/checkpoint and update this header.
READY means refined and unblocked, not implemented. DONE requires all acceptance
checks, attributable source/evidence, integration or explicit non-code completion,
and owned cleanup. BLOCKED records a missing dependency/evidence, not approval
inferred from elapsed time. Planning alone does not satisfy a behavior criterion.
