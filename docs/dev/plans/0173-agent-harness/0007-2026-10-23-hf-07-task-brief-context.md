# HF-07: Pin a task brief and bounded context package to one assignment

State: READY_FOR_AGENT
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-07 (published as #316)
Priority: P0
Area: Task contracts
Blocked by: None; HF-01 design resolved
Grill state: PRODUCT_DECISIONS_RESOLVED; technical handoff pending; apply [HF-01 decisions](hf-01-decisions-and-handoffs.md)
Implementation state: READY_FOR_AGENT; source scope and handoff approved; no live effects
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

An assignment carries its approved objective, phase, non-goals, acceptance conditions and evidence-linked input package.

## Repository surface and reuse

Existing handoff checkpoints; task/assignment inputs; docs authority and context references.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Who may amend the brief, and what invalidates an already-started step?
- Which context is required versus optional?

## Acceptance evidence

- [ ] The assignment pins a brief revision and its source evidence.
- [ ] A proposed scope change remains a request until explicitly approved.
- [ ] Context remains bounded and preserves unresolved obligations and authority references.

## Scope limits and integration

No broad corpus-ingestion engine, automatic task expansion or copied secret/transcript dumps.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.

## 2026-10-24 interview update

See [first-frontier decisions and overlap boundaries](first-frontier-decisions.md).

## Proposed build specification

See [bounded spec](hf-07-spec.md) and the [three-ticket review](first-frontier-spec-review.md).
Spec state: APPROVED; public caller seam and ticket breakdown approved.

Canonical tracker: https://github.com/CochranResearchGroup/codex-wake/issues/316
