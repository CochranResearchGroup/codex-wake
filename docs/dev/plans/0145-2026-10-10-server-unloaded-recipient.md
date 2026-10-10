# Ticket0145 — Qualify explicitly reopened server-unloaded recipient

State: OPEN
Workflow: IN_PROGRESS
Owner: primary
Lane: P71
Branch: docs/a2a-completion-stream
Target: origin/main
Integration: governed_by_plan0141
Work-Item: docs/dev/plans/0145-2026-10-10-server-unloaded-recipient.md
Parent: docs/dev/plans/0141-2026-10-10-a2a-completion-stream.md
Depends-On: Plan0144

## What it delivers

An explicitly opted-in message reaches the same saved conversation when it is genuinely not loaded by the server; default delivery stays held.

## Blocked by

[0144](0144-2026-10-10-release-native-live-submission.md)

## Acceptance criteria

- [ ] First reconcile Plan0138 exact evidence: if notLoaded-to-resume-to-completed is already proved with qualifying source, record that proof and avoid another live sample.
- [ ] Otherwise freeze one owned saved thread with native notLoaded evidence and prior history; default control causes zero resume/queue effects.
- [ ] Explicit --resume-missing admits one intent; original thread resumes, receives, claims and completes, with history preserved and exact native receipt/turn IDs.
- [ ] Replies require their own reopening choice and delegated arm; permission/identity change, unknown composer and ambiguous submission stay held without replay.
- [ ] No server-wide unload/restart or unrelated client closure. If public owned-thread unloading cannot be established, record exact blocker and required capability; do not substitute a closed-but-loaded tab.

## Test seam and bound

Public native thread status and messages/worker workflow; one default zero-effect control and one explicit notification only if existing evidence is insufficient.

## Owned write surface

Owned installed qualification and demonstrated repair if necessary; no shared-daemon patch or forced server restart.

## Execution and terminal condition

One primary owner; obey Plan0141 authority, evidence and no-replay rules. Before
implementation, register the actual branch/checkpoint and update this header.
READY means refined and unblocked, not implemented. DONE requires all acceptance
checks, attributable source/evidence, integration or explicit non-code completion,
and owned cleanup. BLOCKED records a missing dependency/evidence, not approval
inferred from elapsed time. Planning alone does not satisfy a behavior criterion.
