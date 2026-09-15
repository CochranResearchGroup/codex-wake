# Restart-correct process-exit wakes

State: CLOSED
Lane: P51-C2
Issue: #60
Branch: `feat/issue-60-process-exit-wakes`
Target: `main`
Integration: `squash`

## Current state

The accepted implementation was squash-merged through PR #71 at canonical
main commit `54311f35f9e3b6dd0c21be3d0beaa2eb443616a3`, closing issue #60. The
supported `process-exit` recipe registers a schema-v2 arm, and a fresh daemon
reconstructs the exact descriptor and routes evaluation through the
source-owned authorization guard. Legacy `process_done` remains unchanged.

## Objective

Register one currently observable same-effective-UID Linux process by exact
`(boot_id, pid, start_time_ticks, owner_uid)` identity, establish an alive
baseline, and emit once only when that identity is positively terminated.

## Parallel ownership and reconciliation

The process worker owns `process_signals.py` and its focused tests. The systemd
worker owns separate modules. Both issues require shared CLI and daemon files;
the primary alone edits those surfaces, serially, after both adapter contracts
are reviewed. Neither worker may edit shared CLI/daemon/configuration surfaces.

## Scope and write surface

- `src/codex_wake/process_signals.py`
- `tests/test_process_signals.py`
- Primary-only serialized integration: `src/codex_wake/cli.py`,
  `src/codex_wake/daemon.py`, and corresponding existing CLI/daemon tests

Any other change stops for primary reconciliation.

## Safety contract

- Registration reads only fixed identity/status fields under `/proc`; it never
  reads command lines, environments, file descriptors, memory, or arbitrary
  process data.
- Only exact same-effective-UID identities may arm. Missing, already terminal,
  foreign, replaced, unidentifiable, or ambiguous targets fail closed.
- Alive-to-zombie is positive termination. Exact-identity disappearance after
  a verified alive baseline may terminate only under a documented positive
  classification; permission or backend uncertainty degrades.
- PID reuse cannot attach. Boot change invalidates. No exit code or exact exit
  time is claimed; observation time remains observation time.
- Each product-owned observer call is locally bounded and hermetic tests use
  injected snapshots without sleeps or live process mutation.

## Acceptance criteria

- Exact registration and nonmatching baseline rules pass hostile fixtures.
- Alive, zombie, disappearance, PID reuse, boot change, owner mismatch,
  permission failure, cancellation, expiration, deduplication, restart, and
  journal crash boundaries are covered.
- A supported CLI recipe and fresh daemon reconstruction use the same durable
  descriptor, anchor, checkpoint, authorization guard, and occurrence identity.
- Legacy `process_done` tests and behavior remain unchanged.
- Focused, comprehensive, plugin, compilation, planning, lane, and Python
  3.11/3.12 CI gates pass without retry.

## Non-goals

No signaling, killing, tracing, ptrace, namespace entry, process discovery,
foreign-user access, exit-code promise, installed canary, dispatch, release,
deployment, provider call, or global runtime change.

## Validation evidence

- Focused process, CLI, and daemon tier: 100 tests passed.
- Comprehensive Python tier: 383 tests passed.
- OpenClaw plugin tier: 12 tests passed.
- Compilation and diff checks passed.
- Independent adversarial review passed after one bounded correction for
  explicit process-state validation and capped fixed-field reads.

## Next action

Continue P51 through the separately governed systemd integration and shared
product-readiness slice; no process-lane work remains.
