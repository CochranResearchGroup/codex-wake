# HF-04: Prevent competing agents from mutating the same resource

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-04 (local draft; not posted)
Priority: P0
Area: Ownership and actions
Blocked by: HF-02
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Two workers cannot simultaneously own the same declared mutation resource; a deliberate ownership transfer is inspectable.

## Repository surface and reuse

Existing lifecycle/pane locks; worktree custody; launch admission; capability and generation checks.
Extend existing ownership/locking semantics; terminal interactions consume the same ownership rules in HF-05.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which resources need explicit claims versus existing short-lived locks?
- What is the recovery policy for an owner that disappears?

## Acceptance evidence

- [ ] A conflict over an owned worktree or install/build prefix is refused before mutation.
- [ ] Ownership loss, stale generation and controller failure do not authorize a second writer.
- [ ] Release/transfer preserves attributable receipts and leaves unrelated resources untouched.

## Scope limits and integration

No global filesystem lock service, destructive stale-lock cleanup or ownership inferred from a directory name.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
