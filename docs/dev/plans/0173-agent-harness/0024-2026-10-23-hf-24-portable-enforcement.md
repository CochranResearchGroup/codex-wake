# HF-24: Enforce one qualified allowance through continuation and recovery

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-24 (local draft; not posted)
Priority: P2
Area: Resources
Blocked by: HF-18, HF-23
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Extend existing qualified controls to the managed workflow scope without replenishing allowance on resume or handoff.

## Repository surface and reuse

Existing strict-objective/cgroup and goal supervision; host policy; launch/continuation admission.
Reuse #270/strict-objective work; current shipped enforcement is a baseline, not a new missing feature.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- What can be enforced versus sampled on each runtime/host?
- Which remaining #270/#282 delivery or host-wiring gates apply?

## Acceptance evidence

- [ ] The chosen supported runtime stops/holds within its documented bound and preserves consumption.
- [ ] Controller/accounting loss and reboot follow an explicit conservative policy without adopting unrelated processes.
- [ ] Unsupported resource guarantees refuse or require an explicitly selected weaker mode.

## Scope limits and integration

No replacement enforcement framework, generalized live-session termination or unqualified Grok hard-stop promise.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
