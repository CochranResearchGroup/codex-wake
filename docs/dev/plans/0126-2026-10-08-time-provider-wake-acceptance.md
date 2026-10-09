# Plan 0126 — Prove wake behavior across outages sleep and restart

State: PLANNED
Workflow: BLOCKED
Owner: primary agent lane
Branch: feature/network-time-consensus
Parent: docs/dev/plans/0122-2026-10-08-network-first-time-provider.md
Blocked by: docs/dev/plans/0124-2026-10-08-healthy-windows-time-fallback.md, docs/dev/plans/0125-2026-10-08-mailbox-time-uncertainty-recovery.md

## Current State

Approved breakdown published as a repo-native ticket. Implementation has not started. Wait for the named blockers to complete acceptance before implementation.

## What to Build

An isolated installed candidate creates and persists a wake request, evaluates its unchanged deadline, exposes the resume payload and resolves cancellation or due status through provider outages and restart.

## Required Inputs

Plan0122, its committed decision core and tests, and the primary-source production qualification note under `docs/dev/evidence/plan0122/production-requirements.md`. Read current repo policy and applicable TDD/code-review skills before implementation.

## Acceptance Criteria

- [ ] Verify an isolated candidate entrypoint with disposable wake/mailbox state; record exact source/installed identity and command evidence.
- [ ] Demonstrate request creation, cross-process persistence, deterministic pending/uncertain/due transitions, inspectable resume payload and cancellation.
- [ ] Cover network loss, automatic recovery, Windows health loss, tied groups, suspend-length time advance and host/guest restart without early firing or deadline rewriting.
- [ ] Keep injected resume/boot controls distinct from actual suspend/reboot proof. If an actual sleep/restart is necessary, prepare a concrete acceptance procedure and obtain separate host-action authority.
- [ ] Reconcile tickets 0124 and 0125 at the integration seam and record standards/spec review, failed controls and remaining limits.
- [ ] Prepare release and migration/rollback instructions without performing a live rollout; close only when the isolated acceptance evidence supports the claimed behavior.

## Expected Write Surface

Wake integration, disposable installed-candidate harness, acceptance fixtures, review and release/migration documentation.

## Validation and Definition of Done

Record meaningful failing controls before behavior fixes, focused passing tests, entrypoint readback and standards/spec review. Commit the bounded slice with acceptance evidence, reconcile dependency status, and close only when every criterion is supported. Documentation publication alone is not implementation completion.

## Non-goals

No production installation, live mailbox migration, real session dispatch, reboot or suspend without its own explicit authorization.
