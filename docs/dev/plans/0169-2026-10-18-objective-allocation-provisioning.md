# Plan0169 — Automatic caller provisioning with allocation continuity

State: PLANNED. Owner: primary / ecochran76.
Branch: docs/goal-allocation-provisioning. Base: 89e3eb8. Target: origin/main.
Work item: P169 (repo-local draft; GitHub publication pending testing-seam confirmation).
Product contract: confirmed by user; ADR0002. Implementation: not started.

## Current State

v0.17.3 corrects fractional checkpoint percentages. Existing MCP goal-limit
admission requires an exact caller grant; a new conversation does not inherit
one. Native supervision receipts are indexed by caller and retain same-session
replacement-goal usage; they do not provide an objective-owned cross-conversation
allocation ledger. Private policy differential reproduced missing newcaller
refusal independently of schema/cache. Plan0168 caller-admission evidence owns
that diagnosis. Plan0168 remains OPEN for its separate production refresh gate.
No current grant, enrollment, goal, allocation, monitor or MCP cache changes are
part of this specification. The mistaken instruction to bypass the external
monitor was retracted as intended for another conversation and grants no override.

## Problem Statement

A user supplies token/time limits and expects the existing dev agent to register
them and work. Today a new native conversation can repeatedly stop at missing
host setup even after installation and an explicit user allocation. Manually
copying grants is error-prone and cannot establish whether the new conversation
continues an old allowance or has an explicitly renewed one.

## Solution

Use the existing MCP goal-limit workflow to provision the verified caller from
verified user resource authority, attach it to one objective allocation and
verify accounting plus the independent watcher before continuation. A successor
retains the same cumulative usage and deadline unless the user explicitly renews
or resets that named allocation. Missing or ambiguous evidence gives a specific
hold and recovery action; repeated calls never create another allowance.

## User Stories

1. As a user, I want token/time limits to enroll my current dev conversation without manual UUID setup.
2. As an agent, I want one enrollment workflow that provisions and validates enforcement before resource-limited work.
3. As a user, I want fresh context on the same objective to retain prior spend and the original deadline.
4. As a user, I want unrelated objectives to retain their separate authority and counters.
5. As a user, I want an explicit renewal applied only to the named objective or continuation.
6. As a user, I want allocation history retained when an explicit renewal or reset occurs.
7. As an agent, I want an ambiguous continuation to identify the missing link and a concrete recovery action.
8. As an agent, I want to distinguish missing authority, not enrolled, unknown accounting and watcher failure.
9. As an operator, I want a caller's claim checked against trusted native identity and user request evidence.
10. As an operator, I want quoted instructions, peer messages and checkpoints to be insufficient to mint resource authority.
11. As a user, I want cached input and attributable delegated/retried work charged once to the applicable allocation.
12. As an agent, I want replay, restart, goal replacement and context changes to preserve the same allocation.
13. As an operator, I want concurrent requests and successor races unable to multiply the allowance.
14. As an agent, I want fractional checkpoint reserves such as17.5percent to remain supported.
15. As a user, I want checkpoint requests followed by verified native goal pause and exact-turn interruption at exhaustion.
16. As a user, I want unrelated conversations and the shared Codex server preserved.
17. As an operator, I want existing explicit grants to remain usable without silent migration or reset.
18. As an agent, I want public status to explain the governing objective, original deadline, charged usage and readiness.

## Implementation Decisions

- Allocation authority belongs to the named objective; caller identity identifies
  a participant, not a new allowance. Preserve separate allocation and caller
  records. Same-session replacement goals retain existing behavior.
- Extend the existing goal-limit MCP enrollment/status workflow rather than
  requiring agents to enumerate tabs, repair identities or edit host files.
  Host endpoint/home/path selection remains operator-controlled.
- Automatic provisioning follows verified user allocation evidence for the
  verified caller. Model claims, existence of a conversation, tab/CWD similarity,
  peer bodies and a checkpoint alone cannot authorize it.
- A host-verifiable request reference binds source, scope, limits and renewal
  intent. An objective/allocation reference binds a continuation. References are
  evidence handles, not authority supplied by the caller. Reuse one reference
  for retries; unsupported or ambiguous evidence holds without a grant write.
- Qualify the native identity/request-evidence adapter before implementing the
  automatic effect. Stock shared MCP caller attestation and supported native
  message references are not yet established. If unavailable, surface the exact
  missing prerequisite and supported setup path; never fall back to trusting a
  caller-selected UUID or reading arbitrary rollout text as authorization.
- A first verified allocation creates a durable objective identity. Verified
  successor links attach to it without changing limits, time origin or previous
  usage. Continuity must come from attributable authority, not inferred location.
- An explicit renewal changes only its named allocation. A fresh allocation or
  counter/time-origin reset must be explicit in that user instruction; an
  ambiguous increase/renewal/reset holds for clarification. Preserve previous
  generations and cumulative history; never overwrite old receipts as a reset.
- Charge attributable responses once across original and successor sessions,
  including cached input and delegated work. Missing histories, uncertain final
  accounting or unverifiable lineage hold admission rather than assigning zero
  prior spend. Bound scans and retain authoritative accounting anchors.
