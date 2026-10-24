# HF-23: Report cumulative usage and remaining allowance across agents and jobs

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-23 (local draft; not posted)
Priority: P2
Area: Resources
Blocked by: HF-09, HF-14
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Expose one objective usage view across attempts, reviews, successors and owned jobs with truthful unknowns.

## Repository surface and reuse

Existing objective/session ledgers; lifecycle budgets; runtime usage adapters; strict executor accounting.
Existing Codex accounting remains authoritative; reconcile with #270 rather than duplicate its exploration.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- What accounting scope and freshness are supported by each provider?
- Which existing #270 findings remain open versus already shipped?

## Acceptance evidence

- [ ] Concurrent work, retries, reviewers and successors are not free or double-counted.
- [ ] Unsupported or stale token/cost data is labeled unknown rather than zero.
- [ ] Readback distinguishes measured, estimated and enforceable dimensions.

## Scope limits and integration

No duplicate budget ledger, assumed provider pricing or strict token-ceiling claim from sampled telemetry.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
