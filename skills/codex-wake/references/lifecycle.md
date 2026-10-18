# Agent lifecycle requests

When the request includes token, time, memory, CPU, swap or task limits, read
[resource-limit enforcement](resource-limits.md) first. The templates below do
not opt a legacy profile into containment or bootstrap an ordinary caller.

Use the same operation choice through MCP. These are argument templates, not
requests to execute; replace placeholders with your actual identity, approved
profile, checkpoint hash and expiry. Host registry and wake-root paths are
configured on the MCP server, never supplied by an agent.

`wake_sessions_configuration`:

```json
{
  "caller_thread_id": "SOURCE_THREAD_UUID",
  "thread_id": "SOURCE_THREAD_UUID",
  "profile": "worker"
}
```

`wake_sessions_spawn`:

```json
{
  "caller_thread_id": "SOURCE_THREAD_UUID",
  "profile": "worker",
  "intent": "task-001",
  "name": "worker",
  "task": "Inspect the agreed fixture and return the result.",
  "expires_at": "FIXED_FUTURE_ISO8601"
}
```

`wake_sessions_refresh`:

```json
{
  "caller_thread_id": "SOURCE_THREAD_UUID",
  "thread_id": "SOURCE_THREAD_UUID",
  "profile": "worker",
  "intent": "refresh-001",
  "checkpoint": "checkpoints/source.json",
  "checkpoint_sha256": "CHECKPOINT_SHA256",
  "expires_at": "FIXED_FUTURE_ISO8601",
  "resources": [
    "APPROVED_RESOURCE_NAME"
  ]
}
```

`wake_sessions_handoff`:

```json
{
  "caller_thread_id": "SOURCE_THREAD_UUID",
  "thread_id": "SOURCE_THREAD_UUID",
  "profile": "worker",
  "intent": "handoff-001",
  "checkpoint": "checkpoints/source.json",
  "checkpoint_sha256": "CHECKPOINT_SHA256",
  "expires_at": "FIXED_FUTURE_ISO8601",
  "mode": "new-tab"
}
```

Read effective configuration first. Use the selected full writer/reviewer
instructions and preserve its revision, remaining allowance and original
deadline. Spawn assigns a separate worker; refresh reloads approved resources in
the same conversation; handoff moves the objective to fresh context in a new tab
or the same pane. A visible ready client is separate from work acceptance.

For refresh, write a workspace-contained JSON checkpoint with source_thread_id,
objective, authority, next_packet and an empty pending_obligations list; compute
its exact SHA256. For handoff, also preserve repo/worktree/commit, dirty_work,
acceptance_remaining, evidence, hard_stops, reply_route, fixed expires_at and
host-matching resources. pending_wakes, pending_messages and claim_holders must be
empty. Use the selected checkpoint writer instructions for the complete packet;
the host independently checks pending work and native authorship.

Retain the receipt and reconcile the original intent with identical arguments
when held or uncertain. Keep the owned target untouched during the transition.
Prepared handoffs can remain paused until the approved resident monitor activates
the original remaining allowance. Readiness does not accept outgoing work.
Refresh, handoff and rollback preserve spending and deadlines; only explicit
operator authorization can extend the budget. Missing profiles, grants or
instructions require operator setup; an agent cannot invent replacements.

## Shared MCP refresh

A host profile with `refresh_mode: "shared_mcp_idle"` uses the existing refresh
request above. First inspect `wake_sessions_configuration` for its exact scope,
resource names and package version. This profile permits configuration/refresh,
without creating an objective budget or granting spawn/handoff. Missing setup,
caller grant, scope approval or independent monitor refuses admission.

`queued` is a successful admission, not completed refresh. Preserve the receipt
and end the active turn; the monitor waits for all loaded conversations to be
observed idle. Reconcile the same intent and identical arguments. Reload intent
is durable before the one native effect. A lost response does not cause a second
reload: read-only goal and resource proof reconcile it. `verifying`, `uncertain`,
`blocked` and `expired` do not establish completion. The caller's fixed expiry
never renews any resource allowance. Expiry or unknown ownership prevents effects.

This mode reconnects MCP servers for every loaded conversation on that native
server. It keeps existing TUI clients, conversation IDs and goal authority;
all observed counters must remain nondecreasing. Native Codex currently provides
no thread-only reload and no atomic idle compare-and-swap. A racing start after
the final idle observation remains a limitation. The host must approve shared
scope; agents cannot silently select it as a fallback from client-only refresh.

Host setup uses private owned registry/journal paths and an independent managed
process, separate from the goal-limit enforcer:

```sh
install -d -m 700 PRIVATE_LIFECYCLE_ROOT
codex-wake --wake-root PRIVATE_LIFECYCLE_ROOT sessions refresh-watch --interval 1
codex-wake-mcp --lifecycle-root PRIVATE_LIFECYCLE_ROOT --lifecycle-profiles PRIVATE_REGISTRY
```

`--lifecycle-root` leaves other wake tools on their existing root. Legacy profiles
still use the guarded client-replacement flow. A shared profile contains exactly
`refresh_mode`, `scope_approval` (explicit user authorization provenance), `cwd`,
`app_server` (physical owned Unix socket), `codex_path`, `timeout` (up to five
seconds), and `resources`. The registry remains version1 with exact caller/profile
grants. Skill checks use the existing exact path/description/SHA256 fields; MCP
checks use the existing host-approved read-only tool/arguments/expected_content.
A fresh process alone does not prove readiness. Use a stable read-only behavior
probe; `wake_sessions_configuration` on this profile returns static scope/version/
resource names without recursively returning its proof definitions. Operator
provisioning can capture that response as the expected MCP content before reload.

Initial deployment to a client whose cached MCP lacks host scope requires an
operator bootstrap with the identical approved registry/checkpoint and caller.
That is a deployment action, not an agent permission to bypass missing grants.
After the shared reload, the public MCP can admit later self-refresh requests.
