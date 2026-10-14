# Plan0162 development evidence

Base:5b14c05 (unmerged lifecycle dependency); main readback439f749.
Worktree:/home/ecochran76/workspace.local/codex-wake-tab-targets.

Public seams: sessions resolve/target CLI, MCP CommandRunner with real CLI and
injected inventory, capability-checked mailbox CLI with actual fixture database.
Injected provider evidence proves source behavior, never live runtime acceptance.

Red→green commands used PYTHONPATH=src python -m unittest with:
- tests.test_tab_targets: initial1 test had3 failed descriptors and1 missing
  resolution field; implementation then17 resolver+existing tests passed.
- .TabTargetTests.test_target_conditions_distinguish_missing_dormant_busy_and_cwd:
  missing module/operation failed5 cases; target implementation then18 passed.
- .TabTargetTests.test_saved_history_is_cwd_scoped_complete_and_metadata_only:
  missing saved_threads failed; metadata reader then30 related tests passed.
- .TabTargetTests.test_nondefault_policy_requires_host_scope_before_any_effect:
  no_live_codex instead of policy_denied failed; guard then5 target tests passed.
- .TargetLifecycleTests: missing preparation seam failed; zero/multiple histories
  then passed. Fresh and tab-only failed with policy_denied; journaled preparation
  then8 target tests passed.
- .HumanSendTests: missing target result failed; real mailbox routing then16
  target+messages tests passed. Retries after tab replacement hold the original
  route and retain one original envelope.
- tests.test_tab_targets_mcp: unknown_tool failed; registered MCP target and
  real CLI dispatch then4 MCP/lifecycle tests passed.

Focused combined command (recorded in focused.log): PYTHONPATH=src:.
/home/ecochran76/.local/share/codex-wake/releases/0.13.1-241d7a4/bin/python
-m unittest tests.test_tab_targets tests.test_tab_targets_mcp tests.test_sessions
tests.test_messages_cli tests.test_shared_app_server tests.test_lifecycle_mcp
tests.test_a2a_mcp -q:52 passed in6.495s, no retries, no live effects.
This is a selected source lane with installed dependency environment, not full
suite, installed package proof or parent lifecycle acceptance.
