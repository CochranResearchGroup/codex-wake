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

## Final provider-free qualification

Own followup `083ac804e79b6e7f019d3dc461a8515e4d876b99` adds trusted
`authorization_guard(operation, arguments)` to the owner and
`HistoryAuthorization(authority, root, *, host=None, environment=None,
runtime=None, now=None).execute(token, operation, arguments)`. It validates
current OAuth account targets before native source access. Exact account
identity grants are required; conversation-only grants cannot search other
rollouts. Pinned conversation/revision constraints apply to read/resume.
Remote resume requires `history.resume` plus independent operator-authored
PermissionStore delegation and the existing owner's recovery/self authority.
OAuth/delegation is rechecked before each privileged step and delivery.

Own followup `a1a2297d9a26a0b46d3a7ce00ce800d29bcbeca5` returns confirmed
attachment pane/process/time metadata after the existing resume owner observes
a current binding. Unknown/uncertain outcomes never project stale attachment
metadata as ready. Its red receipt was `KeyError: attachment` at the public
resume-result assertion; green follows the same focused command. Another red
caught missing `actor_capability` on the CLI namespace; the parser now provides
the expected absent value before invoking the existing operator-capability
verifier. Guard admission red was the absent authorization_guard constructor
keyword; green verifies a revoked caller is denied before an unusable native
source is opened.

Coordinator-owned registration/transport commits are dependencies, not worker
implementation claims: integration `07c396827e0824ff974aadd39d3ac7d2a02bde43`
and trusted runtime/clock seam `719c427d3dff3497b94ea94557051c30417a8952`.
Final acceptance checkout `/tmp/codex-wake-history396-acceptance`, branch
`test/controller-history396-installed`, tested product source
`9004208077c9b097d781597e4868ea227daed4dc` (equivalent dependencies plus the
attachment followup). Final script/test/evidence changes do not modify package
product sources. Previous worker checkouts retained their isolated state while
ownership moved; no shared integration ledger was edited.

Final focused command:
`PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p 'test_controller_history*.py'`
passes 7 tests in 3.711 seconds. Existing `test_agent_resume*.py` regression
selection passed 11 tests in 1.626 seconds. Ruff 0.14.2 and diff whitespace checks
pass. This is a focused selection, not the full suite; no retries or live/soak
runs. Native websocket connection deprecation remains an existing warning.

Installed package qualification:

1. `uv venv /tmp/codex-wake-history396-qualified-installed` and install declared
   `.[mcp]` dependencies in that isolated environment.
2. `uv build --wheel --out-dir /tmp/codex-wake-history396-final-wheel`.
3. Install that exact wheel with `uv pip install --reinstall-package codex-wake
   --python /tmp/codex-wake-history396-qualified-installed/bin/python
   /tmp/codex-wake-history396-final-wheel/codex_wake-0.22.0.dev2-py3-none-any.whl`.
4. `/tmp/codex-wake-history396-qualified-installed/bin/python
   scripts/controller_history_acceptance.py --bin-dir
   /tmp/codex-wake-history396-qualified-installed/bin` passes.

Wheel SHA256:
`fcd63b468ee9d6ffbe18beca50ce4af1373c88bbb5644cdc12151cc4102e2a0c`.
Receipt `docs/dev/evidence/plan0190/history396-installed.json` records the source,
wheel, installed module hashes and exact commands. Seven installed product
modules were byte-compared to their tested source. The executable children unset
PYTHONPATH; only test fixture code is imported from the source tree.

Acceptance exercises actual installed CLI history search/read, native-context
MCP parity and denied cross-owner reads, OAuth HTTP/API + dynamic OAuth MCP +
remote CLI history reads, and real HTTP/API + OAuth MCP + remote CLI owner resume
through the existing Unix-protocol/attachment owner. The private terminal effect
is injected into SavedRuntime; no real native TUI or provider is launched.
Resume tests preserve same-account/native UUID, existing accounting bytes and
uncertain-effect no-replay, and demonstrate OAuth revocation immediately before
new-window prevents the next terminal effect. Real-window presentation and
production provider/account authentication remain unexecuted qualification
boundaries, not an implicit unsupported fallback or permission grant.

Preserved first failures: before shared HTTP registration, installed search
returned unsupported_operation (raw `/tmp/history396-installed-first.log`). The
first full-catalog fixture omitted the account owner that production factory
supplies, hiding history tools; supplying that owner fixed the fixture rather
than broadening product authority. Final raw installed stdout/stderr remain
`/tmp/history396-installed-qualified.json` and
`/tmp/history396-installed-qualified.stderr`. No provider, credential, production
configuration/service, governor or allowance effect occurred. Manual resource
snapshot showed approximately 36.7 GiB available memory; no resource renewal.

Worker memory disposition: `not_durable`; this delegated acceptance checkpoint
awaits the coordinator's integrated closeout and is not a separate durable
project decision. The coordinator owns the final integrated memory disposition.
