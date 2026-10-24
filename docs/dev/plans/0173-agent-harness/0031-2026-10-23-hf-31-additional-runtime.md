# HF-31: Qualify one selected additional TUI adapter

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-31 (local draft; not posted)
Priority: P2
Area: Runtime portability
Blocked by: HF-25
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Use the common contracts to qualify one chosen Claude Code or open-model TUI without weakening existing guarantees.

## Repository surface and reuse

Runtime adapters; lifecycle/profile contracts; adapter conformance tests; provider docs to research during grill.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which runtime is first and what primary documentation/protocol access exists?
- Which operations can be qualified rather than merely launched?

## Acceptance evidence

- [ ] Select one runtime/version and publish an evidence-based capability matrix.
- [ ] Fixture qualification precedes any separately authorized bounded live acceptance.
- [ ] Identity, protected input, refusal/uncertainty and recovery behavior remain explicit.

## Scope limits and integration

No all-provider support promise, public plugin SDK, hostile multi-tenant claims or implicit live credentials.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
