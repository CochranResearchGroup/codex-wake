# Plan0156 checkpoint17 — running preflight usage stop

State transition: active diagnosis → source-qualified stop → installed proof ready.
Acceptance state: full Plan0156 OPEN / IN_PROGRESS; native handoff still unaccepted.
Progress classification: blocker_reduction.
Authority/window: checkpoint16, start1791887366/deadline1791908966, two million
tokens/six hours; original failed fixtures not renewed. Branch feat/agent-lifecycle.

## Actual public-seam defect

RED: PYTHONWARNINGS=ignore .venv/bin/python -m unittest
 tests.test_agent_handoff_preflight.HandoffPreflightTests.test_running_preflight_over_allowance_interrupts_exact_assignment_once -q.
Actual CLI→native Unix socket→real owned PTY scenario reports active preflight
usage101 against allowance100. Failure: reason
successor_assignment_awaiting_preflight instead of preflight_allowance_exhausted;
no interrupt. Usage was considered only after task completion/proof validation.
Ranked alternatives were missing running usage and missing exact assignment
identity; this pinned fixture supplies both and isolates the completion gate.

GREEN same command after fix: PASS1/0.373s. Handoff now observes target usage
before waiting for completion; an overspend fences future preparation and stops
only in-progress turns containing the exact original client submission ID.
Same-intent readback observes settlement, never resubmits or reinterrupts.

Second RED: same command with
 test_lost_preflight_interrupt_response_reconciles_without_reinterrupt.
Expected uncertain, got blocked when native socket closed after actual interrupt.
GREEN PASS1/0.398s after persisting uncertain-effect before interrupt and
reconciling exact native turn on next read. Original source goal stays paused;
no successor goal, replacement assignment or duplicate interrupt.

Validation: PYTHONWARNINGS=ignore .venv/bin/python -m unittest
 tests.test_agent_handoff_preflight tests.test_agent_handoff
 tests.test_handoff_acceptance_supervision tests.test_agent_spawn
 tests.test_daemon tests.test_lifecycle_mcp -q — PASS85/16.458s.
git diff --check PASS. Source tests are injected native-provider evidence, not
installed runtime acceptance. Enforcement observes reported cumulative usage:
it cannot promise zero overshoot between provider usage reports or during a host
outage. Exhausted work stays blocked; no hidden allowance renewal.

## Next installed packet

Publish exact candidate, build a fresh isolated prefix and verify module parity.
One fresh owned native handoff fixture; source/preflight/continuation total cap
250000, preflight150000, source less than100000, fixed ten-minute deadline bounded
by parent deadline. Two manual assignments maximum; no old intent replay.
Keep configured model/effort (no escalation), record actual config and usage.
Prior observed source40443 + failed preflight161111 means another overspend is a
credible failure: stop and preserve it, do not raise the fixture allowance to pass.
Controller stop plus repaired supervision can distinguish genuine costs from
teardown-induced retries. Completion still needs native selected preflight and
bounded goal continuation; budget failure will not count as acceptance.
Reserve the parent window for the full outstanding program (checkpoint16).
No shared install/service changes. Fresh census and exact cleanup required.
Memory disposition: unavailable; checkpoint16 discovery found no reviewed target.
