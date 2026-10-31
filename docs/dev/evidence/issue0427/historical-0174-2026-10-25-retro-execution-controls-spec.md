# Transparent governor and bounded execution specification

> Historical planning snapshot preserved for issue427. The OPEN wording below
> describes the original October25 planning checkpoint. Current source authority
> is issue350, Plan0175 and merged PR358; this snapshot authorizes no new work.


Work item: RETRO-CONTROLS-SPEC
State: OPEN
Classification: feature and governance gap
Tracker: GitHub / CochranResearchGroup/codex-wake
Publication state: published and read back
Canonical specification: https://github.com/CochranResearchGroup/codex-wake/issues/350

## Problem Statement

The operator needs protection from runaway agents without repeated permission requests or unexplained loss of progress. Current sampled monitoring can detect spend only after requests occur. A previous bounded campaign exceeded its token allowance, left acceptance and review unfinished, and encountered a circular supervision requirement while repairing supervision itself. These historical observations identify gaps; they do not establish the current installed host's capabilities.

A governor that attaches silently, stops work silently, or requires shell/service surgery to disable undermines operator control. Both the operator and the model need an accurate account of which controls are active, what they govern, and why they intervene.

## Solution

Provide transparent, scoped, operator-controlled governance. Apply the existing objective's authorized resource limits automatically across the primary, delegates, successors, retries, and review. Announce activation, mode changes, interventions, and deactivation to both audiences. Keep normal work free of repeated approvals. Provide an easy direct deactivation control that remains usable when the governor is unhealthy.

Protect the path to a completed result with bounded dispatch, early compatibility checks, reliable validation receipts, and explicit resource provision for acceptance, review, and remediation. These improve completion without creating additional operator gates.

## User Stories

1. As an operator, I want active governance announced, so that no control is silently inserted into my work.
2. As a model, I want the effective scope, limits, mode, and remaining allowance, so that I can plan within actual constraints.
3. As an operator, I want one clear activation summary, so that transparency does not become repetitive permission friction.
4. As an operator, I want to see whether enforcement is hard admission, sampled stopping, manual monitoring, inactive, or degraded, so that I understand the actual guarantee.
5. As an operator, I want every intervention explained visibly, so that a stopped agent never looks like unexplained abandonment.
6. As a model, I want the intervention reason and available next actions, so that I do not repeatedly retry blocked work.
7. As an operator, I want intervention notices even when the model cannot take another turn, so that reporting does not depend on the stopped agent.
8. As an operator, I want a discoverable Deactivate governor control, so that I can regain control without shell commands or repeated confirmation.
9. As an operator, I want deactivation failures reported explicitly, so that a successful-looking button cannot conceal active enforcement.
10. As an operator, I want my deactivation choice retained across retries, continuation, delegates, and restart, so that the governor does not silently return.
11. As a model, I want deactivation communicated, so that I do not enforce stale governor state through my own instructions.
12. As an operator, I want scope shown before changing governance, so that unrelated objectives remain unaffected.
13. As an operator, I want deactivation to preserve accounting history, so that disabling enforcement does not falsify prior spending.
14. As an operator, I want stopped work and checkpoints retained, so that intervention does not destroy completed work.
15. As an operator, I want disabling governance separate from resuming work, so that a control change does not unexpectedly dispatch new work.
16. As an operator, I want existing authorization remembered, so that manual repair does not require the same answer repeatedly.
17. As a repairing agent, I want an unavailable governor to permit explicitly authorized repair, so that restoring it is not circularly blocked.
18. As an operator, I want aggregate limits across all actors and attempts, so that delegation cannot multiply my allowance.
19. As a model, I want automatic request admission where the host supports it, so that concurrent actors cannot independently spend the same remaining allowance.
20. As an operator, I want unsupported guarantees stated honestly, so that sampled monitoring is never presented as a hard cap.
21. As a model, I want compact assignments with necessary evidence, authority, and stopping conditions, so that context copying does not consume the work budget unnecessarily.
22. As an operator, I want compatibility checked before costly fan-out, so that missing native support is discovered early.
23. As an operator, I want validation tied to the exact source and runtime tested, so that a passing result is reviewable and reproducible.
24. As an operator, I want a failed required check to prevent a success declaration or automated commit step, so that failure cannot be hidden by shell sequencing.
25. As a model, I want acceptance, review, and bounded remediation included in resource planning, so that implementation does not consume all resources before closure.
26. As an operator, I want unfinished outcomes stated plainly at a limit, so that a checkpoint is not misrepresented as completion.

## Implementation Decisions

