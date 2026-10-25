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
| #344 | primary | integrated | common enrollment/permissions source present | pending |
| #345 | /root/ticket345 | integrated | frozen event contract above | pending |
| #346 | /root/ticket346 | integrated | common attention/permissions source present | pending |
| #343 | primary | pending | all three validated + installed journey | pending |

Worker result requires exact base/result SHA, changed paths, red/green commands,
acceptance evidence and missing gates. Integrate serially; do not close from claims.
Review discovery count 0/1; remediation count 0/1. No repeated broad reviews.

## Current state

Isolated integration checkout established. Frontier prerequisite source reused;
conflicting runbook additions both preserved. Policy wiring and diff checks pass.
#319 recovery/native #318 work is separate; do not claim it is installed here.
No tickets are closed, no UX runtime is installed, no presentation is yet proved.

Worker handles: /root/ticket345 (feat/345-goal-notices) and /root/ticket346
(feat/346-goal-renewal); base e181d28, separate owned sibling worktrees.
Manual meter note: get_goal still reports blocked historical counters despite
explicit resume, so its44,278/151 values are stale; use UTC hard stop plus local
native telemetry if available, and do not claim fresh watcher accounting.

## Checkpoint 2026-10-25T04:54Z

Progress classification: outcome_progress; all three source modules integrated.
Primary readiness3768270, notice worker8012989 integrated19b6db4 plus3953528 hooks,
renewal workerdf6f145 integratedb5760ea plus5fc32c4 hooks. Worker346 successor
2c864ae integrated3c9230d qualifies isolated installed CLI/MCP with injected native
protocol: extension100spent/100to150total, exact authentic operator response,
first-poll resume, reset0window/100lifetime, unchanged peer, zero external providers.
Receipt and final OS process census in goal-renewal-installed.md.

Native worker345 owns fix/345-no-turn-notices in separate native checkout. Pinned
experimental71620df server (development build) plus stock0.164 frontend proves
actual rendered stop, busy owned shell task, exact interrupt, reconnect once,
model context and unchanged peer with no model/provider turns. Receipt is
345-native-render-3 under user-scoped goal-limit-ux evidence. This is presenter
qualification, not the full watcher journey.

The full real watcher/native/frontend join has NOT passed: actual new native
response wrote display token_count but no response-level token_usage_record.
Wake correctly refuses first_usage_unavailable. Failed owned attempts and cleanup
are retained in goal-native-ux-journey.md. No synthetic accounting or policy
weakening is permitted; native worker is qualifying the writer prerequisite.

Comprehensive Python selection at3953528 completed exit0/603.752s in isolated
XDG roots. Later source changes during the run mean this receipt alone is not
proof of the final exact tip; affected checks and a frozen final join remain.
Do not repeat unmodified tests merely to get green. First failures remain retained.

All tickets remain open. No broad review/remediation has run (0/1 each). Required
next join is actual watcher engagement/stop plus approved renewal on qualified
native accounting, then requirement-by-requirement closure, one review and one
bounded TDD remediation. Manual meter04:51Z692,026fresh tokens across3agents;
no production watcher/service/daemon or allowance changed.

## RESOURCE STOP 2026-10-25T05:27Z

The manual fresh-input/output meter crossed the explicit2,000,000token ceiling:
2,048,897 first observed;2,055,524 observed during minimal cleanup. A native-worker
cache miss published more usage than the100k reserve could absorb. This is a
resource-ceiling breach, not successful in-budget enforcement. Stop substantive
work immediately; do not infer renewed authority from automatic continuation.

Published integration includes actual real-native/MCP/stock-TUI journey PASS in
346-native-mcp-20261025T051000Z/attempt4, genuine self-enrollment,20fresh startup,
extension retaining40spent, reset0window/50lifetime, no new notification turn,
model-input notice proof, unchanged peer and empty owned-process census. It is
an isolated development candidate, not a production install or general release.

Required watcher-restart variant found a real renewal refusal after graceful
replacement. Narrow original-exhaustion/fresh-controller fix303a664 successor
3deddf6 integratedf81811d;12focusedtests reportedlypass. Final real restart join
is unverified at the resource stop. Native final schema/protocol/Clippy/formatter
pipeline was still pending; its exact owned Cargo process group2383107 received
SIGTERM during cleanup. Source/patch and prior passing native RPC/render receipts
are retained. Worker handles /root/ticket345 and /root/ticket346 were interrupted.

PR348 remains draft. No tickets closed. Broad review0/1; post-review TDD remediation
0/1. Do not claim the goal complete. Remaining gates: final watcher-restart proof,
final native static/format custody, final exact-tip validation/CI, full acceptance
audit, ticket closure, requested one review and bounded remediation.

Validation honesty: initial mixed-tree1674pass/oneskip is not final proof. Frozen
e9a46b3 run1676tests failed one strict-executor subprocess timeout; first receipt
retained. Same single test passes isolated on prerequisite16c2501; causality of
full-run timeout remains unclassified. CI's10guarded-interaction errors reproduce
on baseline underumask022; private configured fixture root corrections now pass
10tests under022. Preserve earlierfailedpartialfixture fixes; do not hide them.

Shared goal watcher remains masked/inactive and no production allocation/reset,
shared daemon replacement or default release occurred. Memory disposition:forbidden;
no explicit memory update requested. Stop record is the continuation authority
locator, not a new resource allowance.
