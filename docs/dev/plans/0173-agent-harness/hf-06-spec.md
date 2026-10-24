# HF-06 specification: Common session permissions

State: APPROVED_SPEC; test seams and six-slice breakdown approved
Owner: ecochran76
Work item: CW-HARNESS-173/HF-06
Authority: nine affirmative interview answers followed by explicit final confirmation
and direction to reconcile issue318 on 2026-10-24.

## Problem Statement

Sessions encounter independent caller allowlists and operation-specific grants,
so legitimate self-control requires repeated setup and agents cannot consistently
explain what they may do. A refresh-only fix cannot provide common policy for
handoff, enforcement, A2A or wake delivery. Permission also risks being confused
with a runtime's actual ability to perform an operation at the requested scope.

## Solution

Expose one common permission model with global defaults, named profiles and
session/assignment action overrides. Show the effective rule and its provenance,
separately from capability and readiness. The operator's permissive profile
supports authorized automatic self-control and managed-session messaging without
per-UUID grants. Explicit operator prohibitions, declared task scope, allowance,
identity and uncertain-effect handling remain authoritative.

## User Stories

1. As an operator, I want global action defaults so that new verified sessions work without per-UUID grants.
2. As an operator, I want named profiles so that I can choose permissive or restricted behavior consistently.
3. As an operator, I want session and assignment overrides so that an exception does not change every session.
4. As an operator, I want mandatory prohibitions so that a more specific allow cannot defeat my restrictions.
5. As a session, I want effective permission explanations so that I can distinguish a denial from unavailable capability.
6. As an operator, I want permission increases under my control so that an agent cannot promote itself.
7. As an operator, I want scoped controller delegation so that routine policy management can be automated.
8. As a session, I want to restrict myself or select an already authorized profile so that I can adapt within my authority.
9. As an operator, I want new actions to require approval by default so that upgrades do not silently expand authority.
10. As an operator, I want an explicit future-action inheritance option so that I can select a more permissive upgrade policy.
11. As a session, I want automatic refresh and handoff under configured triggers so that routine maintenance needs no repeated prompt.
12. As an operator, I want self-refresh and shared-server reload distinguished so that self permission cannot affect unrelated sessions.
13. As a session, I want to enroll in external enforcement so that agreed limits can be maintained independently.
14. As an operator, I want allowance increases and enforcement disabling to require approval so that self-control cannot renew resources.
15. As a managed sender, I want allowed A2A requests to reach an allowed recipient so that authorized collaboration works.
16. As a recipient, I want my receive rule enforced so that sender permission alone cannot bypass it.
17. As an operator, I want message delivery separate from task authority so that receiving work cannot grant extra tools or scope.
18. As a wake owner, I want explicit background, existing-tab and new-tab permissions so that delivery respects the chosen scope.
19. As a wake owner, I want ordered permitted routes so that supported fallback works without duplicate submissions.
20. As an operator, I want operation, task and standing approvals so that approval lifetime matches my intent.
21. As a successor, I want applicable same-task approvals to continue so that handoff does not require redundant setup.
22. As an operator, I want original-session-only approvals to remain local so that succession cannot broaden authority.
23. As an operator, I want revocation to fence subsequent effects so that queued work respects current restrictions.
24. As an operator, I want already submitted effects reconciled so that revocation does not erase uncertainty or cause duplicate work.
25. As an operator, I want old grants and pending intents preserved during migration so that adoption does not reinterpret existing work.
26. As a caller, I want unsupported scoped refresh reported before admission so that I am not repeatedly asked to approve a broader reload.

## Implementation Decisions

- One common evaluator resolves global baseline, named profile and explicit
  session/assignment rules, constrained by mandatory prohibitions and delegated
  task authority. Within each layer an exact action replaces that layer's
  fallback; omitted actions inherit. Two conflicting explicit settings at the
  same priority are invalid, not a last-write permission increase.
- Rule outcomes are allow, deny and approval-required. Inherit is configuration
  syntax. Resolve matching operator approval without asking again. Malformed
  policy, unknown action identifiers and missing verified identity fail closed.
  An action newly registered by an upgrade requires approval unless the operator
  explicitly enabled inheritance for future registered actions; a typo remains
  invalid rather than becoming a future action.
- Policy changes carry version/revision and verified issuer provenance. Operator
  or scoped delegated-controller changes can increase permissions. Agents can
  narrow permissions or select only previously authorized profiles. Concurrent
  updates cannot silently overwrite a newer prohibition; refuse stale updates.
- Permission evaluation accepts verified actor, target relationship, exact
  action/effect scope, task/allocation, runtime/account and policy revision.
  Reuse existing runtime identities and host delegation. Caller-supplied UUID,
  tab label, inherited pane or inventory membership alone is not authority.
- CLI, MCP and independent controllers consume the same evaluator. Existing
  host profiles and durable operation journals remain authoritative for their
  responsibilities; do not introduce another scheduler, inventory or ledger.
- Inspection exposes the permission outcome, deciding rule, approval scope and
  revision separately from capability, ownership and readiness. A permissive
  policy can produce permission=allow with capability=unsupported; this must
  never be reported as ready or queued for an unavailable operation.
- Apply the confirmed permissive action matrix, including automatic self-refresh,
  self-handoff, self-resume, enforcement enrollment and two-sided managed A2A.
  Allowance increase/enforcement disable require approval; shared reload requires
  standing scope approval. Supported wake routes require admitted task/recipient
  authority and their own rules. Runtime qualification is never inferred.
- Configured triggers may invoke allowed actions without another prompt. Pin
  action and scope to the existing task/allowance; permission does not invent
  a trigger or permit arbitrary new work.
