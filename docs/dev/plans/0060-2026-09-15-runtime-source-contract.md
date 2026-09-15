# Runtime source contract and tracer

State: OPEN
Lane: P51-C1
Issue: #59
Branch: `feat/issue-59-runtime-source-contract`
Target: `main`
Integration: `squash`

## Current state

Issue #59 is the sole ready P51 critical-path slice. The branch starts from
canonical P51 goal-start commit
`0a86c1ffa79e5d1b3c5ef3338f7695881a74ce99`. Existing signal adapters own
source validation and anchors, runners own reconciliation, and the journal and
record publisher own durable occurrence and wake publication state. This slice
freezes the shared local-runtime contract before either process or systemd
implementation begins.

## Objective

Define a closed, versioned runtime-source descriptor and source-specific
authorization seam, then prove its lifecycle with a provider-free tracer. The
contract must fail closed on unknown kinds, widened resources, authorization
revocation, observation ambiguity, and resource-limit exhaustion while reusing
the existing signal journal and runner lifecycle.

## Scope

- A closed source-kind registry with explicit capability metadata.
- Exact descriptor validation and source-specific authorization hooks.
- Bounded tracer observations for registration, baseline, transition,
  repeated reconciliation, restart reconstruction, revocation, cancellation,
  timeout, degradation, and resource ceilings.
- Stable sanitized diagnostic fields and occurrence inputs sufficient for the
  later process and user-systemd adapters.
- Provider-free unit and crash-boundary tests.

## Non-goals

- No process observer or process-exit recipe.
- No systemd or D-Bus observer or user-unit recipe.
- No live process or unit inspection, dispatch, installation, provider call,
  public ingress, release, deployment, or global runtime change.
- No new scheduler, dispatch path, arbitrary command, wildcard selector, or
  source-selected executable behavior.

## Write surface

- `src/codex_wake/signals/base.py`
- `src/codex_wake/signals/runner.py`
- `src/codex_wake/signals/registry.py`
- `src/codex_wake/signals/tracer.py`
- `tests/test_signal_source_contract.py`
- `tests/test_signal_source_tracer.py`

Any required write outside this surface stops the worker for primary-owner
reconciliation before editing.

## Acceptance criteria

- Unknown source kinds and fields are rejected deterministically.
- Requests cannot widen the exact resources authorized in operator-owned
  configuration.
- Revocation prevents new observation and publication without inventing a
  match or discarding journal history.
- Repeated reconciliation, restart reconstruction, and journal crash points
  preserve one stable logical occurrence and cannot duplicate publication.
- Observation and diagnostic payloads are bounded, sanitized, and exclude
  prompts, pane text, process command/environment data, and raw backend data.
- Resource ceilings fail closed and remain inspectable.
- Legacy filesystem, GitHub CI, and `process_done` behavior remains unchanged.
- Focused tests, the comprehensive Python tier, Python 3.11 and 3.12 CI, and
  active planning/goal/lane audits pass.

## Next action

Implement the registry and tracer test-first inside the registered worktree,
publish a coherent checkpoint, obtain one fresh closed-world review, and merge
only after required CI and issue acceptance pass.
