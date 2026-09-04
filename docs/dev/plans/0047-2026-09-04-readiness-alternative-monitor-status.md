# Readiness Alternative Monitor Status

Date: 2026-09-04

Status: CLOSED

## Objective

Stop reporting an inactive repo-scoped service as a warning when an active,
enrolled, healthy user supervisor already owns the same wake root.

## Current State

Released and installed in `v0.5.2`. The live repo-service check now reports
`status=not_needed`, `required=false`, and `covered_by=supervisor` while the
supervisor and monitor checks both report ready. The previous misleading
warning is gone.

## Scope

- Add a neutral `not_needed` readiness status.
- Reconcile the repo-service result only when supervisor and monitor checks are
  both ready for the selected wake root.
- Explain the alternative ownership in the human message and structured data.
- Preserve the existing warning when alternative coverage is absent or
  unhealthy.
- Add focused regression tests, update operator guidance, and validate the
  source and installed public release.

## Non-Goals

- Do not start or install the repo-scoped service.
- Do not change supervisor enrollment or wake dispatch behavior.
- Do not weaken missing-monitor or stale-health failures.
- Do not change wake-record schema version 1.
- Do not initiate a live wake delivery.

## Acceptance Criteria

- A healthy active supervisor covering the selected root changes the inactive
  repo-service result from `warning` to `not_needed`.
- The repo-service result names `supervisor` as its alternative owner.
- An inactive repo service remains `warning` if the supervisor is inactive,
  the root is not enrolled, or monitor readiness is blocked.
- Neutral `not_needed` results do not raise the overall readiness severity.
- Focused and comprehensive tests, compilation, planning audit, package smoke,
  CI, public-tag smoke, and installed readback pass.

## Definition Of Done

The corrected status is released and installed, the live workstation report
no longer shows the misleading repo-service warning, validation evidence is
recorded, the plan is closed, and the repository is clean and pushed.

## Result

- Added `not_needed` as a neutral readiness status that does not increase the
  overall severity.
- Reconciled the repo-service result only when the supervisor is active, the
  selected wake root is enrolled, and monitor readiness is true.
- Preserved the warning for absent, inactive, unenrolled, or unhealthy
  alternative coverage.
- Released and installed `v0.5.2`; source, CI, package, public-tag, skill,
  supervisor, and plugin checks passed.
- Recorded evidence in
  `docs/dev/verification/0071-2026-09-04-v052-readiness-release.md`.

The live overall product status is currently `blocked` for a separate reason:
`openclaw-gateway.service` is masked and inactive. The release did not unmask
that unrelated service. The installed OpenClaw plugin files inspect as version
`0.5.2` with zero diagnostics, but live Gateway RPC was not claimed.
