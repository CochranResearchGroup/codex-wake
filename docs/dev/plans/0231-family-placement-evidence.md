# #603 | Family placement implementation evidence

Scope: `bot_family_placement.py`, focused public-interface tests. Base source:
`ee592e5dfbf7e1dc3bedc1463845ad90aed43557` (#602). Branch:
`feat/bot-family-placement`. Frozen acceptance: `0231-bot-family-spec.md` and
primary-owned `0231-family-contract.md`. Implementation commit is the commit
containing this receipt; coordinator owns integration and ticket disposition.

Implemented background open/reuse, exact prebound native attachment organization,
per-server owned workers sessions, contiguous original-root grouping, adjacent
parent override, exact self/parent/root focus, adoption and parent acceptance.
Manual placement wins after initial organization. No conversation restart or
history deletion occurs. Cleanup requires temporary, successful parent acceptance,
exact live ownership and fresh idle protection evidence. Detached session active
slots alone do not prevent cleanup; attached focus, unknown/busy/pending work,
linked windows and pins remain protected. Empty owned workers sessions are deleted.

Launch, relocation, grouping and close intentions persist before effects. Unknown
launches remain held for explicit exact rebinding. Existing relocation receipts
reconcile moved process births; close reconciliation requires an observed absent
window in the exact namespace. Unknown effects never authorize a duplicate launch,
move or close. Shell bootstrap removal only applies to this owner's first empty
workers-session materialization.

## Local checks

Red: `PYTHONPATH=src uv run --with msgspec python -m unittest
tests.test_bot_family_placement -q`: 3 failures, missing placement implementation
(after resolving the initial missing-msgspec environment error).

Green (final source):

```
PYTHONPATH=src:tests uv run --no-project --with websockets --with msgspec --with jsonschema --with dbus-next python -m unittest tests.test_bot_family_placement tests.test_bot_families tests.test_terminal_relocation -q
```

25 tests passed, 19.725 seconds. Ten new tests use the existing ControllerTabs
boundary and disposable real tmux sessions. Coverage includes background reuse,
contiguous roots, exact native placement once, manual-move retention, separate
clients, adjacent placement, unavailable parent presentation, exact parent/root
focus, adopted/failed/unknown/busy retention, last temporary cleanup, preserved bot
records, and lost launch/move/close replies without duplicate effects.

```
PYTHONPATH=src uv run --no-project --with ruff python -m ruff check --select F821,F822,F823 src/codex_wake/bot_family_placement.py tests/test_bot_family_placement.py
python -m compileall -q src/codex_wake/bot_family_placement.py tests/test_bot_family_placement.py
python scripts/check_policy_wiring.py
git diff --check
```

All passed. Local Python 3.12.13 and Linux tmux replace hosted Ubuntu's Python
3.11/3.12 matrix. Hosted CI skipped under operator cost policy. The full repository
suite and native Bots adapter join remain coordinator checks. No installed prefix,
provider, live bot, production service, native daemon or existing user session was
changed. Disposable tmux servers were terminated by test teardown. No broad review
was performed; the frozen joined review remains reserved for the coordinator.

Memory disposition: `forbidden` — delegated task explicitly prohibits memory
writes. Worktree retained for coordinator cherry-pick and validation; coordinator
owns its next custody review after integration.
