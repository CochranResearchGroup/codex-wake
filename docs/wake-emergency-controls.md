# List, cancel and stop wake delivery

Start with these operator commands:

```bash
codex-wake list
codex-wake cancel WAKE_ID
codex-wake list --all-roots
codex-wake cancel --all --all-roots --json
```

Without `--all-roots`, commands use the current workspace's wake root. Select
another explicitly with `codex-wake --wake-root /owned/wake ...`.
`--all-roots` snapshots every root in the user supervisor registry, including
roots currently disabled for monitoring. Newly enrolled roots after the snapshot
are outside that operation. Use operator `--registry-dir /owned/roots.d` for a
custom registry. No recursive filesystem search or implicit root discovery occurs.

## Emergency stop

```bash
codex-wake pause --all-roots --json
codex-wake pause-status --all-roots --json
```

Pause persists across daemon/controller restarts, blocking new wake deliveries,
worker admissions and successor activation. It preserves records, history,
spending and original deadlines. Existing assignments can still run and existing
resource enforcement continues. If a delivery was already admitted, pause
reports `in_flight: true`; it cannot retract a submission. Read `pause-status`
again to observe quiescence. The command records the hold without waiting on a
possibly ambiguous external submission.

Only control-capable workers enforce this protocol. `enforcement` reports
`upgrade_required_observed_worker`, an unverified worker state, or a capable
worker observation. An observed capable worker is not an exclusive process
census. Upgrade all responsible readers before relying on the control across a
host; changing a CLI link or writing the marker does not upgrade an existing
process. Unsupported transports/readers are never described as stopped.

To retire pending work as well:

```bash
codex-wake cancel --all --all-roots --json
```

Cancellation returns per-root/per-wake outcomes and retains cancelled records.
Submitted/terminal wakes are skipped; unknown submissions hold for reconciliation.
A busy root with admitted delivery reports held rather than racing cancellation.
Some roots can succeed while others hold; exit5 reports incomplete action.
This operation is not an atomic transaction across roots.

To stop running Wake-owned native work, separately and explicitly:

```bash
codex-wake interrupt --all-roots --json
```

Every selected root must already be paused. Native work requires exact durable
assignment identity, payload and current turn evidence. Later unrelated turns in
the same conversation are preserved. Ordinary queued-only native assignments hold
rather than claiming queue deletion. Submitted legacy transports return unsupported.
Handoff stop requests persist for the original resident owner; if it is unavailable
or another generation owns the fence, the result stays `monitor_required`.
Uncertain interrupt responses reconcile by observation, without blind resend.
This is an owned-work control, not an OS process `killall`.

Explicitly resume eligible delivery when ready:

```bash
codex-wake resume --all-roots --json
```

Resume clears the pause/interrupt request; it neither restores cancelled work nor
renews deadlines or budgets, nor silently restarts a stopped handoff. Corrupt
control state holds delivery and resume for operator repair with history preserved.
A newly started incompatible old daemon can ignore this protocol; do not downgrade
readers while relying on a pause.

## Agent tools and host grants

MCP exposes `wake_list`, `wake_cancel`, `wake_pause`, `wake_pause_status`,
`wake_interrupt` and `wake_resume`. Every request supplies the actual native
`caller_thread_id`; that claim alone is not permission. Tools accept optional
`all_roots: true`. `wake_cancel` requires exactly one of `wake_id` or `all: true`.

The operator starts MCP with its host root and grants file:

```bash
codex-wake-mcp --wake-root /owned/wake \
  --wake-control-config /host/wake-control-grants.json \
  --wake-registry /owned/roots.d
```

Grant file example (replace UUID and root with approved values):

```json
{
  "version": 1,
  "callers": {
    "00000000-0000-7000-8000-000000000011": {
      "roots": ["/owned/wake"],
      "actions": ["list", "cancel", "pause", "pause-status", "interrupt", "resume"]
    }
  }
}
```

Grant actions independently: a host can allow an agent to pause while reserving
resume/interrupt to the operator. Every selected root must be granted; the tool
fails instead of silently narrowing a request. A changed registry cannot widen
an already authorized root snapshot. Tool arguments cannot select roots, registry
paths, commands or grant files.

Example MCP arguments:

```json
{"caller_thread_id":"00000000-0000-7000-8000-000000000011","all_roots":true}
```

Use this shape with `wake_list`, `wake_pause`, `wake_pause_status`, `wake_interrupt`
or `wake_resume`. For `wake_cancel`, additionally supply `"all": true` or one
`"wake_id": "WAKE_ID"`. Inspect per-root results and retain receipts on a hold.

## Durable state

Each root stores the private schema1 sidecar at `emergency-control/state.json`.
Its revision and attributable operation history are independent of wake schemas
and trusted time. Native interruption keeps a separate private fsynced ambiguity
journal in `emergency-interrupt/`. Listing across roots returns compact wake
metadata and reports malformed record files rather than silently hiding them.
