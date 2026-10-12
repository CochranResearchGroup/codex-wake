# Cycles23–26 — refresh recovery and scoped MCP

Public CLI and actual stdio MCP are seams. Native websocket and actual launched
PTY client identities remain real fixture boundaries, not helper mocks.

Cycle23 exact lost new-window response: first callback starts real replacement
then loses response; retry must complete without another stop/launch. RED stayed
uncertain/exit5. GREEN5 tests1.170s after unique saved refresh tab name + native/
process generation reconciliation; no blind launch retry.
Command:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_agent_refresh.AgentRefreshTests.test_lost_new_tab_response_reconciles_existing_refresh_without_replacement -q

Cycle24 lost kill-pane response after actual old-client exit. RED retry stayed
uncertain/exit5. GREEN6 tests1.345s. Resume stopping observation on identical
intent; never repeat the uncertain stop. One kill and one launch verified.
Command:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_agent_refresh.AgentRefreshTests.test_lost_stop_response_observes_old_exit_without_stopping_twice -q

Fixed expiry after actual stop already works: added qualification test without
fictitious red. Expired intent creates no replacement; repeats retain same fixed
expiry and effect count.7 refresh tests PASS1.654s.

Cycle25 actual stdio discovery and host scope. RED missing wake_sessions_refresh
KeyError. GREEN36 focused tests9.914s. Host registry/root own all launch/probe
paths; caller can select only named resource checks. Arbitrary tool argument
rejected before executable CLI fixture. Resource list maps to repeated CLI flags;
source caller ID transmitted, generic endpoint/tmux override flags omitted.
Command:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_lifecycle_mcp.LifecycleMCPTests.test_refresh_uses_host_scope_and_only_named_resource_checks -q

Cycle26 host probe without explicit read-only permission must reject before
stop/journal. RED performed transition/returned held receipt instead of rejecting.
GREEN10 refresh/MCP tests3.756s; validates MCP read-only declaration first.
Command:
CODEX_WAKE_STABLE_TIME_CONFIG='' .venv/bin/python -m unittest tests.test_agent_refresh.AgentRefreshTests.test_unapproved_probe_is_rejected_before_stopping_original_client -q

Source partial gates remain: malformed proof/profile contracts, active/unknown/
split/pending-work qualification, goal counter continuity, rollback and installed
refresh native/TUI/MCP proof. No child or parent completion; no live refresh or
new model assignment performed in these cycles. Original full goal unchanged.
Memory unavailable; existing checkpoint-01-memory.json retained.
