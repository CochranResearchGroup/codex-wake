# AuraCall terminal-response wake source

State: CANCELLED
Lane: I169
Issue: #169
Branch: `feat/issue-169-auracall-terminal-source`
Target: `main`
Integration: `squash`

## Current state

Superseded before implementation by Plan 0096. The receipt-directory design
was too specific to AuraCall and would have required producer behavior created
only for Codex Wake. No implementation was performed from this plan.

## Objective

Add an opt-in `auracall.session.terminal` built-in source that admits bounded,
atomically completed receipts only after exact confined result verification,
then creates normal idempotent Codex Wake signals without transporting private
session content.

## Scope and write surface

- Define a versioned, bounded terminal-receipt schema and owner-only source
  configuration rooted at one allowlisted receipt directory.
- Add a source adapter/runner and built-in registry entry with restart-correct
  occurrence identity, durable result checks, bounded polling, and fail-closed
  health.
- Add configure/show/check/remove and terminal-wake CLI surfaces with optional
  profile, session, slug, and accepted-state filters.
- Keep prompts locator-only and route through existing tmux/app-server targets
  plus the existing `--require-monitor` gate.
- Project AuraCall source health separately through signal and product
  readiness without constructing a runner during introspection.
- Add focused contract, runner, CLI, readiness, and routing-boundary tests;
  update operator and source-extension documentation.

Expected implementation surfaces are `src/codex_wake/auracall_*`, the closed
source registry, CLI/readiness integration, focused tests, README/source docs,
and this plan's roadmap/runbook/lane records. A journal schema or dispatch
transport change requires replanning before edit.

## Invariants and effect boundary

- Receipts and referenced results must remain beneath configured canonical
  roots; symlinks, traversal, nonregular files, ambiguous identities, and
  owner/permission mismatches fail closed.
- Observation admits only supported schemas and configured terminal states.
  A receipt visible before its referenced result is durable remains ineligible
  until exact verification succeeds.
- Wake data contains bounded metadata and safe locators only: never raw
  prompts, credentials, cookies, response bodies, or unrestricted paths.
- Immutable session/event identity deduplicates across repeated polls and
  daemon restarts. Observation, wake creation, submission acknowledgement, and
  visible delivery remain distinct evidence states.
- Source configuration grants read-only observation of one bounded root. It
  grants no AuraCall invocation, retry, cancellation, provider access, target
  selection, service installation, or dispatch authority.
- No live AuraCall session, live dispatch, service change, user installation,
  release, provider effect, or AuraCall-repository mutation occurs in this
  plan without a separately recorded exact gate.

## Execution packets

1. Freeze the consumer receipt/configuration contract and add red provider-free
   tests for atomic completion, result durability/digest, state filtering,
   path confinement, malformed input, and immutable occurrence identity.
2. Implement configuration, adapter, runner, registry reconstruction, and
   restart-correct journal convergence at the existing signal seams.
3. Add governed CLI setup/readback/arming, locator-only prompt construction,
   and monitor-gated tmux/app-server boundary tests.
4. Add readiness/support projections and documentation, then run focused,
   comprehensive, compilation, planning, and hosted gates.

The primary agent owns all packets and integration. No delegated lane is
planned because these packets share the receipt/configuration contract and
source-family write surface.

## Acceptance criteria

- One atomic successful receipt produces exactly one eligible wake across
  repeated polls and a fresh runtime reconstruction.
- A pre-result receipt does not fire and becomes eligible only after exact
  durable result verification.
- Configured success/error/cancelled policy is enforced without provider retry
  or source-side effect.
- Malformed, truncated, incompatible, symlink-escaped, unauthorized, or
  path-traversing receipts fail closed with bounded health evidence and zero
  dispatch.
- Wake prompts contain safe AuraCall locators and require the resumed agent to
  re-verify persisted session state before acting.
- Focused tests prove both tmux and app-server routing boundaries without
  treating acknowledgement as visible delivery.
- Product readiness reports source, monitor, hook, and dispatch gates
  independently; focused, comprehensive, compilation, planning, and hosted CI
  checks pass before integration.

## Validation and invalidation map

- Receipt/configuration contract failures invalidate packets 2-4.
- Source observation, confinement, or deduplication failures invalidate the
  source implementation but not existing generic dispatch transports.
- CLI or readiness failures block product acceptance without erasing a valid
  provider-free adapter result.
- Tmux/app-server boundary failures block their affected routing claim only;
  neither permits a live dispatch retry.
- Hosted or packaging failure blocks integration and receives at most one
  bounded repair cycle.

## Goal controls

```text
goal_id: P58-G1
goal_version: P58-G1-v1
max_work_unit_attempts: 2
max_review_rework_cycles: 1
max_hardening_checkpoints: 2
max_review_discovery_passes: 1
checkpoint_interval: 1 execution packet or material gate
concurrency_limit: 1 primary lane
live_provider_reads: 0
live_provider_mutations: 0
live_dispatch_attempts: 0
service_or_install_mutations: 0
authorization_gate: material_departure_or_explicit_action_gate_only
review_verification_mode: closed_world_if_reviewed
checkpoint_fields: state_transition, acceptance_state, progress_classification, evidence, material_blockers, next_action_or_stop_reason
```

## Next action

Write the provider-free receipt/configuration contract tests, demonstrate the
new invariant failures, and implement the smallest source seam that makes them
pass without changing journal or dispatch schemas.
