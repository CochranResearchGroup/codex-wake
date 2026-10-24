# HF-19: Restore a saved workspace and its conversation bindings

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-19 (local draft; not posted)
Priority: P1
Area: Workspace organization
Blocked by: HF-17, HF-18
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Reconcile a Byobu-restored or newly recreated layout with saved agent bindings, including the holding workspace.

## Repository surface and reuse

HF-16/17 layout state; HF-18 agent resume; Byobu restore integration; logical window inventory.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Is the initial operation selected-workspace or last-workspace resume?
- How should manually restored and newly created attachments be reconciled?

## Acceptance evidence

- [ ] One preview maps restored tabs to known agents without relying on old tab numbers or reused tmux IDs.
- [ ] A partial restore reports each agent as launched, conversation-resumed, ready or blocked.
- [ ] Conflicting existing tabs and missing profiles are preserved for operator decisions.

## Scope limits and integration

No duplicate agent launch, implicit work replay, all-host desktop restoration or account auto-switching.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
