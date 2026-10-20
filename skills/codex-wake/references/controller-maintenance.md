# Operator controller maintenance and acceptance

This workflow changes controller availability, never resource authority. Preserve
all existing stop latches, allocation IDs, counters, accounting basis, generations
and deadlines. Keep the shared native daemon running. Maintenance requires all
unlatched campaigns inactive with no active turns; pause them through their
normal authorized control before preparing. Already latched campaigns stay held.
Operator chat remains available. Before production handover, verify every
enrollment writer runs version0.19.0 or later. Existing MCP processes retain their
interpreter/CLI until an approved refresh and cannot honor the new admission gate;
a fresh stdio catalog does not prove those connections changed. Keep this version
check separate from Plan0168's shared refresh authority.

## Bounded graceful controller handover

The host operator provisions a separate private owned JSON file (0600, no
symlinks), with these exact keys. This is host authorization, not an agent-issued
allocation or a security boundary against hostile code running as the same UID.
The feature is CLI-only; MCP callers cannot prepare maintenance.

```json
{"version":1,"enabled":true,"controller_root":"/exact/private/goal-root","max_seconds":30}
```

Use the installed CLI against that same root:

```sh
codex-wake --wake-root /exact/private/goal-root goal-limits prepare-maintenance \
  --policy /exact/private/operator-maintenance.json --seconds 20 --json
```

A `prepared` receipt binds the fresh controller PID, process identity, generation,
boot, exact authority snapshot and fixed boottime expiry. Gracefully stop that
exact controller service, then start the replacement within the interval. The
old finalizer skips campaign-stop effects only after rechecking the unchanged
permission and receipt authority, nondecreasing accounting and inactive native
goals. New enrollment waits for the replacement's first normal budget/policy poll.
There is no resource renewal or automatic goal restoration.

Read controller freshness and `goal-supervision/maintenance/permit.json` after
replacement. `replaced` plus a fresh heartbeat proves the replacement polled;
check each receipt separately before campaign continuation. A missed replacement
window latches `maintenance_expired` on the replacement's first poll. An aborted
preparation expires while the original controller continues enforcing normally.
Unauthorized, expired or changed permits take the normal fail-closed shutdown
path. A dead controller cannot enforce during downtime: goals must remain
inactive, and stale/inactive heartbeat always holds public readiness.

## First-stop evidence

`first_stop` is saved before stop effects and remains immutable through later
healthy observations and failures. It contains the reason, typed native method
and cause, bounded observation duration, controller/receipt generation, budget
snapshot and clock/freshness anchors; exception messages and prompts are omitted.
A changed boot has no qualified wall-time upper bound. Receipts that were already
latched before this diagnostic existed are labeled `existing_latch_observed`;
this does not reconstruct their historical first fault. Later observation and
control fields may change without replacing the retained first diagnostic.

## Real-agent acceptance

Use the repository's `scripts/goal_supervision_real_acceptance.py --help` for an
explicitly approved, capped real-agent acceptance run. Inspect its preflight
receipt before treating failures as product defects. A blocked permission/MCP
setup must fail before goal activation or model dispatch. Retain the exact
owned thread, original allowance/deadline, checkpoint/pause and operator marker
receipts; cleanup applies only to the run's owned thread/turns. A setup failure
does not authorize a larger allowance, a new identity retry or policy edits.
Existing accepted paid runs need no repeat for documentation changes.
