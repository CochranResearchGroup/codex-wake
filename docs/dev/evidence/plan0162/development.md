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


Broad first failure:1224 tests in140.839s,98 failures+4 errors. Optional tmux
metadata initially changed every inventory response shape; native lifecycle
fixtures exposed it. Make shell fields opt-in for the target workflow (not a
weakened parse). Lifecycle lane92 passed47.952s. Host default StableTime client
bypassed network-time fixture decisions; CODEX_WAKE_STABLE_TIME_CONFIG='' isolates
the declared fixture seam.23 time tests passed0.741s. Keep the first failed log;
these are diagnosed source/environment corrections, not erased flaky retries.

Isolated full suite1227 passed145.577s; final suite1229 passed125.098s, below240s
budget, one process, no sharding/retry/exclusions. After that frozen import,
read-only lost-tab-response reconciliation gained one regression (observed red)
and passed the final52-test affected selection in3.864s. No duplicate effect is
issued; unknown thread-start and tab-only creation uncertainty stays held.

Additional red→green: installed smoke asserted18 tools and failed on new tool;
now expects19 plus wake_sessions_target and passes actual installed stdio MCP
request/reply/claim/capability checks. Native own startup03 passed tab-only/fresh/
exact resume with zero model turns and empty fresh OS residue. Exact thread/read
bypasses list omission only with an explicitly supplied ID and matching CWD.
The earlier two natural-list proofs remain partial, without fabricated history.

Commands: CODEX_WAKE_STABLE_TIME_CONFIG='' PYTHONPATH=src:. <installed-dependency-python>
-m unittest discover -s tests -q; final targeted selection tests.test_tab_targets
tests.test_sessions tests.test_messages_cli tests.test_shared_app_server.
Compileall src/tests and check_policy_wiring.py PASS. New wheel built with uv and
installed only at /tmp/codex-wake-p162-install; installed fixture test process uses
repository tests on PYTHONPATH, never repository src. Identity hashes distinguish
this unreleased wheel from the active release with the same project version.

Final wheel:7 target/runtime module hashes exactly match source; owned startup04
PASS fresh/exact resume/tab-only, zero turns, fresh OS residue empty. Installed
final20 target/MCP fixtures passed2.162s. Retained opt-in harness captures startup
proof without publishing auth contents; its fixed owned path prevents accidental
re-run over existing evidence. It is not an unattended production workflow.
