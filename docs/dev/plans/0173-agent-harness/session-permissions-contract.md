# Common session permissions: HF-06 requirement and proposed contract

State: PRODUCT_AND_IMPLEMENTATION_BREAKDOWN_APPROVED
Owner: ecochran76; integration through CW-HARNESS-173/HF-06
Date: 2026-10-24
Source: operator clarification in issue310's repair conversation; reconciled with
first-frontier-decisions.md at docs/agent-harness-backlog 4dfdc39.

## Required product behavior

Codex Wake has one common session permissions model, configurable globally and
tailored by specific action. It covers auto-refresh, auto-handoff, external
resource enforcement, A2A send and receive, and wakes delivered through a background
app server, an existing tab, or a newly created tab. These are examples, not a
closed feature list. New supported actions join the same model rather than adding
an independent allowlist, approval mechanism or self-access switch.

The recorded preferred profile is permissive self-control: verified sessions may
refresh, hand off, resume themselves and opt into external enforcement. This is a
profile selection, not a requirement to hardcode permissive behavior for every
operator. An operator's request or standing policy can authorize the action;
do not require another per-session manual grant merely because its UUID is new.
A caller-supplied identifier is not ownership proof. Inventory enrollment,
permission, runtime capability and execution readiness remain separate.

HF-06 owns the common permission contract and evaluator. Other tickets consume it:

| Action family | Independently configurable actions | Execution owner / constraints |
| --- | --- | --- |
| Inspect | Own-session inspect and configuration | HF-02/03; verified identity, private-data scope |
| Refresh | Auto-refresh self; shared-server refresh effect | Existing lifecycle / #282; shared effect scope is explicit and distinct |
| Handoff | Auto-handoff self to successor | Lifecycle + HF-07/18; link successor, retain task and allowance |
| Resume | Resume exact saved conversation | HF-18; exact conversation/account and fresh binding |
| Enforcement | Enroll/enable; change allowance; disable/unenroll | HF-24 + #270; opt-in does not imply limit renewal or disabling operator enforcement |
| A2A | Send request; receive request; claim; reply | Existing A2A; sender and recipient rules both apply; delivery is not task authority |
| Wake delivery | Background app-server; existing tab; create/load new tab | HF-13 declares selected mode; HF-18/19 execute binding/tab changes |
| Fresh launch | Start a new conversation/task | HF-20/lifecycle; distinct from attaching a new tab to the same conversation |

## Proposed resolution model for HF-06 design interview

Use one versioned host-owned policy resolver across CLI, MCP, controllers and
adapters. Global policy provides a baseline and action map. Named profiles and
operator-approved session/assignment overrides use the same rule vocabulary.
Sessions inherit policy automatically; they do not author their own grants.

Resolved precedence: global baseline, named profile, explicit session/assignment
rule, then independently enforced host ceilings and delegated task scope.
Within a layer an exact action overrides that layer's fallback; absent rules
inherit. A more specific rule can replace an ordinary inherited default. A hard
host ceiling, revoked grant or explicit operator unenrollment cannot be overridden
by a permissive session profile. This distinguishes a configurable default deny
from a non-overridable prohibition. The operator accepted this precedence in round one. Rule syntax and the action
default matrix remain to be resolved; no JSON schema is frozen here.

Proposed rule outcomes: allow, deny or require scoped operator approval; inherit
is configuration syntax, not a fourth authorization result. An existing matching
approval satisfies that rule without another prompt. A request cannot approve
itself or widen a delegated ceiling. Unknown action keys and malformed policies
fail closed with an actionable diagnostic. New actions introduced by an upgrade require approval until configured by
default. The operator may explicitly enable a global option allowing future
actions to inherit the chosen default. This option remains bounded by mandatory
prohibitions and delegated scope.

