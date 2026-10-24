# HF-32: Apply opt-in tab organization with stable protection rules

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-32 (local draft; not posted)
Priority: P2
Area: Workspace organization
Blocked by: HF-17, HF-21
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Run an explicitly enabled activity/repo/holding policy without fighting human tab organization.

## Repository surface and reuse

HF-16/17 layout planning; state transitions; host policy; attention exceptions.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which policies should be automatic, and what counts as dormancy?
- What takes precedence between active-first, repo grouping and manual arrangement?

## Acceptance evidence

- [ ] Policies debounce transitions, preserve pins/focus and limit move frequency.
- [ ] Unknown/mixed ownership and changed layouts hold or request attention.
- [ ] Policies can be disabled and inspected; restart does not cause uncontrolled repeated moves.

## Scope limits and integration

No default unattended rearrangement, process suspension, automatic sorting of unrelated sessions or dependency on silence heuristics.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
