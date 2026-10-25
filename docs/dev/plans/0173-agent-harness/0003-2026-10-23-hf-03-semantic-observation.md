# HF-03: Observe and wait for meaningful agent states

State: CLOSED
Owner: ecochran76; primary integration coordinator
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/330
Priority: P0
Area: Identity and observation
Blocked by: HF-02
Grill state: RESOLVED; bounded implementation decisions recorded in feature spec
Implementation state: SOURCE_VALIDATED; one review and bounded remediation complete
Source baseline: 37a5cbb / v0.21.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Wait for a named agent transition with fresh evidence and a bounded timeout.

## Repository surface and reuse

runtime_delivery.py; codex_runtime.py; grok_runtime.py; sessions/watch; source-health projections.
Extend existing runtime, durable-state and authority mechanisms; do not infer that an existing capability must be rewritten.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which states can each runtime actually prove, and which are inferred observations?
- What freshness and timeout policy applies?

## Acceptance evidence

- [x] Report working, ready, awaiting-human, auth-required, disconnected and unknown only at their supported evidence levels.
- [x] A bounded wait ends on the requested transition or an explicit timeout/unknown result.
- [x] Missing output, stale frames and partial inventory never become idle or completed.

## Scope limits and integration

No generic screenshot-based certainty, automatic recovery, output-silence dormancy rule or hidden reasoning inspection.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.

## Closure

Source validated on feat/harness-observation-ownership; final runtime correction
at0b18828. See hf-03-04-execution-ledger.md and feature spec for acceptance,
review and validation limits. Main merge, release and deployment remain separate.
