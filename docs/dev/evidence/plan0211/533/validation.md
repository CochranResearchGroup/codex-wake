# #533 explicit populated terminal-session deletion

Implementation source commit: `6c7a1cf05044831449306205433231d5dd0f74f0`.
Base: `1b8b224ca2dac73a70fc3ba784ece83a82db742b`.
Worktree: `/tmp/codex-wake-session-533`; branch `feat/terminal-session-533`.
Scope: #533 under [Plan0211](../../../plans/0211-2026-11-09-terminal-session-management.md)
and the retained [ticket](../ticket-07.md). Source implementation only; primary
owns integration/shared contract and #534 owns installed transport/native acceptance.

## Behavior and custody

`tabs.session.delete` delegates before taking the session registry lock to a
private, atomic/fsynced deletion journal. Empty deletion retains its existing
meaning. Populated deletion requires either `destination` or `terminate:true`.
Termination freezes whole-window/pane/process births and server birth before
first native intent, then invokes existing finite `tabs.close` with exact target
and explicit force. Windows panes use native creation filetime; tmux panes use
process generation. Drain uses the existing frozen relocation plan outside the
registry lock. No restart/copy fallback or new native bridge command exists.

Per-tab outcomes remain in the private plan. Partial/uncertain operations retain
the saved definition, reconcile on repeated ID/name/plan selection, and never
redispatch an uncertain close or move. New tabs/changed births remain untouched.
Definitive preflight rejection retains its journal history but clears the saved
active-plan pointer, permitting a later explicit choice. Completed deletion keeps
a tombstone and can reconcile a crash after the tombstone commit.

Primary authorized the one public routing-owner hook
`TerminalRouting.disable_deleted_destination(session_id)`. It verifies the
registry tombstone, locks routing state, disables rules referencing the retired
stable ID with `destination_deleted`, increments revision, and retains history.
Cleanup occurs outside the registry lock and repeats safely after restart.
Primary also authorized the single existing routing-test expectation change from
`destination_unavailable` to the immediate `destination_deleted` reason.

Shared contract requirements for primary: deletion arguments `session`, optional
`server`, optional string `destination`, boolean `terminate`, optional string
`plan_id` (`delete_` plus 32 lowercase hex). `destination` and `terminate:true`
are mutually exclusive. `plan_id` resumes/reconciles the frozen original intent.
Existing `expected_target` and `_request` handling remains accepted. No new public
operation, CLI parser, controller, relocation or bridge edit was made here.

## Focused local validation

Environment: local Linux/WSL user, disposable private tmux sockets, Python3.11 and
Python3.12 environments supplied by primary, `PYTHONPATH=src`. No providers,
production sessions, installed package changes or hosted GitHub CI. Material
hosted-environment difference: local Linux only; Windows-native psmux and installed
CLI/API/native-MCP/OAuth-MCP parity remain #534 qualification.

Commands (run from the worktree):

- `PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest tests.test_terminal_session_delete -q`
  final source selection: 8 tests PASS, 10.613s.
- `PYTHONPATH=src /tmp/codex-wake-p210-py311/bin/python -m unittest tests.test_terminal_session_delete -q`
  final source selection: 8 tests PASS, 10.762s.
- `PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest tests.test_terminal_session_delete tests.test_terminal_routing.RoutingTests.test_deleted_destination_disables_rule_and_never_rebinds_reused_name -q`
  9 tests PASS, 11.714s, before the final additional explicit server-birth dispatch guard.
- Same preceding command with `py311`: 9 tests PASS, 10.656s.
- `git diff --check`: PASS.

Tests cover explicit termination and peer process-birth preservation, drain
process/pane continuity, tombstone/name reuse, public rule listing and refusal to
reenable an old destination, OS-boundary lost-close reply and restart,
uncertain-before-close no replay, name reentry preserving intent, partial drain
preserving enabled rules and saved source, tombstone-commit crash recovery, and
rejected destination followed by explicit termination.

The initial adjacent selection was:
`PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest tests.test_terminal_session_delete tests.test_terminal_sessions tests.test_terminal_relocation tests.test_terminal_routing -q`
(and the same with `py311`). Each ran 35 tests; each had exactly one failure, the
old routing disabled-reason assertion above (34.724s and 47.558s). The authorized
semantic assertion update was qualified by the focused reruns; the entire35 was
not repeated. This is focused affected-surface validation, not comprehensive or
installed/live acceptance.

## Retained first failures and disposition

- Initial `...py312/bin/python -m unittest tests.test_terminal_session_delete -v`:
  one test ERROR, `InventoryError: Unsupported session arguments.` at explicit
  `terminate=True`, before implementation. Green after delegation/owner delivery.
- Tombstone-crash single test, red: `target_not_found` after committed registry
  tombstone but before deletion-plan completion. Green after tombstone reconciliation.
- Name-reentry single test, red: two different `delete_<id>` values on repeated
  name selection. Green after resolving the stable saved session before reusing
  its active deletion plan.
- Rejected-destination single test, red: later explicit termination still tried
  the old missing drain destination. Green after definitive preflight rejection
  releases only the active-plan pointer, retaining rejected history.
- Early four-test run had a test-input error: `selection={'all':[]}` is invalid;
  corrected to the valid empty explicit selection `{'tabs':[]}`.
- One eight-test run failed name-reentry sent count (`0 != 1`): native close was
  held before dispatch. The fixture previously allowed tmux background automatic
  window renaming, which can invalidate the exact snapshot target. Repair:
  disable automatic-rename in the disposable namespace, preserving product fences.
  Subsequent dual-Python focused9 and final focused8 selections pass; no assertion
  was weakened and the failed result is retained here rather than erased by retry.

Final fresh process readback (`ps -eo pid,ppid,args`, filtered to this owner's
`tmux -S /tmp/wake-delete-` namespaces): zero remaining owned tmux processes.
All fixture server teardown is scoped to its generated private socket.

Memory disposition: `forbidden` — assignment explicitly prohibits memory writes.
No tracker writes, ticket closure, merge, deployment, full suite, broad review or
provider/live/Windows acceptance was performed.
