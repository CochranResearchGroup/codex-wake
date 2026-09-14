# Event-driven wakes goal campaign

State: OPEN
Lane: P48
Owner: ecochran76
Work Items: CochranResearchGroup/codex-wake#4, #5, #6, #7, #8, #9, #10
Goal Version: P48-G1-v1
Target: origin/main
Integration: issue-scoped pull requests

## Goal objective

Use this exact objective for one `/goal` campaign:

> Deliver the accepted P48 event-driven-wakes product outcome across issues
> #4 through #10. Integrate a provider-neutral, crash-safe signal module that
> preserves existing predicates and dispatch transports; delivers
> restart-correct filesystem and authoritatively verified GitHub CI wakes;
> converges signed webhook hints with polling; productizes readiness, lifecycle,
> compatibility, and packaging; and records bounded routing calibration through
> issue-scoped pull requests and provider-free acceptance. Do not expose public
> ingress, perform provider or live-dispatch smokes, refresh the installed
> runtime, clean live state, deploy, or release without the exact separate
> authority gate.

One goal can cover all seven issues because they share one product outcome and
form a finite dependency graph. The goal does not make them one branch, one
pull request, or one simultaneous execution packet.

## Current state

Checkpoint `P48-G1-C00` started the goal from `origin/main` commit
`5b5d52943e7ba154eb4c1e0516cc7a0274403715`. Issues #4 through #10 are open
and assigned to `ecochran76`. Issue #4 is claimed on
`feat/issue-4-signal-foundation` at published checkpoint
`80e2db7603070452504caf31282558604602c5c2`; later issues remain dependency
blocked. No signal runtime, provider access, or live dispatch exists.

The current implementation writes schema-version-1 JSON wake records through
`cli.create_record` and evaluates predicates in `daemon.poll_once`. CodeGraph
reports 23 callers of `records.build_record`. The campaign must therefore
freeze the compatibility and storage interface before it fans out.

Graphiti discovery was healthy but returned no P48-specific prior decision or
validation evidence. Current repository documents, GitHub issues, CodeGraph,
tests, and Git history remain authoritative.

## Planning consultation receipt

Three read-only agents challenged the campaign from different constraints. The
primary owner reconciled their evidence and retained the planning decision.

| Handle | Requested model and effort | Scope | Disposition |
| --- | --- | --- | --- |
| `/root/goal_dependency_architect` | `gpt-5.6-sol`, high | Maximum safe issue scope, dependency graph, and concurrency | Accepted all seven issues under one staged goal and two concurrent write lanes. |
| `/root/goal_model_optimizer` | `gpt-5.6-luna`, medium | Tool/model routing, calibration, and cumulative accounting | Accepted tools-first routing, economical sidecars, and narrow specialist escalation. |
| `/root/goal_verification_designer` | `gpt-6-astra`, high | Crash safety, compatibility, adapter fixtures, and acceptance joins | Accepted the crash matrix, provider-free product proof, and one bounded fresh review. |

The runtime did not report separate effective-model or allocation receipts for
these consultations. They are planning evidence, not calibration samples for
issue #10.

## Scope

The campaign completes the provider-free implementation and integration
outcomes in all seven approved issues.

- Implement the versioned signal contract, journal, matching, evidence, and
  recoverable SQLite-to-JSON publication path from #4.
- Preserve existing predicates and target transports through the signal seam
  for #5.
- Implement restart-correct filesystem wakes for #6.
- Implement fixture-backed, authoritatively verified GitHub CI polling for #7.
- Implement signed webhook ingestion that converges with polling for #8.
- Productize readiness, evidence, retention, migration, downgrade, packaging,
  and disposable install behavior for #9.
- Complete a bounded model and delegation calibration from representative #6,
  #7, and verification work for #10.

## Non-goals and effect gates

The campaign must not cross these boundaries without a separate exact
authorization gate:

- expose a public webhook listener or provision webhook secrets;
- use live provider credentials or perform a live GitHub observation smoke;
- dispatch into a live tmux, app-server, or OpenClaw target;
- mutate or clean installed user runtime state;
- deploy, publish a release, create a public tag, or refresh an installation;
- weaken signature, allowlist, durability, compatibility, or evidence controls;
  or
- add unrelated event sources beyond the filesystem and GitHub contracts.

