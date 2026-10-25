# Visible and actionable goal-limit supervision

State: OPEN. Owner: primary / ecochran76. Implementation: in progress.
Execution evidence: goal-limit-ux-execution.md. Acceptance below is unchanged.
Parent: #343. Slices: #344 engagement; #345 visible stop; #346 extend/reset.
Authority: operator request2026-10-25; existing native-supervision ADR and Plan0167;
common session permissions; HF-21 common human-attention contract (#339).
This is new work beyond the observation-recovery fix319 and scoped refresh318.

## Required user journey

1. Starting resource-limited goal work visibly confirms that an actual independent
   watcher has engaged this exact goal/allocation. Configuration or permission alone
   does not establish this. Confirm accounting qualification and a fresh generation,
   preferably the watcher's first successful poll of this enrollment revision.
2. Near the threshold, model and operator receive a visible checkpoint warning
   stating the remaining allowance. Checkpoint work consumes the original reserve.
3. Exhaustion or loss of supervision promptly stops autonomous work and presents a
   prominent interrupting notice with reason, usage/limit, deadline and next actions.
   It persists in the conversation, is available to model context, and survives
   reconnection. A paused status or collapsed JSON tool result alone is insufficient.
4. The operator can extend allowance, reset the budget window or keep work stopped.
   Instructions and actual CLI/MCP/native actions must agree. An already explicit
   user authorization is acted on without asking the same approval question again.

Illustrative startup card (not a receipt for a real campaign):

> External goal watcher engaged. Token allowance: <used>/<limit>, <basis>.
> Stop at <absolute deadline and timezone>. Checkpoint reserve: <tokens>/<time>.
> Scope: <this session or named shared allocation>. Watcher: healthy.

Illustrative stop prompt (assert interruption only after native proof):

> Goal paused: external token allowance reached. Used100,000 of100,000 fresh
> input/output tokens. The watcher interrupted the captured work turn.
> Extend allowance / Reset budget window / Keep stopped.
> Native goal resume alone does not renew this external allowance.

Unknown stop outcome instead says "Stop requested; interruption unverified".
An exhausted allocation grants no extra checkpoint work or notification model turn.

## Verified source gaps

In qualified Wake revision311da84:

- goal_supervision.enroll/show expose heartbeat and controller fields but no
  guaranteed operator-visible engagement card or first-poll/presentation receipt.
- poll sends turn/steer at checkpoint reserve. _stop journals the episode, pauses
  the native goal and interrupts exact captured turns, without a visible stop-reason
  prompt. Steer acknowledgement does not prove model consumption or UI presentation.
- goal_limits_cli exposes set/show/recover/disable, not extend/reset. Enrollment
  rejects same-allocation increases; manual host renewal exists internally.
- Observation recovery319 preserves original resources. It is not extension/reset.
  Common enforcement.increase permission is not itself a usable renewal workflow.
- Current "host/controller" failures conflate several layers for the end user.
  The reported frequency across other sessions has not been independently measured.

## #344 | Engagement and setup

Discover the actual native caller, canonical configured watcher and existing
allocation through the common permissions model. Do not require routine per-session
UUID grants, copy another session's grant, invent a root or create competing watchers.

Distinguish watcher absent, stale/unreachable, policy/identity denied, accounting
unavailable, maintenance, and unsupported runtime/presentation capability. Give each
an actionable remedy. Start/repair the configured watcher automatically where
standing policy and the goal request authorize it; ask only for genuinely missing
scope or an actual action-specific authority boundary. "Ask the host controller"
is not an adequate end-user action.

Enrollment, verified enforcement and visible confirmation are distinct states.
Show the real limits, accounting basis, absolute deadline/timezone, used/remaining,
checkpoint reserve, scope and health. Controller restart/loss updates health without
renewing resources or repeating engagement cards for the same enrollment.

## #345 | Durable interruption and presentation

Use a stable event identity tied to exact session, allocation, generation, stop
episode, reason and captured work turn. Record intent before delivery; reconcile
unknown outcomes without blindly replaying prompts. Restart and reconnect must not
lose pending notices or duplicate decisions.

Track control proof, recorded notice, native/transcript append, UI presentation,
model-context availability and human response independently. A log entry, accepted
steer, queued message or successful tool startup proves only its own boundary.
Never claim the operator has read a notice merely because a client rendered it.

Notifications remain available while ordinary campaign work is held. They convey
external enforcement state, not a new user instruction or permission to resume.
Do not launch a fresh model turn at exhaustion to announce the stop. Do not interrupt
later operator replies, replace a client, restart a shared daemon or affect peers.
Failure to present a prompt must not delay pause/interrupt; surface that delivery
failure honestly and retain the notice for supported presentation/reconnection.

Qualify the actual installed runtime/frontend presentation adapter. Prefer existing
native capabilities; expose any missing primitive explicitly. A backend formatter
or attention-queue record alone does not satisfy visible model/operator delivery.
Reuse the common attention queue for decisions; do not create feature-specific
approval queues. #339's source acceptance is not proof of an installed presenter.

## #346 | Extend and reset

Extend raises the authorized ceiling/deadline and keeps usage.100k used of100k plus
50k allowance yields150k total,100k used,50k remaining. Specify an absolute deadline
or explicit remaining-time grant, especially after expiry; show the proposed
old/new result rather than silently interpreting an ambiguous time instruction.

Reset explicitly opens a new generation/window with a qualified anchor. The new
window can start at zero; lifetime/native usage, old charges and stop history remain
intact. Label the current window and lifetime totals so the operator sees what reset.
Do not overwrite native counters, delete history or use reset to hide unknown usage.

Bind proposal and approval to goal, allocation, revision/generation, scope/member
set and expiry. Reuse the common attention response/permission model. A confirmed
operator action or authenticated explicit user directive supplies authority; model
requests, permission inspection, old approvals, re-enrollment and native resume do
not. Delayed or duplicate responses cannot change a newer allocation or another
session. Shared allowances require explicit shared-scope authority and qualified
all-member accounting. Existing boot, clock, hard policy ceiling and accounting
checks remain effective.

Show "apply only" versus "apply and resume". Resume requires user authority plus
fresh watcher/accounting/native proof. Preserve prior stop/recovery episodes and
make the authorized new window/revision explicit. Publish usable instructions in
startup cards, stop prompts, CLI help, MCP descriptions and skills. Do not advertise
unsupported controls as available or direct ordinary users to edit host JSON files.

## Delivery and acceptance

Sequence344 event/readiness contract first,345 native/frontend presentation second,
and346 approved renewal third; shared files have one integration owner. Verify
integration of332/339/341 where their implementation is reused; do not duplicate
another active lane's comprehensive-test repairs. Existing P167 history stays closed.

Use public-interface fixtures for missing/stale readiness, denied authority, unknown
accounting, busy/idle source, lost delivery acknowledgement, restart/reconnect,
nonzero counters, expired time, stale approval and shared allocation. Run a bounded
owned native/frontend acceptance proving visible startup, visible interruption,
model-context availability and approved extend/reset while a peer stays unchanged.
Tests must fail on silent pause or unverified watcher, not merely assert JSON keys.

Definition of done: the full user journey is implemented, supported capability is
truthful, installed identity is recorded, presentation and control are separately
proved, instructions work, and all three tickets' acceptance evidence exists.
Ticket publication and this specification are not implementation or deployment.
Current production goals, watcher state and resource authority are unchanged.
