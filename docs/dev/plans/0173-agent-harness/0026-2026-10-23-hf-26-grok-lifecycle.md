# HF-26: Qualify managed Grok lifecycle operations through the common interface

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-26 (local draft; not posted)
Priority: P2
Area: Runtime portability
Blocked by: HF-18, HF-25
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Add only the Grok launch/resume/refresh/handoff operations that can be proven with exact identity and truthful capabilities.

## Repository surface and reuse

Runtime delivery/lifecycle adapters; managed Grok bindings; native profiles; current Plan0172 support matrix.
Reuse #282 for its Codex self-refresh operational gap; this ticket is the incremental cross-runtime extension.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which Grok operations actually support same-conversation continuity?
- What evidence and explicit authority are required for a live qualification?

## Acceptance evidence

- [ ] Each operation has its own supported/unsupported/unqualified verdict and bounded acceptance evidence.
- [ ] Changing process, attachment or account does not transfer actor grants or renew budgets.
- [ ] Existing wake/A2A qualification remains intact; #282 baseline host-wiring disposition is reviewed before public MCP claims.

## Scope limits and integration

No duplicate wake/A2A implementation, inferred native caller attestation or promise that every lifecycle operation exists.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
