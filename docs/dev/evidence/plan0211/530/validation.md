# Ticket #530: frozen bulk relocation

Owner: delegated bulk530; parent #526, Plan0211. Source base and exact file hashes:
[source.json](source.json). Commit containing this receipt is the frozen checkpoint.
This worker owns only new relocation/hold modules, its focused tests and this evidence.

Public seam: `TerminalRelocation(root, tabs=owner, automatic=False).execute(operation,args)`;
native boundary: disposable private tmux servers in `TemporaryDirectory`, killed by
fixture teardown. It proves whole-pane/process continuity and per-tab recovery behavior;
it does not prove installed CLI/API/MCP parity. Primary owns transport integration.

## Vertical red/green receipts

- `PYTHONPATH=src python3.12 -m unittest tests.test_terminal_relocation`: first red
  `ModuleNotFoundError: codex_wake.terminal_relocation`; first green one native test.
- Same command, empty-destination slice: red expected `moved`, actual `held`;
  green after journaled session opening and exact operation-owned bootstrap cleanup.
- Same command, retained preview/group slice: red expected `preview`, actual `held`;
  green after making status preserve unsubmitted preview state.
- `PYTHONPATH=src python3.12 -m unittest tests.test_terminal_relocation.RelocationTests.test_host_automatic_relocation_does_not_hold_but_undo_always_holds`:
  red unsupported host-only constructor keyword `automatic`; green after persisting
  trusted origin and keeping undo holds unconditional.

## Focused local validation

Final commands: `PYTHONPATH=src python3.11 -m unittest tests.test_terminal_relocation`
and `PYTHONPATH=src python3.12 -m unittest tests.test_terminal_relocation`.
Python 3.11.15 / 3.12.13, Linux/WSL private tmux. Eight tests per interpreter.
Final results recorded after completion below.

Coverage: multipane final-window transfer retains saved empty source and pane/PID
births; repeated apply reuses receipt; empty destination bootstrap removed only
after exact transfer readback; undo rematerializes original empty saved definition
and holds routing; lost native reply followed by owner reconstruction reconciles
placement without another move; partial batch preserves successes; subsequent
manual placement is skipped by undo; linked tabs rejected; saved-group membership
is frozen at preview; destination focus retained; changed whole pane set held;
trusted automatic moves do not create manual holds, while undo always does.

Journal v1 stores explicit per-effect intent before native moves and durable
placement reconciliation. Unknown source placement after a missing reply remains
uncertain, including when it appears unchanged: no blind retry. Pending entries
in interrupted batches remain unsubmitted and are not replayed. Opening a new
native destination is itself journaled by TerminalSessions; an interrupted binding
of its bootstrap remains held for operator reconciliation, never reopens blindly.

Material hosted-environment differences: source-tree focused unittest selection,
local Python builds and installed tmux; no wheel, broad suite, Windows/psmux,
provider calls, hosted Actions or production effects. Primary owns final public
transport/installed-runtime acceptance. Cross-server/psmux live moves rejected.
Session deletion is not implemented here; #533 reuses source-filtered preview
without a selection and per-tab apply results outside the registry lock.

Memory disposition: forbidden — task explicitly prohibits tracker and memory writes.

Final: both commands PASS, 8 tests each, 7.185s (3.11) / 6.983s (3.12).
No retries, shards, quarantines or failed acceptance tests in final selection.