- Approvals can cover an operation, task or standing rule. Default is current
  task until completion or expiry. Verified same-task successors inherit only
  applicable task approvals, rechecked against their own permissions. Original
  session approvals do not transfer. Preserve original deadlines and allowances.
- Evaluate at admission and immediately before each effect under existing
  ownership/lifecycle fences. Revocation blocks queued/subsequent effects but
  does not itself interrupt a running turn. Emergency and resource-stop controls
  remain independent. Read-only reconciliation of submitted effects remains
  possible; a reconciliation must not become disguised resubmission.
- Freeze selected wake routes and scope in intent. Each ordered fallback route
  must be both permitted and supported. Only definitive non-submission permits
  trying another admitted route; uncertainty requires reconciliation first.
  Permission increases do not rewrite an old intent into a broader route list.
- Migration inventories existing grants and explicit denials, translates supported
  equivalents with provenance, and diagnoses ambiguous mappings without guessing.
  Retain legacy behavior until an explicit policy-adoption revision selects the
  new resolver. Old intents keep their admitted route/deadline and still observe
  current revocation. Remove the refresh-only bridge only after all consumers
  and compatibility checks use the common policy.

### Issue318: requested scope and capability contract

Issue318 reports an installed0.20.1 environment in which the native MCP reload
primitive is shared, while exact invoking-client attachment discovery fails.
These are reported evidence bounds, not proof no upstream version has a scoped
primitive. The common model must distinguish current-connection refresh, exact
client replacement and shared-server reload. Do not treat them as interchangeable
implementations of permission to refresh self.

Before admission, determine actual effect scope and exact owned binding. A request
for only the invoking connection/client cannot fall back to shared reload or a
guessed pane, even when the caller separately has shared-refresh permission.
Return an actionable unsupported-scope, ownership-unavailable or uncertain result
as applicable, with no refresh effect or unverified goal restoration. Fresh
stdio startup is not refresh of an existing connection.

Issue318 owns missing scoped execution and any upstream primitive dependency.
HF-06 owns permission/capability separation and refusal before effects. Supported
scoped execution is not a prerequisite for shipping truthful policy and refusal;
claiming scoped refresh completion does require issue318's acceptance: selected
connection updated, peer unchanged, resource version verified, same goal and
nondecreasing counters/original allowance preserved. #282 retains its wider
operational refresh outcome; #310/#311 must converge with this common model.

## Testing Decisions

Proposed primary seam: public CLI/MCP operation admission and effective-permission
inspection, with injected verified identities, policy and runtime adapter responses.
Use existing operation/controller journals and test repeated commands across
process restart. Exercise the independent controller seam where effects occur;
helper-only tests do not prove enforcement. The operator approved these seams and the six-slice breakdown. No fixture
becomes installed-runtime evidence.

Prior art includes public lifecycle MCP contracts, independent shared-refresh
controllers, goal supervision, A2A identity/claims and native/runtime dispatch
fixtures. Assert observable decisions, effect counts, peer isolation, stable
intent/deadline, approval provenance and ledger continuity rather than internal
function arrangement. Cover global/profile/session/action precedence, mandatory
deny, self-promotion, delegated ceilings, malformed policy, new-action behavior,
two-sided A2A, successor expiry, policy changes after admission and restart.

For #318, simulate a shared-only adapter and missing/conflicting client binding
with two loaded conversations. An allowed scoped request must return unavailable
before queueing or effect; shared reload, guessed replacement and goal restoration
counts remain zero. Separately inject a supported scoped adapter to prove route
selection; installed acceptance still needs a real versioned runtime and peer
connection observations. Preserve original checkpoint, goal and accounting.

## Out of Scope

No live deployment, provider input, broad shared reload, guessed tab replacement,
credential vault, automatic account cycling or promise of hostile same-UID
isolation. No new wake engine, workflow language, inventory or resource ledger.
No unsupported refresh primitive is invented. No source fixture qualifies
current installed capability or closes #318. No new allowance from approval,
refresh, handoff or process restart.

## Further Notes

Product understanding is explicitly confirmed. The contract interview retains
all nine answers. HF-02/#315 and HF-07/#316 remain HF-06's declared prerequisites;
HF-13/#317 owns wake lifetime/startup policy. Downstream runtime execution belongs
to HF-18/19/20/24. The proposed slices separate hard prerequisites from shared
write-surface coordination. The operator approved test seams, granularity and dependency edges; publish
the six bounded children and read back their native blocking relationships. Existing HF locators remain stable.


### Issue319: enforcement recovery is not resource renewal

Issue319 reports an installed0.20.1 transient native observation timeout that
leaves supervision durably stopped after observations recover. Its evidence does
not deterministically reproduce the initial timeout; the retained stop and healthy
recheck were observed. Keep this distinct from enrollment failure and #318.

Common permissions must distinguish enrollment, allowance change, disabling
enforcement and explicit recovery/reconciliation of an observation-fault stop.
The permissive profile's enrollment permission grants neither recovery nor budget
renewal. Recovery needs explicit operator authorization; an allowance-change
approval is not an implicit recovery instruction. An existing task/standing grant
applies only if its scope explicitly covers that recovery.

Issue319 owns runtime recovery and stop-episode diagnostics. Permission to
recover is only a prerequisite: qualified nondecreasing accounting, current exact
native state, fresh controller, same-boot continuity and remaining original
resources must also be verified. A successful read, heartbeat, native goal resume,
refresh or handoff alone cannot clear the latch. Keep the original charges,
deadline, accounting basis and attributable stop/recovery history.

The enforcement slice can ship permission classification and actionable blocked/
unsupported diagnostics before #319 is fixed. Claiming successful recovery of
that observation fault requires #319's own acceptance; do not hide it inside
profile migration, source fixtures or an operator's manual-monitoring workaround.
