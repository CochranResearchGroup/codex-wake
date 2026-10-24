# HF-17: Park and restore dormant live tabs in a holding session

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-17 (local draft; not posted)
Priority: P1
Area: Workspace organization
Blocked by: HF-16
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Move an eligible whole tab into a managed holding session and restore its recorded placement.

## Repository surface and reuse

HF-16 layout plans/receipts; live observation; recipient bindings and pending-work inventory.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- What evidence establishes dormancy, and are future armed wakes allowed?
- Which events should offer restoration or later automatic recall?

## Acceptance evidence

- [ ] Parking preserves the live process/conversation and verifies wake/mailbox routing after the move.
- [ ] A busy pane, draft, human focus/pin or unknown state follows explicit protection rules.
- [ ] Restoration honors original repo grouping where possible and reports conflicts without recreating agents.

## Scope limits and integration

No suspension/termination, budget reset, altered work claim or automatic promotion of output silence to dormancy.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
