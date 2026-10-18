# Plan0166 — Strict objective execution enforcement

State: CLOSED. Owner: ecochran76 / primary. Spec#274; tickets#275–278.
Integration branch: feat/objective-enforcement. Base:0a5c8d1.
Latest renewed allowance: NEW2MMtokens/4h from2026-10-16T22:01:51Z; historical counters preserved inledger.json. Implementation completed within this renewed window.

## Acceptance / non-goals
Implement full published#274 contract and each#275–278 acceptance criterion, using public lifecycle operations, native execution containment and independent OS readback. No deployment/fleet changes, shared-session termination, provider cancellation or exact token ceiling claims. Unsupported guarantees reject before task effects.

## Seam and execution graph
Public lifecycle launch/config/status/stop plus dedicated systemd execution adapter.
275→276;275+276→277;277→278. Only validated integration results unlock dependents.
TDD at public configuration/lifecycle seam; host adapter protocol fixtures plus disposable native acceptance. One whole-branch review, one remediation pass; no broad review restarts.

## Workers / owned paths
Primary owns lifecycle/configuration/monitor/CLI integration, ledger, plan and evidence.
Host worker owns new host_execution module and its tests only, independent branch/worktree.
Native probe owns temporary acceptance harness/evidence only. PhaseA of278 now authorizes two native turns against frozenbeeacfa, then HOLD for actual cost readback. Full campaign envelope atmost5turns/350k observed plus reserved estimate, not a guaranteed charge ceiling. Historic external observed161172 plus two missing-counter100k reserves retained. Later interrupted counters remain observed floors without proven final billing; do not treat reserves as exact upper bounds.
At most3 active agents total. No nested workers.

## Current State

CLOSED: tickets #275–278 are implemented, integrated and validated on
`feat/objective-enforcement`, with final source commit `4ce6ae5`. Native public
acceptance covers concurrency, failed checkpoint preservation, explicit renewal,
refresh, semantic review, successor continuation, final accounting and unrelated
sentinel preservation. The final campaign settled 191,562 tokens with zero
reservations or unknown actors.

The local provider-turn count axis failed: four turns occurred against three
planned. The extra automatic DONE turn issued no command and was fully charged.
The approved continuation command ran exactly once; this retained failure does
not invalidate the functional identity, accounting or deadline evidence.

Exactly one whole-branch review compared `0a5c8d1` with `1b0848a`, followed by one
bounded remediation. Standards finding S1 confirmed a missing directory fsync;
`4ce6ae5` fixes it. The spec axis found no substantiated issue. Verification:
62 focused checks passed; the final full suite passed 1,326 tests with one optional
host skip in 726.676 seconds; the isolated installed-package selection passed all
69 checks, including actual systemd. Its 106 Python files match source. Compilation,
policy wiring and plugin checks pass. No accepted blocker remains. See
`evidence/plan0166/acceptance-audit.md` and `review-adjudication.json`.

Delivery supersedes the earlier source-only boundary: PR280 merged3cdc037 and
v0.17.0 is released/installed under the standing install/deploy/reconcile request.
Tracker reconciliation follows the delivered acceptance evidence in Plan0167.
Earlier failures and checkpoints remain historical. Operator-provisioned strict
bootstrap remains the documented supported route, not automatic first spawn.

The latest renewal preserved root baseline 1,364,205, external observations 427,289
and a 200,000 historical unknown-cost reserve. At closeout these were 1,652,641,
618,851 and 200,000 respectively: approximately 480k tokens in the renewed window.
Unknown-cost reserves are estimates, not guaranteed billing bounds.

## Historical authority and evidence

## Renewed authority | 2026-10-16T20:33:11Z

User resumed and renewed allocation, then edited stable goal ceiling to2MMtokens/4h. Preserve historical consumption; latest cumulative2MM ceiling supersedes original1MM. Conservative4h deadline from original19:41:41Z start is23:41:41Z; checkpoint by23:31:41Z. Earlier600k/700k planning checkpoints are superseded, not approval gates. At renewal root689,337 plus external native69,585 observed and200k reservedunknown. No claim that reservations prove exact total cost.

275 validated on contained launch/cleanup slice: native Codex/code-mode/shell/child and setup/build/test, effective kernel controls, public stop, sentinel, public unsupported/shared refusals. Full isolated1303testsPASS/1opt-in skip; installed35checks including livehostPASS. Sourcefrozen full run precedes ab7bf49 exactidentity-stop fix; focused37 and four actualOS/injectedtelemetry cases cover that change. The initial live-test cgroup-removal race remains retained as firstfailure, with exact-invocation same-deadline polling repair.

Historical276 packet: public lostlaunchresponse recovery proved on actualsystemd/guard/CLI with generic sleep+injectedaccounting; no native/provider substitution. Replacement invocation and wronggeneration remain unadopted. Native worker owns one actualblockedtool/TERMresistant-child/deadline/transportloss proof; host worker owns separate restart/BOOTTIME continuity tests only. Both fromab7bf49; primary retains production-source ownership. Native deadline packet: max1paidturn/75kestimated/120sec; unknownfinalusage reserves100k. One authoritativezero-effect startupretry only. No host suspend/reboot or shared-session/service effects.

Historical277 preparation, supporting actual native sampledcap evidence already retained:22,874totalincluding12,160cachedinput againstcap1;22,873observedovershoot. Not a maximumovershoot bound. At this earlier checkpoint278 was pending. One wholebranchreview remains unused and occurs onlyafterallticketsvalidated. No deployment/merge/trackerclosure.
