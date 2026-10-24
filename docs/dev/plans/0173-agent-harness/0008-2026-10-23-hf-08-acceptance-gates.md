# HF-08: Accept one work result using independent declared checks

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-08 (local draft; not posted)
Priority: P0
Area: Task contracts
Blocked by: HF-04, HF-06, HF-07
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Separate the worker completion report from acceptance of its required artifacts and checks.

## Repository surface and reuse

Mailbox outcome/evidence receipts; artifact references; verifier commands; approved task brief.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which checks are deterministic, reviewer judgments or human decisions?
- How are verifier failures distinguished from work failures?

## Acceptance evidence

- [ ] A convincing done message cannot pass a missing artifact or failed required check.
- [ ] Checks bind to the exact artifact/commit and brief revision; stale or unavailable evidence returns unknown.
- [ ] The result is usable as a typed branch condition and records the accepting authority.

## Scope limits and integration

No generic quality score, test-count productivity metric or new workflow engine inside the verifier.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
