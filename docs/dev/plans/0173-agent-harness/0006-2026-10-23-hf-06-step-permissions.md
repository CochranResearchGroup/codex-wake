# HF-06: Apply host-approved permissions to an assignment step

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-06 (local draft; not posted)
Priority: P0
Area: Ownership and actions
Blocked by: HF-02, HF-07
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

A review, implementation or test assignment runs under its declared tool/workspace profile and cannot silently widen it.

## Repository surface and reuse

lifecycle_configuration.py; host grants; MCP CommandRunner; runtime profiles; strict-objective documentation.
Reuse existing host grants and lifecycle profiles; resolve #282 host-wiring scope instead of creating a parallel configuration system.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which restrictions are genuinely enforceable per runtime?
- How does an operator approve a profile change?

## Acceptance evidence

- [ ] A read-only review step cannot gain implementation/publishing authority through its own arguments.
- [ ] Changing task, conversation or account requires validation of the applicable grant.
- [ ] CLI and MCP enforce the same declared profile and explain unsupported restrictions.

## Scope limits and integration

No new credential vault, account auto-cycling or promise of hostile same-UID isolation.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.

## 2026-10-24 interview update

See [first-frontier decisions and overlap boundaries](first-frontier-decisions.md).
