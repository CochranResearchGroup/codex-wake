# Agent lifecycle

`sessions spawn` creates a worker conversation, attaches one visible tab and
admits a bounded initial assignment only after its exact client is ready. Use
`sessions open` for attachment without task delivery. Tab creation, task
admission and completed execution have separate receipt evidence.

The operator supplies a host launch registry, an existing approved workspace,
an existing owned app-server socket and tmux session. The workspace must already
be trusted in the selected Codex home. Example registry:

```json
{
  "version": 1,
  "callers": {"00000000-0000-7000-8000-000000000011": ["worker"]},
  "profiles": {
    "worker": {
      "cwd": "/approved/workspace",
      "codex_path": "/installed/codex",
      "codex_home": "/approved/codex-home",
      "app_server": "unix:///owned/app-server.sock",
      "tmux_session": "approved",
      "tmux_socket": "/owned/tmux.sock",
      "timeout": 10
    }
  }
}
```

`codex_home` and `tmux_socket` are optional; the other profile fields are required.
Keep the registry and journal private and operator-controlled. The host grants
each MCP caller only the profiles it may select. `caller_thread_id` is a claim,
not an attestation or permission grant. Obtain it from your native shell; never
substitute a peer's ID. Spawn does not enroll the worker in A2A or copy the
parent's mailbox capability, bus selection, receipt authority or thread identity.

```bash
codex-wake --wake-root /owned/wake sessions spawn \
  --profiles /host/launch-profiles.json --profile worker \
  --intent task-001 --name worker --expires-at 2026-10-12T18:00:00Z \
  --task 'Inspect the agreed fixture and return the result.' --json
```

Choose a future fixed timezone-aware expiry under the approved allowance.
Admissible UTC is required before effects; guest wall time is not substituted.
The journal at `WAKE_ROOT/lifecycle/` records the exact profile, source, task,
native thread, pane/client generation and submission identity. Repeating the
same command observes/reconciles that intent; changing its assignment or expiry
under the same key is rejected. Exit0 means the exact assignment's native turn
completed. Exit5 means held, uncertain, expired or still awaiting evidence.
Native failure/interruption is retained as blocked; history is preserved.

Admission requires native idle, one exact client generation and an observed
empty local composer. Drafts, unknown composer layouts and split tabs hold the
assignment. The composer adapter recognizes the observed Codex0.162.1 ANSI
placeholder at its cursor; a changed layout holds rather than clearing input.
Controller restart rechecks readiness before admitting an unqueued assignment.
These observations do not atomically exclude concurrent human input; keep the
owned target untouched during the transition.

When an external response is unknown, retain its receipt. Known tab or native
queue/turn evidence can reconcile the original effect. An unknown thread/start
response has no native idempotency key: it stays uncertain. Do not use another
intent, root, transport or automatic replacement to bypass that uncertainty.
An original task may finish before its queue receipt is observed; the exact
client message ID and text must match its containing native turn.

For MCP, the operator configures both host paths:

```bash
codex-wake-mcp --wake-root /owned/wake \
  --lifecycle-profiles /host/launch-profiles.json
```

`wake_sessions_spawn` takes `profile`, `intent`, `name`, `task`, `expires_at` and
the actual `caller_thread_id`. Tools cannot override profiles files, journal
roots, launch commands, endpoints or credential locations. Missing host scope
or caller grant holds the operation.

The source candidate also exposes `sessions refresh` / `wake_sessions_refresh`.
Installed candidate evidence proves the same-thread transition and stale-MCP
hold with no goal; nonnull-goal and full readiness acceptance remain pending.
Supply the exact `thread_id`,
stable `intent`, workspace-contained `checkpoint`, its `checkpoint_sha256`,
fixed `expires_at` and named `resources` (CLI repeats `--resource`). The checkpoint
JSON must identify `source_thread_id`, `objective`, `authority`, `next_packet` and
an empty `pending_obligations` list. Actual pending-work inventory independently
guards the stop. MCP callers must name their own source thread and have its host
profile grant; host paths and probe definitions cannot be supplied by the caller.

Refresh profiles add a `resources` map. A skill check contains `kind: "skill"`,
the exact installed `path`, expected exported `description` and `sha256`. An MCP
check contains `kind: "mcp"`, host-approved `server`, `tool`, `arguments`,
`read_only: true` and `expected_content` from its actual tool response. Only
read-only behavior probes are eligible. A new TUI process alone does not prove
MCP readiness; an old result blocks the requested refresh.

Refresh preserves the checkpoint and original conversation, observes the old
process generation's exit and reattaches the same thread. Its replacement tab
has a unique refresh suffix for lost-response reconciliation. Repeat the exact
intent to observe/reconcile; do not replace an uncertain stop or launch. Source
expiry guards prevent a late replacement and never renew the deadline. Draft,
active/unknown work and pending obligations hold without a force option.

Explicit `--rollback` (MCP `rollback: true`) observes the original conversation.
It reuses a uniquely observed attachment with matching goal evidence. It may
reattach only after complete absence of the owned replacement tab and observed
exit of the original OS generation. Pending or ambiguous tabs hold rollback;
expiry still prevents a new attachment. Rollback adds a separate receipt result,
preserves resource failures and does not create a fresh thread or submit work.
The current rollback comparison requires the saved goal to match exactly;
changing accounting counters can hold it. Live nonnull-goal proof is pending.

Fresh-agent handoff remains Plan0159 work. TUI restart, fresh context and a file
read alone prove neither MCP refresh nor renewed goal allowance.
