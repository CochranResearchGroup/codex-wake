# Handoff preflight bounded diagnosis

## Scope and outcome

PR #341 handoff-only diagnostic lane, revision observed after the probe:
`e6e2227c63f3b7cc22a6a921db686b5a1e78ba9c` (shared checkout; concurrent primary changes may advance it).
Final repair changes fixture transition expectations only; production remains unchanged.
The fixture now allows one explicitly verified readiness deferral within its existing
two-call scenario bound and reconciles the same intent. The existing fixture retains the latest
real session snapshot and attachment revalidation result in the assertion diagnostic;
the wrappers return the real results unchanged. The capture clears stale revalidation
when a new snapshot arrives. Earlier failures remain preserved below; focused passes
do not erase them. The final causal probe and repair appear in the final section.
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

## Earlier missing evidence gate

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

Memory disposition is owned by the primary closeout; this lane makes no memory write.

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

## Earlier primary reconciliation after comprehensive join

The single authorized comprehensive join at17c1d4c passed1651tests/636.042s,
OK(skipped1). This is a current passing run, not proof that the earlier handoff
failure was fixed. No production source repair is supported; issue342 remains
open for the exact readiness predicate on a future occurrence. No repeated full
suite, quarantine or weakened guard is used to relabel the intermittent history.
The retained assertion diagnostic now deep-copies native-clock bounds so later
fixture mutations cannot rewrite the observed evidence. Full join covered the
prior equivalent diagnostic; the copy-only correction receives focused smoke.

## Exact original red, ranked probes, and semantic fixture repair

A later focused smoke reproduced the exact original test failure naturally:
`/tmp/validation-repair-final-diagnostic-smoke.log`, three tests in 14.284 seconds,
one failure. The observation was incomplete solely because tmux reported
`SharedSourceError`; native source and target were idle/direct-input eligible but
had zero attachments. Native observation timestamp was `04:07:00.152161` and tmux
observation was `04:07:03.214527`, an elapsed 3.062 seconds. The configured fixture
inventory timeout is **one second**, not three seconds. Backward wall-clock steps
in another lane do not directly trigger this inventory's monotonic deadline.

Ranked falsifiable hypotheses were sent before probes:

1. Real `/proc` identity scan consumed the inventory deadline: identity timings
   would dominate, and exact exception would be `tmux observation timed out`.
2. Fixture tmux command/output consumed budget or was malformed: command time
   would dominate, or exact exception would identify parsing.
3. Scheduler delay consumed budget: inventory elapsed would exceed one second
   despite short command/identity work.

Three isolated original-test iterations passed, then the original three-case
selection passed in 6.788 seconds. No additional natural failing exception was
captured in those bounded probes. Their logs are `/tmp/handoff-single-timing-probe.log`
and `/tmp/handoff-three-timing-probe.log`.

The deterministic matched-path probe (archived as `handoff-budget-probe.py` in the
private diagnostic directory below; temporary executable removed after use) runs the real
source and target fixture processes, real `/proc` uniqueness/start-tick checks,
and real inventory code. It advances only the sessions-local monotonic observation
budget after the first real identity scan in a two-pane inventory. With no injection,
the case passes; with the injected budget exhaustion, the exact original
`awaiting_preflight` / `exact_idle_owned_client_not_ready` appears, snapshot is
incomplete, and the captured exception is **`tmux observation timed out`**.
Log: `/tmp/handoff-budget-probe.log`. This establishes the matching timeout path;
it does not distinguish CPU work from host scheduling in the natural red.

Healthy timing baseline from that probe: six inventories, per-pane identity scans
62–76 ms, two-pane inventory totals 131–145 ms, non-scan overhead below 0.3 ms,
leaving approximately 855–869 ms of the one-second two-pane budget. The injected
probe retained all process identity checks and matched the actual source failure
shape without raising budgets or relaxing a production guard.

Production correctly defers admission on incomplete inventory. The fixture's
unconditional immediate-readiness expectation was incorrect. The existing
one-successor test now deterministically forces that single timeout and asserts:
`awaiting_preflight`, one `thread/start`, zero `thread/queue/start`, and no successor
goal. It then reconciles the same intent once, within the existing two-call bound,
and requires successful activation readiness and exactly one queue assignment.
A second readiness deferral still fails; no polling loop or sleep was added.
Other scenarios recognize this same exact safe transient within their existing
bound, retaining all later state and budget assertions.

Retained regression red before the semantic change: one test in 0.972 seconds,
`/tmp/handoff-controlled-regression-red.log`. After repair, three affected tests
passed in 7.270 seconds: `/tmp/handoff-controlled-regression-green.log`.
The first affected-module validation failed six cases in 217.428 seconds;
`/tmp/handoff-module-after-semantic-repair.log` preserves those failures. No further
comprehensive run was started by this lane. Source `sessions.py` remains unchanged. The earlier primary
full pass is historical evidence for the pre-repair revision, not final-patch proof.

The final natural-red log, bounded probe logs, controlled red/green logs, and
throwaway budget probe script are also retained in the private diagnostic directory
`~/.local/state/codex-wake/next-frontier-final-validation/handoff-diagnostics/`
with the same basenames, so temporary-file cleanup does not erase this evidence.

## Natural timeout confirmed; fixture observation clock isolated

The post-semantic module supplied the previously missing exact natural exception.
Examples: `test_lost_source_restore_response_observes_existing_generation_without_respawn`
measured **1.420987 seconds** in the source-pane identity scan, followed by
`SharedSourceError: tmux observation timed out`; two other natural failed cases
measured **1.738009** and **1.729529 seconds** in that same scan. Each exceeded the
fixture's one-second budget before target identity inspection. These are real
monotonic durations, with no synthetic budget injection in those cases. This
confirms the first ranked hypothesis at the scan boundary; CPU work versus
scheduler delay inside that scan remains undistinguished and is unnecessary for
this fixture repair.

Semantic reconciliation alone does not isolate all other scenarios: rollback and
source-admission observations also use the same budget. Therefore the final fixture
uses a sessions-local deterministic monotonic observation clock throughout each
inventory. Its base advances across inventories and preserves monotonic ordering.
The explicit controlled regression still advances that clock by two seconds after
a real source identity scan, producing the real timeout guard and testing safe
deferral plus same-intent reconciliation. All `/proc` uniqueness/start ticks,
PTY generation, native-idle state, composer, input and budget guards remain real;
production timeout behavior and source files are unchanged. No timeout was raised,
retry bound increased, or sleep added.

A three-case final smoke (controlled regression and two naturally failing cases)
passed in **10.720 seconds**, `/tmp/handoff-clock-isolated-smoke.log`. Final affected
module passed **51 tests in 205.689 seconds**, exit 0, at
`/tmp/handoff-module-final-clock-isolated.log`. `git diff --check` passed. This is
focused affected-module proof for the final fixture, not a repeated comprehensive
suite or a claim that production observation cannot defer under host load.
