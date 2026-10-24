# HF-02 specification: Managed inventory and configurable enrollment

State: APPROVED_SPEC
Owner: ecochran76
Decision authority: HF-01 and first-frontier interview records, including direct
2026-10-24 follow-up. Source baseline: origin/main f96f4c8; planning branch
4dfdc39. This spec describes proposed behavior, not implemented capability.
Public caller seams and the three-ticket breakdown were approved by the operator.

## Problem Statement

Sessions can already be discovered and qualified through runtime-specific paths,
but discovery, durable management identity and enrollment policy are not one
operator-facing contract. Tab labels and process identities change; they cannot
serve as the durable conversation identity. Manual per-thread enrollment would
contradict the operator's preferred default.

## Solution

Provide a durable management record for one verified native conversation.
Enrollment is configurable, defaulting to verified self-enrollment with explicit
operator unenrollment. Preserve identity across attachment/process changes and
expose unavailable or ambiguous bindings honestly.

## User Stories

1. As an operator, I want to inspect all deliberately managed conversations through one durable inventory, so that I can track conversation continuity without confusing it with tab location or permission.
2. As an operator, I want to allow verified sessions to self-enroll under the selected enrollment policy, so that I can track conversation continuity without confusing it with tab location or permission.
3. As an operator, I want to choose self-enrollment, operator-only enrollment or operator-selected adoption, so that I can track conversation continuity without confusing it with tab location or permission.
4. As an operator, I want to unenroll a conversation explicitly without automatic enrollment undoing that decision, so that I can track conversation continuity without confusing it with tab location or permission.
5. As an operator, I want to keep the same managed identity when its tab moves or its exact conversation resumes, so that I can track conversation continuity without confusing it with tab location or permission.
6. As an operator, I want to inspect an unavailable conversation without losing its history, so that I can track conversation continuity without confusing it with tab location or permission.
7. As an operator, I want to distinguish a successor conversation from the original while linking its task and allocation, so that I can track conversation continuity without confusing it with tab location or permission.
8. As an operator, I want to see runtime capabilities without treating inventory membership as an operation grant, so that I can track conversation continuity without confusing it with tab location or permission.
9. As an operator, I want to refuse spoofed conversation identity and ambiguous process bindings, so that I can track conversation continuity without confusing it with tab location or permission.
10. As an operator, I want to read the same inventory and policy outcome through CLI and MCP, so that I can track conversation continuity without confusing it with tab location or permission.

## Implementation Decisions

- A small inventory owner exposes enroll, inspect/list, reconcile-binding,
  unenroll and operator re-enable behaviors behind one policy boundary. These
  are logical operations; exact command spelling is not frozen by this spec.
- Store versioned private inventory state under the configured durable Wake root,
  independent of disposable worktrees. Use the existing private-file, lock and
  atomic-replace conventions; do not create another daemon or database service.
- Each record binds an opaque managed-agent identifier to runtime and verified
  native conversation namespace/identity. Keep current process generation,
  attachment evidence, observed source/freshness and profile references separate.
- Serialize enrollment/rebinding per native identity. Repeated enrollment returns
  the existing identity. A crash/retry cannot create competing management records.
- Operator unenrollment persists suppression for the exact conversation. Automatic
  enrollment cannot override it; only explicit operator re-enable clears it.
  Changing a default policy or restarting a controller does not clear suppression.
- Unavailable/ambiguous observations retain identity/history and cannot authorize
  input. A verified new process for the same conversation may rebind; a different
  conversation is a successor with a separate managed ID and explicit linkage.
- Membership does not mint lifecycle permissions, budget or mailbox claims.
  Consume trusted caller evidence and host delegation already owned by session
  policy; the independently owned #310 repair governs default own-session access.
- Use exact caller/process binding appropriate to each runtime. Codex native
  evidence and Grok host-bound evidence keep their distinct provenance. Unsupported
  runtime evidence produces an actionable unqualified result rather than a
  guessed enrollment.
- CLI and MCP route through the same inventory owner. Read projections contain
  capability and binding state, not credentials or private host endpoints.
- Version the new inventory record independently; unknown versions hold. Existing
  wake, mailbox and objective-ledger schemas retain their meaning. Inventory is
  new metadata, not a migration that rewrites all existing sessions.

## Testing Decisions

Use the public CLI/MCP handler boundary with disposable roots and injected native
and host-bound runtime evidence. Cover idempotent concurrent enrollment, controller
reconstruction, tab move, exact-conversation new-process rebind, successor identity,
operator-only policy, explicit suppression/re-enable, forged caller, partial
inventory and stale observations. Assert identical policy outcomes through both
callers. Existing session discovery and mailbox identity tests are prior art;
assert externally visible records/results, not private helper calls. No real
provider session or operator tab is required.

## Out of Scope

No new conversation launch, generic plugin SDK, lifecycle policy repair, cross-host
fleet inventory, credential migration or automatic adoption by matching tab text.
The #310 overlap is an integration dependency for shared caller-policy changes,
not a reason to block an isolated inventory leaf indefinitely.

## Further Notes

[Resolved interview](first-frontier-decisions.md) and [shared decisions](hf-01-decisions-and-handoffs.md) own product provenance. This document proposes the bounded build contract. The parent backlog owns wider sequencing. Public caller seams and ticket granularity were approved by the operator.

Canonical implementation work item: [#315](https://github.com/CochranResearchGroup/codex-wake/issues/315).
