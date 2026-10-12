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

Same-thread refresh and fresh-agent handoff are separate Plan0158/0159 operations
whose implementation and acceptance remain pending. TUI restart, fresh context
and a file read alone prove neither MCP refresh nor renewed goal allowance.
