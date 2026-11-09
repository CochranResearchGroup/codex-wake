# Plan 0211 / issue 531 — routing implementation evidence

Scope: persistent prioritized routing and the existing tab monitor hook. Source
base is `2a91b5c` in `/tmp/codex-wake-session-531`, branch
`feat/terminal-session-531`; this base contains primary-owned shared contracts,
deadline propagation, saved-session factory restoration and read-only hold enumeration. The routing delta
is `terminal_routing.py`, `tab_monitor.py` and `test_terminal_routing.py`.
No merge, deployment, installed runtime, provider, model, production terminal,
Windows-native runtime, hosted CI, tracker mutation or memory write is qualified.

## Behavior and portable field contract

Operations are `tabs.route.list/show/save/delete/enable/pause/tick/status/hold/`
`resume/pin/unpin`. The primary owns CLI/API/MCP schema and dispatch wiring.

- `save`: required `name`, `destination`, `selection`; optional `rule_id`,
  `priority` (integer, -1000000 through 1000000; default 100),
  `stability_seconds` (finite 0 through 3600; default 10). Saves and edits are
  paused until explicitly enabled. Lower numerical priority wins.
- `show/delete/pause`: identify by `rule_id` or unique `name`.
- `enable`: identify by `rule_id` or `name`; `include_existing` defaults false.
  The response previews `existing_matches`, frozen birth references are excluded
  by default, and only new eligible tab births can route afterward.
- `hold/resume/pin/unpin`: require an explicit bounded JSON `selection`;
  optional bounded `reason`. `resume` clears an ordinary hold; pins require
  `unpin`. Each explicit control acknowledges present placement so resumption
  does not immediately recreate the same external-move hold.
- `list/status/tick`: no user arguments. `expected_target` and `_request` are
  accepted for the shared controller envelope; target fencing happens under
  the routing lock. Tick is mutating; read-only status performs no reconciliation
  or native cleanup.

Rules return `rule`/`rules`, with stable `id`, session-identity `destination`,
`selection`, `priority`, `stability_seconds`, `enabled`, `revision`, `excluded`
and timestamps. Tick returns `status`, `outcomes`, `pending`; incomplete routing,
conflicts and held work return `partial`. Status returns rule definitions, the
last outcomes and pending receipts, pins, all durable holds and monitor state.

Canonical durable state is `terminal-routing/routing.json`; rule provenance
is retained in `terminal-routing/plans/{plan_id}.json` with `identity`,
`rule_id`, `rule_revision`, original `selection` and exact native relocation
`plan_id`. Holds retain the existing `terminal-tab-holds/holds.json` owner.
Rules reference immutable destination identity, and unavailable destinations
are disabled rather than rebound to reused names. Rule/trait changes and
backward clocks reset stability; stale/unavailable monitor rows cannot
accumulate stability. Pending native receipts reconcile before new dispatch;
uncertain effects block further automatic dispatch.

The existing service-owned monitor publishes `tab-routing-v1` and a compact
`last_routing` summary. Injected inventories do not start a daemon. A running
legacy monitor missing the capability is reported as
`partial/monitor_upgrade_required` and is never restarted implicitly. The
monitor passes its existing snapshot and remaining cycle deadline; native
observations remain soft bounded at existing adapter boundaries, while expired
budgets prevent new dispatch. No hard preemption of arbitrary external calls
is claimed.

## TDD and first failures

Public seams: routing owner/controller operations, durable restart, disposable
private tmux, real monitor start/status/stop. Time is injected for deterministic
stability; interrupted native replies are injected only at the native command
boundary. No sleeps determine trait stability.

1. `PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest tests.test_terminal_routing -v`
   initially failed importing the missing routing module. The first implemented
   vertical slice passed future-tab routing while preserving existing births.
2. The interrupted-move test failed because reconciliation treated an already
   completed automatic placement as an external manual move. Updating confirmed
   placement from the original retained receipt fixed the observed defect;
   only one move was submitted across restart.
