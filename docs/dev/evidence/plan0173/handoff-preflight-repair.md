# Handoff preflight bounded diagnosis

## Scope and outcome

PR #341 handoff-only diagnostic lane, revision observed after the probe:
`e6e2227c63f3b7cc22a6a921db686b5a1e78ba9c` (shared checkout; concurrent primary changes may advance it).
No production or test behavior changed. The existing fixture now retains the latest
real session snapshot and attachment revalidation result in the assertion diagnostic;
the wrappers return the real results unchanged. The capture clears stale revalidation
when a new snapshot arrives. The two original comprehensive failures remain
unresolved flakes; twenty focused executions passed and do not erase the failures.
CI and another comprehensive suite were not run by this lane.

## Preserved first failure

Original artifact:
`~/.local/state/codex-wake/next-frontier-final-validation/frontier-full312.log:488-511`.
Both assertions expected `awaiting_activation`, observed `awaiting_preflight`, with
successor reason `exact_idle_owned_client_not_ready` and zero respawns. Original
1647-test/529-second run remains the first-failure authority.

## Actual bounded probe

Working directory: `/home/ecochran76/workspace.local/codex-wake-next-frontier`.
Interpreter: `/home/ecochran76/workspace.local/codex-wake-harness-frontier/.venv/bin/python`.
Executed once, with the explicit maximum of ten iterations:

```sh
PYTHONPATH=src:tests /home/ecochran76/workspace.local/codex-wake-harness-frontier/.venv/bin/python - <<'PY'
import unittest
names = [
    'test_agent_handoff_preflight.HandoffPreflightTests.test_one_successor_runs_preflight_without_two_active_goals_or_duplicate_assignment',
    'test_agent_handoff_preflight.HandoffPreflightTests.test_pinned_task_brief_reaches_successor_preflight',
]
for i in range(10):
    print('ITERATION', i + 1, flush=True)
    result = unittest.TextTestRunner(verbosity=1).run(
        unittest.TestLoader().loadTestsFromNames(names))
    if not result.wasSuccessful():
        break
PY
```

Observed: ten iterations, two tests each, all `OK`; iteration durations were
4.595, 4.765, 3.286, 3.483, 3.388, 3.222, 3.359, 3.626, 4.905, and 4.612 seconds.
This command drives the actual CLI/native-socket/PTY path and exact failing assertion,
but it did not reproduce the failure. No ranked causal hypotheses or hypothesis tests
were undertaken: the diagnosing-bugs skill requires actual reproduction first.

The fixture isolates XDG config/state in `setUp`, creates private native sockets and
PTY-backed clients, waits for each client's explicit `ready` signal, and tears clients
and descriptors down in its `finally` block. No live providers, production services,
shared CLI/MCP changes, additional agents, or global mutations were used.

## Exact missing evidence and next bounded step

`src/codex_wake/agent_lifecycle.py` uses this single reason for multiple independent
checks: snapshot completeness, exact row/attachment counts, pane identity, cwd,
idle status, direct-input eligibility, active flags, and attachment revalidation.
The original history records only the aggregate reason, so it cannot identify which
predicate failed. The process fixture already prints readiness after setting its
`comm` to `codex`; adding arbitrary sleeps would be unsupported.

The fixture diagnostic now captures the observation at this boundary:
source availability/error codes, successor row and attachment (including process
PID/generation), and the attachment-revalidation result. The capture is bounded to the private failing fixture and appears only in failure output. A future bounded reproduction should preserve
that first failing capture and compare it against the fixture's exact owned process
and PTY. No source relaxation, fixture sleep, or retry increase is justified by the
present evidence.

Memory disposition: `not_durable` — bounded probe is incomplete diagnostic evidence;
this artifact retains the exact unresolved gate for the primary lane.

## Additional ordering probe

Executed whole-module focused probe:

```sh
PYTHONPATH=src:tests /home/ecochran76/workspace.local/codex-wake-harness-frontier/.venv/bin/python -m unittest test_agent_handoff_preflight
```

Result: **51 tests in 117.817 seconds; one failure**,
`test_preflight_crossing_original_deadline_cannot_prepare_a_goal` expected `expired`
but observed `awaiting_preflight`. Both originally failing tests passed. Preserved log:
`~/.local/state/codex-wake/next-frontier-final-validation/handoff-module-diagnosis.log`.
That branch's original assertion did not include readiness details, so the exact
reason was not captured; this cannot yet be classified as the same underlying bug.
The expired-state assertion now includes the receipt and the same bounded diagnostic.

The failing deadline test passed isolated once (1.501 seconds), retained at
`~/.local/state/codex-wake/next-frontier-final-validation/handoff-deadline-diagnosis.log`.
A minimized ordering candidate, the deadline test and its four alphabetic predecessors,
passed all three bounded iterations (five tests each; 7.455, 7.080, 8.411 seconds):
`test_non_github_review_accepts_evidence_without_changing_native_guards`,
`test_one_successor_runs_preflight_without_two_active_goals_or_duplicate_assignment`,
`test_pinned_task_brief_reaches_successor_preflight`,
`test_preflight_allowance_must_fit_before_creating_a_successor`, and
`test_preflight_crossing_original_deadline_cannot_prepare_a_goal`.
Log: `~/.local/state/codex-wake/next-frontier-final-validation/handoff-neighbor-diagnosis.log`.

The primary lane separately observed backward host wall-clock steps in another guard.
This is advisory cross-lane evidence, not a demonstrated cause of the handoff failures.
The handoff diagnostic now captures wall time, monotonic time, the real session
snapshot timestamp, and the fixture's native clock bounds, allowing a future red
observation to test this prediction without changing any guard or readiness semantics.
The fixture already sets process identity before printing its readiness signal, and
`launch` waits for that signal before adding pane inventory. No missing asynchronous
process startup handshake was established by source inspection.

Final diagnostic smoke: three affected tests passed in 5.581 seconds, exit 0;
final diagnostic patch also passed `git diff --check`. Log:
`~/.local/state/codex-wake/next-frontier-final-validation/handoff-final-diagnostic-smoke.log`.
No actual failing observation has yet supplied the required guard predicate, so no
ranked causal diagnosis or production fix is claimed. The primary lane may retain
the diagnostic for its already-authorized single comprehensive run.
