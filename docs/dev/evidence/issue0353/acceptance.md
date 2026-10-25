# Issue #353: early host preflight and authorized repair fallback

Work item: <https://github.com/CochranResearchGroup/codex-wake/issues/353>.
Parent specification: <https://github.com/CochranResearchGroup/codex-wake/issues/350>,
stories 4, 16, 17, 20 and 22.
Source baseline: `c34592bfc27c40a890d624df6dfecb5ffe984d95`.
The coordinator owns the parent plan, integration and external issue disposition.

## Public behavior and boundaries

The existing public `sessions spawn` path accepts an optional host launch-profile
`governance_preflight`, selecting an existing private goal grant, requested mode
and optional retained manual authorization. No model-facing authority selector or
new approval exchange was added. Legacy profiles remain feature-off.

Preflight precedes thread/tab/queue effects and rechecks opted-in effects. It
reads actual selected endpoint metadata/Unix peer PID, process generation and
executable, separately hashes the selected client and source/configuration, and
performs fresh public diagnosis, status, control and native notice/model-context
readback. It never enrolls a goal or changes service, resource or control state.

An unsupported explicit `hard_admission` request returns one actionable held
result, with no silent downgrade or thread/tab/task effects. Native request-path
admission remains unsupported; successful ledger operations or matching client
and server executables do not establish a hard token ceiling.

The deterministic public journey proves `sampled_stop` only after qualified
accounting, actual resident first-poll acknowledgement, current controls and
fresh notice/model-context readback. Operator UI rendering remains independently
unverified by this read-only seam. Sampled mode has no exact overshoot bound.

Retained manual authorization carries an explicit manual-mode notice and permits
a repair assignment without the resident lifecycle watcher. Existing independent
budget reservations are still charged and settled (the fixture uses 70 tokens),
with original deadline and all permission/strict executor gates retained. No
watcher is started or unmasked; no goal is resumed, stop cleared, counter reset,
resource renewal or campaign renewal occurs. An explicit inactive choice applies
only to its exact selected allocation. Unknown control state is not deactivation
or revocation. Inactive control does not bypass independent lifecycle supervision.

Static receipt reuse is separate from fresh eligibility: source/client/connected
server/configuration/caller bindings are rechecked every attempt. Only static
notice-read capability qualification is reused. Accounting, remaining allowance,
controller heartbeat, operator control and actual notice/model-context readback
are not cached. Unknown native probe outcomes do not become qualified cache
entries. The first assignment's compact mode snapshot is retained on retry;
current results remain available as `compatibility_preflight`.

## Red/green and focused validation

Tests use CPython 3.12.13, `PYTHONPATH=src:tests`, the existing private Unix
WebSocket/tmux/client fixtures, controlled clocks, original response-usage files
and an actual isolated resident watcher process. No provider inference,
production dispatch, installation or existing service change was authorized.

Interpreter prefix for commands below:

```sh
PYTHONPATH=src:tests /home/ecochran76/workspace.local/codex-wake/.venv/bin/python \
  -W ignore::DeprecationWarning -m unittest
```

1. `tests.test_agent_spawn.AgentSpawnTests.test_hard_admission_preflight_refuses_before_thread_tab_or_task_effects -q`
   initially failed because the public profile rejected the new optional host
   field. After wiring opt-in preflight, **1 passed, 0.670 s**. Assertions prove
   zero thread creation, tab creation and task submission.
2. `tests.test_agent_spawn.AgentSpawnTests.test_authorized_manual_repair_spawns_without_a_resident_watcher_or_renewal -q`
   initially failed with `resident_objective_supervisor_required` despite the
   retained manual authority. After the bounded manual fallback, **1 passed,
   1.714 s**, including original budget settlement and no watcher artifact.
3. The public sampled/cache fixture initially returned `degraded` correctly:
   enrollment alone lacked a resident first-poll acknowledgement. The test now
   waits at most six seconds for actual public engagement, rather than weakening
   that qualification. Its next run passed **1 test, 6.805 s**.

Affected regression selection:

```sh
PYTHONPATH=src:tests /home/ecochran76/workspace.local/codex-wake/.venv/bin/python \
  -W ignore::DeprecationWarning -m unittest \
  tests.test_agent_spawn tests.test_host_preflight tests.test_task_brief_lifecycle -q
```

**40 tests passed, 37.430 s**, exit 0. This is an affected source selection, not the
full repository suite. Subsequent bounded review tightened fresh notice readback,
remaining-allowance checks, newest control readback and explicit peer PID binding;
those surfaces were then rerun through the final five-case selection below.

Final acceptance selection:

```sh
PYTHONPATH=src:tests /home/ecochran76/workspace.local/codex-wake/.venv/bin/python \
  -W ignore::DeprecationWarning -m unittest \
  tests.test_host_preflight.HostPreflightTests \
  tests.test_agent_spawn.AgentSpawnTests.test_hard_admission_preflight_refuses_before_thread_tab_or_task_effects \
  tests.test_agent_spawn.AgentSpawnTests.test_authorized_manual_repair_spawns_without_a_resident_watcher_or_renewal \
  tests.test_agent_spawn.AgentSpawnTests.test_inactive_preflight_honors_operator_choice_without_manual_permission \
  tests.test_agent_spawn.AgentSpawnTests.test_sampled_preflight_reports_degraded_before_costly_dispatch -q
```

**5 tests passed, 10.744 s**, exit 0. The matrix proves static
reuse, client binary drift, server metadata drift, profile drift, separate peer
PID/client identities, and fresh degradation after either loss of current native
notice/model delivery or death of the resident controller. It asserts no native
thread/queue/goal/interrupt effect during the compatibility matrix.

New files pass Ruff 0.14.2 without exclusions. Affected legacy lifecycle/spawn
files pass with their existing E701/E702 style debt excluded. `git diff --check`
passes. CodeGraph was initialized for the verified worktree and synchronized.

## Remaining qualification

This is source/public deterministic acceptance. Actual selected native/client
binaries, deployment configuration and operator UI rendering require separate
runtime qualification by the coordinator. A private v2 host-delegated grant that
needs native caller attestation remains unqualified when this CLI dispatch
context cannot supply that attestation; manual authority is never invented to
compensate. Native request-level hard admission remains with #354 and must not be
claimed from this preflight, ledger or sampled watcher.

Memory disposition: **forbidden**. The delegated lane is restricted to this
worktree; user-scoped memory and parent closeout are outside its write scope.

## Tested production source hashes

- `src/codex_wake/goal_host_preflight.py`: `ea0609744752a192594c6a2ba593eb82fe5432f509363ce68a2f4a1e5acd9866`
- `src/codex_wake/agent_lifecycle.py`: `a212ea404f9724af971beba3c590ee5d606cb4af22cc00703dc9eb1ed8afd981`
- `src/codex_wake/dispatch_packet.py`: `35300c5dc475a6160c23c8496981815fccabe580297d8c6f24f744c4c84c052e`
