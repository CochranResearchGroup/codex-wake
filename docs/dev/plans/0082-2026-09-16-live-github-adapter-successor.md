# Live GitHub adapter correction and qualification successor

State: OPEN
Lane: P53-C7
Issue: #109
Branch: `fix/issue-109-live-adapter-runtime`
Target: `main`
Integration: `squash`
Parent plan: `docs/dev/plans/0070-2026-09-16-signed-github-webhook-ingress.md`
Predecessor: `docs/dev/plans/0081-2026-09-16-live-github-webhook-delivery.md`

## Current state

Plan 0081's single authorized runtime establishment and cleanup attempts are
consumed. The attempt stopped before provider effects. GitHub hook inventory is
empty, trigger PR #131 closed unmerged, the exact service is absent with PID
zero, port 8820 is free, and no live dispatch occurred. Both secret artifacts
were retired exactly once. The owner-only failed root and external receipt are
retained because the cleanup census did not reach safe root-removal evidence.

Two live-only production adapter defects are reproduced:

1. `install_wheel` inherited caller `PYTHONPATH`; pip returned zero by treating
   checkout metadata as an already satisfied distribution, leaving the
   isolated venv without the package or required console scripts.
2. `runtime_census` rejected the host's legitimate absent-unit readbacks:
   `is-active` rc 4 plus `inactive`, `is-enabled` rc 4 plus `not-found`, and
   `show MainPID` rc 0 plus `0`.

A bounded implementation worker owns only adapter code and tests. The primary
owns this plan, failure custody, integration, and any later authority gate.
No successor runtime or provider effect is authorized by this plan.

Checkpoint `2e6bf2dc31f886d24f995e13b8380988e5590f76` resolves both reproduced
defects. Installation now strips caller `PYTHONPATH` and `PYTHONHOME`,
force-installs the exact local wheel, binds installed distribution metadata to
the isolated venv, and proves all four exact console-script mappings and
files. Cleanup accepts the host's exact rc 4 absent-unit tuple while rejecting
contradictory or failed reads. The real-venv regression reproduces pip's former
zero-exit/no-install result against the pre-fix implementation. Focused tests
pass 24/24, comprehensive Python passes 565/565, the plugin tier passes 12/12,
compilation and diff hygiene pass, and active/goal planning audits pass.
Closed-world reviewer `/root/p53_c6_runner_review` accepted F1 and F2 with 15
additional negative census probes and no critical regression. Worker
`/root/p53_c7_adapter_fix` completed its single bounded implementation attempt;
effective runtime cost telemetry remains unavailable, so no allocation-saving
claim is made. Integration and the fresh trigger candidate remain.

Corrective PR #132 passed both hosted Python release gates and squash-merged as
canonical `27dedc00228c4ff99820dfa4b84e7895f62075a1`. The correction is now a
prerequisite of the fresh docs-only successor trigger. No successor runtime,
secret, service, hook, trigger, observation, cleanup, or dispatch effect has
occurred.

## Objective

Repair both adapter defects, prove the exact live failure shapes with
provider-free regression tests, integrate the correction through both hosted
release gates, and prepare a fresh docs-only trigger candidate. Stop at a new
exact lifecycle gate before any successor runtime, secret, hook, trigger,
observation, or cleanup effect.

## Scope

- Strip `PYTHONPATH` and `PYTHONHOME` from isolated installation commands and
  prove the installed distribution plus exact required entry points exist in
  the isolated venv.
- Accept only semantically valid systemd absent-unit tuples, including the
  observed rc 4 forms, while continuing to reject empty output, bus errors,
  malformed PID output, and contradictory status/return-code pairs.
- Add focused regressions that reproduce both live failures.
- Preserve Plan 0081's receipt, counters, root, and no-retry disposition.
- Run focused and comprehensive Python tests, the plugin tier, compilation,
  diff hygiene, planning audits, independent closed-world verification, and
  both hosted release gates.
- After integration, create one fresh docs-only successor trigger PR and freeze
  its exact head/base/files/checks without merging it.

## Non-goals

- Retrying, editing, or deleting the retained Plan 0081 root or counters.
- Reopening or merging trigger PR #131.
- Creating, redelivering, disabling, or deleting a GitHub webhook.
- Establishing a successor runtime or secret before a new exact gate.
- Changing the accepted Cooper/bastion route, global installation, release,
  arbitrary repository scope, diagnostics exposure, or live dispatch.

## Inherited evidence and effect bounds

```text
predecessor_runtime_establishments: 1
predecessor_runtime_cleanup_attempts: 1
predecessor_secret_provisions: 1
predecessor_secret_retirements: 1
predecessor_hook_creates: 0
predecessor_trigger_merges: 0
predecessor_hook_deletes: 0
predecessor_redeliveries: 0
predecessor_observations: 0
predecessor_dispatches: 0
correction_live_effects: 0
successor_runtime_establishments_before_new_gate: 0
successor_secret_provisions_before_new_gate: 0
successor_hook_creates_before_new_gate: 0
successor_trigger_merges_before_new_gate: 0
successor_hook_deletes_before_new_gate: 0
successor_redeliveries: 0
successor_dispatches: 0
```

Any later authorized successor packet uses a fresh root, receipt, secret, wake,
journal, and trigger PR. The frozen source/service identity may remain
`p53-c6-live-github` because the predecessor failed before creating that source,
service, wake, or journal; current absence must be re-proved before execution.
It may not reuse or reset Plan 0081 state. Provider writes remain one-shot:
ambiguity permits exact readback only, never retry.

## Execution graph

| Unit | Owner | Depends on | Write surface | Exit condition |
| --- | --- | --- | --- | --- |
| C7-R1 | implementation worker | reproduced failures | adapter and focused tests | both exact regressions pass |
| C7-R2 | primary | C7-R1 | plan, catalog, PR, integration | local tiers and hosted gates pass |
| C7-R3 | closed-world reviewer | C7-R1 checkpoint | no writes | both accepted defects resolved without critical regression |
| C7-R4 | primary | C7-R2, C7-R3 | fresh docs-only trigger branch | green candidate frozen; new exact gate recorded |
| C7-R5 | primary | explicit future authorization only | fresh isolated runtime/provider lifecycle | one accepted delivery or truthful no-retry stop |

Balanced execution uses at most one implementation worker and one reviewer.
No nested delegation is allowed. One implementation attempt and one
closed-world remediation verification are the loop bounds.

## Acceptance criteria

- A contaminated caller environment cannot influence isolated wheel install or
  make an absent distribution look installed.
- Exact required entry points and distribution provenance are verified after
  installation without a global install.
- The observed systemd rc 4 absent-unit tuple validates as safe, while query
  failure and contradictory tuples fail closed.
- Plan 0081's raw failure receipt and root remain unchanged except for the
  already completed secret retirement evidence.
- The corrective PR passes all local and hosted gates and merges to canonical
  `origin/main` before any successor live effect.
- A fresh trigger candidate is docs-only, green, unmerged, and bound to exact
  identities before the new gate.

## Definition of done

The correction is canonical, the predecessor failure remains attributable and
secret-free, a fresh successor trigger candidate is frozen, GitHub reports no
hook, no successor runtime exists, and the lane stops at a new exact lifecycle
authorization gate. Issue #109 and parent #103 remain open until one live
delivery is accepted or the wider program records a truthful terminal failure.
