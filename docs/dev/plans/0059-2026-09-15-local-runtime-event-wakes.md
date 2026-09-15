# Local runtime event wakes goal campaign

State: OPEN
Lane: P51
Issues: #58, #59, #60, #61, #62, #63
Branch: `multi-lane; see docs/dev/active-lanes.yaml`
Goal ID: P51-G1
Goal Version: P51-G1-v4
Checkpoint: P51-G1-C03

## Goal objective

> Deliver production-safe, restart-correct local runtime event wakes for one
> exact same-user process termination and one exact user-systemd unit state
> transition. Reuse the provider-neutral signal journal, existing dispatch
> transports, lifecycle controls, and supported operator surfaces. Preserve
> legacy `process_done` behavior and fail closed on identity, authorization, or
> observation ambiguity. Prove the installed boundary with one isolated
> candidate and at most one visible Codex wake. Do not add public ingress,
> system-manager control, provider mutation, arbitrary commands or D-Bus
> access, a release, deployment, or global installation refresh.

## Current state

Checkpoint `P51-G1-C03` records issue #59 implementation checkpoint
`37df666b12a433a63acfb4dfc88a6d27ff521a74` as integration-ready in PR #67.
Focused, comprehensive, plugin, compilation, CI, and fresh adversarial review
gates pass. Issues #60 and #61 still wait for its canonical-main integration;
#62 joins both adapters, and #63 remains acceptance-only.

CodeGraph is healthy with 94 indexed files, 2,462 nodes, and 9,002 edges. It
confirms that `SignalSourceAdapter` owns contracts and anchors,
`SignalSourceRunner` owns reconciliation, `default_signal_runners` reconstructs
published arms after restart, and the journal/record publisher already owns
deduplication and lifecycle publication. The current process predicate captures
PID start ticks and boot ID, which is the compatibility boundary to preserve.

Graphiti was healthy but `codex_wake_main` returned no relevant local-runtime
facts. Current repository, issue, Git, test, CodeGraph, and runtime evidence
remain authoritative. The deterministic policy selector reports
`product-engineering`, `balanced`, `repo-product-engineering`, and
`already-aligned`; active planning, goal-policy, active-lane, and forge-create
preflights pass.

## Architecture decisions

1. Local runtime sources extend `SignalSourceAdapter` and
   `SignalSourceRunner`; they do not add a second scheduler or dispatch path.
2. Allowlisting has two layers: a closed versioned source-kind vocabulary and
   source-specific exact resource authorization. Process registration may
   select only a currently observable same-effective-UID Linux process and
   freezes boot ID, PID, and start ticks. User-systemd registration selects
   only an exact preconfigured canonical user-unit name and allowed target
   `ActiveState`.
3. Both recipes use state-transition semantics. Registration establishes a
   nonmatching baseline; an already-terminated process or already-matching unit
   does not manufacture an event. A positive later observation may emit one
   stable logical occurrence.
4. A process watch identifies `(boot_id, pid, start_time_ticks, owner_uid)`.
   PID reuse cannot match. A pidfd may accelerate one daemon lifetime but is
   not durable identity. Zombie state proves termination; absence or
   replacement must be positively classified. Permission and observation
   errors degrade. Exit code and exact exit time are unsupported.
5. The first systemd surface is the current user's manager only. It supports a
   narrow documented target-state set such as `active`, `inactive`, and
   `failed`. Alias resolution occurs before authorization. Missing units are
   unavailable, not inactive. The observer exposes fixed read-only fields and
   cannot start, stop, restart, enable, disable, create transient units, reach
   the system manager, or invoke arbitrary methods.
6. Same-boot recovery reuses the persisted identity, baseline, source
   fingerprint, and occurrence namespace. A boot change invalidates process
   watches and conservatively re-baselines systemd watches. A reconciled
   systemd state change may satisfy `becomes`; an enter-and-leave cycle wholly
   missed during an observation gap is not claimed.
7. Observation, occurrence identity, source progress, match reservation, and
   wake publication reuse the existing journal/outbox authority. Repeated
   reconciliation or dispatch recovery cannot create a second logical event.
