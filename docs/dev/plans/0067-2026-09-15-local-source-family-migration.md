# Local source-family registry migration

State: OPEN
Lane: P52-C2
Issue: #83
Branch: `feat/issue-83-local-source-family-migration`
Target: `main`
Integration: `squash`

## Objective

Move filesystem, process-exit, and user-systemd reconstruction into registered
built-in family factories without changing batching, ordering, authorization,
anchors, recovery, health, or malformed-record behavior. Correct only the
accepted unloaded-unit diagnostic.

## Scope and write surface

- `src/codex_wake/local_source_families.py` for the three registered factories.
- `src/codex_wake/daemon.py` for primary-owned removal of the migrated local
  branches and catalogue composition.
- Focused local-family and daemon parity tests; existing source-specific tests
  may receive narrow regression cases.
- Lane documentation and active-lane projection.

The implementation worker owns the new local-family module and focused tests.
The primary owns all `daemon.py` reconciliation so the parallel GitHub lane
cannot conflict on shared orchestration.

## Invariants

- Filesystem remains one batched runner in durable pending order.
- Process remains one runner per sorted source instance and retains exact
  descriptor/anchor validation plus `RUNTIME_ANCHOR_INVALID` fallback.
- User-systemd retains configured-instance sorting, one batched runner, live
  configuration authorization, backend injection, and
  `SYSTEMD_SOURCE_UNSUPPORTED` fallback.
- Missing or unloaded units are reported unavailable, not inactive; no unit
  selection or control authority changes.
- Local family factories construct only; they do not observe, reconcile,
  dispatch, write configuration, or mutate runtime state.

## Acceptance

- The three local `(source, kind)` pairs are registered once with no daemon
  source-selection branches remaining.
- Existing direct daemon tests and new parity fixtures prove identical runner
  types/order, candidate grouping, injected dependencies, and failure results.
- Focused, comprehensive, plugin, compilation, planning, and required CI gates
  pass with one independent review.

## Non-goals

No GitHub migration, new source, live filesystem/process/systemd observation,
unit control, dispatch, installation, provider effect, release, or deployment.

## Next action

Publish the exact lane checkpoint, implement the local factories in the
isolated worktree, then let the primary serialize daemon integration and review.
