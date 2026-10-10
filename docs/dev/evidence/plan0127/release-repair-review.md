# Plan0127 release audit repairs

Baseline: canonical0a05c661d3dd854831614ab77ee732aa7f96b351.
Spec: Plan0127 execution contract and native delivery/migration tickets0128/0132.
Owning lane: release/native-workflows-closeout; primary serial review.
Repo-local tickets remain the work-item authority; no remote issue is required.

## Findings and disposition

- R1 blocking: installed accepted native record reports attempts0 despite its
  native_submission_started event. Count one durable intent before external
  submission; reconciliation must not increment. Earlier records remain raw.
- R2 blocking: live0.9 monitor advertises reader schemas1/2 instead of1/2/3/4.
  Advertise the package's shared read-version contract, without implying every
  trigger/transport has native replacement parity.

Both fixes are source-qualified below. Installed supervisor readback and new
normal-root dispatch remain required before the findings close.

## Standards

PASS for the bounded source diff: existing lifecycle lock and atomic record
replacement retain custody; the counter and nonce are persisted together before
the external effect. Counter validation is native-only, rejects bool/string/
negative values, and does not coerce or rewrite malformed legacy state. Monitor
uses existing schema_summary rather than another version authority. No broker,
new storage, thread replacement, transport fallback or unrelated refactor.
Existing tests protect the changed observable contracts. No accepted standards
finding remains; compilation and diff hygiene pass.

## Spec

R1 increments only at new durable submission intent; busy/offline/expiry paths
return before it, and uncertain paths reconcile before it. Counter1 means an
intent, including a crash before queueing, not proof of external execution.
Migration preserves the entire earlier record except schema_version, including
counter0. R2 truthfully exposes supported record formats. Old installed workers
are not upgraded by changing global aliases and remain explicit compatibility
readers. No exactly-once claim or broader native signal/network parity claim.

## Validation

Public registration/scheduler/persisted-record seam:

- release-counter-red.log:7 tests,2 expected failures (attempts0 !=1).
- release-counter-green.log:7 tests pass after intent increment.
- release-counter-invalid-red.log: malformed due counters cause3 scheduler
  errors with the validation guard removed; guard restores unchanged held state.
- release-counter-focused.log:12 native delivery/migration tests pass.
- release-monitor-red.log:10 tests,1 expected failure (schemas3/4 absent).
- release-monitor-green.log:10 monitor tests pass.
- release-final-full-tests.log:983 source tests pass113.575s. This run preceded
  the monitor fix; frozen installed comprehensive validation is separately required.

Logs reside in /home/ecochran76/.local/state/codex-wake/plan127-runtime/.
Commands: PYTHONPATH=src venv/bin/python -m unittest discover -s tests
-p test_native_delivery.py/test_native_migration.py/test_monitor.py; the full
run uses -q without -p. No retries erase failed samples. The invalid-state test
now makes both due_at and next_attempt_at due so it reaches the dispatch risk.
