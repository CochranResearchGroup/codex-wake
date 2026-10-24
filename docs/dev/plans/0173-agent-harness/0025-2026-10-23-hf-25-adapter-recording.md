# HF-25: Record a redacted adapter interaction and replay it as a conformance fixture

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-25 (local draft; not posted)
Priority: P1
Area: Runtime portability
Blocked by: HF-05
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Turn a qualified observation/action exchange into an opt-in diagnostic fixture that detects adapter/version drift.

## Repository surface and reuse

Runtime adapters and terminal host; executable smoke harnesses; existing fault fixtures; evidence projection.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- What may be captured and retained, and what makes a fixture representative?
- Which compatibility/version changes invalidate qualification?

## Acceptance evidence

- [ ] Recorded data is bounded and redacted with explicit capture authority.
- [ ] Replay exercises the real adapter interface without provider input or fabricated live acceptance.
- [ ] Changed identity/UI/version and delayed/missing evidence are caught before enabling an adapter.

## Scope limits and integration

No automatic transcript harvesting, production-input replay or second workflow event journal.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
