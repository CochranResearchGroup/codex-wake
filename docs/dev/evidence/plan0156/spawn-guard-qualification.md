# Spawn guard qualification at the public CLI seam

Existing production guards were tested without changing their behavior:
active native recipient, unknown native status, split owned tab and lost exact
thread/queue/start response after accepted turn. All hold or reconcile without
another thread/tab/task/turn. No red/green claim for already-working guards.

Command:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_agent_spawn tests.test_lifecycle_mcp tests.test_session_lifecycle -q
Result26 tests PASS in5.868s. Native websocket peer plus launched PTY process,
tmux/time external fixture boundaries. No live model assignment or service
mutation. Source-only proof; current installed candidate qualification follows.

Concurrent human input cannot be atomically excluded by native readiness and
separate TUI capture. Public guidance requires keeping the owned target untouched
during transition and holds unknown layout. This limitation is not proof of
refresh safe-stop, which must additionally protect work and pending obligations.

Memory disposition: unavailable; checkpoint-01-memory.json retained.