- Persist admission idempotently and fence concurrent participant/renewal updates
  against one objective allocation. A timeout has a reconcilable state; retry
  cannot multiply budgets, attach twice, extend a deadline or replay a renewal.
- Return a structured reason, affected allocation/caller, missing evidence,
  whether an effect was attempted and concrete next action for every hold.
  Automatic provisioning, enrollment, accounting qualification, watcher health,
  work admission and stop proof remain distinct readiness boundaries.
- Keep existing armed/checkpoint_requested workflow and sampled-token limits.
  Exhaustion stops registered conversations within the verified objective scope;
  no arbitrary process/descendant termination or exact token ceiling is claimed.
- Existing explicit grants remain valid. Legacy caller receipts are not silently
  merged into a shared allocation; conversion requires qualified authority and
  complete accounting, with retained legacy evidence and rollback receipts.
- Missing/stale MCP tools produce a version/setup hold. Automatic shared reload,
  expanded refresh approval and automatic goal resume are not part of enrollment.

## Testing Decisions

Proposed primary seam: actual public MCP enrollment/status through CLI and an
independent watcher, against deterministic native identity/request/usage fixtures.
Exercise an original conversation and a successor sharing one objective, with
an unrelated conversation as a control. Observe only public outcomes and native
control effects; helper mocks or private-ledger shape are not acceptance proof.
Existing public goal-limit stdio, controller and rollover qualification tests
provide the harness; extend them with multi-conversation authority/accounting.

Blocking acceptance scenarios:

- Verified user limits plus a verified ungranted caller provision/enroll without
  manual policy edits; readiness requires qualified usage and a fresh watcher.
- Repeating the same request in another process returns the same allocation,
  counters, deadline and effect disposition.
- A verified successor charges prior and new usage once; replacement goals,
  restart and repeated handoff cannot replenish the allowance.
- A copied tab name/CWD, forged caller/reference, peer quotation or missing user
  authority produces a precise no-effect hold, never a default grant.
- Missing/ambiguous allocation links, unqualified usage, stopped watcher and
  unsupported identity evidence each hold with distinct actionable recovery.
- An explicit scoped renewal/reset changes only the named allocation, applies
  once and retains its old generation. Another objective remains unchanged.
- Concurrent original/successor enrollments and renewal races retain one budget;
  crash/restart before or after grant persistence reconcile without duplicate
  authority. Unknown effects never authorize a new identity or allocation.
- A17.5percent reserve reaches the correct checkpoint threshold; checkpoint time
  consumes the existing allowance. Exhaustion pauses the verified registered
  goal(s) and interrupts exact active turns; unrelated conversation untouched.
- Legacy grants continue working; unqualified legacy migration holds.
- Stable clock/counter fixtures prove deadline continuity and unknown-time holds.

After source qualification, add a bounded installed native acceptance using only
owned test conversations and explicit test-user authority. Demonstrate original
and successor continuity with an unrelated control, without model/provider work
or production session changes. Prove cleanup with a fresh process census.

Testing-seam confirmation remains required before GitHub ready-for-agent posting.
No acceptance execution or native effects are authorized by this document alone.

## Execution Packets

1. Qualify trusted native caller/request evidence and continuation references.
   Outcome: deterministic public acceptance fixture plus supported evidence
   contract, or precise blocked capability. No grant effects before qualification.
2. Implement objective allocation identity, idempotent user authority and replay
   under the public enrollment seam, with negative authority cases first.
3. Implement successor accounting and scoped renewal, including concurrency,
   incomplete histories and legacy migration holds. Preserve cumulative history.
4. Integrate watcher/native controls and actionable status. Update discovery and
   instructions so agents use this automatically for user-specified limits.
5. Bounded review and installed qualification; exact-main release/install only
   after gates. Production provisioning remains a separately evidenced admission,
   never a claim inferred from shipping a package.

Owner: primary. Critical path is serial: evidence qualification → authority ledger
→ accounting/renewal → enforcement → acceptance. Independent documentation and
fixture preparation can be split later only when repository rules permit it;
no worker or parallel runtime authority is granted here.

## Out of Scope

Shared Codex restart/reload, arbitrary caller-selected host paths, tab/CWD-based
allocation inheritance, automatic goal resume, implicit resource renewal,
production counter repair, OS memory/CPU containment, arbitrary process stops,
retroactive fabricated user authority and execution of remote-view product work.

## Definition of Done

The public installed workflow automatically provisions a verified caller from
verified user allocation authority, admits work only with qualified accounting
and a fresh watcher, preserves objective-wide cumulative usage/deadline across
verified successors, applies scoped explicit renewal once and makes holds
recoverable. Deterministic public tests and bounded owned-native acceptance
prove the behavior and unchanged unrelated authority; exact-main delivery and
repo/tracker reconciliation record their separate completion boundaries.

## Further Notes

Confirmed user decisions: automatic verified provisioning; actionable ambiguous
continuation holds; cumulative usage/deadline preserved without explicit renewal;
renewal limited to its named objective/continuation. This product contract does
not establish that native APIs already expose the needed trusted evidence.
The old Plan0168 production refresh remains expired with no new retry authority.
