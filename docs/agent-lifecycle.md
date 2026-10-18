# Agent lifecycle

## Resource-limited objectives

For a user-supplied token/time or host resource budget, start with the packaged
[agent workflow](../skills/codex-wake/references/resource-limits.md) and
[operator setup](agents/strict-objectives.md). Strict containment requires an
approved dedicated executor; it is not enabled by ordinary spawn, an expiry,
a native goal token display or an existing TUI. The first launch from an ordinary
MCP caller currently requires operator bootstrap. Do not use CLI to bypass that
caller's authority boundary.

## Quickstart

Choose **spawn** for a separate worker assignment, **refresh** to reload named
resources while keeping the conversation, or **handoff** to continue the same
objective in fresh context. Use `sessions open` when you only want a visible tab.

For humans, start with `codex-wake sessions --help` and the chosen subcommand's
`--help`. For agents, use the corresponding `wake_sessions_*` MCP tool and the
installed Codex Wake skill. The operator must configure a trusted workspace,
owned endpoint, launch profile and caller grants before these operations work;
installation alone does not configure or authorize them.

1. Obtain the operator-approved profile and wake root. Inspect effective
   configuration before a configured launch or handoff:

   ```bash
   codex-wake --wake-root /owned/wake sessions configuration \
     --profiles /host/launch-profiles.json --profile worker \
     --thread-id SOURCE_THREAD_UUID --json
   ```

   Read the selected writer/reviewer instructions, resource limits, deadline and
   existing ledger. Agents use `wake_sessions_configuration` with their actual
   `caller_thread_id`, approved `profile` and source `thread_id`; host paths stay
   outside the tool arguments.

2. Prepare the bounded task for spawn, or write the checkpoint described below
   for refresh/handoff and compute its exact SHA256. Choose one stable intent and
   a fixed future timezone-aware expiry within the approved allowance.
3. Submit the chosen operation. The following are templates: replace every
   placeholder and path with approved values. Refresh resource names must exist
   in the host profile; handoff needs an approved continuation entry.

   ```bash
   codex-wake --wake-root /owned/wake sessions refresh \
     --profiles /host/launch-profiles.json --profile worker \
     --intent refresh-001 --thread-id SOURCE_THREAD_UUID \
     --checkpoint checkpoints/source.json --checkpoint-sha256 CHECKPOINT_SHA256 \
     --expires-at FIXED_FUTURE_ISO8601 --resource APPROVED_RESOURCE_NAME --json

   codex-wake --wake-root /owned/wake sessions handoff \
     --profiles /host/launch-profiles.json --profile worker \
     --intent handoff-001 --thread-id SOURCE_THREAD_UUID \
     --checkpoint checkpoints/source.json --checkpoint-sha256 CHECKPOINT_SHA256 \
     --expires-at FIXED_FUTURE_ISO8601 --mode new-tab --json
   ```

   Use `--mode same-tab` to replace the source in its pane instead. Keep the
   owned target untouched while the controller checks and changes its client.
4. Read and retain the receipt. A held or uncertain result means reconcile the
   **same intent**, retaining its original arguments and expiry. Do not create a
   replacement intent to bypass a hold. A prepared successor can remain paused
   awaiting the already approved resident monitor; readiness is separate from
   work acceptance and permission to continue.

Configured operations require a resident monitor on the same wake root. Fresh
context, refresh and rollback preserve cumulative spending and original
deadlines. Missing instructions, stale probes, pending obligations and unknown
accounting hold the operation. Only an operator's explicit budget authorization
can extend resources; agent MCP cannot reset them.

### Agent requests

Use the [packaged agent request reference](../skills/codex-wake/references/lifecycle.md)
for configuration, spawn, refresh and handoff MCP templates. This same file ships
with the installed skill, so agents can reach it outside this repository.

## Operator setup and spawn

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
  "callers": {
    "00000000-0000-7000-8000-000000000011": [
      "worker"
    ]
  },
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
  --intent task-001 --name worker --expires-at FIXED_FUTURE_ISO8601 \
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
For owned sessions, the ledger uses cumulative rollout `total_tokens`, including
cached input. A native goal's displayed `tokensUsed` can use a smaller accounting
metric and does not replace that session counter. Native goal identity and its
own limits remain separate checks. Goal completion waits for final owned-turn
accounting before releasing a session reservation.
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

## Refresh the same conversation

Use `sessions refresh` / `wake_sessions_refresh` to reload approved resources.
Released lifecycle acceptance covers configured goal preservation and updated
versus stale resource behavior; see the acceptance evidence linked below.
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

