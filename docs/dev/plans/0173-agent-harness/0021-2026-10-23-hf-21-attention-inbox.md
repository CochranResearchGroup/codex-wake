# HF-21: Route one blocked decision through a durable human-attention queue

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-21 (local draft; not posted)
Priority: P0
Area: Human supervision
Blocked by: HF-03, HF-06
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Present an actionable decision request and bind the human response to the exact still-valid operation.

## Repository surface and reuse

Existing status/receipts and host grants; observation outcomes; CLI/MCP decision projection.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which decisions require explicit human acceptance versus advisory notice?
- How are priority, expiry and response ownership represented?

## Acceptance evidence

- [ ] Each request states the needed decision, evidence, scope and expiry.
- [ ] A stale response cannot authorize a changed turn/account/action or duplicate a completed decision.
- [ ] CLI inspection and response work before a dashboard exists; closed/unknown requests retain history.

## Scope limits and integration

No separate approval queues per feature, automatic credential entry, unsolicited external notifications or invented permissions.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