Evaluation uses verified principal/actor, exact target and relationship (self,
peer, successor or shared), action, requested delivery mode/effect scope, task
and allocation references, runtime/account and policy revision. A future successor
is linked explicitly rather than pretending it is the same conversation. Native
self evidence, delegated controller evidence and operator authority are distinct
supported identity sources; CLI and MCP must agree for equivalent verified facts.
Missing runtime identity support yields unsupported/unverified, not simulated
native attestation.

For A2A, sender permission to send and recipient permission to receive must both
allow the exchange, including any peer/task scopes. Neither creates permission to
execute the requested task. Replies/claims remain correlated and scoped. For
sleeping owners, wake lifetime and recipient-startup choice are independent of
permission. Authorizing an existing tab does not authorize a background route,
new tab or new conversation. Wake policy may declare an ordered list of permitted routes. Resolve and retain
that list at admission; automatic fallback uses only its allowed, supported
routes. An uncertain submission must be reconciled before another route is tried.
No route falls back to a broader route outside the admitted list.

Resolve permission before admitting work and revalidate it before each effect.
Persist the admitted action, target, scope and policy/approval provenance with the
existing durable operation. A new permissive policy does not rewrite an old
intent, deadline, selected startup mode or uncertain submission. A revocation
blocks new effects, including after restart; reconcile uncertain effects read-only
before retry. Permission is necessary but does not bypass idle observations,
capability qualification, ownership claims, emergency pause, resource proof,
fixed deadlines or cumulative accounting.

Expose an effective-permissions explanation: action, target relationship,
allow/deny/approval-needed result, deciding rule and policy revision, applicable
ceiling, and capability/readiness status as separate fields. Do not expose peer
secrets or make agents reverse-engineer multiple registries to explain refusal.

## Existing implementation and migration boundary

Issue310 / PR311 provides a narrow native self-refresh default and regression
coverage. Its `session_permissions.self_access` switch is not the final common
policy schema. HF-06 must reconcile or migrate that bridge into the common
resolver before advertising a unified model. Do not proliferate equivalent
switches for handoff, A2A or delivery, or claim PR311 completes HF-06.

Reuse existing host profiles, grants, actor identities, operation journals and
allocation ledgers. Inventory enrollment is not an action grant. Preserve explicit
legacy denials and authorization history; define conflict/migration diagnostics
and compatibility before switching adapters. Existing pending wakes retain their
original mode and behavior unless explicitly revised. Rollout needs one serial
integration owner for shared CLI/MCP/profile/controller surfaces.

## Acceptance additions

- One global configuration changes the effective baseline for new verified
  sessions without adding each UUID to a registry.
- Per-action overrides demonstrably distinguish refresh, handoff, enrollment,
  send, receive and each wake route; absent overrides inherit predictably.
- Two sessions can select different operator-approved profiles without changing
  one another's permissions. Sessions cannot self-promote.
- Explicit deny, hard ceilings, scoped approvals and operator unenrollment have
  deterministic precedence, explainable results and restart-safe behavior.
- An allowed sender cannot bypass a denied receiver. Receiving a message grants
  no extra tools, workspace or resource allowance.
- Background, existing-tab, new-tab and fresh-conversation actions are tested
  independently; denied/unsupported modes produce no broader fallback effect.
- CLI/MCP/controller decisions agree on the same verified inputs. A stale policy
  or revoked rule prevents queued effects without discarding uncertain history.
- Permission and runtime support/readiness are independently visible; unsupported
  enforcement does not become enforceable because policy says allow.

## Remaining design inputs and limits

HF-06 still needs its own approved technical handoff, including concrete
schema, migration and caller-level proof. Precedence and authority for profile
edits are resolved below.
HF-13 now records configurable retirement of pending owner-bound wakes on
verified explicit owner completion, and configurable create/load/run as the
preferred default for new wakes (4dfdc39). The permission decision still applies
to that selected route; a default mode is not blanket authority. Older intents
retain their admitted behavior. HF-02 and HF-07 retain
their prerequisites. This document records requirements and a reviewable design
proposal; it performs no runtime implementation or global policy change.


## Interview round one: resolved

Authority: operator answered "yes all" to Q1–Q3 in this conversation.