8. Runtime evidence is bounded and sanitized. Do not persist process command
   lines, environments, unit secrets, raw D-Bus payloads, prompt bodies, or raw
   pane text. Operator surfaces expose capability, health, recovery strength,
   observation age, and safe resource identity only.
9. Legacy `process_done` remains a schema-v1 compatibility path. P51 adds a
   supported signal recipe without silently changing old registration,
   readiness, or completion behavior.

## Scope

- Add one versioned runtime-source descriptor and exact authorization seam.
- Add a provider-free tracer proving registration, recovery, observation,
  matching, cancellation, timeout, revocation, and resource bounds.
- Add a restart-correct process-termination adapter and supported CLI recipe.
- Add a restart-correct user-systemd state-transition adapter, exact source
  configuration, and supported CLI recipe.
- Reconstruct both sources in fresh daemon processes and expose bounded health.
- Extend doctor, readiness, status, support export, documentation, packaging,
  and installed-wheel provider-free verification.
- Run one isolated installed candidate against the higher-residual-risk source,
  one disposable resource, and at most one live tmux dispatch.
- Use GitHub issues, short-lived branches, pull requests, CI, and canonical-main
  readback for every independently mergeable slice.

## Non-goals and effect boundaries

- No system-manager observation or mutation; only the current user manager.
- No start, stop, restart, enable, disable, transient-unit creation, or other
  unit-control operation by product code.
- No arbitrary PID discovery, process command/environment capture, shell
  command, wildcard selector, D-Bus method, bus name, object path, or property.
- No promise of process exit code, exact exit timestamp, or lossless replay of
  every systemd transition across downtime.
- No public listener, webhook deployment, provider configuration or credential
  mutation, network source, global installation refresh, tag, release, or
  deployment.
- No more than one installed canary registration or one live dispatch. Failure
  or ambiguity ends the canary without a retry; product correction requires a
  separately linked issue and new acceptance decision.

## Dependency graph and ownership

```text
#59 runtime contract and provider-free tracer
        |                         |
        v                         v
#60 process-exit adapter    #61 user-systemd adapter
        |                         |
        +------------+------------+
                     v
          #62 productization join
                     |
                     v
          #63 installed canary
```

The primary orchestrator owns the shared contract, issue graph, architecture,
authority, integration order, live canary, and final acceptance. After #59 is
accepted, #60 and #61 may use two disjoint worktrees concurrently. #62 is a
serialized join and cannot redefine the contract. #63 changes only canary
procedure and evidence; any implementation defect returns to a corrective
issue rather than being repaired inside the acceptance branch.

## Multi-agent and model-routing policy

Execution bias is `balanced`, with at most two implementation workers plus one
read-only reviewer. Nested delegation is disabled.

- The primary or `gpt-6-astra` high owns #59 because identity, authorization,
  crash recovery, and compatibility are cross-cutting safety decisions.
- `gpt-5.6-terra` high is the standard route for disjoint #60 and #61
  implementation after the contract freezes.
- `gpt-5.6-terra` medium is the default for bounded #62 product integration.
- `gpt-5.6-luna` medium is reserved for narrow inventories, fixture checks,
  and one fresh independent review; deterministic tools own hashes, counters,
  tests, CI polling, and runtime readback.
- The primary owns #63 and all live, installed, merge, issue-close, and final
  acceptance effects.

Requested and runtime-reported effective model, effort, elapsed time, defects,
repairs, and acceptance are recorded when exposed. Model changes and worker
replacement remain inside the same cumulative goal bounds. Workers may not
change scope, weaken safety, mutate GitHub beyond their assigned branch/PR,
operate live services, dispatch, merge, close issues, or release.

Initial consultations were read-only. `/root/p51_runtime_semantics` was
requested on `gpt-6-astra` high and supplied the process/systemd identity,
recovery, privacy, and hard-stop decisions incorporated above.
`/root/p51_issue_acceptance` was requested on `gpt-5.6-luna` medium and
confirmed the five-slice graph, contract ownership, join, and acceptance-only
canary boundary. Effective runtime model and allocation receipts were not
reported; no savings claim is made.

## Goal controls and bounds

