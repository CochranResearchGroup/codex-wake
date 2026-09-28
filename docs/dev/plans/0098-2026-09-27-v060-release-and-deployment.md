# v0.6.0 release and deployment

State: OPEN
Lane: P60
Issue: #175
Branch: `chore/issue-175-v060-release`
Target: `main`
Integration: `squash`

## Current state

Canonical `origin/main` is `e90b587`, with issue #172 integrated and its
Python 3.11/3.12 main gates passing. Public and user-installed package metadata
remain `0.5.2`. Release preparation now reports `0.6.0` and passes 713 Python
tests, 12 OpenClaw plugin tests, compilation, package build, installed-wheel
source-registry/product smokes, diff hygiene, and active/goal planning audits.
Candidate artifact SHA-256 is
`c671012eac5ae109073f09f7c51e92862b8d623978cc1d0b134ddecc71b3f5b5`
for the wheel and
`10c25783ddc44cd6dfd446cfdc17eb95528cf337633516e54b40f72cb5de752d`
for the source archive. The user supervisor is active/enabled with four ready
enrolled roots, including this repository; the legacy repo-scoped service is
inactive/disabled and covered by the supervisor. OpenClaw Gateway is stopped
and outside this deployment.

## Objective

Publish exact canonical functionality as `v0.6.0`, install it from the public
tag, synchronize the installed skills and OpenClaw plugin source, and reconcile
the user services without changing their intended ownership state.

## Scope

- Bump Python and OpenClaw plugin package identities to `0.6.0`.
- Publish release notes covering the integrated post-`v0.5.2` capabilities.
- Pass focused version checks, comprehensive Python/plugin tests, build,
  installed-wheel smoke, planning audits, and hosted Python 3.11/3.12 gates.
- Merge the release preparation through an issue-linked pull request, then tag
  and publish that exact canonical commit.
- Prove a clean public-tag install, refresh the user-scoped tool, user hook,
  installed skill copies, OpenClaw plugin source, and active supervisor.
- Preserve the repo-scoped service as inactive/disabled and record fresh
  version, PID, readiness, hash, release, and service readback.

## Non-goals

- No live wake creation or dispatch.
- No GitHub workflow rerun, webhook mutation, or provider delivery.
- No OpenClaw Gateway start, unmask, or unrelated plugin upgrade.
- No change to enrolled wake roots or unrelated systemd services.

## Execution packets

1. Prepare and validate the release commit on a clean branch from canonical
   main; publish and merge the issue-linked PR after hosted gates pass.
2. Tag and publish the exact merged commit, then run the public-tag product
   smoke without mutating the user installation.
3. Capture rollback identity, install from the public tag, synchronize product
   assets, restart only the already-active supervisor, and verify all roots.
4. Publish the deployment receipt, close the plan/lane/roadmap, and close issue
   #175 after the closeout PR and canonical main gates pass.

## Acceptance criteria

- `v0.6.0` resolves to an exact commit on canonical `origin/main` and the
  GitHub release is public, non-draft, and non-prerelease.
- Source, artifacts, public tag, and installed CLI/plugin identities report
  `0.6.0`; hashes and install provenance are recorded.
- Local comprehensive and hosted Python 3.11/3.12 release gates pass.
- Public-tag product smoke completes without provider or dispatch effects.
- The user supervisor is active/enabled on the installed release with all four
  existing roots ready; the repo-scoped service remains inactive/disabled.
- Installed skill copies match the tracked release and the OpenClaw plugin
  reports the release identity without starting its stopped Gateway.
- A durable receipt records exact release, install, service, and residual
  readiness evidence.

## Goal controls

```text
goal_id: P60-G1
goal_version: P60-G1-v1
max_work_unit_attempts: 2
max_review_rework_cycles: 1
max_hardening_checkpoints: 2
max_review_discovery_passes: 1
checkpoint_interval: 1 execution packet or material gate
concurrency_limit: 1 primary lane
release_attempts: 1
install_attempts: 1 candidate plus 1 rollback on failed postcondition
live_dispatch_attempts: 0
provider_mutations: 0
authorization_gate: material_departure_or_explicit_action_gate_only
review_verification_mode: closed_world_if_reviewed
checkpoint_fields: state_transition, acceptance_state, progress_classification, evidence, material_blockers, next_action_or_stop_reason
```

## Next action

Validate the release preparation, publish its issue-linked pull request, and
wait for both hosted release gates before integration.