Ordinary in-scope repository edits, tests, issue coordination, branches,
worktrees, pull requests, CI repair, and merges remain inside the goal envelope
when the `/goal` invocation explicitly adopts this objective.

## Dependency graph

The graph preserves the accepted issue dependencies and exposes the two safe
fan-out points.

```text
#4 signal interface, journal, and cross-store authority
├── #5 existing predicate compatibility
│   └── #6 filesystem adapter ───────────────┐
└── #7 GitHub polling adapter               ├──> #9 product join
    └── #8 signed webhook convergence ──────┘

#6 + #7 ───────────────────────────────────────> #10 calibration
```

Issue #10 observes work from accepted implementation samples. It cannot block a
correctness repair, and an inconclusive result retains the current `balanced`
routing defaults.

## Milestones and execution waves

Each milestone unlocks work only after its required commits are merged into the
current `origin/main` and its acceptance evidence is durable.

| Wave | Issues | Execution shape | Unlock condition | Milestone proof |
| --- | --- | --- | --- | --- |
| 0 | Campaign control | Primary only | This plan is merged and the goal starts from a fresh readback. | Objective, authority, issue state, baseline, bounds, and first packet are recorded. |
| 1 | #4 | Serialized critical path | None | Register, publish, ingest, reserve, match, inspect, and restart through the provider-free interface with dispatch disabled. |
| 2 | #5 and #7 | Two worktrees in parallel | #4 accepted and merged | Existing predicates remain compatible; GitHub polling produces verified normalized receipts from fixtures. |
| 3 | #6 and #8 | Two worktrees in parallel | #5 and #7 accepted and merged | Filesystem recovery works; webhook and polling inputs converge on one logical occurrence. |
| 4 | #9 and #10 | Two disjoint worktrees when eligible | #6 through #8 accepted; #6 and #7 samples frozen | Disposable product lifecycle passes; calibration reports a bounded result without delaying correctness. |
| 5 | Integrated acceptance | Primary plus one fresh reviewer | #4 through #10 merged | Current `origin/main` satisfies every provider-free criterion and retains every gated effect as unexecuted. |

If #10 finishes before #9, its evidence remains provisional until the final
integrated acceptance check confirms that later repairs did not invalidate its
sample identities.

## Issue packets

Detailed implementation steps are derived just in time, but every issue keeps
one independently mergeable branch and pull request.

### Issue #4: signal foundation

The primary owner keeps authority over the shared module, interface, schemas,
durability protocol, and final acceptance.

- Packet 4A defines the versioned `register`, `arm`, `ingest`, and `evaluate`
  interfaces plus an in-memory adapter and contract tests.
- Packet 4B adds the SQLite journal, source anchors, deduplication, checkpoints,
  reservations, retention pins, and bounded evaluation progress.
- Packet 4C adds the recoverable JSON outbox, daemon seam, inspection output,
  corruption handling, and fresh-process crash tests.

The first evidence deadline is Packet 4A: it must demonstrate one provider-free
registration-to-match trace before storage breadth or adapter work expands.

### Issues #5 and #7: first fan-out

Issue #5 owns existing predicate compatibility in `records`, `daemon`, `cli`,
and their direct regression tests. Issue #7 owns the GitHub adapter, source
configuration, fixtures, and provider checkpoint logic.

Issue #7 may build its adapter and contract fixtures while #5 runs. It must not
change the shared signal interface or complete overlapping CLI integration
until #5 merges. After #5 merges, #7 starts its final integration packet from
the new `origin/main`.

### Issues #6 and #8: second fan-out

Issue #6 owns filesystem observation, fingerprints, reconciliation, coalescing
evidence, and filesystem-specific CLI behavior. Issue #8 owns authenticated
webhook ingestion, delivery limits, acknowledgement ordering, and convergence
with the accepted GitHub polling occurrence identity.

These lanes use the accepted signal interface. Any requested shared-interface
change returns to the primary owner and pauses only the affected lane until the
contract decision is integrated.

### Issues #9 and #10: terminal join

Issue #9 owns readiness, lifecycle, migrations, retention, evidence export,
packaging, and disposable installed-wheel acceptance. Issue #10 owns the
calibration dataset, analysis, and any recommendation.

