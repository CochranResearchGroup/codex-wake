# MR-04: Exchange correlated work between Codex and Grok

State: CLOSED
Ticket state: DONE
Owner: ecochran76
Work item: CW-MR-172/MR-04 (local draft; not posted)
Priority: First-release dependency order
Blocked by: MR-03 satisfied
Specification: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md)

Lane: P172-MR04
Branch: feat/mr04-cross-runtime-a2a
Base: 36412c4
Target: origin/main
Integration: squash_pr

## Outcome

An enrolled Codex sender assigns scoped work to an enrolled Grok recipient and receives a correlated reply; the reverse direction works with independent authority.

## Scope

Reuse mailbox records, work claims and correlation through the runtime delivery seam. Establish and verify each caller/recipient binding without assuming CODEX_THREAD_ID or Codex metadata for Grok.

## Non-goals

Do not transfer another actor's grant, treat UI observation as a work receipt, grant new production scope or implement cross-host messaging.

## Acceptance Evidence

- [x] AC2: both directions prove exact recipient authentication, claim-before-work and correlated replies.
- [x] AC5: duplicate notifications, restart, stale generation and uncertain delivery do not create duplicate work.
- [x] AC6: current Codex mailbox actor keys and caller/receipt controls retain their meaning.
- [x] AC7: unavailable runtime attestation is explicit; a claimed caller ID does not bypass grants.
- [x] Demonstrate terminal-observed delivery can later gain a genuine authenticated work receipt without fabricating one.

## Repository Surface and Risks

Mailbox enrollment/caller admission, notification binding and scheduler, claim/reply CLI/MCP and recipient receipts.

Shares journal/identity writes with MR-05; serialize integration. Receiving a notification must not automatically charge or renew another objective's allocation.

A complete slice requires its stated evidence. Source completion, integration,
installed acceptance and external publication remain separate states.


## Reconciled acceptance

Primary coordinator sourceef8b5b4 qualifies this slice for source and isolated
artifact: frozen1451 tests PASS341.346s/one expected skip, unchanged source/tests,
final installed changed-axis15 PASS5.140s and lint PASS. Independent source packet
is retained, with shared CLI/MCP and authority corrections owned by the primary.
No packet ref alone is a merge-ready claim. MR-06 is READY for real visible TUI and
bidirectional live acceptance; native Grok caller attestation remains unqualified.
Production installation, main integration and release remain separate.
