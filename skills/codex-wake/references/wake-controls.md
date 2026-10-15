# Wake controls

Use the actual native CODEX_THREAD_ID as caller_thread_id. The host configures
the wake root, optional registry and caller root/action grants; tools cannot
select paths or grant themselves scope.

| Outcome | MCP tool | Extra arguments |
|---|---|---|
| Inventory | wake_list | optional all_roots:true |
| Cancel eligible records | wake_cancel | one wake_id or all:true |
| Persistently hold new delivery | wake_pause | optional all_roots:true |
| Inspect hold and admitted effects | wake_pause_status | optional all_roots:true |
| Stop proven owned turns | wake_interrupt | paused roots required |
| Release hold explicitly | wake_resume | separately granted action |

Every tool accepts all_roots:true for the host registry snapshot; all selected
roots must be granted. Disabled registrations are included; later enrollments
are outside the snapshot. Default scope is the host-selected root.

For emergency control, pause first, inspect status/in_flight and enforcement,
then cancel eligible records or explicitly interrupt owned turns as authorized.
Only upgraded control-capable readers honor pause. A capable worker observation
is not proof that every possible reader was inventoried. Missing/stale/old-worker
readback is not proof of enforcement. Existing assignments remain running under
pause alone. Native queued-only work holds; unsupported transports remain explicit.
Handoffs depend on their original resident owner, never a takeover or blanket kill.

Inspect each root and actor outcome; successful roots do not erase held ones.
Reconcile ambiguous effects by observation before any retry. Pauses and cancelled
records survive restart. Resume releases only the hold; it cannot restore cancelled
work, restart stopped handoffs, or renew deadlines/budgets. Retain operation receipts.

CLI equivalents: codex-wake list; cancel WAKE_ID or cancel --all; pause;
pause-status; interrupt; resume. Add --all-roots and --json for an explicit
registered-root snapshot with structured per-root results.
