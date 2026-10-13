# Plan0156 checkpoint16 — resumed window and reproduced supervision defect

State transition: paused campaign → active resumed window → first diagnosis repair.
Acceptance state: Plan0156 OPEN / IN_PROGRESS; installed handoff remains unaccepted.
Progress classification: blocker_reduction.

## Authority and counters

Operator explicitly requested a resource-counter reset, then resumed the full
Plan0156 goal using Matt's process, without implementation theater, stopping and
checkpointing before 2,000,000 tokens or six hours. New native goal thread
01a1331c-0344-7b31-bac5-519b0ba3755a was observed ACTIVE with zero usage at start.
Creation1791887366 anchors this window; deadline1791908966
(2026-10-13 16:29:26 UTC). Stop with checkpoint headroom before either limit.
Observed mid-packet root90632 tokens/127seconds. No external model assignments
in this window. Prior root/external counters and failed fixtures remain historical;
the operator reset does not renew any expired fixture or change product accounting.
Branch feat/agent-lifecycle, base9e693cf. Preserve other worktrees and services.
Inherited acceptance criteria, two attempts/seam, one consolidated review plus one
remediation, and 45-minute checkpoint backstop remain. No review cycle consumed.

## Diagnosis and repair

Selected diagnosing-bugs and TDD instructions consumed. Stable seam: acceptance
runner's installed CLI polling supervision, with command output and elapsed clock
as injected external boundaries. No new provider/native assignment.

Actual pre-fix loop replay: .venv/bin/python
/tmp/plan156-resume-diagnosis/replay_hold.py. It executes the original AST loop
with a blocked/admissible_time_unavailable result followed by awaiting_activation
for the same existing receiver/task. RED: RuntimeError handoff held:
admissible_time_unavailable. The second observation was never reached, causing
execute's cleanup to tear down the owned server while work could still run.
This is a diagnostic replay, not native runtime acceptance.

Ranked predictions: blanket blocked classification terminates a recoverable hold;
missing successor identity prevents reconciliation; observation deadline expires.
Pinned clock and explicit successor/task reproduce failure before deadline,
distinguishing the first from the other two for this reproduction.

Runner now polls the identical intent through this one recoverable clock hold.
All other blocked reasons stay terminal; original observation deadline remains.
Public supervisor regression verifies same-intent observation, fixed deadline,
and exhausted allowance still stopping. Initial regression RED was a missing
supervisor entrypoint; actual defect RED is the original-loop replay above.
GREEN: PYTHONWARNINGS=ignore .venv/bin/python -m unittest
 tests.test_handoff_acceptance_supervision tests.test_agent_handoff
 tests.test_agent_handoff_preflight -q — 29 tests PASS8.533s.
No claim of native preflight, installed parity, or product acceptance follows.
No debug instrumentation or disposable source prototype added. git diff --check PASS.

## Outstanding critical path

Current controller checks preflight spending only after worker completion and
proof validation; prompt token_allowance alone is not enforcement. Preserve
161111/150000 overspend as failed evidence. Next: build a public-seam red
reproduction of live preflight overspend, then fix its observation/stop boundary;
qualify whole proof cost before another fresh bounded installed attempt.
Same-tab, active-successor/missing-source rollback, ownership race/cached rollback
spending, nonnull refresh-goal installed proof, successful selected preflight and
bounded native continuation remain. Then consolidated review/remediation, required
local gates, combined CLI/MCP/skills acceptance, integration, release/rollback,
cleanup, clean main, and issues248–251 closure. No acceptance criterion narrowed.

Memory disposition: unavailable. Healthy Graphiti doctor; bounded atlas query
returned zero reviewed cloud candidates for Codex Wake. No memory write attempted.
