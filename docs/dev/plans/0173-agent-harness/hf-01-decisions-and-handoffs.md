# HF-01 shared harness decisions and first handoffs

State: DESIGN_RESOLVED
Date: 2026-10-24
Work item: CW-HARNESS-173/HF-01
Authority: operator questionnaire 536123222930, response
4714471256de4ac29536f14d29677f03, revision
63b3b775934957ae27965f68f922d1888bbc72228b47208444588d730256c0fa,
submitted 2026-10-24T15:46:46.656782+00:00. All seven substantive answers
selected the recommended choice; optional comments were unanswered.
This records resolved product decisions, not implemented capabilities.

## Resolved scenarios

| Scenario | Decision | Owning follow-up |
| --- | --- | --- |
| Tab moved/reordered/parked | Keep managed-agent identity; update terminal attachment. A label or index is not identity. | HF-02/16/17 |
| Reboot, same conversation resumed | Keep managed-agent identity and history; verify a new process binding before actions. | HF-02/18 |
| Replacement conversation | Create a new managed agent linked by handoff; preserve task and allocation continuity. A worker role may span agents but is not their identity. | HF-02/07/18 |
| Changed account/profile | Preserve continuity only after verifying access to the exact conversation; otherwise offer explicit successor handoff. Never copy credentials or reset allowance. | HF-18 |
| Interrupted instruction | Keep unresolved effects unknown; reconcile evidence before retry/continuation. Do not require human review where supported evidence resolves the uncertainty. | HF-05/09 |
| Missed daily occurrence | Retain occurrence and original due time; each schedule declares catch-up, skip and overlap policy. No new catch-up default is implied. | HF-13/20 |
| Contract boundary | Settle identities, ownership and recovery invariants now. Defer storage/schema, UI and workflow syntax to their feature interviews. | All |

## Shared ownership

HF-02 owns managed identity and binding history; HF-03 owns normalized observations
and freshness; HF-04 owns mutation-resource claims and HF-05 consumes them for
terminal input/takeover; HF-09 owns instruction attempts/cursor; HF-21 owns human
attention records; HF-13 owns wake lifetime and retained intent, while HF-20
resolves recurrence authority and occurrence admission. These are responsibilities,
not mandated module names or a requirement for new stores.

Task identity, conversation identity, attachment and process generation remain
separate. A management record is not a grant. Existing host delegation, exact
recipient checks and resource ledgers remain authoritative. Unknown state is
not readiness, lost responses are not non-submission, and new context does not
renew budgets. Retaining a missed occurrence does not authorize its delivery.

## Repository and tracker reconciliation

- [Runtime delivery contract](../0172-multi-runtime/runtime-delivery-contract.md):
  core owns locks, cancellation, expiry, attempt identity and uncertainty;
  adapters own runtime protocol/evidence. Preserve capability distinctions.
- [Existing goal supervision](../../../adr/0001-existing-goal-supervision.md): exact
  owned-turn stop is distinct from shared-executor termination.
- [Objective allocation](../../../adr/0002-objective-allocation-provisioning.md):
  host-delegated enrollment and successor accounting already exist; reuse them.
- `src/codex_wake/a2a_identity.py:RuntimeIdentity` binds native namespace/thread/root.
  `src/codex_wake/objective_ledger.py:ObjectiveLedger` retains objective charges,
  deadlines and authorization history. The new inventory cannot replace either.
- [#270](https://github.com/CochranResearchGroup/codex-wake/issues/270) was verified
  open on 2026-10-24. Its original feasibility scope predates released accounting
  and strict execution. HF-23/24 must inventory residual runtime portability,
  not recreate ledgers or imply arbitrary existing sessions have OS containment.
- [#282](https://github.com/CochranResearchGroup/codex-wake/issues/282) was verified
  open on 2026-10-24. Its host-scope/public-MCP self-refresh outcome remains its
  own work item. HF-06 reuses host profiles; HF-18/26 must not claim that a new
  PID proves refreshed resources or that Grok inherits Codex's native capability.
  This interview does not close either issue or qualify the installed runtime.

## First parallel interview handoffs

HF-02: enroll one existing exact conversation; distinguish its durable agent ID
from current attachment/process binding. Decide discovery versus authorized
adoption and stale-record recovery. First proof: controller restart preserves ID,
changed conversation produces a successor, ambiguous binding prevents actions.

HF-07: pin the objective, phase, non-goals and acceptance references to an
assignment. Decide who can amend the brief and how revisions affect in-flight
work. First proof: an agent's requested scope expansion does not become authority.

HF-13: extend existing wake intent with explicit lifetime/owner semantics; preserve
origin, due time, expiry and uncertain attempts. Decide lifetimes and owner-end
behavior. First proof: isolated restart/epoch-change evidence distinguishes saved
records from monitor readiness and actual delivery. No machine reboot required.

Each handoff starts its own grill-with-docs; none is a coding authorization.
Primary integrates shared CLI/MCP/profile/schema changes serially. Leaf changes
can run in parallel after their designs and write boundaries are resolved.

## Proposed documentation changes for implementation handoffs

Proposed glossary correction: a managed agent tracks one exact conversation
through verified process/attachment changes; a successor conversation is a
separate managed agent. Proposed term: agent succession links predecessor and
successor while preserving task obligations and resource continuity.
Keep definitions domain-only; storage keys and process fences belong in design.
The identity-versus-worker-role tradeoff merits an ADR when HF-02 chooses its
concrete contract. No new ADR or glossary correction is applied by this record.

## Acceptance and limits

All six scenarios and shared ownership are resolved, and #270/#282 were read
against the current contract/code evidence. HF-01 is complete as a design ticket.
Deferred feature decisions are explicit above. No runtime changes, provider
operations, installations, tab moves or new GitHub issues were performed.
