# Resume a saved managed agent

Resume loads the exact saved Codex conversation. It preserves the managed-agent
ID and reconciles a positively observed process/terminal binding. It does not
submit an instruction, accept pending work, clear an enforcement stop, or change
resource accounting. Work admission remains a separate operation.

The CLI leaf registers under `agents`:

```sh
codex-wake --wake-root /private/wake agents resume \
  --managed-agent-id agent_EXACT_ID --profile workstation \
  --profiles /private/lifecycle-profiles.json \
  --intent recover-original --expires-at 2027-01-16T09:00:00+00:00 \
  --bus-root /private/bus --operator-capability /private/bus/operator.json --json
```

Use a real managed ID from inventory and a real future expiry. The example has
no authority by itself. Agent MCP exposes `wake_agents_resume` with the same
managed ID, named profile, stable intent and expiry. The MCP host supplies the
private profiles path and authenticates native caller metadata; tools cannot
supply roles, launch commands, credentials or a profile-file path.

An owned private version-1 lifecycle profile supplies `cwd`, `app_server`,
`codex_path`, `tmux_session` and `timeout` (at most 30 seconds), with optional
`tmux_socket`, `codex_home` and existing resource metadata. The executable must
be absolute, the workspace must match inventory, and the endpoint must be an
existing owned local Unix socket. The launcher constructs only `codex resume`
for that exact conversation, using the selected Codex home when configured.
The destination tmux session must already exist. This operation does not recreate
workspaces or start an app-server.

The common permission store must be active. Self callers use `resume.self`.
Recovery of another conversation uses the actual operator/controller principal
and `resume.recover`, whose default requires approval. Recovery also requires an
exact host `recovery_callers` entry mapping that principal's subject to the
managed-agent ID. This host execution boundary cannot override common denial.
For example, a verified CLI operator's subject is `local-operator`. Controllers
must possess existing host-verified delegation. Task-scoped callers supply the
existing assignment ID; task membership is verified against its admitted brief.
Operator capabilities are checked through the existing mailbox bus. An arbitrary
UUID or an inventory record is not authority.

Every attempt journals its exact intent and profile fingerprint in private
`agent-resume` state before launch. It selects the last confirmed ready binding;
`record_sha256` can select one exact retained ready history record. Selection
does not reuse its PID as live proof. Profile/enrollment/current permission and
expiry are checked again before terminal effects. A changed profile holds the
original operation. Different intent keys cannot bypass an unresolved launch.

Results distinguish `resumed`, `starting`, `uncertain` and `held`. `resumed`
requires fresh exact native metadata plus current process-generation/attachment
evidence and inventory reconciliation. A launched tab alone is `starting`.
After response loss, retry the same intent to observe/reconcile its original
binding. Wake never blindly sends the launch again. Existing unqualified
attachments, suppression, missing history or ambiguous identity hold execution.

Changing the account while retaining the same home/provider is allowed only
when the exact saved history remains accessible. This is history-access evidence,
not account attestation. Changing Codex home/provider changes the native namespace
and holds this first slice; it has no verified cross-namespace migration path.
Grok resume and restarting strict contained executors remain unqualified. A fresh
conversation requires a separately authorized successor workflow.

Source tests use real local Unix WebSocket metadata and a private attachment
fixture backed by the test worker's current OS process identity. They exercise
fixed launch arguments and both authenticated caller handlers without contacting
a provider or manipulating an operator terminal. They are source qualification,
not installed-provider or native TUI acceptance.
