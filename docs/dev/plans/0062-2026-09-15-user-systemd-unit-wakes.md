# User-systemd unit transition wakes

State: CLOSED
Lane: P51-C3
Issue: #61
Branch: `feat/issue-61-systemd-unit-wakes`
Target: `main`
Integration: `squash`

## Current state

The pure adapter/config and shared product integration were squash-merged
through PR #73 at canonical main commit
`f41ef0ba6d5b37ab85bea7a1cebbc9bd6b0ad748`, closing issue #61. The supported
`systemd-unit` configuration and `becomes` recipe use one exact current-user
unit allowlist. A fresh daemon reconstructs that source through a fixed
read-only session-bus call plan and rechecks durable configuration authority
before observation, evaluation, and publication.

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
  `src/codex_wake/daemon.py`, `pyproject.toml`, and corresponding existing
  CLI/daemon tests

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

## Validation evidence

- Focused systemd, configuration, CLI, and daemon tier: 115 tests passed.
- Comprehensive Python tier: 411 tests passed.
- OpenClaw plugin tier: 12 tests passed.
- Compilation and diff checks passed.
- A built wheel installed its bounded `dbus-next` dependency and imported the
  production backend successfully in a clean virtual environment.
- Independent adversarial review passed after bounded corrections for reply
  shape validation and pre-observation exact-anchor validation.

## Integration receipt

PR #73's initial Python 3.11/3.12 run failed because one hermetic fixture
hard-coded UID 1000 while the hosted runner used another effective UID. The
production same-user denial was correct. The fixture now patches the effective
UID deterministically; the comprehensive 411-test local tier remained green,
and both CI versions passed on the first authorized retry. The PR was
squash-merged and canonical-main ancestry was read back at the commit above.

## Next action

Continue through productization join #62. No systemd-adapter work remains.
