# HF-28: Approve a decision and step a paused workflow from the console

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-28 (local draft; not posted)
Priority: P1
Area: Operator console
Blocked by: HF-05, HF-11, HF-21, HF-27
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Expose existing authorized control operations and workflow inspection through the operator view.

## Repository surface and reuse

HF-27 frontend; attention queue; workflow execution/branches/cursor; guarded action interface.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which first controls and confirmations are needed?
- What does stepping mean while a native turn or external job is already running?

## Acceptance evidence

- [ ] A human can inspect why a branch ran, set a breakpoint and advance one eligible instruction.
- [ ] Approval/steer/pause actions use the same permissions and receipts as CLI/MCP.
- [ ] Stale UI state cannot target a replacement agent or repeat an uncertain action.

## Scope limits and integration

No duplicate orchestration state, new kill-all authority or UI bypass of action admission.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
