# HF-06: Apply host-approved permissions to an assignment step

State: READY_FOR_AGENT; children blocked by their explicit prerequisites
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-06 (local draft; not posted)
Priority: P0
Area: Ownership and actions
Blocked by: HF-02, HF-07
Grill state: product, public test seams and six-slice breakdown approved
Implementation state: approved bounded source-work handoffs; no live deployment authority
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Codex Wake resolves one common session permissions policy with global defaults,
selectable profiles and action-specific overrides. Review, implementation and
test assignments consume that policy without silently widening their scope.
See [common permissions requirement and proposed contract](session-permissions-contract.md).

## Repository surface and reuse

lifecycle_configuration.py; host grants; MCP CommandRunner; runtime profiles; strict-objective documentation.
Reuse existing host grants and lifecycle profiles; resolve #282 host-wiring scope instead of creating a parallel configuration system.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which restrictions are genuinely enforceable per runtime?
- Concrete approval interface and schema must implement the resolved operator/delegated-controller authority; see the contract interview.

## Acceptance evidence

- [ ] A read-only review step cannot gain implementation/publishing authority through its own arguments.
- [ ] Changing task, conversation or account requires validation of the applicable grant.
- [ ] CLI and MCP enforce the same declared profile and explain unsupported restrictions.

## Scope limits and integration

No new credential vault, account auto-cycling or promise of hostile same-UID isolation.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.

## 2026-10-24 interview update

See [first-frontier decisions and overlap boundaries](first-frontier-decisions.md).


## 2026-10-24 common permissions clarification

The operator explicitly requests global configuration tailored by action, covering
refresh, handoff, external enforcement, A2A send/receive and distinct wake delivery
routes. HF-06 owns the shared resolver; HF-13/18/19/24 consume it. The linked
contract adds requirements, action coverage, proposed precedence and acceptance.
Issue310 / PR311 is a narrow refresh bridge, not completion of this ticket.
No implementation readiness or live permission is inferred from this update.


## Confirmed product and bounded build proposal

[Implementation spec](hf-06-spec.md) records the confirmed nine decisions and
issue318's scoped-refresh capability boundary. [Proposed slices](hf-06-implementation-breakdown.md)
retain existing #315/#316 prerequisites and reuse #317/#318 rather than duplicating
their execution work. Test seams and breakdown are approved for publication as six bounded children.
Each child retains its explicit prerequisites and runtime qualification gates.
