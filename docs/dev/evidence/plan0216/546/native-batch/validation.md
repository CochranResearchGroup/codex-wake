# Bounded native formatting cohorts and selective process fencing

Base source `61665a89`, branch `fix/observer-native-batch-546`. The deferred-resource
loader correction was separately committed as `0abec5da`. No production terminal,
monitor, provider or service configuration was changed.

The corrected steady active profile identified 80 native formatting batches over
ten ticks (0.421 seconds) and full-roster process generation checks despite only
two changed conversations per second. Selected profile data and artifact hashes
are retained in profile-and-guards.json. These are profiled diagnostic timings,
not passing CPU-gate measurements.

## Change and safeguards

The existing native attachment now advertises its finite formatting_batch seam.
Every member is validated before any effect; only existing managed window option
reads/writes are accepted. Four-window cohorts bound worst-case 8KiB option
readbacks below the existing 1MiB output limit (within the approved limit of at
most16). A cohort read uses one native client. Writes and complete explicit,
effective, inherited-parent and exact-window readbacks also share one client.
All original baselines remain fsynced before first native writes. Existing
psmux/generic and deliberately overridden host adapters keep their prior paths.

Failures are isolated with read-only reconciliation; a mutating cohort is never
replayed. Live members can be confirmed after a sibling disappears, while absent
or mismatched members return errors. Native CLI trailing-semicolon escaping keeps
literal format values, including a bare semicolon and newline, intact rather than
allowing them to become command separators. The shared _command_batch signature
and body remain unchanged for the primary's capture batching integration.

Session custody is still read before window effects. A valid already-owned lease
with at least15 seconds remaining is reused; normal active deltas do not reset its
20-second deadline. Native lease writes follow verified window readbacks. If a
failed changed window may retain an old dynamic cue, its lease is not extended.
Unowned failures or unchanged valid projections need not prevent safe renewals.
The independent five-second quiet renewal and native publisher-death expiry remain.

The read-only lifecycle inspection has an optional window_ids selection. Default
lifecycle/input callers still fence every process. Formatting keeps the complete
window roster but freshly fences only changed/audited windows. Unchanged windows
reuse a verified cached birth only while current native pane metadata matches
exactly and no native window effects are needed. Unexpected replacement escalates
to a second bounded inspection; continued churn refuses before effects. Missing
or replaced observations still lose old claims, and all_window_ids/current_windows
retain complete native membership for audits and rollback.

## Red/green public checks

A real private four-window test initially started11 native processes for two
dirty windows. Native cohorts plus lease reuse reduced this to at most6. The
intermediate test then failed because unchanged panes were still freshly checked;
selective inspection now reads only the two dirty PID stat files, verified at the
real procfs boundary. Rollback remains exact.

A separate native fault test initially demonstrated a correctness defect: after
source loss, a refused cue-clear write still advanced the old RUN lease by six
seconds. Deferred lease commit now leaves that old deadline untouched. This is a
product ordering fix, not a relaxed test or a disabled source-loss check.

Additional public adapter/native tests cover inherited values and parents, literal
readbacks, all-member validation before any write, disappeared windows, no replay
of a partially applied write cohort, full default lifecycle fencing, and process
replacement outside the initially selected dirty set. Existing manual custody,
source-loss, preset, rollback and reenable tests remain in the affected selection.

Commands and final outcomes:

- `PYTHONPATH=src /tmp/wake216-py311/bin/python -m unittest discover -s tests -p 'test_tab_format*.py' -q`: 70 passed in17.767 seconds.
- Same selection with `/tmp/wake216-py312/bin/python`: 70 passed in17.843 seconds.
- `test_tab_lifecycle.py` after fixture correction:8 passed on Python3.11 in1.449 seconds and Python3.12 in1.897 seconds.
- Undefined-name lint for affected source/tests and `git diff --check`: passed.

The first Python3.11 lifecycle run failed with stale_target during bare-shell
startup; its original log is retained. A bounded public inspection probe reproduced
it immediately: exact window/PID/birth/TTY/cwd/name stayed fixed while the operator's
startup hook changed pane_current_command from ln to zsh. The disposable fixture
now selects a plain /bin/sh without login/profile hooks and removes its ENV startup
hook. No product generation check was weakened and no automatic operation replay
was added. This fixture isolation is distinct from the selective read-only product
path. A passing retry was not used to erase the first failure.

Hosted CI was skipped under repository cost policy. These are focused functional
checks, not a full-suite, installed-package or resource acceptance claim. The
primary must still stage the exact combined source, measure the actual service
with all tiers/100tabs, and run the immutable package gates. CPU caps remain1% idle
and5% active; no cadence or threshold was relaxed here.

No broad review, tracker closure, merge, deployment or memory write was performed.
The primary owns the final single closeout memory disposition.
