# Integrated formatting regression diagnosis

Input source: `72bda0b7`, branch `test/observer-format-diagnosis`.
This is bounded diagnosis of the first dual-version presubmit failure, not the
reserved broad code-review pass. No product source was modified.

The first Python 3.12 presubmit failed 1 of 185 tests after 57.418 seconds:
`test_unqualified_running_monitor_is_partial_exit_without_restarting_it` indexed
a null retained operation result. The original log is preserved unchanged in
`first-presubmit-312.log`; the Python 3.11 selection passed. Standalone retry
passing did not clear this failure.

## Bounded feedback loop

A diagnostic assertion now includes actual CLI stdout/stderr before indexing a
null result. Ten pairs of the exact Python 3.12 failing test alongside Python
3.11 `test_tab_format_monitor` all passed. Their zero reproduction rate is
preserved in `bounded-pairs.log`; it is not clean-retry evidence for the original
suite failure.

Ranked falsifiable causes were: (1) SIGSTOP freezes the monitor while it owns the
formatting lock, producing `formatting_busy`; (2) a concurrent owner-record
replacement overwrites the synthetic capability change; (3) pre-effect target
identity changes cause refusal. The public operation reason distinguishes these.

One further causal probe used a real disposable tmux server and real monitor.
It paused only the fixture monitor PID after `/proc/locks` proved that process
held the exact formatting lock, then verified the lock remained held while
stopped. The same CLI returned exit 3, `phase=uncertain`,
`reason=formatting_busy`, and `result=null`. This reproduces the exact original
null-result symptom and identifies a fixture scheduling defect: start publishes
an owner before its first formatting cycle has completed, and SIGSTOP may strand
that cycle's lock. The probe resumed and cleaned up its owned monitor/server.
The actual public payload is in `frozen-lock-public-payload.json`; `freeze_probe.py`
is retained for replay. No private runtime or production socket was involved.

## Repair and validation

The test now starts its owned monitor with a long interval (300 seconds,
stale_after 600), waits through public monitor status for a completed formatting
cycle and terminal routing record, then freezes it during the idle interval.
No arbitrary startup delay, product lock mock or weakened acceptance is used.
The synthetic missing-capability check, partial exit and exact unchanged monitor
process identity assertions remain intact. The diagnostic assertion is retained.

The corrected exact test passed on Python 3.11 in 0.745 seconds and Python 3.12 in
0.496 seconds. Logs are `fixed-311.log` and `fixed-312.log`. This is a targeted
repair validation; it does not relabel the original presubmit as passing or claim
the full suite was rerun. `git diff --check` and undefined-name lint passed.

No product fix, package rebuild, merge, deployment, live formatting change or
tracker closure was performed by this worker. The primary owns final integration
validation and the single closeout memory disposition.