```text
goal_id: P51-G1
goal_version: P51-G1-v1
max_work_unit_attempts: 2
max_review_rework_cycles: 1
max_hardening_checkpoints: 2
max_review_discovery_passes: 1
checkpoint_interval: 1 accepted issue or material gate
concurrency_limit: 2 implementation lanes plus 1 read-only reviewer
live_provider_mutations: 0
live_dispatch_attempts: 1
installed_canary_attempts: 1
installed_canary_retries: 0
global_install_mutations: 0
authorization_gate: material_departure_or_explicit_action_gate_only
review_verification_mode: closed_world_if_reviewed
checkpoint_fields: state_transition, acceptance_state, progress_classification, evidence, material_blockers, next_action_or_stop_reason
```

The approved goal authorizes ordinary issue/branch/PR implementation,
provider-free fixtures, bounded read-only local process and user-systemd
inspection, one isolated candidate service, one disposable same-user process
or user unit controlled by the canary owner, one wake with `max_attempts: 1`,
and at most one live tmux dispatch. It does not authorize any excluded effect.

## Validation and invalidation map

- Contract validation: hostile descriptors, authorization revocation, resource
  ceilings, process-boundary recovery, journal crash points, deduplication,
  cancellation, and timeout tests.
- Process validation: owner mismatch, PID reuse, zombie, disappearance during
  registration, permission failure, same-boot restart, boot invalidation, and
  legacy `process_done` regressions without arbitrary sleeps.
- Systemd validation: exact unit/state configuration, alias authorization,
  initial match, real transition, repeated state, missing unit, reconnect,
  observation gap, boot change, timeout, cancellation, and fake-boundary crash
  tests.
- Product validation: supported CLI, fresh daemon reconstruction, doctor,
  readiness, status, support export, installed wheel, Python 3.11/3.12,
  OpenClaw plugin, compilation, planning audits, and GitHub CI.
- Installed validation: exact commit/wheel/executable/configuration/unit/PID,
  target and resource identity, restart recovery, one observation/match/
  dispatch/ack/visibility result, archive, and exact rollback.

A source-specific test failure invalidates only that adapter and its dependent
join. A shared contract or journal failure invalidates both adapters. A #62
packaging/readiness failure does not erase accepted adapter behavior but blocks
the installed canary. A canary failure blocks installed acceptance only unless
its evidence identifies a causal product defect; it never erases unaffected
provider-free evidence. Any duplicate or ambiguous live effect ends #63.

## Stop and replan conditions

Stop a source before integration if it cannot prove exact resource identity,
authorization, bounded observation, stable occurrence identity, or
restart-correct recovery without acquiring an excluded capability. Stop #60 on
foreign ownership, boot ambiguity, PID reuse ambiguity, or any need to inspect
command/environment data. Stop #61 if the implementation needs system-manager
access, mutation methods, arbitrary D-Bus authority, wildcard resources, or a
lossless replay claim.

Stop before the canary if source, wheel, service, wake-root, disposable
resource, target, or attempt-bound identities disagree; if the isolated root
is pre-existing or nonempty; if the normal/global runtime drifts; or if restart
recovery is incomplete. After registration, any ambiguous observation, match,
dispatch, acknowledgement, visibility, or cleanup ends the attempt without
retry.

## Acceptance criteria

- Issues #59 through #62 each deliver their stated provider-free product
  boundary through accepted pull requests and required CI.
- Process termination and user-systemd state transition are exact,
  authorization-bound, restart-correct, deduplicated, inspectable, and fail
  closed without weakening legacy behavior.
- Readiness and support surfaces tell the truth about availability, recovery,
  observation gaps, unsupported evidence, and privacy.
- One isolated installed canary produces exactly one bounded visible wake and
  is archived and rolled back without global or unrelated runtime drift.
- ROADMAP, RUNBOOK, vision, plan, active lanes, GitHub, Git, tests, CI, and
  installed receipts agree on the outcome.

## Definition of done

Issues #58 through #63 are closed from accepted evidence; all implementation
branches and worktrees are reconciled; the plan and P51 roadmap lane are
closed; the active-lane catalog is empty; comprehensive validation passes from
canonical integration state; one installed local-runtime wake is verified and
rolled back; and clean synchronized `origin/main` has no P51 topic branch,
open issue, or pull request.
