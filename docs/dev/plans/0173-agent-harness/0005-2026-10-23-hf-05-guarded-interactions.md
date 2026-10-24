# HF-05: Perform one guarded multi-step interaction and human takeover

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-05 (local draft; not posted)
Priority: P1
Area: Ownership and actions
Blocked by: HF-03, HF-04, HF-06
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Complete a supported menu/approval interaction using fresh state preconditions, then safely hand terminal control to or from a human.

## Repository surface and reuse

Runtime adapters; grok_terminal.py; native controls; shared pane locks; action receipts.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which first interaction and runtime can be qualified?
- What confirms human takeover and return of control?

## Acceptance evidence

- [ ] The operation pins the exact target, expected pre-state and allowed transition; changed identity or a draft refuses input.
- [ ] One input owner exists across the interaction; human takeover fences automated input.
- [ ] Lost responses become uncertain and are reconciled without a second paste or invented success.

## Scope limits and integration

No arbitrary remote shell panel, default approval bypass, unsupported interrupt claim or automatic repeated keystrokes.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
