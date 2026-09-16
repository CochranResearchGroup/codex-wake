# Built-in source registry contract and conformance tracer

State: CLOSED
Lane: P52-C1
Issue: #82
Branch: `feat/issue-82-source-registry-contract`
Target: `main`
Integration: `squash`

## Current state

PR #89 squash-merged at canonical
`f8059cd2390a3459ce6b28073cfb040446ea05ba`, closing #82. The immutable
built-in family registry, reconstruction context, provider-free conformance
fixture, and optional daemon injection seam are accepted. Production-family
migration remained in #83 and #84.

## Objective

Add an immutable built-in source-family registration contract and generic
reconstruction path, then prove the seam with a provider-free fixture source.
Existing production sources and all public behavior remain unchanged in this
slice.

## Scope

- A frozen registration descriptor with unique identity and closed source/kind
  ownership.
- A registry that rejects duplicate identities and overlapping ownership.
- An explicit reconstruction context and candidate type carrying one durable
  pending record plus its loaded `ArmedSignal`.
- A family-level factory over the complete deterministic candidate tuple.
- An optional injected registration catalogue in `default_signal_runners` for
  provider-free conformance without adding a fixture-specific daemon branch.
- Tests for selection, ordering, batching, collision rejection, malformed
  records, construction failure isolation, and construction-time side effects.

## Non-goals

- No migration or semantic change for filesystem, process, user-systemd, or
  GitHub CI production sources.
- No readiness/status/support changes; catalogue introspection remains pure and
  later source-owned projections belong to #85.
- No arbitrary package loading, entry points, dynamic import, hot registration,
  external plugin ABI, new source, provider call, live runtime observation,
  dispatch, installation, release, or deployment.

## Write surface

- `src/codex_wake/source_registry.py`
- `src/codex_wake/daemon.py` only for the generic injected catalogue seam
- `tests/test_source_registry.py`
- `tests/test_daemon.py` only for compatibility and fixture reconstruction
- this plan, P52 plan/checkpoint, roadmap/runbook, and active-lane projection

Any production-source module or public schema change stops for primary-owner
reconciliation before editing.

## Acceptance criteria

- Duplicate registration IDs and overlapping `(source, kind)` ownership fail
  deterministically before any factory runs.
- Candidate selection uses durable `ArmedSignal` source/kind identity, preserves
  pending-record order, and passes each family one complete immutable tuple.
- Unknown and unowned source families remain governed by existing behavior.
- Factory failure is isolated and cannot prevent another injected family from
  constructing; it performs no implicit retry or state/provider mutation.
- A provider-free fixture family reconstructs through `default_signal_runners`
  without a source-specific daemon branch and without changing production
  runner order when no catalogue is injected.
- Focused tests, comprehensive Python tests, Python compilation, plugin tests,
  Git diff checks, planning audits, and required CI pass.

## Model and review route

A `gpt-6-astra` high worker may implement the bounded source/test surface after
the exact branch and plan checkpoint are published. The primary owns contract
reconciliation, commits, GitHub, CI, merge, and acceptance. One fresh
`gpt-5.6-luna` medium closed-world review is allowed; one repair cycle maximum.
Nested delegation and live effects are disabled.

## Next action

Merge the exact integration-ready projection, squash-merge PR #89, verify the
canonical result, then close the #82 lane and assign #83 and #84 as disjoint
parallel migrations.
