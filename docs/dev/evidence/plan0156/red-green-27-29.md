# Cycles27–29 — goal accounting and proof admission

Public refresh CLI seam with native websocket/actual PTY client fixtures.
Cycle27 goal authority unchanged while native usage advances: RED returnedblocked
because full goal dict equality treated monotonic counters as changed authority.
GREEN retains exact before/after observations, compares all stable fields, requires
numeric nondecreasing tokensUsed/timeUsedSeconds/updatedAt. No goal mutation,
clear/reset or allowance increase.9 refresh tests PASS2.414s.
Command:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_agent_refresh.AgentRefreshTests.test_refresh_preserves_native_goal_authority_with_monotonic_usage -q

Cycle28 unsupported resource kind must reject before journal/runtime. RED returned
held receipt and created journal instead of rejecting. GREEN10 tests2.079s.
Cycle29 extended the same proof-contract invariant to missing required skill/MCP
fields. RED2failures, journal created; GREEN10 tests1.990s after exact supported
field sets. No arbitrary-command resource path or shell execution introduced.
Command:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_agent_refresh.AgentRefreshTests.test_unsupported_resource_proof_is_rejected_before_journal_or_runtime -q

Existing guards qualified without fictitious red: active/unknown recipient,
split pane and unaccounted pending wake input leave original process alive and
perform no stop/launch; changed goal budget or reset counters hold without native
goal mutation; actual updated MCP behavior producesready. Combined focused:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_agent_refresh tests.test_agent_spawn tests.test_lifecycle_mcp tests.test_a2a_mcp tests.test_session_lifecycle -q
42 tests PASS12.810s. No live model/provider/shared-service effects.

Checkpoint before installed refresh effects: current source partial0158 acceptance
requires owned installed native/TUI evidence, rollback and final schema/scope audit.
Full0156/handoff/release/clean-main obligations remain. Next proof uses new private
home, workspace, app-server, tmux socket and only toy read-only MCP/skill resources;
no model assignment or autonomous goal owner. Original goal caps unchanged.
Memory unavailable; checkpoint-01-memory.json retained.
