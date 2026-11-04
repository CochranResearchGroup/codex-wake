# #476 Grok local session control

State: IMPLEMENTING; accountable owner: ecochran76; worker: self_limits_468.
Parent: Plan0200 and GitHub #466; work item: #476; dependency #475 closed.
Base: f4f77a2546e22525040db8b08debea12c3aaca8c.
Branch: feat/476-grok-local-control.

Deliver Grok through the existing local.* operation registry and CLI verbs.
Add the agreed local.create convenience verb for Grok only: validate one existing
owned profile and reuse grok.create, with a retained creation idempotency key.
Codex creation remains explicitly unsupported. No hand-written target/grant JSON
is required for ordinary headless Grok startup.
The supported mode is a sole-owned headless ACP session, explicitly distinct
from arbitrary existing TUI control. Preserve the default Codex behavior.

Primary owns shared CLI/service/MCP wiring, generated contracts and lane catalog.
This worker owns the Grok adapter, focused tests and Grok documentation. Reuse
ControllerGrok, GrokACPConnection, grok_stdio_host and ControllerRuntime; introduce
no second journal or terminal input fallback. Select with harness=grok, explicit
profile and grok:SESSION selector, then pin the exact provider/process/build/home/
agent-instance identity. Retained operation IDs route by original custody.

## Vertical slices and seams

1. Public discovery/resolve: real ACP boundary fixture proves owned-session
   selection and generation refusal; installed native proof remains separate.
2. Public prompt/result/output: existing journal proves original-result retention,
   idempotency and no replay after uncertain transport; fixtures do not prove auth.
3. Public health and slash capabilities: advertise only negotiated and qualified
   native semantics, with explicit unsupported exact TUI health/cancel/metering.
4. Supported command execution and a controller interaction, only after native
   protocol evidence identifies a safe semantic action; never slash prompt text.

Use feature TDD one slice at a time. Local focused Python3.11/3.12 checks replace
hosted CI. Final broad review/remediation remains with primary and unused.

## Native qualification gates

Exact installed binary is grok1.0.70, SHA256
22d281c5964c5444147328096ba2a221f3f0874c6858e27c825656a80f6e58e9.
Fresh initialize/session-list receipt is private under
~/.local/state/codex-wake/testing/plan0200/grok476/native-readiness.json.
It proves ACPv1 metadata and zero sessions in the owned workspace, not successful
authentication, model execution, native command execution or TUI ownership.

No model turns are authorized in this first gate. Primary must reserve at most
two marker-only provider intents before provider qualification. Do not copy or
read provider credentials, authenticate a new account, change working daemons,
or adopt unrelated conversations. Preserve exact launch/process generations,
source/wheel/install identity, failed attempts and cleanup census. Installed
native acceptance must distinguish genuine Grok responses from protocol fixtures.

Memory disposition: forbidden; this task prohibits memory writes.


## Installed bootstrap repair

Exact installed86d4780 wheel exposed native create completed followed by empty
same-owner discovery. Preserve private failed receipt installed-db986d5a; it
consumed one additional native fixture, cumulative2, zero provider intents.
Repair creates then activates through stable existing grok.load custody; persist
both IDs before activation I/O. Expose created_not_ready without relabeling native
creation, cache successful readiness, and reconcile uncertain activation with
read-only native list only. Primary separately opens replacement fixture ceiling3
once repaired source and exact installation are qualified. Provider packet closed.
