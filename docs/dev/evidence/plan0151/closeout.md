# Plan0151 closeout — Discoverable agent exchanges

Source PR241: 95f621d883e71021b009dfe56e939330aa6d561f.
Feature checkpoint: 8940ebfedae68163288d195e2e093c28a02d378a.
Public release: https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.13.0.
Issue240 terminal documentation follows this qualified source; existing A2A
acceptance remains complete independently. Plan0151 uses P75: its initial P73
label collided with the preserved historical Plan0146 lane.

## Delivered

README and bundled/installed agent skill advertise tracked requests, exclusive
processing claims, correlated replies and suspended reply wakes. Public guides
explain operator setup, direct human tab selectors, exact session identity,
receipt meanings, CLI workflow and MCP installation/tool contracts.
The optional official-SDK stdio server exposes 14 fixed tools over the same
installed CLI. No new store, dispatcher, worker or mailbox schema is introduced.
Unknown arguments are rejected; bounded timeouts preserve uncertainty and original
intent without retry. Capability, roots and runtime endpoint remain host-selected.

Each message/current call supplies its actual native-shell thread claim. Existing
runtime/root/fixed-capability checks enforce it; this is not caller attestation.
No per-tool credential or root override exists. The private shared-connection
child claim is refused using the parent's capability. Current host MCP startup
lacks CODEX_THREAD_ID; the upstream context limitation is documented at
https://github.com/openai/codex/issues/19937. Agents must not substitute a peer's
identity to bypass refusal.

## Qualification

- 27 focused MCP/mailbox/claim tests PASS (5.636 seconds); 13 message/actor CLI
  regression tests PASS (3.206 seconds). SDK2.2.0, jsonschema4.26.
- Actual installed stdio discovery and private request/read/claim/reply/reconcile
  PASS in 5.643 seconds. Dedup, accepted/completed receipts, repeated claim
  refusal, wrong capability and shared-connection child refusal verified.
  Zero notifications/native turns; private roots removed; zero remaining children.
- All 83 packaged files match source, wheel and immutable installed prefix
  /home/ecochran76/.local/share/codex-wake/releases/0.13.0-95f621d.
- Downloaded wheel SHA256 a3d1f103c59315b3706fb95c977c13d9efb969c883a2fd66f66651f4f57b2388;
  sdist SHA256 05d73f8d2eb3bf8d00cd4841b69ca7fd2d07545a935aaea3bf1c60a7c1be2830.
  Remote peeled v0.13.0 tag matches source95f621d.
- User-scope codex-wake registration enabled, five command links qualified at
  0.13.0. Fresh actual stdio SDK client using that registered command discovers
  all 14 tools and resolves the exact existing session.
- Two installed skill copies match bundled source; both previous copies retained
  privately. All 13 service PID/state snapshots unchanged; no restart performed.
- Policy wiring and active planning audit checked at terminal documentation;
  hosted CI waiting waived by the operator. No hosted PASS is claimed.

## Limits and retained failures

Fresh SDK discovery does not prove this already-running Codex session reloaded
its tool catalog. Start a new session and verify tool discovery before relying on
MCP. Global registration contains environment variable names, not an actor's
capability; messaging requires explicit operator enrollment/private launch context.

Live exact thread resolution succeeds. The current-session identity call rejects
an inherited-pane conflict (code6), as the unchanged CLI requires. This is retained
as a refusal, not relabeled success or bypassed. The installed private exchange
proves working identity and facade semantics; previously accepted native A2A
receipts prove live delivery independently. No new production exchange was sent.

Initial missing-entrypoint red test, SDK attribute and smoke projection harness
corrections, metadata mutation annotation correction and live current-identity
refusal remain recorded. Raw logs live in the private Plan0151 state directory;
no blind effect retries, duplicate wakes or production recovery occurred.

## Activation and rollback

Activation receipt retains exact previous four command link targets; remove only
the new owned MCP registration/link and restore recorded links and skill copies
for rollback. Previous 0.12.0 installed prefix remains available. No service
configuration, enrollment, worker, process authority, other session, Byobu tab or
retained plan127 worktree changed. Credentials/bodies are absent from public
receipts. No operator setup was applied to a production bus.

Terminal documentation reconciles Plan0151, ROADMAP, RUNBOOK and lane P75.
Final integration returns the root checkout to clean main; issue240 closes through
the terminal PR. Gov_policy evaluation remains parked for future engineering.
Memory disposition: unavailable — no reviewed Codex Wake Graphiti group is
configured; machine-readable non-write receipt records zero Graphiti writes.