The two lanes may overlap only while their write surfaces remain disjoint. Any
repo-default model or policy change proposed by #10 uses a separate serialized
pull request after #9 integration. Inconclusive calibration closes with the
current defaults unchanged.

## Worktree and subagent topology

One primary orchestrator owns the goal contract, authority, critical path,
shared interface, issue transitions, lane catalog, integration order, and final
acceptance claim.

The campaign uses no more than three concurrent subagents and no nested
delegation:

| Role | Write authority | Typical assignment |
| --- | --- | --- |
| Primary orchestrator | Coordination branch and explicitly retained shared-contract edits | #4 interface decisions, merge ordering, checkpoints, and final acceptance |
| Worker A | One issue-scoped worktree | #5 then #6 |
| Worker B | One issue-scoped worktree | #7 then #8 |
| Worker C | Read-only verification, then one issue-scoped worktree | Fresh review and #10 calibration |

At most two implementation worktrees write concurrently. The third slot is
reserved for read-only verification or calibration unless a plan revision
shows a higher-value disjoint lane. Each branch uses the approved prefixes and
stable names:

- `feat/issue-4-signal-foundation`
- `feat/issue-5-predicate-compatibility`
- `feat/issue-6-filesystem-wakes`
- `feat/issue-7-github-ci-polling`
- `feat/issue-8-github-webhooks`
- `feat/issue-9-signal-productization`
- `chore/issue-10-model-calibration`

Before parallel writes begin, the primary must publish exact branch, worktree,
owner, issue, expected surface, and dependency custody through
`docs/dev/active-lanes.yaml` on the default branch. A lane starts from the
current accepted dependency commit on `origin/main`; the campaign does not use
stacked dependent branches.

## Model selection

Model routing minimizes cumulative allocation per accepted milestone. Tools
perform deterministic discovery, diffing, hashing, test execution, fixture
comparison, counters, Git, and provider readback.

| Work | Default model and effort | Topology | Escalation rule |
| --- | --- | --- | --- |
| Routine orchestration, repair, and issue integration | `gpt-5.6-sol`, medium | Primary only | Increase effort only for a reproduced reasoning obstacle. |
| Shared architecture, security, and final acceptance | `gpt-6-astra`, high | Primary at material gates only | Retain authority with the primary and return routine work to the standard tier. |
| #4 storage and recovery implementation | `gpt-5.6-sol`, high | One implementation worker with primary contract review | Escalate one named crash-ordering or compatibility decision to `gpt-6-astra` only after conflicting evidence. |
| #5 compatibility implementation | `gpt-5.6-sol`, medium | One implementation worker | Increase reasoning only for a reproduced semantic regression. |
| #6 filesystem adapter | `gpt-5.6-sol`, medium | Worker A | Use high effort only for unresolved anchor, overflow, or coalescing causality. |
| #7 GitHub polling adapter | `gpt-5.6-sol`, high | Worker B | Escalate only for provider identity or verification ambiguity. |
| #8 webhook convergence and security | `gpt-5.6-sol`, high | Worker B plus bounded fresh security review | Escalate a specific signature, replay, acknowledgement, or storm-control finding. |
| #9 docs, manifests, and mechanical exports | `gpt-5.6-luna`, medium | Narrow sidecar with deterministic verifier | Return integration and migration decisions to `gpt-5.6-sol`. |
| #10 data extraction and comparison | `gpt-5.6-luna`, medium | Bounded evaluator | Use `gpt-5.6-sol` for synthesis; use `gpt-6-astra` only for contradictory causal evidence. |
| Ordinary PR conformance review | `gpt-5.6-luna`, medium | Fresh read-only reviewer | Escalate only an accepted blocking architecture, security, or causality finding. |

Every consequential run records requested model, reasoning effort, runtime-
reported effective model when available, context scope, topology, status,
accepted outcome, defects, interventions, elapsed wall time, summed worker
effort, and measured allocation or a labeled proxy. Unknown effective model or
shared-account allocation remains explicitly unknown.

## Calibration packet

Issue #10 freezes its comparison before representative #6 and #7 packets run.
The bounded sample covers adapter implementation, fixture construction, and
fresh independent verification.

The initial comparison uses these configurations where the task type fits:

