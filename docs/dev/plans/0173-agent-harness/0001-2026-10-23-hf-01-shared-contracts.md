# HF-01: Grill and reconcile the shared harness contracts

State: DONE (design only)
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-01 (local draft; not posted)
Priority: P0
Area: Shared contracts
Blocked by: None for the shared-contract interview
Grill state: RESOLVED; see [decisions and handoffs](hf-01-decisions-and-handoffs.md)
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Approve a small shared vocabulary and ownership map that makes the first implementation slices independent.

## Repository surface and reuse

GLOSSARY.md; docs/adr/; Plan0172 runtime contract; existing sessions, runtime_delivery, wake_control and lifecycle documentation.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- What is the stable managed-agent identity and its relationship to native conversation, process generation and terminal attachment?
- Which contracts must be frozen now, and which decisions belong to individual feature interviews?

## Acceptance evidence

- [x] Resolve six scenarios: moved tab, rebooted process, replaced conversation, changed account, interrupted instruction, and missed daily occurrence.
- [x] Assign one owner for identity, observations, mutations, attempts, attention and wake occurrence state.
- [x] Reconcile open #270/#282 against current code; record remaining scope without silently closing either issue.

## Scope limits and integration

No framework implementation, DSL selection, database selection, provider activation or omnibus feature specification.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
