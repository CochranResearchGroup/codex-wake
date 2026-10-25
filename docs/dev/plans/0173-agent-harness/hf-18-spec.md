# HF-18 exact saved-agent resume specification

State: IMPLEMENTED_SOURCE; shared CLI/MCP integration and combined review pending
Work item: #338 / CW-HARNESS-173/HF-18
Authority: operator questionnaire response d9b59f368e984dff925597304f90e901,
all recommended answers approved; primary implementation delegation 2026-10-24.
Base: 012f173; common `resume.recover` catalog prerequisite 0f92c3f.

## Frozen outcome and ownership

Resume the last confirmed exact managed conversation using one explicit named
host-approved profile under current common permission. Keep the original managed
ID only after fresh binding qualification and inventory reconciliation. Optional
older history selection uses an exact record fingerprint. No credential copying,
account attestation, thread/start, fresh-conversation fallback, provider turn,
pending-work replay, allowance renewal or ledger migration is included.

Leaf owner: agent_resume.py, agent_resume_commands.py, their tests and
agent-resume.md. Primary owns shared CLI/MCP registration, glossary and catalog.

## Decisions

- Reuse native namespace/conversation/root identity, private inventory, the
  existing terminal command boundary, current process evidence, common
  permissions and authenticated bus/native callers.
- Persist intent before effects and serialize both intent and managed-agent
  custody. Lost responses fence another intent and require same-intent exact
  observation. A completed launch is distinct from a qualified binding.
- Check policy at admission and immediately before each terminal command;
  re-read private profiles to detect revocation/change. Suppression stays binding.
- Self uses resume.self. Non-self recovery requires real operator/controller
  identity, existing exact host delegation and common resume.recover approval.
  No invented self principal or independent approval registry.
- Same-home/provider history access can qualify identity across an account
  change; it does not prove which account is active. A namespace change holds.
- Reconciliation updates only inventory/binding and resume receipts. Pending
  effects and resource ledgers remain unchanged. Loading a conversation does
  not authorize continuing stopped or uncertain work.
- Unsupported Grok/strict-executor recovery holds rather than claiming parity.

## Acceptance seams and limits

CLI parser/handler and native-authenticated MCP handler enter the same owner.
Real local Unix protocol fixtures exercise saved metadata reads; private process
fixtures exercise attachment readiness and fixed launch arguments. Include
idempotence, reconstruction, response loss, missing history, namespace change,
stale attachment, suppression, forged native caller, real operator capability,
self/operator pre-effect revocation, and byte-preserved ledger/pending records.

Shared executable registration is primary integration work. Provider/native TUI
canaries and installation are outside this slice. Source qualification cannot
claim either.
