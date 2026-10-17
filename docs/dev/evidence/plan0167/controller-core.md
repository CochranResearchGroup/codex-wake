# Existing native session controller source acceptance

Public seams: enroll/show/poll/watch(root,interval=1). Policy paths and native
scope are host-selected, private, exact caller UUID grants. Outward readbacks
omit private grant/path/prior allocation history. Same allocation can only
tighten and preserves original goal boundary, response accounting, deadline,
BOOTTIME epoch, effects and stop latch across replacement goals. Only a changed
host allocation_id permits explicit reset against qualified response identities.
Cross-native endpoint/home migration is refused. Future native goal start after
qualified trusted current time is refused. No display-counter substitution.

Focused command: CODEX_WAKE_STABLE_TIME_CONFIG='' PYTHONPATH=src:tests
/home/ecochran76/.local/share/codex-wake/releases/0.16.0-d3ea192/bin/python
-m unittest discover -s tests -p test_goal_supervision.py

Nine public tests pass. Accounting uses actual goal_usage code and raw native
shape files. Watch readiness uses an actual separate Python watcher process,
real PID/start identity and private generation heartbeat. Native RPC effects are
injected at native_request only; no Codex/model/provider calls occurred. Tests
kill only their own disposable watcher process; subsequent show reports held,
not armed. Checkpoint/pause/interrupt assertions verify the durable effect intent
exists BEFORE the injected native call. Unknown checkpoint and pause responses
are not replayed; original stop is not delayed by checkpoint uncertainty.

Initial runs exposed host Codex executable symlink overrestriction and then a
fixture token_usage_record missing its payload envelope. The approved executable
may be a host-selected absolute symlink; Codex home remains canonical. Correcting
the fixture to the actual native shape qualified cached-inclusive40 tokens.
These first failures were retained as development observations, not represented
as product acceptance. Source was initially drafted before the complete public
fixture; this lane does not claim every implementation line arose via strict
one-test-first sequencing. Meaningful regression behaviors remain verified at
public seams, not private helper assertions.

Default checkpoint threshold is5%tokens OR60seconds remaining. An idle checkpoint
is queued durably in the controller and delivered to the next exact active turn;
it never starts an extra model turn. Native stop is current-goal pause plus exact
active-turn interrupt and readback proof. Failed native effects report
stop_unverified. Native controls do not guarantee arbitrary tool-process death or
exact token/time ceilings. Watch SIGTERM requests final native stop; SIGKILL is
observable only through stale/dead heartbeat and cannot promise a final RPC.

Policy is reread each poll. Revocation/malformed grants stop through the already
enrolled exact-thread scope, preserving unrelated shared services. RPC timeout
is host-selected but bounded to5seconds. Durable per-session locks and atomic
file plus parent-directory fsync protect intent visibility. Graceful/watch
process and native stop end-to-end qualification remain the integration lane.
