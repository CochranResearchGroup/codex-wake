# Issue270 — External resource enforcement feasibility

2026-10-15. Research disposition: **conditional GO for a bounded implementation proposal; NO-GO for a claimed exact token ceiling or live rollout.** No production code changed or live agent interrupted. Intake: [issue270](https://github.com/CochranResearchGroup/codex-wake/issues/270); execution scope: [Plan0165](../plans/0165-2026-10-15-resource-enforcement-feasibility.md).

## Decision

Reuse the objective ledger and resident lifecycle controller. Add one host execution adapter that launches all objective-owned execution inside verifiable systemd/cgroup boundaries before admission. An independent manager deadline can stop a local process tree even if the agent ignores reminders or its lifecycle observer dies. Sampled rollout token counts support conservative admission and an eventual stop request, not a proven exact token cap.

This is feasible on the tested WSL2 Linux host (kernel6.6.87.2, systemd255.4, cgroupv2). It is not yet demonstrated for an actual Codex app-server/tool tree. Wrapping only a TUI that connects to a shared remote app-server would leave the actual work outside containment. That ownership problem is the first implementation gate.

## Existing enforcement and remaining boundary

Source inspected at main75c54a9053942f9d8ed16f4b04a392880f30dabf. Four relevant modules byte-match installed0.15.1 at `/home/ecochran76/.local/share/codex-wake/releases/0.15.1-1ee7229`: [parity receipt](../evidence/issue0270/source-installed-parity.json). The root checkout's uncommitted emergency-controls lane is excluded from this baseline and must be reconciled before implementation.

| Existing source | Established behavior | Remaining gap |
| --- | --- | --- |
| `src/codex_wake/objective_ledger.py` | Locked persistent configuration, atomic reservations, cumulative usage, original deadline, explicit extension/reset history. Unknown or decreasing usage holds admission. | Ledger decisions do not terminate processes. Only enrolled attributable actors count; arbitrary outside work is not automatically captured. |
| `src/codex_wake/lifecycle_budget.py:207` | Reads rollout `token_count.info.total_token_usage.total_tokens`; cached input remains counted. Exact terminal markers gate settlement. | No enforced publication interval or upper bound for tokens consumed between snapshots. Native goal display can use a different metric. |
| `src/codex_wake/lifecycle_supervision.py:47` | Polls owned spawns, checks budget/deadline, requests `turn/interrupt` for exact owned assignment, cancels exact queued assignments. | Sequential native RPCs and full rollout reads can delay checks. Outer exceptions record observation errors and continue; no independent process kill. Losing the controller or transport can leave work running. |
| `src/codex_wake/agent_handoff.py:720` | Reconciles owned source/successor goals, pauses successor, interrupts its active turn, retains budget and uncertainty receipts. | Requires live native control path and accounting; not an OS containment guarantee. |
| [Lifecycle contract](../../agent-lifecycle.md) | Host-selected configuration and resident supervisor required for configured admission; fresh context does not replenish allowance; legacy profiles explicitly use expiry only. | Documentation explicitly excludes enforcement during host outages. A host-scope configuration error is not itself a defect. |

Redundancy conclusion: issue256 already delivered useful accounting and active-turn interruption. Issue270 remains distinct because independently enforceable execution containment and quantitative stop guarantees are not established. `.out-of-scope/` and `docs/adr/` were absent; no prior rejection found there. This is a source/host feasibility assessment, not reproduction of the motivating filename-search incident.

## Three disposable experiments

Run command: `python3 docs/dev/evidence/issue0270/experiment.py`. [Harness](../evidence/issue0270/experiment.py), [raw result](../evidence/issue0270/experiment-results.json). No native Codex turns or provider calls. Three unique transient user services, each with parent and child ignoring SIGTERM. A separate sentinel sleep process stayed outside their cgroups.

Each service used `Type=exec`, `RuntimeMaxSec=3s`, `TimeoutStopSec=1s`, `KillMode=control-group`, `SendSIGKILL=yes`, `Restart=no`, `MemoryMax=128M`, `MemorySwapMax=0`, `CPUQuota=20%`, `TasksMax=16`. Readback confirmed kernel values `memory.max=134217728`, `memory.swap.max=0`, `cpu.max=20000 100000`, `pids.max=16`, and both owned PIDs in the exact service cgroup.

| Experiment | Observed result | What it establishes |
| --- | --- | --- |
| Deadline with blocking child | No live owned PIDs at4.138s from launch; service result timeout, SIGKILL; cgroup removed. | Manager runtime plus bounded grace stops this TERM-resistant local tree. |
| Injected token exhaustion | Synthetic count125 against cap100; explicit unit stop completed in1.082s; no live owned PIDs. | Stop actuator works on an injected exhaustion decision. No native accounting, polling delay, token-rate or provider-cancellation guarantee was tested. |
| Controller loss analogue | Independent dummy controller killed; no stop RPC issued; manager deadline stopped tree at4.122s. | Deadline does not depend on that observer remaining alive. This is not a real Codex controller crash or prompt accounting-loss stop. |

Sentinel survived all three. All experiment units were stopped/reset; fresh `list-units 'cw270-*'` returned none. No remaining live owned test processes or cgroups were observed. Zombies, if any, are not executing work; the harness explicitly treats them as non-live. Existing services and sessions were not targeted.

These timings are measurements, not certified worst-case latency. The nominal stop sequence is3s runtime plus1s grace plus manager/kernel scheduling and signal delivery. A frozen host or uninterruptible kernel task prevents a universal real-time bound. Memory/CPU/task limits were read back, not stress-tested. CPUQuota limits execution rate, not total CPU-seconds; memory limits do not bound disk, remote compute or uncharged service work.

## Smallest viable integration

1. Keep one durable objective identity and original absolute deadline in `ObjectiveLedger`. Bind each admitted actor to an exact systemd unit/invocation/cgroup and native assignment identity. Write intent before effects and reconcile uncertain creates/stops. Do not identify ownership from tab name or PID alone.
2. Launch a dedicated app-server/tool executor and its objective-specific MCP children inside the boundary before any setup, builds, tests or task admission. A tmux window is display attachment, not execution ownership. Existing shared app-servers/MCP services remain excluded and preserved; either provide dedicated workers or report their operations as unsupported for hard containment. Same-user services can ask a manager or external daemon to create work elsewhere, so cgroup membership alone is not an adversarial security sandbox. A stronger identity/IPC isolation policy is needed if bypass-resistant enforcement is required.
3. Apply objective-wide aggregate controls through a common parent boundary; per-session services retain lower limits. Admit successors/reviewers/delegates only under that objective boundary. Set remaining runtime from the fixed deadline, never a fresh full duration on restart. `Restart=no`; exhaustion persists as a terminal fence until explicit operator renewal. Same-thread refresh must retain binding; handoff cannot grant new time or tokens.
4. Keep sampled token observations and reservations in the existing ledger. Poll at a declared interval (proposed1s, not a guarantee), detect stale/missing/decreasing data, fence new admission, then interrupt the exact owned turn and stop the owned unit if needed. First-ever missing usage requires a short explicit observation allowance; no indefinite unmetered run. A token reserve does not bound overshoot unless maximum in-flight charge is known. Formula: overshoot depends on unreported/in-flight usage plus spend during detection and stop; those terms are currently unbounded by evidence. Advertise **sampled token stop, maximum overshoot unknown**.
5. Pair the fixed manager deadline with a separate short lease/watchdog for observer/accounting loss. The lease may only renew from fresh trustworthy observations and can never move the absolute deadline. No actor-controlled timeout extension. Lease wiring and crash/restart behavior remain untested here; the third experiment proves deadline fallback only.
6. Start graceful checkpointing before the final deadline, using an explicit reserve included in the same objective token/time caps. Fence new assignments first, pause goal and request interruption, allow a bounded checkpoint window, then enforce unit termination. `KillMode=control-group` sends TERM to children too; a required graceful sequence needs a separately bounded preparation stage before final unit stop. If checkpointing fails, retain the last verified artifact and an incomplete/unknown receipt; never extend automatically to obtain a tidy checkpoint.

Suspend deserves a separate acceptance test: native objective time already includes waiting, but these tests did not suspend WSL. Do not equate service elapsed timers with an absolute deadline that counts host suspend. A tested suspend-aware watchdog/alarm and resume-before-admission check are required before claiming that guarantee. Host-down work cannot execute locally; remote provider work may continue and its cancellation/accounting is unknown.

## Implementation scope and go/no-go

Estimated engineering scope: three bounded slices, roughly4–8 engineering days before a small owned canary (estimate, not authorization): (1) execution ownership/host adapter and persisted bindings, (2) ledger/lease/stop/renewal integration, (3) actual Codex tree and failure acceptance. Reuse current lifecycle code; reconcile the emergency-controls lane's stop interface. No new handoff framework.

First acceptance gate: demonstrate an isolated real Codex app-server, tool, and child membership without shared sessions, then block a tool and prove no owned execution remains after the declared stop sequence. Additional gates: native token exhaust with measured telemetry delay, stale/missing accounting, actual observer death, lease failure, concurrent actors, restart without deadline reset, suspend/resume, no unrelated termination, and explicit renewal preserving prior usage. Provider-side cancellation and finite token overshoot remain separate evidence requirements. Unsupported hosts must reject strict mode before execution, not downgrade silently.

Recommendation: proceed to operator decisions on ownership/exclusions, token accounting and acceptable unknown overshoot, then a bounded implementation brief. Do not activate against current shared TUI sessions. This feasibility report completes the research slice; issue270's full native proof is not complete.

## Primary sources and validation

- [systemd255 service source](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.service.xml): runtime/start/stop/watchdog directives. Installed255 manuals were also inspected. `Type=oneshot` does not supply the desired runtime limit; notify services can extend timeouts, so extensions require exclusion/control.
- [systemd255 kill source](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.kill.xml): control-group kill and TERM/KILL escalation.
- [systemd255 resource-control source](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.resource-control.xml): memory, swap, task and CPU quota controls.
- [Kernel cgroupv2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html): children inherit membership; migrating a parent does not migrate existing descendants. Hierarchical limits are the relevant containment primitive.
- Source fixture tests:11 objective-ledger tests PASS. 27 spawn fixture tests PASS using installed release Python ([log](../evidence/issue0270/spawn-tests-installed-python.log)); these use injected native behavior, not production Codex termination. Initial plain-python spawn collection lacked `websockets`; retained error log, rerun with installed release interpreter rather than installing dependencies.
- Graphiti atlas read returned5 routing facts and three unrelated candidate manifests; no appropriate Codex Wake target was established. No source groups queried or memory facts used as authority.
