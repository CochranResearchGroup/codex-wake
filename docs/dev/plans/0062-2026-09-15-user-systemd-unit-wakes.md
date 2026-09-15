# User-systemd unit transition wakes

State: OPEN
Lane: P51-C3
Issue: #61
Branch: `feat/issue-61-systemd-unit-wakes`
Target: `main`
Integration: `squash`

## Current state

The shared runtime-source contract is accepted on canonical main
`2760402a2dc9818f43d9567c67c64ad51fb745d6`. No systemd observer or authority
exists. This lane adds a fixed read-only current-user-manager boundary and an
exact configured unit/state adapter.

## Objective

Allow one exact preconfigured canonical user-unit name to wake when its
observed `ActiveState` enters one allowed target state, without acquiring any
unit-control, system-manager, arbitrary D-Bus, wildcard, or command authority.

## Parallel ownership and reconciliation

The systemd worker owns its adapter/config modules and focused tests. The
process worker owns separate modules. Both issues require shared CLI and daemon
files; the primary alone edits those surfaces, serially, after both adapter
contracts are reviewed. Neither worker may edit shared CLI/daemon surfaces.

## Scope and write surface

- `src/codex_wake/systemd_source_config.py`
- `src/codex_wake/systemd_signals.py`
- `tests/test_systemd_source_config.py`
- `tests/test_systemd_signals.py`
- Primary-only serialized integration: `src/codex_wake/cli.py`,
  `src/codex_wake/daemon.py`, and corresponding existing CLI/daemon tests

Any other change stops for primary reconciliation.

## Safety contract

- Configuration is operator-owned, versioned, bounded, nonsecret, and
  allowlists exact canonical user-unit names plus `active`, `inactive`, or
  `failed` targets.
- Alias resolution happens before authorization and cannot widen the configured
  canonical identity.
- The backend is injected, current-user-manager-only, read-only, time-bounded,
  and returns fixed `ActiveState` plus safe identity/generation metadata.
- Missing units are unavailable, not inactive. Already matching baselines do
  not fire. Reconnect, boot change, and observation gaps reconcile
  conservatively; wholly unseen enter-and-leave cycles are never claimed.
- No product path can start, stop, restart, reload, enable, disable, mask,
  create transient units, select the system manager, or invoke arbitrary bus
  names, paths, interfaces, methods, properties, or commands.

## Acceptance criteria

- Exact configuration, alias authorization, nonmatching baseline, transition,
  repeated state, missing unit, backend timeout/unavailability, reconnect,
  boot change, gap ambiguity, cancellation, expiration, deduplication, restart,
  and crash-boundary fixtures pass.
- A supported CLI recipe and fresh daemon reconstruction use the same durable
  descriptor, anchor, checkpoint, authorization guard, and occurrence identity.
- Diagnostics disclose only safe unit identity and bounded state/health facts.
- Focused, comprehensive, plugin, compilation, planning, lane, and Python
  3.11/3.12 CI gates pass without retry.

## Non-goals

No live systemd operation, system-manager access, mutation method, arbitrary
D-Bus access, shell command, public ingress, installed canary, dispatch,
release, deployment, provider call, or global runtime change.

## Next action

Implement and review the fake-boundary adapter/config test-first, then let the
primary serialize shared CLI/daemon integration before publishing the issue PR.
