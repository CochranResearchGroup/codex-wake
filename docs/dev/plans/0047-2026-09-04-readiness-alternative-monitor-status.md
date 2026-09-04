# Readiness Alternative Monitor Status

Date: 2026-09-04

Status: OPEN

## Objective

Stop reporting an inactive repo-scoped service as a warning when an active,
enrolled, healthy user supervisor already owns the same wake root.

## Current State

`product-readiness` evaluates the repo service before the supervisor and emits
`warning` whenever the repo service is inactive. The final aggregation does not
reconcile that warning with the later evidence that the supervisor is active,
the root is enrolled, and monitor health is ready. This creates an actionable-
looking warning for an intentionally redundant service.

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
