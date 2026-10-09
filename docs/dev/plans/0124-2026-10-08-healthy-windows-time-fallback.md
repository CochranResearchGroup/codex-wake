# Plan 0124 — Use healthy Windows fallback during network outages

State: CLOSED
Workflow: DONE
Owner: primary agent lane
Branch: feature/network-time-consensus
Parent: docs/dev/plans/0122-2026-10-08-network-first-time-provider.md
Blocked by: docs/dev/plans/0123-2026-10-08-network-time-inspection.md

## Current State

Implemented synchronization-health-qualified Windows fallback through the inspection interface. Controlled evidence proves healthy fallback and conflict exclusion; the actual installed candidate excludes this host's stopped synchronization service while accepting network consensus.

## What to Build

The inspection path uses bounded healthy Windows UTC only when network consensus is absent and remaining usable evidence agrees.

## Required Inputs

Plan0122, its committed decision core and tests, and the primary-source production qualification note under `docs/dev/evidence/plan0122/production-requirements.md`. Read current repo policy and applicable TDD/code-review skills before implementation.

## Acceptance Criteria

- [x] Demonstrate healthy fallback and exclusion of unsynchronized, stale, unbounded or unavailable Windows observations through the inspection entrypoint.
- [x] Define and validate synchronization-health and UTC-uncertainty evidence; service-running status alone does not establish health.
- [x] Keep host elapsed-time authority separate from UTC health, including boot identity and restart invalidation.
- [x] Network consensus overrides an outlying Windows reading. Competing network groups cannot be resolved by Windows.
- [x] Cover network outage, surviving conflicting observations, stopped synchronization service, interop timeout and recovery with deterministic tests and a read-only candidate demonstration.

## Expected Write Surface

Windows acquisition/health adapter, shared inspection diagnostics, fixtures and qualification evidence.

## Validation and Definition of Done

Record meaningful failing controls before behavior fixes, focused passing tests, entrypoint readback and standards/spec review. Commit the bounded slice with acceptance evidence, reconcile dependency status, and close only when every criterion is supported. Documentation publication alone is not implementation completion.

## Non-goals

No synchronization-service startup, clock adjustment, mailbox activation or global host configuration changes.

## Acceptance Evidence

See `docs/dev/evidence/plan0124/qualification.md`. Focused time tests: 23 pass; existing CLI tests: 66 pass. Wheel built with `uv build`, installed only in `/tmp/codex-wake-time-candidate`, and its real `codex-wake time inspect` command returned network consensus. Initial plain pip wheel attempt failed for missing build backend; isolated uv build succeeded, with no production package changes. Whitespace and staged review are required before commit.
