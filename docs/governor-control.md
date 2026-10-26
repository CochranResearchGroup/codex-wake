# Governor control

The existing native conversation exposes the selected governor scope in its
activation/status notice. To deactivate it, send the whole message:

> Deactivate governor

The model calls `wake_goal_limits_disable` as a mechanical adapter. Wake reads the
actual native user message for that exact current caller turn; model arguments,
quoted or embedded instructions, historical turns and tool outputs cannot grant
operator authority. No further confirmation or model approval is required. The
same control works with a missing/stopped watcher. A shared allocation is the
selected scope, including its existing and future members; peer allocations stay
unchanged. A mismatched explicit allocation is refused.

The result reports `governor_enabled: false`, `state: inactive`, and
`governor.mode: inactive`. `campaign_state` retains the underlying work state.
`governor_revision` identifies the durable control choice. Accounting, checkpoints,
stop latches, original limits/deadline, service masks and unrelated objectives are
preserved. Deactivation does not resume work or renew resource authority. The model
must drop superseded governor checkpoint/stop instructions while honoring
independent platform controls and the operator's existing work authority.

To reactivate, send the whole message:

> Reactivate governor

`wake_goal_limits_enable` verifies the same native provenance and announces the
scope and sampled stopping mode. It does not resume stopped work, clear a stop,
reset usage, extend a deadline, or undo a service mask. A stopped watcher remains
stopped. Watcher readiness and operator/model notice delivery remain separate
reported facts; neither is invented by changing this switch.

Both audiences receive a revision-bound no-turn native notice when the selected
host supports the existing notice extension. Delivery failures remain explicit in
`notices` and retained governor status; effective deactivation does not depend on
notice availability. The control notice says its revision supersedes older
notices. Unsubmitted older notices are presented as historical with a current
scope-state reference; original text is retained. Already attempted/uncertain
notice text is never rewritten or replayed. Historical delivery cannot reactivate
the governor. UI rendering and human reading still require native qualification.

The conversational adapter requires a connected model capable of making that
mechanical tool call and a native endpoint capable of reading the caller turn.
For a disconnected model/native runtime, a trusted operator host can independently
call `goal_governance.change(root, thread, enabled=False, principal=operator)`.
Only a host-authenticated `Principal(thread, 'operator')` is accepted; an agent
principal cannot self-disable, including under permissive policy. The existing
capability-authenticated `goal-limits disable` / `enable` CLI also exposes this
operation for host integrations. Current mandatory common-policy prohibitions
remain enforceable and failures are explicit. The runtime is a same-UID authority
boundary, not hostile same-UID isolation.

Scope state commits under the existing enrollment/membership and all member
receipt locks, in the controller's receipt-before-allocation order. Queued polls
observe the switch before effects; in-flight effects complete before it takes
effect. The allocation ledger commits first so a partial member-copy failure still
leaves the authoritative switch disabled. Retrying reconciles copies/notices at
the same revision. A late approved renewal resume is held while disabled.

`goal_governance.snapshot(root, thread_id)` provides a read-only host snapshot for
first dispatch intent creation: `state`, `enabled`, `mode`, `revision`, `scope`,
`thread_id`, `source` and `observed_at`. Missing/unqualified state is explicitly
unavailable and is not a new work/repair gate. Keep the original snapshot on intent
retry; it is context, while current durable scope authority governs effects.
