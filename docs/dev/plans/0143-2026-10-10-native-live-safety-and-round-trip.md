# Ticket0143 — Qualify normal request and reply after transport change

State: CLOSED
Workflow: DONE
Owner: primary
Lane: P71
Branch: docs/a2a-completion-stream
Target: origin/main
Integration: governed_by_plan0141
Work-Item: docs/dev/plans/0143-2026-10-10-native-live-safety-and-round-trip.md
Parent: docs/dev/plans/0141-2026-10-10-a2a-completion-stream.md
Depends-On: Plan0142

## Current State

Installed two-agent request/reply PASS on immutable0.11.2-313e5aa. Both actual
notification turns completed with exact message/attempt markers and terminal work
claims. Original arm submitted; paused public reconciliation finished bookkeeping
from the committed reply receipt with zero additional sends. Both tabs closed
forced=false, all four owned PIDs and both panes absent. No source changes.
Evidence: docs/dev/evidence/plan0143/installed-acceptance.md.

## What it delivers

Two owned agents exchange a request and correlated result without a controller relay; current idle/draft and lifecycle safety still govern native submission.

## Blocked by

[0142](0142-2026-10-10-native-live-submission.md)

## Acceptance criteria

- [x] Released-candidate commands, source PYTHONPATH unset: one request and one correlated reply use exact original threads, claims and terminal acknowledgments; both native turns complete.
- [x] Original sender receipt arm causes automatic return after its initiating turn ends; no controller reply, post-send prompt or foreground inbox poll.
- [x] Focused installed guards cover busy/draft/approval/identity/cancel/expiry/uncertain behavior; pending work remains held, terminal work permits ordinary close.
- [x] Use accepted restart/reconnect evidence when source/config/freshness still qualify it; otherwise run only the invalidated owned-worker control.
- [x] Freeze source/version, IDs and bounds before the sample; preserve failed receipts and close owned tabs/processes after fresh OS readback.

## Test seam and bound

Public messages/worker/sessions commands and native completed-turn readback. One request/reply pair; no automatic effect retries. Source changes discovered here return to ticket0142 red-green; no repeated broad soak merely to get a green report.

## Owned write surface

Installed acceptance evidence and only demonstrated regressions; preserve unrelated workers, LitScout and private histories.

## Execution and terminal condition

One primary owner; obey Plan0141 authority, evidence and no-replay rules. Before
implementation, register the actual branch/checkpoint and update this header.
READY means refined and unblocked, not implemented. DONE requires all acceptance
checks, attributable source/evidence, integration or explicit non-code completion,
and owned cleanup. BLOCKED records a missing dependency/evidence, not approval
inferred from elapsed time. Planning alone does not satisfy a behavior criterion.
