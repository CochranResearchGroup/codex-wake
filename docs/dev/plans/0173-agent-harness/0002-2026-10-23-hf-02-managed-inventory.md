# HF-02: Enroll one existing agent into a unified managed inventory

State: TRIAGE
Owner: ecochran76; implementation assignee unassigned
Work item: CW-HARNESS-173/HF-02 (local draft; not posted)
Priority: P0
Area: Identity and observation
Blocked by: HF-01
Grill state: TRIAGE; read prerequisite decisions before freezing design
Implementation state: NOT_AUTHORIZED; own grill-with-docs and approved handoff required
Source baseline: 7ef73b12dde59cedbd98b5b73ac5250106ee63aa / v0.20.0
Parent: [Plan0173](../0173-2026-10-23-agent-harness-backlog.md)

## Outcome

Adopt one already-running Codex or qualified Grok TUI and inspect it using a stable logical record that survives controller restart.

## Repository surface and reuse

sessions.py; tab_targets.py; runtime_delivery.py; runtime_a2a.py; CLI/MCP read projections.
Reuse current session discovery, managed Grok bindings and native identity checks; inventory alone is not a grant.

## Grill-with-docs gate

Start with Matt’s grill-with-docs: read AGENTS.md, GLOSSARY.md, relevant ADRs/docs and current code/tests. Retrieve factual answers from the repository; ask the operator product/tradeoff questions. Return resolved design, required glossary/docs changes, evidence and a bounded implementation handoff before coding. Use Previews for more than a few questions. Completion of a prerequisite does not waive this ticket’s own interview. Missing native capability stays unsupported/unqualified.

Open decisions:

- Which existing unmanaged sessions may be adopted, and who can authorize adoption?
- How are stale logical records retired or rebound?

## Acceptance evidence

- [ ] A deliberate enrollment links exact native conversation, process generation, attachment, repo/worktree and profile evidence.
- [ ] Restarting the controller preserves the logical record; stale, ambiguous and unavailable bindings remain distinguishable.
- [ ] Codex and managed Grok appear through one capability-aware inventory without granting new authority.

## Scope limits and integration

No new conversation creation, credential discovery, screen-text attestation or automatic adoption of unrelated terminals.

This draft grants no live provider input, production/account/service change or manipulation of existing operator tabs. Begin with provider-free evidence at the real caller seam; record any later canary authority separately. Preserve exact identity/grants, original intent/deadline and uncertain-effect reconciliation. Shared CLI/MCP/schema/profile edits retain one integration owner; see the parent collision map.
