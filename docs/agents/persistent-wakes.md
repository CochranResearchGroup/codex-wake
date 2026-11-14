# Persistent wakes and recurring schedules

Spec #610; implementation tickets #611–#616. These source interfaces do not deploy
a monitor or register production checks. Use a compatible supervised monitor for
the exact root; inspection reports retained/inactive unless its live heartbeat
advertises `recurring_schedules_v1`.

New native agent wake tools require explicit `session_mode`: `session_only`,
`reopen_live`, or `background`. Recurring schedules always require a mode. Existing
stored wakes retain their policy. The older operator `native after|at|file` CLI
remains compatible with its explicit lifetime/startup policy interface; omission
of `--session-mode` uses that legacy contract, not an inferred new session mode.
Agents must use explicit mode registration.

Register an agreed interval schedule with `codex-wake --wake-root ROOT schedules
register --request FILE --codex-path /absolute/stable/codex`. Example request:

```json
{
  "idempotency_key": "agreed-check-twice-daily",
  "thread_id": "11111111-1111-4111-8111-111111111111",
  "prompt": "Perform the agreed check within the existing task scope.",
  "session_mode": "background",
  "cadence": {"kind": "interval", "seconds": 43200, "start_at": "2033-05-18T03:33:20Z"},
  "end": {"kind": "until_cancelled"},
  "missed": {"policy": "latest", "max_lateness_seconds": 3600},
  "overlap": {"policy": "queue", "limit": 1},
  "delivery_window_seconds": 3600
}
```

These values are examples, not defaults or permission to register. Seconds are
positive whole numbers for interval and delivery windows. End may instead be
`{"kind":"count","count":10}` or `{"kind":"until","at":"2033-06-01T00:00:00Z"}`
(exclusive end). Clock cadence is described in [persistent-clock.md](persistent-clock.md).
Skipped/expired occurrences count; successful-check counts are outside this API.

Missed policy is `skip`, `latest`, or `catch_up` with an explicit `limit` for
catch-up. Every policy includes maximum lateness. Overlap is `skip`, `latest`, or
`queue` with an explicit queue `limit`. Bounds are at most 256. Poll work is
bounded to 256 planned occurrences per schedule; a larger downtime backlog is
retained and enumerated across polls before dispatching catch-up work. Original
UTC due/expiry anchors and per-occurrence identities are preserved.

Inspect with `schedules list` or `schedules show ID`. Change future behavior with
`schedules revise ID --request FILE --expected-revision N`; pass the intended
stable harness and endpoint for the new revision. Identity/key cannot change;
prior checks keep their revision. `schedules cancel ID --expected-revision N`
cancels future and queued checks, leaving admitted running/uncertain effects for
completion or evidence reconciliation. A cancelled schedule needs a new explicit
registration to restart. These commands support the existing bus/operator or
actor capability flags when common permission policy is active.

Native tools `wake_schedules_register|list|show|revise|cancel` use host-verified
caller metadata and the host root/endpoint. Model arguments cannot select another
conversation, root, executable, authority role or private restoration profile.
Readiness and actual delivery/execution remain separate receipt boundaries.

Background dispatch prefers the exact qualified live TUI. Without a TUI it resumes
the exact saved conversation and starts a turn through the existing app-server
protocol; queue acceptance alone is not claimed to run a background check.
Per-root conversation admission serializes schedules and reconciles prior exact
turn evidence. Unknown ownership holds. A known absent pinned tmux socket and
original client generation can qualify a closed server, while mere disconnect or
failed inventory cannot. This is scoped to the declared runtime/terminal namespace;
it is not discovery or locking of unrelated wake roots and hosts.

Live restoration setup is described in [persistent-live.md](persistent-live.md).
Missing host profiles, missing directories, unsupported routes and uncertain
launches hold for attention. Affected recurring schedules stop further admission,
retain their original deadlines, and issue a notice through the existing attention
queue when its current permission policy admits the notice. Any notice failure
is retained as `attention_error`; schedule inspection remains authoritative.
Resolve configuration/authority, then explicitly revise the schedule to resume
future checks. Acknowledging a notice never grants permission or replays work.

No path changes existing resource allowances or task authority. Keep installed
runtime, source qualification, monitor readiness, accepted delivery and completed
checks separate when reporting acceptance.

Ordinary monitor polling jitter within the delivery window does not make a check
a missed run. Qualified monitor/coordinator generation identifies restart recovery;
a shared supervisor's helper-worker rotation does not itself mean restart. A
previously admitted overlap queue keeps its separate policy. Large recovery
batches finish bounded enumeration before applying missed-run selection.

Past terminal peer evidence is retained privately, bound to the exact original
submission and recipient. Admission does at most one bounded remote reconciliation
and a five-second local history scan; unknown history holds rather than bypassing
execution exclusion. Terminal evidence never grants new task/effect authority.
