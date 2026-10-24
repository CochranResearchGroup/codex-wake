# HF-12: Repeat a checked step with explicit exit and progress limits

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-12 (local draft; not posted)
Priority: P1
Area: Turn flow
Blocked by: HF-10
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Perform a bounded repair/review cycle that exits on verification, exhaustion or lack of accepted progress.

## Repository surface and reuse

Workflow attempts; independent acceptance; task brief; progress evidence.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- What constitutes progress for the selected task type?
- When is another correction permitted versus a human hold?

## Acceptance evidence

- [ ] Repeat/until has a maximum iteration/resource allowance and independent stop condition.
- [ ] Repeated unchanged failures or artifacts trigger the declared no-progress outcome.
- [ ] Correction attempts preserve prior failures and do not replenish the objective allowance.

## Scope limits and integration

No open-ended while-goal loop, reward for diff size or indefinite qualification campaign.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
