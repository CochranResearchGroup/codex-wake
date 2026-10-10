# Plan0139 — Repair message acknowledgment and ordinary test-tab closure

State: OPEN
Workflow: IN_PROGRESS
Owner: primary
Lane: P69
Branch: fix/a2a-consumption-cleanup
Target: origin/main
Integration: squash_pr
Work-Item: docs/dev/plans/0139-2026-10-10-a2a-acknowledgment-and-tab-close-repair.md

## Approved scope

User approved2026-10-10 the ask-matt recommendation: repair notification
instructions so agents can acknowledge a received result, then repair tab-close
inspection so ordinary cleanup does not require force. Preserve Plan0138's failed
receipts and its shipped same-saved-recipient permission behavior. Root checkout
stays main. Hosted CI waiting remains waived; installed behavioral gates remain.

## Sequence and exit conditions

| Unit | Depends on | Public seam and acceptance | Bound |
| --- | --- | --- | --- |
| U1 acknowledgment instructions | none | Delivered notification gives the existing accepted-work claim step, checks claim ownership before processing, and permits completed result acknowledgment without another reply; both live and saved transports agree | One minimized red loop, evidence-backed fix, affected tests |
| U2 close inventory | U1 | Public mailbox pending-work inspection and sessions close correctly attribute normal outbox records; terminal idle owned tab closes without force; pending/uncertain/unattributable work still blocks | One minimized red loop, evidence-backed fix, affected tests |
| U3 installed verification/review/release | U1,U2 | Installed commands exercise consumption and close behavior; serial Standards/Spec review; source/release/installed parity; owned cleanup; published integration and clean checkout custody | One bounded owned live acceptance if needed; ambiguous effects never replay |

TDD at existing public mailbox, notification-delivery and sessions CLI seams.
Use external-runtime fixtures for unit regressions; never query private database
state as the passing oracle. Corrupt-state fixtures may inject an unavailable
external store but must inspect behavior through the public interface.

No weakening claims/permissions, automatic terminal ack, human-draft bypass,
manual completion of old acceptance records, unrelated service restarts, custom
Codex patch, new enrollment or wider Plan0101/0119 completion claim. No new goal
is inferred from this bounded repair authorization. Existing glossary is authority.
One owner, sequential repairs; retain red/green commands and exact installed
evidence. Unresolved verified blockers produce held state and a precise next step.

## Installed acceptance clarification

The single original notification was consumed and completed by its actual recipient,
but the transport recorded visibility as uncertain and stopped its worker. Public
reconcile reports held_for_exact_evidence; it supplies no clearing operation.
Preserve that exact original record and never resend it. Ordinary closure must
continue to hold that recipient. U2 uses one separate owned terminal-inbox control
on the same bus, without notification delivery, to prove the repaired receipt
inventory and no-force close. This control does not qualify the original uncertain
delivery. Cleanup of the original owned tab may explicitly use force after native
completion and preserving the hold receipt. No transport repair is added here.
