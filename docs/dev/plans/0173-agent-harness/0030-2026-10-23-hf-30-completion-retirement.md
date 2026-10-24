# HF-30: Deliver an accepted work package and retire only its owned resources

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-30 (local draft; not posted)
Priority: P2
Area: Task contracts
Blocked by: HF-09, HF-14
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Finish one assignment with a usable artifact/evidence handoff and attributable resource retirement.

## Repository surface and reuse

Existing handoff/checkpoint, close-session, pending-work and process ownership; verifier/job receipts.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which resources persist for review and which may be retired automatically?
- What human acceptance and retention rules apply?

## Acceptance evidence

- [ ] Deliver exact changes/artifacts, validation, remaining risks and next owner.
- [ ] Pending/uncertain obligations prevent an incorrect all-done or destructive cleanup claim.
- [ ] Only owned eligible jobs, locks, worktrees and attachments retire; failure leaves a recoverable receipt.

## Scope limits and integration

No blanket workspace deletion, cancellation of unrelated work or new completion authority separate from HF-08.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
