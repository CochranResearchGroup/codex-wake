# Event source extension framework goal campaign

State: OPEN
Lane: P52
Issues: #81, #82, #83, #84, #85
Branch: `multi-lane; see docs/dev/active-lanes.yaml`
Goal ID: P52-G1
Goal Version: P52-G1-v6
Checkpoint: P52-G1-C06

## Goal objective

> Deliver a closed built-in event-source extension framework so future wake
> sources can integrate without adding another source-specific branch to daemon
> reconstruction, readiness, status, and support wiring. Preserve every current
> filesystem, process, user-systemd, and GitHub CI behavior while proving the
> seam with provider-free conformance and an isolated installed-wheel smoke. Do
> not add arbitrary third-party loading, a new source, provider effects, live
> dispatch, a release, deployment, or a global installation refresh.

## Current state

P51 closed at canonical commit `0df33860562fea1ab7136e9fa5104b3e761e0807`
with no open issue, pull request, or active lane. `SignalSourceAdapter`,
`SignalSourceRunner`, and the journal/outbox already provide the provider-neutral
observation and durable publication boundaries. The remaining extension cost is
central wiring: `default_signal_runners` reconstructs filesystem, process,
user-systemd, and GitHub CI sources through source-specific branches, while
readiness and support integration remain bespoke.

CodeGraph confirms that source families do not have a uniform one-arm-to-one-
runner shape. Filesystem, user-systemd, and GitHub CI batch candidates; process
creates runners per configured instance. The extension seam must therefore be
a family-level runner factory over the complete ordered candidate set, not a
generic per-arm adapter constructor.

PR #86 passed both required release gates and merged the coordination state at
`b554a0f2cf1bee75d8c8268575055c6652112919`. Issue #82 is now the sole ready
implementation slice under lane plan
`docs/dev/plans/0066-2026-09-15-built-in-source-registry-contract.md`; #83
through #85 remain dependency-blocked. Its implementation is integration-ready
at `e9e55031b2a03d22467c854b80074f3c333ece3f` in PR #89 after 39 focused
tests, 425 comprehensive Python tests, 12 plugin tests, compilation, required
Python 3.11/3.12 CI, and independent review with no findings.

PR #89 subsequently squash-merged at canonical
`f8059cd2390a3459ce6b28073cfb040446ea05ba`, closing #82. Local migration #83
and GitHub migration #84 are now assigned as disjoint parallel worktrees. Their
workers own separate family modules and tests; the primary reserves shared
`daemon.py` catalogue composition and integrates it serially.

Local migration #83 squash-merged through PR #93 at canonical
`3c30947ffedb1e87a312e6377d75353b9d5361a6`, closing the issue. GitHub
migration #84 is integration-ready in PR #95 at
`1be2a395bab644a02c5f4f1f1e868c5bd065f2f7` after reconciling canonical main,
preserving legacy instance/arm ordering, and passing 68 focused tests, 435
comprehensive Python tests, 12 plugin tests, compilation, installed-wheel CI on
Python 3.11/3.12, and independent review with no findings.

Graphiti was healthy but returned no P52-specific durable facts. Current source,
Git, GitHub, policy, plan, and test evidence are authoritative. Deterministic
planning, goal-policy, active-lane, and forge-create preflights pass. Parent
issue #81 and vertical child issues #82 through #85 are the coordination ledger.

## Architecture decisions

1. Add one immutable catalogue of built-in source-family registrations. A
   registration has a unique identity, owns a closed set of `(source, kind)`
   pairs, and supplies a family-level runner factory.
2. Keep `SignalSourceAdapter`, `SignalSourceRunner`, normalization, matching,
   checkpoints, reservations, publication, cancellation, expiration, and
   dispatch ownership unchanged.
3. Registration states implementation availability only. Configuration and
   source-specific authorization remain mandatory before observation; a
   registered family acquires no authority by existing in the catalogue.
4. Factories receive the complete deterministically ordered candidate set plus
   an explicit reconstruction context. They do not receive the daemon object or
   an untyped dependency bag.
5. Reject duplicate registration identities and overlapping source/kind
   ownership when the catalogue is constructed.
6. Preserve the existing source and runner order, family batching, source-
   instance identity, material-reconfiguration checks, anchors, authorization
   rechecks, retry deadlines, failure isolation, health codes, and malformed-
   record handling during extraction.
7. Catalogue introspection is read-only. Readiness, status, and support may use
   source-owned projections but must not call runner factories, create provider
   clients, poll a source, or migrate state.
8. Keep `default_signal_runners` as the compatibility entry point while its
   internal source selection delegates to the closed catalogue.
9. Correct the systemd unloaded-unit diagnostic narrowly: missing or unloaded
   is unavailable, never silently described as inactive. This does not widen
   unit selection or observation authority.

## Scope

- Define the built-in source-family registration and reconstruction context.
- Prove the seam with a provider-free fixture source and conformance harness.
- Migrate filesystem, process, user-systemd, and GitHub CI reconstruction while
  preserving behavior.
- Reuse the catalogue for side-effect-free built-in inventory and source-owned
  readiness/support contributions.
- Document the internal extension procedure and closed security boundary.
- Build an exact candidate wheel and run one isolated provider-free,
  dispatch-disabled installed compatibility smoke.
- Use GitHub issues, short-lived branches, pull requests, required CI, and
  canonical-main readback for each independently mergeable slice.

## Non-goals and effect boundaries

- No arbitrary package loading, entry points, dynamic imports from
  configuration, hot registration, external plugin ABI, or universal source
  configuration schema.
- No new event source, webhook ingress, new provider, credential change,
  provider read or mutation, public listener, or raw provider payload storage.