- The governor's purpose is runaway containment, not additional operator ceremony. Routine enforcement and implementation choices do not require repeated approval.
- Model and operator visibility are separate delivery obligations. A durable event, model-context delivery, and operator rendering are separate facts. An intervention notice must not require a new inference merely to become operator-visible.
- Activation summaries identify governor identity, objective scope, authorized limits, accounting basis, effective enforcement mode, and controls. Reattaching a client restores visible current state without inventing a new activation or silently changing policy.
- Intervention events identify affected objective/actors, trigger, observed usage and uncertainty, action taken, timestamp, and concrete recovery/deactivation options. Persist notices for reconnect; deduplicate replay without suppressing materially new interventions. Report delivery failures through an independent operator status surface.
- Deactivation is a normal authenticated operator action, not an action requiring approval by the governor or model. It has a visible scope and durable resulting state. Acknowledge success only after effective control state changes; otherwise show a concrete failure. Reject stale enforcement actions after a deactivation takes effect; report already-issued actions truthfully rather than claiming they were recalled.
- Explicit deactivation persists within its selected objective scope across continuation, delegation, retry, and process restart. Reactivation requires an explicit operator action or an explicit operator scope change, with a new activation notice. Service restarts and inherited defaults must not override that choice.
- Deactivation disables this governor's interventions in scope. It neither cancels unrelated platform protections nor changes service masks, replenishes allocation, erases history, or resumes stopped work. Show any remaining independent controls accurately.
- Reuse the existing objective budget and reservation model. Request-level admission, where supported, must arbitrate aggregate reservations atomically before dispatch and settle attributable usage idempotently. Include retries, fallbacks, descendants, failed attempts, and review in accounting. Unknown completion must not automatically refund potentially consumed resources.
- Preserve the authorized accounting basis; do not silently change token definitions or promise exact hard caps from sampled data. A hard-cap guarantee requires demonstrated request-path coverage and conservative enforceable bounds. Native hook details remain an engineering qualification task, not an approved installed capability.
- An explicit hard-cap execution request must not be silently downgraded. A limitation must be explained once with supported options. Explicitly authorized manual development/repair remains available without watcher availability becoming its own prerequisite. Existing operator choices persist; no implicit renewal of an exhausted campaign.
- Before costly dispatch, run a bounded compatibility preflight against the selected native host, identity/metadata, accounting, and required notice/control surfaces. Reuse qualified receipts until a relevant source, binary, configuration, or identity change invalidates them. Do not rerun broad matrices without a reason.
- Default delegated work to compact explicit packets containing objective, authority, evidence locators, scope, acceptance, allowance, and stop conditions. Full history is an exception justified by the task. Preserve evidence coverage, ambiguity, and freshness when summarizing output.
- Plan acceptance, review, and bounded remediation before dispatching implementation. Track remaining obligations against actual resources. If the remaining path is infeasible, narrow work or checkpoint and explain; do not claim closure or silently extend allowance. Reserve sizing is an engineering choice to validate, not a new per-packet operator approval.
- Validation must fail fast on required checks, bind receipts to the exact source/runtime/environment, and prevent mixed mutable worktrees from masquerading as one qualified result. Independent acceptance failures remain individually visible.

## Testing Decisions

Prefer the existing public goal-supervision/operator-control journey as the highest integration seam, with a deterministic mock model transport and controllable clock/usage. Verify externally visible dispatch, notices, control responses, and durable state across process boundaries. Use focused existing ledger tests only where concurrent admission and settlement cannot be demonstrated adequately through that journey. Avoid exposing internal APIs solely for tests.

Prior art includes the repository's objective-ledger, lifecycle admission, strict-executor, and deadline-continuity acceptance tests. The separate goal-limit implementation lane has native no-turn notices and model/operator journey evidence worth reusing after source and runtime qualification; those results are not assumed to cover this specification.

Required observable cases:

- Activation is delivered to both audiences and identifies scope, limits, mode, and controls. Attachment cannot silently introduce governance.
- A forced resource intervention stops or denies only the affected work and explains the actual reason. The operator sees it without another model request; the model receives it before subsequent governed continuation.
- A stopped/disconnected model does not prevent operator notice; operator reconnection restores the intervention and current state. Journal-only publication does not satisfy rendering acceptance.
- Deactivation from the normal operator interface works while the watcher is unavailable; failures remain explicit. After successful deactivation, stale queued decisions cannot issue new interventions in scope.
- Retry, delegate creation, continuation, and restart retain deactivation. Explicit reactivation announces itself. Peer objectives remain unchanged.
- Deactivation preserves usage and checkpoints, does not dispatch work, and does not manufacture renewed allowance.
- Concurrent actors cannot acquire the same remaining reservation on a qualified admission host. Duplicate completion, fallback, retry, and missing completion preserve conservative aggregate accounting.
- Sampled/manual modes display their limitations. Unsupported hard-cap execution produces one actionable limitation, while previously authorized repair proceeds without a repeated-consent loop.
- Compatibility failure is discovered before expensive fan-out. Source/runtime changes invalidate the relevant receipts.
- A failing required validation command prevents subsequent success/commit steps. Receipts name the actual tested source and environment.
- Completion scheduling includes acceptance/review/remediation and produces a truthful checkpoint when resources cannot cover the remaining path.

Seam status: proposed for operator review alongside this published specification. Existing public journeys are preferred; no new seam is assumed approved. This check does not block producing or publishing the specification.

## Out of Scope

Implementation, deployment, service unmasking, native binary replacement, provider experiments, remote ticket decomposition, renewal of the exhausted PR348 campaign, automatic issue closure, and a general-purpose operating-system kill switch. Deactivation does not revoke unrelated safety or platform controls. No guaranteed token overshoot bound is claimed without host qualification.

## Further Notes

This specification synthesizes the October 25 retrospective and subsequent explicit operator corrections: prevent runaway agents without operator friction; no silent insertion or stoppages; transparency for operator and model; easy deactivation. The retrospective identified excess spend, late compatibility discovery, unfunded completion work, unreliable local validation sequencing, and excessive context transfer. Detailed prototype source observations and retrospective locators remain in the companion design record; historical evidence is not installed-runtime proof.

No implementation or validation success is claimed. Publish this specification as ready-for-agent without triage; subsequent ticket decomposition is a separate workflow. The initial acceptance seam proposal is presented with the publication for review rather than requiring another interview.

<!-- codex-wake-spec:retro-controls-20261025-v1 -->
