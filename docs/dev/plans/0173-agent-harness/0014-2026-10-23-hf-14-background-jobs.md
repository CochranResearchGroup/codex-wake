# HF-14: Own a durable background job and await its result

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-14 (local draft; not posted)
Priority: P1
Area: Durability and jobs
Blocked by: HF-02, HF-04, HF-06, HF-13
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Start one approved command outside an active agent turn and resume the owner from its attributable result.

## Repository surface and reuse

Process identity/signals; supervisor; current process/file/CI triggers; command logs and wake receipts.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which command classes and child-process ownership can be supported first?
- Who owns cleanup and how does a workflow await consume completion?

## Acceptance evidence

- [ ] The owner can end its turn while the job continues with bounded resources.
- [ ] Exit status, logs and artifacts bind to the original process generation and survive controller restart.
- [ ] Cancellation and uncertain completion reconcile the original job; the command is not blindly rerun.

## Scope limits and integration

No generic remote execution platform, implicit provider calls or model turn kept alive merely to poll.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