3. The actual daemon test with ordinary configured workspace names failed with
   source placement unchanged. Primary commit `3cd8a88` (local cherry-pick
   `ac92162`) repaired duplicate native aliases and saved-session factory
   restoration; the same service-owned test then passed.
4. The first concurrent dual-Python selection had 3.11 pass 29 tests in
   38.747s and 3.12 fail one readiness assertion in 36.520s. The assertion
   incorrectly treated any reported routing outcome, including a budget-held
   partial outcome, as move completion. Readiness now requires the actual native
   source-window placement before asserting success, within an eight-second
   bound. Test cleanup stopped its daemon and killed only its private server;
   there was no ambiguous shared effect to retry. Final lanes run serially.

5. The public controller assertion for a manual bulk hold created before any
   routing activation failed with an empty hold list. Primary commit `cf2d88c`
   (local `2a91b5c`) provides read-only `TabHolds.list()`; route status now uses
   that public enumeration. The changed controller test is rerun on both Python
   versions below, without repeating unaffected native acceptance.

## Final focused validation

Command for each interpreter:

```sh
PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest tests.test_terminal_routing tests.test_terminal_routing_deadline tests.test_terminal_selection_cli tests.test_terminal_relocation tests.test_tab_selection tests.test_tab_monitor -v
PYTHONPATH=src /tmp/codex-wake-p210-py311/bin/python -m unittest tests.test_terminal_routing tests.test_terminal_routing_deadline tests.test_terminal_selection_cli tests.test_terminal_relocation tests.test_tab_selection tests.test_tab_monitor -v
```

- Python 3.12: 29 passed, 35.208s, serial focused lane.
- Python 3.11: 29 passed, 33.845s, serial focused lane.
- `/tmp/codex-wake-p210-py312/bin/python -m ruff check --select F821,F822,F823 src/codex_wake/terminal_routing.py src/codex_wake/tab_monitor.py tests/test_terminal_routing.py`: passed.
- `/tmp/codex-wake-p210-py312/bin/python -m compileall -q src/codex_wake/terminal_routing.py src/codex_wake/tab_monitor.py tests/test_terminal_routing.py`: passed.
- `git diff --check`: passed.

These are focused local source checks, not the full suite or an immutable-wheel
installation qualification. Compared with hosted Ubuntu CI, this is the current
WSL/Linux host using pre-existing Python 3.11/3.12 environments and native tmux.
The full-suite, OpenClaw, build/release and Windows lanes were excluded by the
bounded assignment. Hosted GitHub Actions were not started or purchased.

Memory disposition: `forbidden` — the delegated scope explicitly prohibits
memory writes. Issue 531 remains open for primary integration and review.

Changed public-controller hold visibility follow-up (after the two 29-test lanes):

```sh
PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest tests.test_terminal_routing.RoutingTests.test_public_controller_rules_use_management_target_fences_and_reject_implicit_all_tabs -v
PYTHONPATH=src /tmp/codex-wake-p210-py311/bin/python -m unittest tests.test_terminal_routing.RoutingTests.test_public_controller_rules_use_management_target_fences_and_reject_implicit_all_tabs -v
```

Both passed: 3.12 in 1.413s; 3.11 in 1.384s. The only post-lane behavior
change is replacing tracked-hold enumeration with the public complete hold list.

Source-content SHA-256 at validation closeout:

- `src/codex_wake/terminal_routing.py`: `1997b1b704d3361e2dee8927e2610d7d9056057c8f6ef45c3db7015b4468a171`
- `src/codex_wake/tab_monitor.py`: `0f9270ce53eb44fbbd9743aa916a0373edf694514459b13589701705cb8399ed`
- `tests/test_terminal_routing.py`: `1a4befd65a85b502b4386fffc2c3e13e8e5ec181b3831460ba399e4aa55c3a33`

Fresh OS process readback after cleanup: 0 remaining owned routing-test monitor/tmux processes.
