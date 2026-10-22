# MR-04: Exchange correlated work between Codex and Grok

State: PLANNED
Owner: ecochran76
Work item: CW-MR-172/MR-04 (local draft; not posted)
Priority: First-release dependency order
Blocked by: MR-03
Specification: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md)

## Outcome

An enrolled Codex sender assigns scoped work to an enrolled Grok recipient and receives a correlated reply; the reverse direction works with independent authority.

## Scope

Reuse mailbox records, work claims and correlation through the runtime delivery seam. Establish and verify each caller/recipient binding without assuming CODEX_THREAD_ID or Codex metadata for Grok.

## Non-goals

Do not transfer another actor's grant, treat UI observation as a work receipt, grant new production scope or implement cross-host messaging.

## Acceptance Evidence

- [ ] AC2: both directions prove exact recipient authentication, claim-before-work and correlated replies.
- [ ] AC5: duplicate notifications, restart, stale generation and uncertain delivery do not create duplicate work.
- [ ] AC6: current Codex mailbox actor keys and caller/receipt controls retain their meaning.
- [ ] AC7: unavailable runtime attestation is explicit; a claimed caller ID does not bypass grants.
- [ ] Demonstrate terminal-observed delivery can later gain a genuine authenticated work receipt without fabricating one.

## Repository Surface and Risks

Mailbox enrollment/caller admission, notification binding and scheduler, claim/reply CLI/MCP and recipient receipts.

Shares journal/identity writes with MR-05; serialize integration. Receiving a notification must not automatically charge or renew another objective's allocation.

A complete slice requires its stated evidence. Source completion, integration,
installed acceptance and external publication remain separate states.
