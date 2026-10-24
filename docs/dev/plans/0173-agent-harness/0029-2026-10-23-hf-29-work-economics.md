# HF-29: Attribute time and usage to accepted work and correction cycles

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-29 (local draft; not posted)
Priority: P2
Area: Operator console
Blocked by: HF-23
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Explain workflow expenditure and progress using existing accepted results and attributed evidence.

## Repository surface and reuse

Workflow attempt/acceptance events; objective usage; diagnostic references; dashboard projections.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which comparisons help an operator act without rewarding implementation theater?
- What attribution is supported by evidence rather than model guesses?

## Acceptance evidence

- [ ] Report accepted outcomes, waiting, corrections and usage with explicit unknown/unattributed categories.
- [ ] Repeated qualification/governance activity is inspectable against task phase without a simplistic productivity score.
- [ ] Metrics derive from existing records and do not change execution authority.

## Scope limits and integration

No token-to-quality score, diff-size ranking or fabricated exact cost/time attribution.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
