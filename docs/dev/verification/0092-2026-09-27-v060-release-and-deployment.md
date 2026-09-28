# v0.6.0 release and deployment verification

Date: 2026-09-27

Plan: `docs/dev/plans/0098-2026-09-27-v060-release-and-deployment.md`

Issue: `CochranResearchGroup/codex-wake#175`

## Result

PASS. Codex Wake `v0.6.0` is published from exact canonical main, installs
from the public tag, and is deployed to the user-scoped tool, installed skill
copies, OpenClaw plugin source, and active user supervisor. The repo-scoped
service retained its inactive/disabled state. No wake or provider dispatch
occurred.

## Release identity

- Release preparation PR: `#176`
- Canonical/tag commit: `d0a277bf81a48d799581ba5dbbff61af70768568`
- Tag: `v0.6.0`
- GitHub release:
  `https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.6.0`
- Published: `2026-09-28T01:21:24Z`
- Draft: `false`
- Prerelease: `false`
- GitHub latest-release API returned `v0.6.0`.

## Validation

Local release preparation passed:

- 713 Python tests;
- 12 OpenClaw plugin tests;
- Python compilation and Node entrypoint syntax;
- package build;
- isolated installed-wheel source-registry and product smokes;
- active and goal planning audits; and
- diff hygiene.

Candidate artifacts:

```text
codex_wake-0.6.0-py3-none-any.whl
sha256=c671012eac5ae109073f09f7c51e92862b8d623978cc1d0b134ddecc71b3f5b5

codex_wake-0.6.0.tar.gz
sha256=10c25783ddc44cd6dfd446cfdc17eb95528cf337633516e54b40f72cb5de752d
```

PR #176 hosted run `36365516911` passed Python 3.11 and 3.12 release gates.
Canonical main run `36365595386` also passed both release gates, including
unit, plugin, package-build, and installed-wheel smoke steps.

The public-tag product smoke installed `v0.6.0` into a disposable environment
and reported:

```text
cli_version=0.6.0
schema_version=1
github_fixture_lifecycle.status=matched
runtime_fixture_lifecycle.status=matched
signal_lifecycle.dispatch_attempted=false
supervisor_once_roots=1
tmux.status=manual_only
```

Live app-server, OpenClaw Gateway, and tmux dispatch smokes were intentionally
not run because this deployment did not authorize a wake dispatch.

## Installed identity

The user tool was installed from the public tag:

```text
requested_revision=v0.6.0
commit_id=d0a277bf81a48d799581ba5dbbff61af70768568
codex-wake=0.6.0
```

The installed `codex_wake/__init__.py` SHA-256 matches the tagged source:

```text
55baef1cdb9d248cab12abc3b6c29852fe600b18e0ee5c6c419f69dcb5b5cba4
```

The user hook check reports installed/valid with command `codex-wake-hook`.
All three installed skill copies match the tagged skill SHA-256:

```text
3249a222506ab0e1d5d632dbb29e8997893dae25c207e42f30b0d34daaef6715
```

The materialized and installed OpenClaw plugin package files match the tagged
SHA-256:

```text
3c82e97684c9ed26899bb27a4be88034bfcb483c7138af455201ba12a9d2601f
```

OpenClaw runtime inspection reports plugin `codex-wake` version `0.6.0`,
activated/loaded, with zero diagnostics. Its source is the materialized public
tag path under `~/.local/share/codex-wake/openclaw-plugins/v0.6.0`.

## Service readback

The already-active supervisor was explicitly restarted after tool installation
so it could not retain the old loaded Python process:

```text
before_pid=14250
after_pid=68539
active=active
enabled=enabled
root_count=4
all_roots_health_status=ready
all_roots_health_recent=true
```

The canonical repo-scoped service retained its pre-deployment state:

```text
unit=codex-wake-codex-wake.service
load=loaded
active=inactive
substate=dead
enabled=disabled
pid=0
readiness.status=not_needed
readiness.covered_by=supervisor
```

Canonical-root product readback reports CLI, monitor, supervisor, repo-service,
and plugin checks ready or neutral. Active and firing wake counts are zero.

## Residual boundary

Overall product readiness remains `blocked` only because the unrelated
OpenClaw Gateway is stopped. This deployment did not start or unmask it. No
live wake creation, target dispatch, GitHub webhook/provider mutation,
enrolled-root change, unrelated plugin upgrade, or unrelated service mutation
occurred.

## Closeout

Plan 0098 and P60 are complete. Issue #175 may close after this receipt and
the lane removal integrate through the protected-main pull-request workflow.
