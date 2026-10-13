# Plan0156 checkpoint25 — late source accounting fences continuation

Plan0156 remains OPEN / IN_PROGRESS. SP-01 accepted as blocking spec defect:
continuation monitor previously compared goal identity/budget/status but omitted
paused-source cumulative counter advances after preparation/activation. That left
successor allowance valid against a stale source snapshot.

Public CLI→native-socket fixture→daemon regression
`PYTHONWARNINGS=ignore .venv/bin/python -m unittest tests.test_agent_handoff_preflight.HandoffPreflightTests.test_late_source_accounting_fences_active_successor -q`
RED: active != paused,1 test0.668s; /tmp/plan156-sp01-red.log.
GREEN: PASS1/0.545s; /tmp/plan156-sp01-green.log.
Worked fixture source budget1000/used50, successor920 after preflight30;
source usage advances to150 while successor is active. Next supervision poll
pauses the exact owned goal and interrupts its exact in-progress turn, preserving
objective/caps/deadline. No silent rebasing or allowance increase. Block reason
source_accounting_advanced; rollback is the existing path for fresh reconciliation.
Malformed/regressed source counters also cannot authorize continuation.

Positive qualification checks cover time12→13 while active and source50→150
before activation; prepared successor remains paused with no activation effect.
These are not claimed as additional observed RED cycles. Monitor applies the
accounting guard before accepting completed goals. Existing uncertain pause/
interrupt reconciliation path retains original effects and ownership fencing.

Focused selection: tests.test_agent_handoff_preflight tests.test_agent_handoff
 tests.test_daemon PASS72/19.007s, /tmp/plan156-sp01-focused.log.
Earlier preflight selection PASS30/15.474s; git diff --check PASS.
Native transport injected at public socket boundary; no provider assignments or
installed/native acceptance claim. Known external reset-window499975, old
unreported receiver reserve250000 unchanged; root678429/7575s last readback.
Fixed parent deadline1791908966 and two-million campaign stop remain.

Next: SP-02 checkpoint contract public rejection repro, validate restart-safe
repo/workspace/revision/dirty disposition, acceptance/evidence, resource/expiry/
hard-stop and reply route fields against immutable host intent; update approved
writer and contract docs. No additional broad review; closed-world remediation.
Then both handoff modes/rollback native proof, nonnull refresh goal/instruction
proof, all local CI, integration/release/recovery/cleanup, clean main and
issues248–251 closure. ST-01 duplicate math remains nonblocking, no unrelated
refactor. Memory unavailable; no reviewed Graphiti target, prior receipt retained.
