# Plan 0127 — Native Codex and Wake product boundary

State: PLANNED
Workflow: APPROVED
Owner: primary agent lane
Branch: prototype/native-session-lookup

## Current State

Nine product decisions accepted in the design interview. Native A→B→A passed on Codex 0.162.0; unattended queue submission to an idle attached recipient passed on 0.162.1. These are bounded runtime proofs, not a production integration. The user approved the breakdown and validation boundary on 2026-10-09 and requested a simple governing execution plan. No ticket is implemented yet. Repository-native plans are used as requested; no remote tracker issues are created.

## Problem Statement

Users need agents to communicate, resume when conditions become true, and appear in manageable Byobu tabs. Maintaining duplicate native messaging machinery obscures Wake's distinct value and increases recovery complexity.

## Solution

Native Codex owns conversations, turns, direct messages and task status. Wake owns durable time/condition triggers, explicitly tracked exchanges, recovery visibility and visible tab lifecycle. Exact thread identity persists across tab changes. Native delivery is preferred; legacy delivery requires an explicit compatibility choice.

## User Stories

1. As a human, I want to address a visible tab so I can identify the intended agent.
2. As an agent, I want native direct messaging so ordinary exchanges need no Wake mailbox.
3. As an agent, I want a durable conditional follow-up so work continues after my turn ends.
4. As an operator, I want due work submitted without a live initiating TUI.
5. As a human, I want to open a new conversation in a chosen directory.
6. As a human, I want to resume an exact conversation in a visible tab.
7. As a human, I want existing attachments reused to avoid accidental duplicates.
8. As an operator, I want closing a tab to preserve its conversation.
9. As an operator, I want active work and pending wakes to prevent ordinary close.
10. As an operator, I want explicit force-close to report affected work without cancelling it.
11. As an agent, I want unavailable recipients held until expiry with an explicit same-thread resume option.
12. As an operator, I want uncertain submission reconciled before retry to avoid duplicate execution.
13. As an operator, I want native acceptance distinguished from completion and acknowledgment.
14. As an existing user, I want legacy records readable throughout migration and rollback.
15. As a maintainer, I want duplicate paths retired only after their replacements pass their contracts.

## Implementation Decisions

- Keep trigger evaluation, durable state and transport separate. Reuse the existing scheduler and exact-session-resolution interfaces; do not create another broker or database.
- Default direct communication to native tools. Durable workflow transport may use the qualified native CLI or app-server interface; the prototype proves one CLI candidate, not equivalence among interfaces.
- Native acceptance is not completion. Preserve pending, submitted, uncertain, acknowledged and terminal outcomes according to the retained record contract; define any required schema changes before coding.
- Resolve tab selectors once to exact thread and attachment identity; revalidate attachment identity before closing. Tab name/index is not a durable destination.
- New versus exact-thread resume is explicit. Extra attachment, force-close, legacy transport and missing-target resume are explicit choices.
- Busy or unavailable recipients hold scheduled work until expiry. Unknown state is not permission to close, dispatch or retry.
- Do not claim exactly-once delivery. Reconcile ambiguous effects and expose unresolved outcomes.

## Testing Decisions

Use the public CLI and installed scheduler as the primary behavior seam. Exercise native submission, durable outcome and visible TUI synchronization together. Existing scheduler, mailbox recovery and session-resolution behavior tests are prior art; supplement with disposable real-client runs. Test failure outcomes through externally visible state, not helper internals. Tab lifecycle uses the public session interface plus exact tmux identity. The user approved these behavior seams with the ticket breakdown.

## Keep / Simplify / Replace / Retire

| Area | Direction |
| --- | --- |
| Time/condition triggers, durable state, expiry and recovery | Keep |
| Session discovery and human tab addressing | Simplify around native metadata and exact identity |
| Ordinary agent messaging and idle wake | Native first |
| Visible tab lifecycle | Add |
| Default custom injection where native replacement is qualified | Replace, then retire per path |
| Required compatibility and existing-state readers | Preserve until their migration contracts pass |

