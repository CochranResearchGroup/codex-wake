# v0.5.2 Readiness Release Verification

Date: 2026-09-04

Plan: `docs/dev/plans/0047-2026-09-04-readiness-alternative-monitor-status.md`

## Scope

Verify that alternative supervisor coverage produces a neutral repo-service
result instead of a misleading warning, then publish and install `v0.5.2`.

## Behavior

`product_readiness_summary` now reconciles the repo-service result after both
monitor and supervisor checks are available. It emits `not_needed` only when:

- the repo-scoped service is inactive;
- the supervisor check is ready;
- the selected wake root is enrolled; and
- monitor readiness is true.

The structured result is:

```json
{
  "status": "not_needed",
  "required": false,
  "covered_by": "supervisor",
  "active": "inactive",
  "enabled": "disabled",
  "message": "repo-scoped service is not needed because the active user supervisor owns this wake root"
}
```

`not_needed` has neutral severity. When every other check is neutral or ready,
the overall status remains `ready`. Missing or unhealthy supervisor coverage
leaves the inactive repo-service result at `warning`.

## Test Evidence

The focused test was first run before implementation and failed because
`STATUS_NOT_NEEDED` did not exist. After implementation:

```text
Focused product-readiness module: 10 tests passed
Comprehensive Python suite: 182 tests passed
OpenClaw plugin suite: 12 tests passed
Python compilation: passed
OpenClaw entrypoint syntax: passed
Active planning audit: passed
git diff --check: passed
```

The focused run also exposed a pre-existing import-order dependency on
`unittest.mock`; importing `mock` explicitly made the module independently
runnable.

## Package Evidence

```text
codex_wake-0.5.2-py3-none-any.whl
sha256=cb5e10e6beb8e125ce198668ab8e5984aef123ca57a8a1ddfc310df0f4e6823c
codex_wake-0.5.2.tar.gz
sha256=7a2a2effaae7411212b9df0d7df6847311a2a33124423d02f5b372001553a1e9
```

Installed-wheel smoke reported CLI `0.5.2`, schema version `1`, and one
isolated supervisor root. Live delivery checks were intentionally skipped.

## Commit, CI, And Release

```text
120c39b Report supervisor-covered repo service as not needed
99079e629a83c206f91f47455cd4691d484d6b34 Prepare v0.5.2 readiness release
v0.5.2 -> 99079e629a83c206f91f47455cd4691d484d6b34
```

GitHub Actions:

```text
run_id=33866311984
url=https://github.com/CochranResearchGroup/codex-wake/actions/runs/33866311984
status=completed
conclusion=success
Python 3.11=success
Python 3.12=success
```

GitHub release:

```text
https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.5.2
publishedAt=2026-09-04T11:06:30Z
draft=false
prerelease=false
```

Public-tag smoke reported:

```text
public_tag=v0.5.2
cli_version=0.5.2
schema_version=1
supervisor_once_roots=1
tmux_status=manual_only
```

## Installed Readback

The user-scoped tool was refreshed from public tag `v0.5.2`. The user hook and
three standard skill copies were synchronized, and the user supervisor was
reinstalled and started.

Live installed readiness for this root reports:

```text
codex-wake=0.5.2
repo_service.status=not_needed
repo_service.required=false
repo_service.covered_by=supervisor
supervisor.status=ready
supervisor.current_root_enrolled=true
monitor.status=ready
monitor.monitor_ready=true
```

The OpenClaw plugin source was refreshed from public `v0.5.2`; static runtime
inspection reports version `0.5.2`, activated, tool
`codex_wake_schedule`, and zero diagnostics.

## Separate Runtime Condition

The attempt to restart `openclaw-gateway.service` failed because the unit is
masked:

```text
/home/ecochran76/.config/systemd/user/openclaw-gateway.service -> /dev/null
enabled=masked
active=inactive
```

Therefore the live overall product status is `blocked` by OpenClaw Gateway RPC,
not by the repo-scoped service. This release does not unmask the unrelated
Gateway unit and does not claim live OpenClaw delivery. The condition is kept
separate so the corrected readiness result is precise rather than falsely
green.

## Closeout

P47 is complete. The misleading warning is removed in the public and installed
product, fallback warning behavior remains protected, and the unrelated masked
Gateway state is reported without mutation.
