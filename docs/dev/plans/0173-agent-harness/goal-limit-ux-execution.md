# Goal-limit UX implementation ledger

State: OPEN. Owner: primary / ecochran76. Work items: #343, #344, #345, #346.
Spec: goal-limit-operator-ux.md; current GitHub issue acceptance is frozen unchanged.
Branch: feat/goal-limit-ux-implementation. Target: origin/main.
Base: 37a5cbb03e1c9e7db5026c99d6dca3cbf443ee5f.
Prerequisite source: frontier 16c2501d950416099b0d7bf0def18a4dc99e8d98
(PR341 still draft; installed qualification is separate). UX contract: 84e39d3.

## Authority and resource control

User explicitly requested ticket closure, one ticket per agent, one broad code-review
and one bounded TDD remediation pass. User subsequently authorized manual resource
monitoring to bypass unavailable external supervision for this implementation.
The shared watcher remains masked; no production allowance, service, or native daemon
is changed. Original goal meter at resume: 44,278 tokens /151 seconds.
Resume readback 2026-10-25T04:21:23Z. Conservative hard stop 06:15Z;
implementation stop 06:05Z, leaving closeout reserve. Token cap 2,000,000 cumulative,
reserve 100,000. Check meter/time at every integration and at most 10 minutes apart.
Concurrency: primary plus two shallow workers, no nested agents. Balanced bias.

## Shared contract and ownership

Primary owns goal_supervision.py, goal_limits_cli.py, mcp_server.py, skills,
registration, integration and startup readiness (#344).
#345 worker owns new goal_notices.py and goal_notice_commands.py, native presenter
qualification/artifacts and its tests. Public API: record_notice(root, receipt,
kind, *, controller=None) -> event, kinds engagement/checkpoint/stop/recovery;
present_notice(root, event_id, *, adapter=None) -> independent delivery proof.
Events bind exact thread/allocation, receipt generation/revision, stop episode,
reason and captured work turns; deduplicate by semantic event, retain unknown effects.
No presentation API may launch a model turn or turn steer acknowledgement into
render/model-context proof. Worker may refine implementation signature with primary.
#346 worker owns new goal_renewal.py, goal_renewal_commands.py and tests/docs for
extend/reset. Common attention queue is the only decision store. Model proposal
cannot approve itself. Primary wires CLI/MCP registrations serially.
Both workers can implement independently against existing enrollment/permission
seams; primary alone adapts shared hooks. Final installed acceptance joins all lanes.

## Execution graph

| Ticket | Owner | State | Dependencies | Evidence |
| --- | --- | --- | --- | --- |
| #344 | primary | running | common enrollment/permissions source present | pending |
| #345 | worker to assign | pending | frozen event contract above | pending |
| #346 | worker to assign | pending | common attention/permissions source present | pending |
| #343 | primary | pending | all three validated + installed journey | pending |

Worker result requires exact base/result SHA, changed paths, red/green commands,
acceptance evidence and missing gates. Integrate serially; do not close from claims.
Review discovery count 0/1; remediation count 0/1. No repeated broad reviews.

## Current state

Isolated integration checkout established. Frontier prerequisite source reused;
conflicting runbook additions both preserved. Policy wiring and diff checks pass.
#319 recovery/native #318 work is separate; do not claim it is installed here.
No tickets are closed, no UX runtime is installed, no presentation is yet proved.
