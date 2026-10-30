# Permitted native history and owning resume — issue 396

Authority: issue 396 under specification 393. Base integration:
`519beebc54931ada96a3f8cafb267bb407f54c14`. Isolated lane:
`feat/controller-history396`, `/tmp/codex-wake-history396`.

Scope is unified-operation/account-authority integration, reusing accepted
Profiles `history.discover` / `select_session` and Wake `AgentResume`. No login,
credential storage, history conversion, linked successor, accounting owner,
permission owner, runtime enrollment, or native attachment implementation is
reimplemented. Shared CLI/MCP/controller/remote registration belongs to the
coordinator, serialized against build and authenticated-transport workers.

## Operation contract

`ControllerHistory(config_path, *, root, host, environment,
authorized_accounts, resume_owner=None).execute(operation, arguments)` returns
the operation result payload; typed failures use `InventoryError`.

- `history.search`: optional owners array and metadata query; returns sessions,
  holds, complete/partial status. Each session keeps owner, native UUID,
  workspace, title, rollout locator, native schema/namespace/source provenance,
  and target. Duplicate native IDs remain separate by owner.
- `history.read`: exact owner/native UUID and optional pinned expected target;
  returns session and native JSONL records unchanged, with provenance.
- `history.resume`: exact owner/native UUID, required pinned expected target,
  stable intent and fixed expires_at; returns session plus the existing resume
  owner's status/correlation, preserving conversation ownership and accounting.

Targets extend the account owner's target with `conversation_id` and
`rollout_revision` (SHA256 of the exact native source). Scope is admitted before
native discovery/read. Host `[history].readable_accounts` intersects trusted
adapter `authorized_accounts`; these are not client-controlled operation fields.
Absent scope never implicitly discovers all accounts. History search is metadata
search over title/UUID/workspace, not transcript semantic search. Native schema 5
is supported by the absorbed discovery owner. Unsupported schemas, compressed
or non-JSONL source, unavailable native lineage, over-8-MiB rollout reads and
cross-namespace paths are held rather than converted or silently substituted.

Resume requires `[history].resume_enabled=true`, an explicit host binding, a
trusted principal, existing enrollment, existing recovery/self permission and
qualified exact backend/account/workspace identity. Example binding:

```toml
[history]
readable_accounts = ["alice", "bob"]
resume_enabled = true
[history.callers]
"exact-native-caller-UUID" = ["alice"]
[history.bindings."exact-saved-thread-UUID"]
account = "codex-alice"
managed_agent_id = "existing-enrolled-managed-ID"
profile = "existing-saved-profile"
profiles = "/private/host-resume-profiles.json"
```

`ManagedHistoryResume(root, principal, *, runtime=None, now=None)` delegates to
`AgentResume`, preserving its durable intent/effect receipt and no-replay fences.
Before every privileged step the adapter rechecks source binding, current host
read scope, private resume profiles and native server `codexHome`/thread/workspace;
the existing owner rechecks its permission store and expiry. Missing qualified
bindings return unsupported before effect. Native goal/accounting continuity is
not inferred from history: no successor is created, no goal is copied, no work
is submitted and no allowance/deadline is renewed. Strict-executor recovery
retains the existing unsupported gate. Lost attachment responses remain uncertain
until existing positive binding reconciliation, never blindly replayed.

CLI adapter `history_commands.register_parser`, `command(args, root)`; CLI resume
requires existing operator bus capability through `verified_cli_principal`.
MCP `tool_specs()` and `mcp_call(runner, arguments, native_context, verb)` require
verified native context plus exact host caller account scope; resume additionally
uses the existing session/controller principal and permission authority. Remote
integration must inject authenticated exact account scope before discovery and
an independently authorized principal for resume. Read tokens alone must never
authorize resume. Remote account target policies must include conversation ID
and rollout revision when pinned; mere result filtering after native read is
insufficient for input scope admission.

## Validation state

Core public red/green receipts, repository `.venv` Python and `PYTHONPATH=src`:
`python -m unittest discover -s tests -p test_controller_history.py`.
First red: missing ControllerHistory module; green cross-account read/search.
Second red: missing ManagedHistoryResume adapter; green real Unix appserver
protocol and injected attachment boundary, same-owner resume and replay with
one attachment effect. An initial fixture used a different native UUID than the
existing protocol fixture; that binding failed stale, corrected to the fixture's
actual UUID. Four focused tests currently pass, including unauthorized owner,
stale rollout, unsupported compression, caller injection and standalone CLI/MCP
adapter parity. Native `connect()` emits the existing websocket deprecation
warning; this lane does not alter the protocol owner.

Installed full CLI/MCP and protected remote acceptance remain pending until the
coordinator adds reserved shared registration. This worker checkpoint does not
claim issue completion or production activation. All test state is disposable;
no provider calls, real credentials, service activation/restart, resource renewal,
or governor activation is authorized.
