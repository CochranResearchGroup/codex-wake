# GitHub source-family registry migration

State: OPEN
Lane: P52-C3
Issue: #84
Branch: `feat/issue-84-github-source-family-migration`
Target: `main`
Integration: `squash`

## Current state

PR #95 is integration-ready at
`1be2a395bab644a02c5f4f1f1e868c5bd065f2f7`. The GitHub family factory and
primary-owned daemon integration preserve configured-instance grouping,
legacy arm order, retry state, health, failure isolation, and injected provider
clients. Focused, comprehensive, plugin, compilation, installed-wheel CI, and
independent review gates pass with no provider or live effect.

## Objective

Move GitHub CI reconstruction into one registered built-in family factory while
preserving fixed-origin, read-only, bounded, positive-only, retry, health,
coverage, and recovery semantics.

## Scope and write surface

- `src/codex_wake/github_source_family.py` for the registered factory.
- Provider-free focused family tests and narrow GitHub parity tests.
- `src/codex_wake/daemon.py` only under the primary after #83 integration has
  established final shared catalogue composition.
- Lane documentation and active-lane projection.

The implementation worker must not edit `daemon.py`; the primary owns that
overlap after the local lane is accepted.

## Invariants

- Group candidates by configured source instance and preserve sorted instance
  construction plus durable arm order.
- Retain exact configuration selection, disabled/unsupported rejection,
  injected client factory, retry failure restoration, health store, and silent
  skip behavior for the currently caught construction failures.
- Registry/catalogue inspection never constructs a client or calls GitHub.
- `GITHUB_COVERAGE_UNPROVEN` and all existing evidence limits remain unchanged.

## Acceptance

- The GitHub `(source, kind)` pair is registered once and the final primary
  integration removes its daemon selection branch.
- Provider-free tests prove grouping, client injection, retry restoration,
  configuration damage, failure isolation, and zero construction-time network
  calls.
- Focused, comprehensive, plugin, compilation, planning, and required CI gates
  pass with one independent review.

## Non-goals

No webhook, live GitHub read, GitHub mutation, credential change, new source,
dispatch, installation, release, or deployment.

## Next action

Merge the exact integration-ready projection, squash-merge PR #95, verify
canonical main, then remove the accepted topic branch and worktree before #85.
