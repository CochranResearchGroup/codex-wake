# Cycles17–18 — profile rejection and restart-time readiness

Cycle17 public CLI: malformed host launch profile must produce WakeError before
journal creation/runtime checks. Initial cwd=null red leaked TypeError (1error).
Small type guard green1 test. Extended the same malformed-profile invariant to
bad timeout/string/path types; red4failures/3errors in9.915s. Validate required
and optional nonempty string fields, reject NUL and nonnumeric/bool timeout;
green23 focused tests in5.712s. No endpoint fallback or launch retry added.

Exact single-test command:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_agent_spawn.AgentSpawnTests.test_malformed_host_profile_is_rejected_without_creating_journal -q

Cycle18 public CLI: terminate controller at the external time observation before
admission after its durable ready receipt, render a local draft in the existing
pane, then retry identical intent. Red admitted one native task despite draft.
Recheck exact recipient/client/composer when recovering ready with no queue ID;
retain the same submission identity. No new thread/tab/task when held.

Exact red command:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_agent_spawn.AgentSpawnTests.test_restart_rechecks_draft_before_prepared_task_admission -q
Observed1failure in0.343s: native tasks list had one item.

Combined green command:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_agent_spawn tests.test_lifecycle_mcp tests.test_session_lifecycle -q
Observed24 tests PASS in4.253s. These are focused source checks, not installed
qualification or final full suite. Clock/native/tmux are external fixture
boundaries; actual launch constructs an owned PTY process. No live effects in
these cycles. Concurrent input between observations/admission remains unproven.
Plan0158 is still blocked by full0157 qualification; no refresh implementation
or acceptance was substituted for that prerequisite.

Memory disposition: unavailable; existing checkpoint-01-memory.json retained.
