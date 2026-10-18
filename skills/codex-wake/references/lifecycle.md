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
