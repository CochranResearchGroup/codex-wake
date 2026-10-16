# Issue270 — Proposed implementation brief

Status: design decisions confirmed by ecochran76 on2026-10-16 ("yes all"). This brief prepares a successor implementation scope; it does not change the research-only authorization of issue270 or authorize deployment. Provenance: Plan0165 and the2026-10-15 feasibility report. Owner: ecochran76.

## Agent Brief

**Category:** enhancement

**Summary:** Extend existing objective accounting and lifecycle controls with independently enforced execution containment and a sampled token stop.

**Current behavior:** ObjectiveLedger retains cumulative allowance and reservations across lifecycle transitions; the resident controller can interrupt owned native turns. Its native control path and accounting observations are not independent process containment. Disposable host tests demonstrate systemd/cgroup termination of a TERM-resistant parent and child; real Codex execution membership, lease failure and suspend-aware bounds remain unproven.

**Confirmed desired behavior:**

- Strictly limited objectives require dedicated execution boundaries covering actual executors, objective-specific tools, dependency setup, tests, builds and descendants. A display client alone is insufficient. Shared services are explicitly excluded; reject work requiring an unsupported strict guarantee rather than silently claim it is contained.
- One objective allowance includes cached input, reviewers, preflight, successors, failed attempts, retries and delegates. Refresh/restart/handoff does not replenish it. Token enforcement is sampled, with maximum overshoot unknown until evidence proves a finite bound.
- Missing or stale accounting fences admission and stops owned execution. Preserve the last verified checkpoint and uncertainty receipts. Exhaustion requires explicit operator renewal; no automatic resume, allowance reset or deadline extension.

**Key interfaces / implementation choices:**

- Reuse ObjectiveLedger and existing lifecycle admission/monitor/stop contracts. Reconcile concurrent emergency-controls work before choosing a shared stop interface.
- Add a host execution adapter with durable objective/actor, native assignment, unit invocation and cgroup identity. Model admission, running, stopping, stopped and uncertain outcomes explicitly; reconcile ambiguous effects before retry.
- Strict-mode host configuration must explicitly supply memory, swap, CPU rate, task, session/objective token/time limits, observation interval, maximum accounting age and stop/checkpoint grace. Do not adopt the research experiment's numeric caps as product defaults. Reject absent/inconsistent controls before admission. Grace consumes the original allowance and deadline.
- Independently enforce the original absolute deadline and controller/accounting lease. Define time domains and suspend/resume behavior; unsupported host guarantees fail admission. A user-owned cgroup is containment for cooperative host ownership, not proof against arbitrary same-user IPC escape or external compute.
- Readback must distinguish enrolled execution, exclusions, deadline enforcement, sampled token accounting, accounting freshness and stop verification.

**Acceptance criteria:**

- [ ] Dedicated real Codex executor, local tools and active child membership are verified before strict-mode task effects; shared sessions remain untouched.
- [ ] A blocked tool and TERM-resistant child stop under a stated observed bound; independent cgroup/process readback verifies no executing owned work.
- [ ] Native token exhaustion records actual accounting metric, observation delay, in-flight uncertainty and stop timing; no exact ceiling claim without proof.
- [ ] Stale/missing accounting, transport loss and actual controller death stop owned work via independent enforcement; no reliance on a model notification.
- [ ] Concurrent actors share aggregate limits; successors/reviewers/preflight/retries are counted once and cannot renew allowance.
- [ ] Restart and suspend/resume retain the original objective deadline; expired work cannot restart before the fence is checked.
- [ ] Checkpoint failure cannot postpone the stop; last verified checkpoint and unknown accounting remain attributable.
- [ ] Explicit operator renewal retains prior consumption and authorization history; changes to defaults do not renew active objectives.
- [ ] Unsupported containment or missing configuration returns a structured refusal before task execution. No unrelated service/process termination.

**Out of scope:** fleet rollout, deployment, termination of existing shared sessions, replacement handoff framework, performance optimization campaign, proof of provider-side cancellation, and guaranteed exact token ceilings.

## Execution sequence

1. Specify and validate ownership/binding/configuration, with effect-free fixtures.
2. Add disposable dedicated executor integration and independent deadline/lease enforcement.
3. Integrate existing ledger/stop/renewal paths and run a bounded native acceptance packet.

Each slice needs its own acceptance evidence. First native gate is execution membership; stop/reframe if actual work escapes the declared boundary. This brief does not mark issue270 complete or ready for unbounded AFK implementation. Follow the existing protected-main integration workflow when an implementation work item is opened.