For client replacement, refresh records the original goal state and pauses an
active goal before closing the client. It restores active status only after
same-thread continuity, an empty composer, resource readiness and the original
expiry are verified. Goals that were already paused, blocked or complete remain
inactive. Only the exact recognized "Resume paused goal?" prompt is dismissed
with Escape; an unknown dialog or draft holds the operation. Dismissal is recorded
before sending its one-shot key, and the composer must subsequently be observed.

For unattended single-client refresh, the host profile selects
`refresh_mode: "client_idle"`, names the exact `tmux_session` (and optional
`tmux_socket`/`codex_home`), and records `scope_approval`. The existing independent
`sessions refresh-watch` controller owns execution. Admission returns `queued`;
end the source turn and observe the same durable intent afterward. It waits only
for the source conversation, preserving other active conversations; it never
calls the shared MCP reload API. The private profile/checkpoint and any configured
budget binding are revalidated before advancement. Watcher shutdown fences new
native and tmux effects; an acknowledged operational pause survives restart.

Automatic goal restoration requires the configured lifecycle budget or an
explicit host-profile `goal_supervision` binding containing `root`, `policy` and
`allocation_id`. The existing controller must report armed, qualified accounting,
a fresh heartbeat, remaining tokens/time and no stop latch. This binding selects
an existing allowance; it cannot enroll, renew, clear a stop or reset counters.
An unqualified allowance leaves the goal paused. Shared-server idle reload is a
separate profile mode and does not acquire permission to resume any goal.

Explicit `--rollback` (MCP `rollback: true`) observes the original conversation.
It reuses a uniquely observed attachment with matching goal evidence. It may
reattach only after complete absence of the owned replacement tab and observed
exit of the original OS generation. Pending or ambiguous tabs hold rollback;
expiry still prevents a new attachment. Rollback adds a separate receipt result,
preserves resource failures and does not create a fresh thread or submit work.
Rollback requires matching saved goal evidence; changed or unknown goal
authority holds the operation.

## Handoff to fresh context

Use `sessions handoff` / `wake_sessions_handoff` with
`thread_id`, checkpoint path/hash, stable intent, profile, explicit `mode` and
fixed expiry. A host `continuations` entry keyed by source UUID supplies objective,
approval locator, original `started_at`, `token_cap`, `time_cap_seconds`,
`tokens_before_source`, `seconds_before_source` and a `preflight` descriptor:
absolute `script`, pinned `sha256`, workspace-contained `receipt`,
`workflow` matching the effective `preflight_reviewer.name`, nonempty
`required_checks` and bounded
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
Handoff supports new-tab and same-tab preparation and explicit `--rollback`
(MCP `rollback: true`) when the successor is paused and settled and the original
source can be restored with exact ownership and goal evidence. Rollback keeps
the original goal paused and
subtracts observed receiver spending once; uncertain effects reconcile before
retry. An active successor or ambiguous source ownership holds. Both tab modes and
rollback have native acceptance evidence. TUI restart,
fresh context and a file read do not prove MCP readiness or renewed allowance.

## Select writer, reviewer and limits

The operator adds `lifecycle_defaults` to the registry and can overlay those
fields in the approved continuation entry's `configuration`. This is a registry
fragment; it does not replace the required profiles, callers and continuation
approval/preflight fields described above. Paths must resolve to existing,
nonempty UTF-8 instruction files. Names identify the selected workflow; the
preflight descriptor's `workflow` must match the effective reviewer name.

```json
{
  "lifecycle_defaults": {
    "handoff_writer": {
      "name": "checkpoint-writer",
      "path": "/approved/instructions/writer.md"
    },
    "preflight_reviewer": {
      "name": "local-review",
      "path": "/approved/instructions/reviewer.md"
    },
    "session_token_limit": 100000,
    "session_time_limit_seconds": 1800,
    "objective_token_limit": 300000,
    "objective_time_limit_seconds": 7200,
    "max_correction_cycles": 2
  }
}
```

Run configuration readback after editing the registry. It returns the selected
instruction text and hashes, effective limits and revision. Editing defaults
does not authorize active work or replenish its budget. A new authorization
requires the operator's exact approved revision; agent MCP cannot apply one.

## Release evidence

Lifecycle operations shipped in 0.14.0. The [acceptance matrix](dev/evidence/plan0156/final-acceptance.md)
separates paid native candidate runs, public fixture coverage and exact released
installation checks. The [0.15.1 installed closeout](dev/evidence/plan0162/final-acceptance.md)
records later tab targeting and installation qualification. These receipts do not
configure profiles or grant authority on another host.