- `gpt-5.6-sol` at medium effort with primary-only execution;
- `gpt-5.6-sol` at medium effort plus one `gpt-5.6-luna` sidecar; and
- `gpt-5.6-luna` at medium effort for mechanical fixture or evidence work.

The sample ceiling is six work units with no more than two units from one task
family. The quality floor is full acceptance with no unresolved critical or
high-severity finding. Failed, timed-out, repaired, retried, replaced, and
reconciled attempts remain in cumulative accounting.

The campaign promotes no routing change from fewer than three accepted task
families. It stops calibration at the sample ceiling, a critical quality
failure, or evidence that configurations cannot be compared fairly. A small or
inconclusive sample retains the `balanced` defaults.

## Goal controls and bounds

This plan resolves the duplicated example values in the general goal policy
for this campaign without changing repo-wide policy.

```text
goal_id: P48-G1
goal_version: P48-G1-v1
max_issue_scope: 7
max_concurrent_subagents: 3
max_concurrent_write_lanes: 2
max_work_unit_attempts: 2
max_review_rework_cycles: 1
max_hardening_checkpoints: 2
max_review_discovery_passes: 1
checkpoint_interval: 1 accepted issue or 90 minutes of active execution
authorization_gate: material_departure_or_explicit_action_gate_only
continuation_default: execute_obvious_in_scope_low_risk
bound_exhaustion_mode: local_replan_before_escalation
review_verification_mode: closed_world_if_reviewed
checkpoint_mode: material_boundary_with_cadence_backstop
checkpoint_record_fields: state_transition, acceptance_state, progress_classification, evidence, material_blockers, next_action_or_stop_reason
```

Two failed attempts split or reframe the affected work unit. One review cycle
may repair accepted blocking findings; verification then remains closed-world
against those findings plus critical regressions introduced by the repair. Two
consecutive hardening or no-progress checkpoints require a local tactic change
or bounded successor packet without resetting cumulative controls.

The one broad fresh-context `drift_discovery` review runs after #6 and #8 merge
and before #9 final integration. The three planning consultations used to write
this plan do not consume that future implementation review pass.

## Checkpoint contract

The primary records a durable checkpoint after every accepted issue merge,
dependency unlock, material replan, gated boundary, context handoff, and final
closeout. Checkpoints use stable IDs such as `P48-G1-C01` and contain:

- the state transition and current acceptance state;
- progress classification: `outcome_progress`, `blocker_reduction`,
  `hardening`, `no_progress`, or `regression`;
- exact branch, commit, issue, pull request, tests, and artifacts;
- current active-lane and worktree custody;
- accepted review findings and remaining review allowance;
- material blockers and their affected criteria; and
- the next ready action or exact stop reason.

Goal-level controls survive plan revisions, context changes, worker
replacement, and successor packets. A new filename or agent handle cannot reset
attempts, reviews, drift discovery, or no-progress history.

## Acceptance topology

Each issue pull request must pass focused tests at the signal module interface
and the affected integration seams. Each accepted merge must then pass the
repository presubmit matrix on Python 3.11 and 3.12.

### Contract and recovery proof

Issue #4 must test these interruption points through fresh processes:

1. before and after the prepared-arm transaction commits;
2. during temporary JSON writing, after rename, and before arm publication;
3. after publication commits but before registration returns;
4. before and after receipt plus checkpoint commit;
5. after match reservation but before JSON match evidence;
6. between match evidence, firing publication, and pending-path removal; and
7. during cancellation, expiry, cleanup, archive, retention, and migration.

Tests must cover two simultaneous registrars or evaluators at the SQLite seam.
They must establish process-crash correctness separately from host or power-loss
durability. Host-durability claims require an explicit SQLite synchronization
mode plus file and directory synchronization protocol; atomic rename alone is
not sufficient.

One logical observation may reserve one trigger winner per wake. Existing
bounded dispatch retries may still requeue delivery. The campaign must not
claim exactly-once external delivery.

### Compatibility and adapter proof

Contract tests cover `occurs`, `holds`, and `becomes`; anchor ordering;
`Invalid` versus `Degraded`; bounded `eq` and `in`; source isolation; fan-out;
evaluation budgets; and credential-shaped sanitization canaries.

Adapter fixtures cover:

- filesystem creation, existing and missing baselines, rename, delete and
  recreate, rapid writes, missed notifications, restart, overflow, and
  coalescing evidence;
