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
Keep the registry and journal private and operator-controlled.
New launches require the existing owned Unix socket itself; a listener locator
symlink must be resolved by the operator before storing the approved endpoint.
Invalid endpoint types are rejected before a new creation journal.

The host grants
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

When the registry supplies lifecycle defaults or objective configuration, spawn
also requires an approved `continuations` entry. Operator launches select its
key with `--objective-ref`; MCP uses the actual caller's entry and cannot select
another objective. Start a resident `codex-waked --wake-root /owned/wake
--no-dispatch --interval 1` before launching configured tasks. One-shot polling
does not publish admission authority. The daemon's owned process generation and
fresh heartbeat must be available before creation and task effects.

Configured spawn reserves its session within the shared objective allowance.
An approved continuation entry may set `spawn_token_limit` to a positive lower
allowance within `session_token_limit`; this cannot raise the session cap.
Actual overspend remains charged and blocks a success claim even if the native
turn completed.
An active native parent keeps its finite future quota reserved before a worker
is admitted. Repeated intents preserve the original reservation and deadline.
The daemon observes native usage and interrupts only the assignment's exact
owned turn on exhaustion, time loss or previously known accounting becoming
unknown. A missing first snapshot permits observation under the existing
reservation, with no further admission. Completion retains the reservation until
the owned rollout's final accounting marker; later turns are excluded from that
settlement. Profiles without lifecycle configuration use explicit expiry only,
reported as `explicit_expiry_only_legacy_profile` in their receipts.

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

The source candidate exposes `sessions handoff` / `wake_sessions_handoff` with
`thread_id`, checkpoint path/hash, stable intent, profile, explicit `mode` and
fixed expiry. A host `continuations` entry keyed by source UUID supplies objective,
approval locator, original `started_at`, `token_cap`, `time_cap_seconds`,
`tokens_before_source`, `seconds_before_source` and a `preflight` descriptor:
absolute `script`, pinned `sha256`, workspace-contained `receipt`,
`workflow: "github-handoff"`, nonempty `required_checks` and bounded
`token_allowance`. Native source usage and any smaller native budget constrain
the host cumulative ceiling. An unlimited native budget grants no additional
allowance; the explicit host cap still binds.
Handoff checkpoints additionally require `repo` (absolute existing repository
path), `worktree` (exact launch workspace), `commit` (40 lowercase hexadecimal
characters), explicit `dirty_work` disposition, nonempty string lists
`acceptance_remaining`, `evidence`, `hard_stops`, and a nonempty `reply_route`.
`pending_wakes`, `pending_messages`, `claim_holders` must each be empty; runtime
inventory independently verifies that no custody is outstanding. `resources`
contains the host `token_cap`, `time_cap_seconds`, `started_at`,
`tokens_before_source`, and `seconds_before_source`; caps/start must match the
immutable host intent. Checkpoint carried counters are nonnegative lower bounds:
the host may incorporate later observed spending but may never reduce those
bounds. `expires_at` must exactly match the fixed intent expiry. Native source
counters remain authoritative and are accounted separately. These shape and
intent checks run before native effects; revision/evidence claims are snapshots
for successor reconciliation, not independently certified acceptance.
 Source checkpoint writer must be
observed in native completed command evidence. Source drafts and pending work hold.

The fresh successor executes the host-selected preflight and produces its exact
native command/hash/identity receipt. Actual rollout usage is charged before a
paused successor goal receives the remaining allowance. `awaiting_activation`
does not establish autonomous continuation. Host policy must additionally supply
`activation: {"approved": true, "max_poll_seconds": 1,
"deadline_margin_seconds": 45}` for a continuous owned monitor. The interval is
positive, at most five seconds and within the host bound; the safety margin must
cover that interval plus four native request timeouts. Operator command:

```bash
codex-waked --wake-root /owned/wake --no-dispatch --interval 1
```

The existing monitor verifies exact goals, leaves source paused, activates only
the original remaining successor allowance, and pauses/interrupts owned activity
at its deadline safety boundary. One-shot polling cannot activate. Graceful
monitor exit pauses its goal; a different live PID generation prevents takeover.
Monitor availability is a runtime requirement, not a claim of enforcement during
host outages. Unknown effects retain original receipts for reconciliation.
Current source supports new-tab preparation and explicit handoff `--rollback`
(MCP `rollback: true`) when the successor is paused and settled and the original
source attachment remains ready. Rollback keeps the original goal paused and
subtracts observed receiver spending once; uncertain effects reconcile before
retry. An active successor or missing source attachment holds. Same-tab, broader
rollback and full installed native continuation acceptance remain open Plan0159
gates. TUI restart,
fresh context and a file read do not prove MCP readiness or renewed allowance.
