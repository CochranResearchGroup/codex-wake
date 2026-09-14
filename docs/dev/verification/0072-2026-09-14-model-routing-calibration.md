# Model-Routing Calibration Verification

Date: 2026-09-14

Plan: [`docs/dev/plans/0056-2026-09-14-model-routing-calibration.md`](../plans/0056-2026-09-14-model-routing-calibration.md)

Issue: [#10](https://github.com/CochranResearchGroup/codex-wake/issues/10)

## Frozen comparison

This is the Plan 0049/0056 closeout of the predeclared window. The six-unit
ceiling and two-per-family bound were not widened. Families are adapter
implementation, fixture construction, and fresh independent verification.
The quality floor was accepted issue criteria, Python 3.11 and 3.12 suites,
plugin tests, no unresolved blocking finding, and no gated live effect.

Requested routes and topology were the routes recorded by Plans 0052--0054:
the implementation route named by each plan, `gpt-5.6-luna` medium for
verification/evidence work, one exclusive writer with primary reconciliation,
and no nested delegation. Effective runtime model and measured allocation
counters were not exposed, so both are `unknown` in every sample. Summed worker
effort is also `unknown`. Allocation below is therefore `unknown`, not a
savings claim. The only deterministic work-size proxy is durable output: the
#6 feature commit changed 1,090 lines, the #7 feature commit changed 1,023
lines, and the fresh-review proxy is one bounded pass plus its finding count.
Those proxies are shared within each lane/family pair and are not token,
compute, effort, cost, or quality measurements.

## Sample ledger

| ID / family | Workload identity; frozen criteria and topology | Requested / effective model+effort | Accepted outcome; defects and primary interventions | Git elapsed wall-clock proxy; allocation; cumulative repair/reconciliation |
|---|---|---|---|---|
| S1 adapter implementation | Issue #6 `FilesystemSignalAdapter` and runner; provider-free registration, restart, reconciliation, and no-dispatch acceptance; exclusive issue lane plus primary review | `gpt-5.6-sol` / high (Plan 0053); effective `unknown` | Initially accepted through PR #25. Fresh review found grouping/one-checkpoint duplication; primary reconciliation separately found request-boundary subclass trust. The later campaign drift pass then found P48-DRIFT-01, a per-arm baseline defect, so final integrated acceptance is pending its #9 repair. | `034c285` (13:12:14) -> accepted merge `4169d7e` (13:35:14), 23m00s proxy; feature checkpoint `df5130b`. Overlaps S2/other lanes; not model time. Allocation and summed effort `unknown`; shared output proxy 1,090 changed lines. Repairs/reconciliation included; drift repair cost remains cumulative when known. |
| S2 fixture construction | Issue #6 provider-free watcher-loss, overflow, rename, delete/recreate, coalesced-write, path-escape, restart, and bounded-evidence fixtures; same topology | `gpt-5.6-sol` / high (Plan 0053); effective `unknown` | Initially accepted with 126 focused, then 272 comprehensive tests per runtime before review; final focused 64 and comprehensive 289 per runtime, plugin 12. The fixtures missed the staggered-arm `created` and repeated-registration `exists` cases in P48-DRIFT-01, which is now a quality-floor failure pending #9 repair. | Same accepted endpoints as S1, 23m00s overlapping proxy. Allocation and summed effort `unknown`; shares the 1,090-line lane output proxy and cannot be partitioned. Cumulative costs include fixture REDs, repair, rebase, validation, and pending drift repair. |
| S3 adapter implementation | Issue #7 `GitHubPollingAdapter`; exact allowlist, post-anchor verified attempt, bounded cursor, retries/gaps/restart; exclusive issue lane plus primary reconciliation | `gpt-6-astra` / high (Plan 0052); effective `unknown` | Accepted provider-free adapter. TDD exposed config bypass, malformed evidence, checkpoint and retry-restoration gaps; primary/worker repairs closed them. Shared-seam follow-up added ordering and read-only checkpoint behavior; aggregate ownership remained primary. | `3940de5` (12:46:16) -> accepted merge `15a3620` (13:09:36), 23m20s proxy; feature checkpoint `18c880c`. Overlaps S4/shared work; not causal model duration. Allocation and summed effort `unknown`; shared output proxy 1,023 changed lines. Repairs/reconciliation retained. |
| S4 fixture construction | Issue #7 success/failure/cancellation/timeout, duplicate/stale, auth/rate-limit, verification-failure, pagination, and restart fixtures; same topology | `gpt-6-astra` / high (Plan 0052); effective `unknown` | Accepted. Focused 13 and comprehensive 252 per runtime passed; shared-seam affected selection 157 passed. Fixtures caught the listed contract failures before repair; no provider read or test retry. | Same accepted endpoints as S3, 23m20s overlapping proxy. Allocation and summed effort `unknown`; shares the 1,023-line lane output proxy and cannot be partitioned. Includes failed tests, repairs, shared-seam follow-up, and primary validation. |
| S5 fresh independent verification | Fresh read-only review of issue #6 against frozen acceptance and no-live-effect boundary; reviewer does not own disposition | `gpt-5.6-luna` / medium (Plan 0053); effective `unknown` | Accepted after primary adjudication. The review identified source-instance grouping, checkpoint/observation fan-out, and quiescence defects. Exact request/clause validation was a separate primary finding in the same bounded repair cycle. | Reviewer elapsed, allocation, and summed effort `unknown`; proxy is one bounded pass with one blocking finding. Findings, repair, rebase, and primary reconciliation remain in S1/S2. |
| S6 fresh independent verification | Fresh read-only review of issue #8 webhook convergence/authentication/commit-before-ack and no-live-effect boundary; reviewer does not own disposition | `gpt-5.6-luna` / medium (Plan 0054); effective `unknown` | Accepted with no findings in the final fresh review. Earlier primary and worker checks had already found and repaired short-read prefix acceptance and arbitrary checkpoint seeding. Final focused 30, comprehensive 275 per runtime, plugin 12, compile and diff checks passed. | Reviewer elapsed, allocation, and summed effort `unknown`; proxy is one bounded pass with zero findings. Earlier RED/GREEN repair and primary reconciliation remain cumulatively included; no retries or live provider calls. |

The Git endpoint proxies are overlapping elapsed intervals: work happened in
parallel and commits include coordination and waiting. They cannot establish
causal duration, per-model effort, or attribution of shared-account usage.
Plan test durations are validation command wall time, not model allocation.

## Result and promotion decision

All three required families have evidence, but the samples are not a fair
controlled comparison: requested configurations differ by workload, effective
models are unavailable, allocation is unavailable, and the Git intervals
overlap. P48-DRIFT-01 also invalidated the final quality floor for the #6
implementation and fixture samples until its bounded #9 repair lands. The
frozen promotion rule therefore yields **honest inconclusive**, not a routing
win. Retain the current `balanced` defaults and make no model or policy-default
change. The results demonstrate useful accepted slices and correction
evidence, not relative cost or delivery superiority.

No new runs, widened matrix, retries, provider reads, dispatch, install,
release, or other live effect was performed for this calibration.

## Durable receipts

- Plan 0052: GitHub adapter and fixture outcomes, focused 13, comprehensive
  252 per runtime, and 157-test shared-seam follow-up.
- Plan 0053: filesystem adapter/fixture outcomes, review repairs, and final
  64-focused / 289-comprehensive-per-runtime / 12-plugin receipt.
- Plan 0054: webhook review findings and final 30-focused / 275-comprehensive-
  per-runtime / 12-plugin receipt.
- Git custody endpoints: `3940de5`, `034c285`, `18c880c`, `df5130b`,
  `15a3620`, `4169d7e`, and current base `bf05bb8`; all are local readbacks,
  not a calibration allocation ledger.

Known gaps are precisely the missing effective-model telemetry, measured
allocation, and non-overlapping causal timing. A future calibration would need
those fields frozen before execution; this packet does not authorize it.