- GitHub repository, workflow, ref, conclusion, pagination, run attempts,
  stale and duplicate runs, authentication loss, retry windows, history gaps,
  checkpoint restart, and verification failure; and
- webhook signature and body limits, rejection diagnostics, duplicate success,
  commit-before-acknowledgement, delivery order, replay, and bounded storms.

The canonical GitHub occurrence identity must include rerun and attempt
semantics before #8 starts, so polling and webhook delivery converge on the same
receipt.

Compatibility proof includes executable old/new-reader fixtures, mixed v1 and
signal records, writer capability gating, plugin-produced v1 records,
mixed-version supervisor behavior, interrupted migration, and safe downgrade or
explicit downgrade refusal.

### Product and integrated proof

The final provider-free acceptance runs:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
npm --prefix plugins/openclaw-codex-wake test
python -m compileall -q src tests
```

Issue #9 also builds a wheel, installs it into a disposable environment, and
proves registration, restart, observation, resolution, inspection, evidence
export, retention, and retirement for filesystem and fixture-backed GitHub
wakes. Fake transports prove submission, retry, and acknowledgement behavior;
`--no-dispatch` alone proves only trigger resolution.

Every validation receipt records the exact commit, tier, command, environment,
first failure, retry, flake, exclusion, and artifact identity. Passing
provider-free tests does not prove a public listener, live provider access,
installed runtime, release, or live dispatch.

## Integration workflow

Each issue follows the same governed sequence:

1. Reconcile the issue, current `origin/main`, active-lane catalog, and expected
   write surface.
2. Create and register one issue branch and worktree before implementation.
3. Derive one bounded packet with owner, surface, inputs, evidence, and terminal
   condition.
4. Implement test-first at the deepest stable interface.
5. Run focused checks, affected integration checks, and the required presubmit
   fallback for uncertain impact.
6. Push a coherent checkpoint and verify the remote commit.
7. Open a linked pull request with scope, live effect, validation, and overlap.
8. Use one bounded review/rework cycle, then merge only after required CI passes.
9. Read back the merge commit, update issue evidence, and reconcile active-lane
   custody before unlocking dependents.

Prefer squash merge for each independently mergeable issue. Do not delete a
branch or worktree until integration and custody readback prove cleanup is safe.

## Stop and replan conditions

The primary pauses the affected lane and replans when any of these conditions
occurs:

- #4 leaves the shared interface, storage authority, compatibility path, or
  contract tests unsettled;
- a dependency is not accepted on current `origin/main`;
- branch or worktree custody is ambiguous, or two lanes overlap in writes;
- provider-specific logic leaks into the daemon or ordinary caller interface;
- schema-v1 predicates, retry, expiry, cancellation, firing recovery, or target
  dispatch semantics regress;
- a required new top-level workflow or interface exceeds the approved design;
- closed-world verification fails an accepted blocking finding;
- a work unit, review, hardening, or calibration bound is exhausted; or
- an exact effect gate requires authority that the campaign does not have.

A scoped gate blocks only the affected criterion. The goal continues unrelated
safe provider-free work while meaningful progress remains.

## Definition of done

The campaign is complete only when all of these conditions hold:

- issues #4 through #10 satisfy their acceptance criteria and close from exact
  merge evidence;
- every issue-scoped pull request is integrated into the intended `origin/main`;
- the provider-free lifecycle works through the installed candidate package;
- existing predicates and all target transports retain their documented
  behavior;
- crash, replay, concurrency, migration, downgrade, retention, and evidence
  invariants pass at their real seams;
- filesystem, GitHub polling, and webhook fixtures prove the accepted source
  semantics without live effects;
- the bounded calibration reports a valid result or an honest inconclusive
  result that retains current defaults;
- the active-lane catalog, plans, roadmap, runbook, issue states, branches, and
  worktrees reconcile with current GitHub and Git readback;
- one fresh review has no unresolved accepted blocking finding; and
- final evidence distinguishes provider-free acceptance from every unexecuted
  live, release, deployment, and installed-runtime gate.

The first goal action is to record checkpoint `P48-G1-C00`, claim issue #4,
register `feat/issue-4-signal-foundation`, and derive Packet 4A from the current
`origin/main`. No adapter implementation begins before the #4 contract
milestone merges.
