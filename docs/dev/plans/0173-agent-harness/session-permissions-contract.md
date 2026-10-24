# Common session permissions: HF-06 requirement and proposed contract

State: REQUIREMENTS_RECORDED_DESIGN_PROPOSED
Owner: ecochran76; integration through CW-HARNESS-173/HF-06
Date: 2026-10-24
Source: operator clarification in issue310's repair conversation; reconciled with
first-frontier-decisions.md at docs/agent-harness-backlog 5593168.

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

Proposed order: global baseline, named profile, explicit session/assignment
rule, then independently enforced host ceilings and delegated task scope.
Within a layer an exact action overrides that layer's fallback; absent rules
inherit. A more specific rule can replace an ordinary inherited default. A hard
host ceiling, revoked grant or explicit operator unenrollment cannot be overridden
by a permissive session profile. This distinguishes a configurable default deny
from a non-overridable prohibition. Final precedence and rule syntax require
HF-06's design interview; no JSON schema or default matrix is frozen here.

Proposed rule outcomes: allow, deny or require scoped operator approval; inherit
is configuration syntax, not a fourth authorization result. An existing matching
approval satisfies that rule without another prompt. A request cannot approve
itself or widen a delegated ceiling. Unknown action keys and malformed policies
fail closed with an actionable diagnostic. Explicit policy must determine how
new actions added in later versions inherit; a wildcard must not silently turn
an upgrade into new cross-session authority.

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
new tab or new conversation. No route falls back to a broader allowed route
unless the admitted intent explicitly allows that fallback.

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
precedence/schema, authority for profile edits, migration and caller-level proof.
HF-13's pending owner-completion policy and preferred startup default remain
unanswered; this clarification does not choose either. HF-02 and HF-07 retain
their prerequisites. This document records requirements and a reviewable design
proposal; it performs no runtime implementation or global policy change.