1. Global rules are defaults; profiles and session-specific rules may override
   them. Explicit mandatory operator prohibitions always win.
2. The operator controls permission increases. Agents may restrict themselves
   or select profiles already authorized for them. The operator may delegate
   profile management to a controller within an explicit scope; agents cannot
   self-promote.
3. Unknown actions added by upgrades require approval until configured. An
   explicit global option may instead let future actions inherit the chosen
   default, without overriding mandatory restrictions.

Next frontier: action defaults for the permissive profile, approval reuse and
policy-change behavior for already queued work. No runtime change is authorized
by this interview record.


## Interview round two: resolved

Authority: operator answered "yes all" to Q4–Q6 in this conversation.

### Permissive profile action defaults

| Action | Default |
| --- | --- |
| Self-refresh, self-handoff and self-resume | Allow |
| Enroll in external resource enforcement | Allow |
| Increase allowance or disable operator enforcement | Require approval |
| A2A send/receive between operator-managed sessions | Allow when both sessions' rules permit |
| Background app-server, existing-tab and create/load/run wakes | Allow when declared task and recipient authorize the selected route |
| Shared-server refresh affecting other sessions | Require standing scope approval |

These defaults retain mandatory restrictions, verified identity, declared scope
and existing resource allowances. Automatic operation does not require repeated
per-session UUID grants. They do not qualify unsupported runtime capabilities.

### Approval lifetime and reuse

Approvals support one operation, one task or a standing rule. Default scope is
the current task until completion or expiry; standing approval must be selected
explicitly. Matching actions reuse that approval. Broader actions require their
own authority; a reusable approval is not an allowance renewal.

### Revocation and work already in flight

Revocation immediately blocks queued actions and subsequent effects. Already
submitted effects may be observed and reconciled without granting another
effect. Revocation alone does not automatically interrupt a running turn.
Emergency pause and resource-stop controls retain their separate behavior.

Next frontier: automatic trigger authority, approval continuity through successor
handoff, and explicitly permitted delivery-route fallback. These decisions do
not change production policy or authorize provider effects.


## Interview round three: resolved

Authority: operator answered "yes all" to Q7–Q9 in this conversation.

1. An authorized session or controller may perform allowed actions automatically
   when configured conditions occur, without another prompt. The policy covers
   both action and trigger. Automation stays within the existing task and
   allowance; permission does not invent a trigger or a new task.
2. A verified successor continuing the same task inherits applicable task-scoped
   approvals, subject to its own effective permissions and current operator
   restrictions. Original expiry and remaining allowance persist. Approvals
   explicitly limited to the original session do not transfer.
3. Wake policy supports an ordered list of permitted routes, with automatic
   fallback only within that list. Every selected route must be allowed and
   supported. Uncertain submissions are reconciled before a different route
   is attempted, preventing duplicate work.

## Interview boundary

All nine product questions have explicit affirmative answers. The operator confirmed
the combined understanding and directed reconciliation with issue318. Concrete schema, storage reuse,
identity-adapter feasibility, compatibility and provider-free validation belong
to the bounded technical handoff; no remaining technical choice may silently
change these product decisions. HF-02/HF-07 prerequisites and the serialized
shared-surface integration boundary remain. This record does not authorize
implementation or production permission changes.


## Confirmed understanding and issue318 reconciliation

Operator confirmed the combined nine decisions, then requested review of #318.
The [HF-06 spec](hf-06-spec.md) separates current-connection refresh, exact-client
replacement and shared reload. An allowed action with unsupported scope or
unverified ownership refuses before admission/effects; permission never supplies
a missing runtime primitive. See [proposed bounded slices](hf-06-implementation-breakdown.md).
The operator subsequently approved the test seams and six-slice breakdown.
Publication creates bounded source-work tickets, not deployment authority.


The operator also directed attention to the new goal-limits error, issue319.
The implementation spec separates observation-stop recovery from enrollment
and renewal and retains #319 as its runtime-recovery acceptance owner.
