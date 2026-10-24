# HF-27: Show a unified operator overview and attach to a known agent

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-27 (local draft; not posted)
Priority: P1
Area: Operator console
Blocked by: HF-03
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Provide the first operator view of agents/workspaces, current state and evidence with direct attachment navigation.

## Repository surface and reuse

Existing CLI/MCP read projections; managed inventory/observation; operator frontend choice deferred.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Web, terminal or both; what audience/authentication and local deployment scope?
- What is the smallest useful overview and accessibility/navigation model?

## Acceptance evidence

- [ ] Display runtime, repo/worktree, task and freshness without exposing credentials.
- [ ] Attach navigation resolves the current known attachment rather than a remembered tab number.
- [ ] Unavailable capabilities and partial inventory are visible; no workflow engine is embedded in the view.

## Scope limits and integration

No public ingress, new remote shell server, mutating control surface or dependency on the full workflow language.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
