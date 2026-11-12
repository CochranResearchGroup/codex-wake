# LOCAL-P221 source validation

Source commit: `008e949f4da6f82a24e6de1a92d79d61ac1ef02d`.
Base: `95bbebb308d22eb81b9909717ed61358d16095e5` (`origin/main` readback).
Environment: Linux/WSL, tmux, Python 3.12.13 from the installed dev7 candidate;
all source checks set `PYTHONPATH=src:tests`. Working installation unchanged.

## Tight red/green loop

`python -m unittest test_tab_formatting.FormattingTests.test_enable_after_server_restart_preserves_old_baseline_and_new_rollback -v`

Before product edit: ERROR `InventoryError: Formatting baseline belongs to a
different namespace; preserve it for recovery.` After edit: PASS in0.384s.
Temporary original same-socket real server restart harness also passed in0.214s;
it was removed after diagnosis. Permanent fixture uses a new socket to eliminate
a witnessed shutdown/rebind race while exercising the same namespace fence.

## Focused checks

- `python -m unittest discover -s tests -p 'test_tab_format*.py' -q`:
  PASS100 tests,46.348s.
- `python -m unittest test_tab_psmux_formatting test_controller_tabs test_tab_targets test_tab_targets_mcp -q`:
  PASS34 tests,14.084s. psmux evidence is provider-free adapter testing.
- `python -m unittest test_ci_scope -q`: PASS1 test,4.365s.
- `ruff check --select F821,F822,F823 src scripts tests .codex/hooks`:
  PASS, pinned ruff0.14.2 in disposable tool directory.
- `python -m compileall -q src tests .codex/hooks`: PASS.
- `python scripts/check_policy_wiring.py`: PASS, errors empty.
- `git diff --check`: PASS.

Plain system Python first lacked msgspec; using the installed dependency runtime
resolved setup. One related-test invocation named nonexistent
`test_stable_tab_operations`; corrected to the actual34-test selection above.
Neither setup error was treated as a passing test.

## Packaged public CLI acceptance

`python -m pip wheel --no-deps --wheel-dir /tmp/codex-wake-p221-wheel .`
PASS. Wheel SHA256:
`35a8265210e7cf7373d1f3d2554fafd015e56ac9efbd3df29582ceccc60f09a0`.
The wheel's `codex_wake/tab_formatting.py` exactly matches the source commit.

Installed only into a disposable `/tmp` package directory. A throwaway CLI harness
used `python -m codex_wake.entrypoint --wake-root FIXTURE tabs ... --json` against
a private tmux socket. It enabled, stopped the fixture monitor, replaced the
server, observed stale status, enabled again, checked terminal/completed/applied
journal state and a running monitor, verified native formatting, then rolled back
to exact replacement originals with unchanged pane identity. PASS. Fixture
monitor and server were stopped; harness removed. No working service restarted.

## Boundaries and custody

Focused validation only; no comprehensive suite, Python3.11, native Windows or
provider acceptance claim. No hosted Actions by operator cost policy. Local Linux
and existing dependencies differ from the hosted3.11/3.12 clean environments;
OpenClaw/plugin and unrelated smoke lanes were not run. No merge, source push,
release or working-host installation occurred. Source review checkout retained
for the integration decision; original dirty main remains preserved.
