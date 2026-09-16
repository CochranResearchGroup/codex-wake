# GitHub source health projection correction

State: OPEN
Lane: P53-C4-v4
Issue: #107
Predecessor: Plan 0076 (`BLOCKED_BY_PRODUCT_HEALTH_PROJECTION`)
Branch: `chore/issue-107-installed-webhook-canary`
Target: `main`
Integration: `squash`

## Current state

Plan 0076 fixed the source-only poll fixture's missing publisher. Independent
execution of the generated fixture now proves exact pending-to-firing
projection with one retained receipt, one new match, one fired wake, zero
dispatch, and zero production-provider calls. Strict qualification still fails
because `GitHubSignalRunner.reconcile()` constructs
`SourceInstanceReconcileResult` without the health code and observation time it
has just persisted, producing `code=""` and `observed_at=null`.

The original Plan 0075 installed receipt/root remain unchanged. Its service,
restart, and delivery evidence remains a separate valid axis; its failed
polling and immediate `TIME-WAIT` cleanup result remain explicit. No new
service, provider, dispatch, ingress, or retained-evidence effect occurred in
Plan 0076.

## Objective

Project GitHub per-instance source health code and observation time through the
daemon result, then prove the complete strict provider-free convergence path
and finish #107 without another installed-service effect.

## Scope

- Test-drive `GitHubSignalRunner` propagation of the exact `Degraded` health
  code and aware observation timestamp into `SourceInstanceReconcileResult`.
- Add an executable generated-fixture test with production-provider and
  dispatch tripwires; string inspection alone is insufficient.
- Preserve the accepted Plan 0076 publisher wiring and every retained Plan
  0075 evidence boundary.
- Publish one sanitized composite verification artifact and complete the
  issue-linked pull request after required CI.

## Non-goals and effect boundary

- No service install/start/restart, listener, provider request, external
  ingress, wake dispatch, global install, release, deployment, Cooper change,
  or mutation of the retained Plan 0075 receipt/root.
- No changes to GitHub polling authorization, coverage semantics, matching,
  deduplication, source health persistence, or dispatch behavior.
- No relaxation of the strict `GITHUB_COVERAGE_UNPROVEN` qualification check.

## Execution sequence

1. Add a failing focused product test for GitHub health code/time projection.
2. Implement only the per-instance projection and run focused daemon/source and
   installed-runner tests.
3. Add or adapt an executable generated-fixture test that proves strict
   convergence with provider and dispatch tripwires.
4. Run comprehensive Python, plugin, compilation, diff, and planning tiers;
   obtain one closed-world verification of P76-R01 and critical regressions.
5. Publish the clean candidate, sanitized composite verification, linked PR,
   and merge only after both required CI release gates pass.

## Acceptance criteria

- GitHub source results carry the exact persisted health code and aware
  observation timestamp for each reconciled instance.
- The generated provider-free fixture passes strict convergence: receipts
  `1 -> 1`, matches `0 -> 1`, pending `1 -> 0`, firing `0 -> 1`, fired `1`,
  dispatched `0`.
- Production GitHub client and dispatch tripwires remain zero.
- Full validation and both CI release gates pass, while retained failure and
  service evidence remain unchanged and separately characterized.

## Stop conditions

Stop on any provider/dispatch/service action, retained-evidence mutation,
changed polling or matching semantics, non-aware timestamp, health mismatch,
dirty/unpublished candidate, or failed critical regression. No installed
service retry is permitted.

## Definition of done

The product health projection and strict installed-fixture proof pass; the
composite verification satisfies #107; its PR merges through required CI;
canonical main, issue closure, branch/worktree cleanup, and lane custody are
reconciled; and #108 becomes ingress-eligible.
