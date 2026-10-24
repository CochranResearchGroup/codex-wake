# HF-13: Specify wake lifetime, ownership and reboot recovery

State: READY_FOR_AGENT
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-13 (published as #317)
Priority: P0
Area: Durability and jobs
Blocked by: None; HF-01 design resolved
Grill state: PRODUCT_DECISIONS_RESOLVED; technical handoff pending; apply [HF-01 decisions](hf-01-decisions-and-handoffs.md)
Implementation state: READY_FOR_AGENT; source scope and handoff approved; no live effects
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Declare which owner lifecycles/restarts a wake must survive while preserving the existing durable-intent contract.

## Repository surface and reuse

records.py; native_intents.py; runtime_wakes.py; supervisor/monitor readiness; state-lifecycle docs.
Existing wakes are already persisted; this ticket adds explicit policy/ownership, not a second durable wake store.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which lifetimes are needed and what does owner completion/cancellation mean?
- Where is persistent task-owned state stored independently of disposable worktrees?

## Acceptance evidence

- [ ] Existing durable records retain their behavior; new lifetime/owner selections have explicit retirement rules.
- [ ] Controller/process/reboot discontinuities preserve original origin, expiry and uncertain-attempt state.
- [ ] An isolated restart/epoch-change matrix distinguishes record persistence, monitor readiness and delivery; live reboot proof is a separate authorized gate.

## Scope limits and integration

No changed default cancellation, delay rebasing, automatic uncertain replay or new recurrence engine.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.

## 2026-10-24 interview update

See [first-frontier decisions and overlap boundaries](first-frontier-decisions.md).

Resolved defaults: configurable owner-end behavior defaults to retirement after
verified explicit completion; configurable startup defaults to create/load/run
for new wakes. Existing wakes retain their behavior. See the interview record.

## Proposed build specification

See [bounded spec](hf-13-spec.md) and the [three-ticket review](first-frontier-spec-review.md).
Spec state: APPROVED; public caller seam and ticket breakdown approved.

Canonical tracker: https://github.com/CochranResearchGroup/codex-wake/issues/317