- No new scheduler, journal schema, dispatch transport, executable callback,
  arbitrary URL, command, filter, or resource selector.
- No live tmux or app-server dispatch, service installation, normal wake-root
  mutation, global installation refresh, tag, release, or deployment.
- No normalization of existing asymmetric health behavior unless a separate
  issue and acceptance decision explicitly authorizes that behavior change.

## Dependency graph and ownership

```text
#82 contract + provider-free conformance tracer
             |
             +-------------------+
             v                   v
#83 local-source migration   #84 GitHub migration
             +-------------------+
                         |
                         v
#85 productization + installed compatibility
```

The primary owns the shared architecture, issue graph, catalogue schema,
integration order, GitHub mutations, installed boundary, and final acceptance.
After #82 freezes the contract, #83 and #84 may run in disjoint worktrees in
parallel. #85 is a serialized join and may not redefine accepted source
semantics.

## Multi-agent and model-routing policy

Execution bias is `balanced`, with at most two implementation workers plus one
read-only reviewer. Nested delegation is disabled.

- The primary or `gpt-6-astra` high owns #82 because the closed authority and
  compatibility seam is cross-cutting.
- `gpt-5.6-terra` high is the standard route for the disjoint #83 and #84
  migrations after the contract freezes.
- `gpt-5.6-terra` medium is the default for bounded #85 product integration.
- `gpt-5.6-luna` medium is reserved for narrow fixture work and independent
  acceptance review. Deterministic tools own audits, tests, hashes, counters,
  CI polling, and installed readback.
- The primary owns all branch/PR integration, issue closure, and installed
  effects. Workers may not expand scope, perform provider or live effects,
  merge, close issues, or release.

Initial read-only consultations were bounded. `/root/p52_contract_review` was
requested on `gpt-6-astra` high and established the family-level factory,
batching, ordering, authority, and introspection invariants. `/root/p52_acceptance_review`
was requested on `gpt-5.6-luna` medium and confirmed provider-free conformance,
installed compatibility, and hard effect boundaries. Effective runtime model
and allocation receipts were not reported, so no allocation-savings claim is
made.

## Goal controls and bounds

```text
goal_id: P52-G1
goal_version: P52-G1-v1
max_work_unit_attempts: 2
max_review_rework_cycles: 1
max_hardening_checkpoints: 2
max_review_discovery_passes: 1
checkpoint_interval: 1 accepted issue or material gate
concurrency_limit: 2 implementation lanes plus 1 read-only reviewer
live_provider_reads: 0
live_provider_mutations: 0
live_dispatch_attempts: 0
installed_compatibility_attempts: 1
installed_compatibility_retries: 0
global_install_mutations: 0
authorization_gate: material_departure_or_explicit_action_gate_only
review_verification_mode: closed_world_if_reviewed
checkpoint_fields: state_transition, acceptance_state, progress_classification, evidence, material_blockers, next_action_or_stop_reason
```

The approved goal authorizes normal issue, branch, pull-request, test, CI, and
provider-free isolated virtual-environment work. It does not authorize any
excluded effect.

## Validation and invalidation map

- Contract validation: ownership collisions, deterministic ordering, whole-
  family batching, construction failures, unavailable fallback, side-effect-
  free introspection, fresh-process reconstruction, and fixture-source
  integration without a daemon source branch.
- Local migration validation: filesystem/systemd batching, process per-instance
  runners, exact authorization, anchors, cancellation, expiration, revocation,
  malformed records, failure isolation, and unloaded-unit diagnostics.
- GitHub validation: configured-instance batching, fixed-origin authority,
  anchors, bounded retry timing, coverage truthfulness, degraded health,
  provider-free clients, and failure isolation.
- Product validation: CLI and daemon compatibility, doctor/readiness/status/
  support output, documentation, wheel build, isolated installed reconstruction,
  Python 3.11/3.12 CI, comprehensive Python tests, OpenClaw plugin tests,
  compilation, Git diff checks, and planning audits.

A contract or catalogue defect invalidates both migration lanes. A source-
specific parity failure invalidates only that migration and #85. A packaging or
operator-surface failure blocks installed compatibility but does not erase
accepted runtime parity. An installed-smoke failure blocks installed acceptance
and receives no retry inside the same attempt.

## Stop and replan conditions

Stop if the seam requires arbitrary code loading, untyped daemon access,
per-arm construction that changes batching, new source authority, journal or
dispatch redesign, provider access, or any public/output behavior change not
covered by an explicit acceptance criterion. Stop a migration on changed
ordering, budgets, retry schedules, anchors, authorization, recovery, health,
or malformed-record handling. Stop the installed smoke if the commit, wheel,
executable, isolated root, or dispatch-disabled condition is ambiguous.

## Acceptance criteria

- Issue #82 proves one closed registration contract and provider-free fixture
  source without a daemon source branch.
- Issues #83 and #84 route all four production families through the catalogue
  with documented behavior parity and required CI.
- Issue #85 aligns runtime inventory, readiness/support, documentation, and an
  isolated dispatch-disabled installed wheel.
- The systemd unloaded-unit diagnostic is truthful without expanded authority.
- ROADMAP, RUNBOOK, this plan, active lanes, GitHub, Git, tests, CI, and the
  installed receipt agree on the accepted result.

## Definition of done

Issues #81 through #85 are closed from accepted evidence; all implementation
branches and worktrees are reconciled; the P52 plan and roadmap lane are
closed; the active-lane catalogue is empty; comprehensive and plugin validation
passes on canonical integration state; installed compatibility is proven and
cleaned up; and synchronized `origin/main` has no P52 topic branch, open issue,
or pull request.