## Scope and Out of Scope

Scope: one native durable workflow, exact new/resume/open/close tab lifecycle, recovery qualification, and staged legacy migration. No new trigger classes, general workflow engine, cross-host support, automatic worktree creation, clock redesign, OpenClaw changes, or deletion of historical state. No host reboot or disruption of shared agents is implied.

## Acceptance Criteria and Definition of Done

All child criteria pass with source/installed-version evidence; one complete lifecycle runs unassisted in disposable clients; uncertainty, expiry and close semantics agree with the accepted decisions; migration protects existing state; standards/spec review is adjudicated; roadmap/runbook and release documentation reflect what actually shipped. Plan publication does not satisfy runtime acceptance.

## Execution Contract — No Implementation Theater

This plan governs tickets 0128–0132. One owner executes the ready dependency frontier; do not start a blocked ticket or mark a dependency complete without its acceptance evidence. Default order is **0128 → 0129 → 0130 → 0131 → 0132**; 0129 is independent of 0128 and may run first if useful. No parallel agents are required.

1. Begin each ticket with exact source, worktree, installed version and relevant current policy readback. Preserve unrelated dirty work. Establish an implementation branch from the current integrated baseline; this prototype branch currently holds planning and evidence custody only.
2. Build the smallest complete user-visible behavior through the existing CLI/scheduler seams. No substitute broker, simulated product, documentation-only completion or helper-only acceptance.
3. Reproduce failures and fix them. Use focused regression checks plus actual installed-command/live-client evidence appropriate to the ticket. A mocked pass is supporting evidence, not proof of native delivery or tab lifecycle.
4. Record source commit, installed version, exact recipient/tab identities, command outcomes and durable state transitions. Keep submission acceptance distinct from execution, acknowledgment and completed workflow.
5. Record every criterion as PASS, FAIL or NOT RUN, with its evidence locator. A ticket closes only when every required criterion passes. Preserve failed samples and explain their disposition; do not redefine criteria to fit a failure.
6. On ambiguity, hold affected work and inspect native evidence. Never blindly resend, swap the recipient, silently fall back or claim exactly-once behavior. Fix an in-scope blocker; otherwise leave the ticket open with its exact missing evidence.
7. Review standards and spec independently, adjudicate findings, then commit the coherent slice and update ticket state, roadmap and runbook truthfully. Do not present a partial helper or prototype as shipped functionality.
8. Retire a legacy path only after its specific replacement and existing-state migration/recovery gates pass. No historical-state deletion, unrelated service disruption, shared-daemon restart or host reboot is implied.

Completion demonstration: **open/resume a tab → assign ordinary work natively → persist a conditional follow-up → end the originating turn → observe native execution and result → close the tab preserving its conversation**. Prove interruption, expiry and guarded close separately. Plan completion requires the actual installed product to perform this workflow and all child acceptance criteria to pass.

## Tickets and Blocking Edges

- [0128: Deliver an existing durable wake natively](0128-2026-10-09-native-durable-delivery.md) — blocked by none.
- [0129: Open and close exact Byobu tabs](0129-2026-10-09-byobu-tab-lifecycle.md) — blocked by none.
- [0130: Recover interrupted native delivery](0130-2026-10-09-native-delivery-recovery.md) — blocked by 0128.
- [0131: Prove the complete native agent lifecycle](0131-2026-10-09-native-agent-lifecycle-acceptance.md) — blocked by 0128, 0129, 0130.
- [0132: Migrate and retire redundant delivery paths](0132-2026-10-09-legacy-transport-retirement.md) — blocked by 0131.

## Further Notes

Evidence: prototype commits 3619e60 and 0445918, with scripts/prototype_native_sessions/README.md and UNATTENDED.md. Accepted interview provenance remains in the original checkout's docs/dev/notes/0011-2026-10-08-native-wake-product-boundary-interview.md. No default-branch active lane is claimed until the reviewed plan projection is integrated.
