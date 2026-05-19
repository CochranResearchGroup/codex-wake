# PID Reuse Safety

State: CLOSED
Lane: P19

## Scope

Harden `process_done` predicates against PID reuse when the platform exposes a stable process identity.

## Non-Goals

- Do not add shell-command predicates.
- Do not add process supervision or child process ownership.
- Do not require Linux-only behavior for basic `pid` wakes.
- Do not change the `codex-wake pid <pid> -- <prompt>` user-facing command shape.

## Current State

P17 introduced `process_done` as a liveness predicate. It fires when `os.kill(pid, 0)` reports that the PID no longer exists. That leaves a correctness gap when the original process exits and the operating system later reuses the same PID before the daemon polls.

Closed by [PID Reuse Safety](../verification/0016-2026-05-19-pid-reuse-safety.md).

## Design

At registration, `codex-wake pid` should record the best available process identity:

- `registered_start_time_ticks` from `/proc/<pid>/stat` field 22 on Linux.
- `registered_boot_id` from `/proc/sys/kernel/random/boot_id` when available.

At evaluation, the daemon should fire when:

- the PID no longer exists, or
- a registered boot id is present and the current boot id differs, or
- a registered start time is present and the live PID has a different start time.

If identity data is not available, the predicate should remain backward-compatible and fall back to PID liveness.

## Acceptance Criteria

- `codex-wake pid <pid> -- <prompt>` records process identity when available.
- Existing wake records that contain only `pid` still evaluate with liveness fallback.
- The daemon keeps a matching process pending.
- The daemon fires when a live PID no longer matches the registered identity.
- README documents the stronger Linux behavior and fallback limit.
- Validation evidence is recorded.

## Definition Of Done

This lane can close when source tests cover registration, liveness fallback, matching identity, mismatched identity, and invalid predicates, and a CLI smoke verifies the installed command creates the identity-enhanced predicate on this host when `/proc` supports it.
