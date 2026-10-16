# Plan0166 — Strict objective execution enforcement

State: OPEN. Owner: ecochran76 / primary. Spec#274; tickets#275–278.
Integration branch: feat/objective-enforcement. Base:0a5c8d1.
User ceiling: stop/checkpoint before1,000,000 tokens or3h from2026-10-16T19:41:41Z; hard checkpoint by22:31Z (10min reserve). Track native goal counters and UTC.

## Acceptance / non-goals
Implement full published#274 contract and each#275–278 acceptance criterion, using public lifecycle operations, native execution containment and independent OS readback. No deployment/fleet changes, shared-session termination, provider cancellation or exact token ceiling claims. Unsupported guarantees reject before task effects.

## Seam and execution graph
Public lifecycle launch/config/status/stop plus dedicated systemd execution adapter.
275→276;275+276→277;277→278. Only validated integration results unlock dependents.
TDD at public configuration/lifecycle seam; host adapter protocol fixtures plus disposable native acceptance. One whole-branch review, one remediation pass; no broad review restarts.

## Workers / owned paths
Primary owns lifecycle/configuration/monitor/CLI integration, ledger, plan and evidence.
Host worker owns new host_execution module and its tests only, independent branch/worktree.
Native probe owns temporary acceptance harness/evidence only. Initial20k packet exceeded (46,711 observed); its second turn and the new packet first turn have unknown costs, conservatively100k each. No further paid turns authorized in the active packet. Root counter checkpoint600k leaves reserve below the user1MM ceiling. Each native turn bounded120s; this is elapsed containment, not an exact token bound.
At most3 active agents total. No nested workers.

## Ledger

Current public containment/stop proof: evidence/plan0166/native-probe/public-containment-stop.json. Ticket275 integrated, not yet validated; downstream tickets remain pending. Full development suite failed; handoff failure counts reproduced on unchanged base (49tests,50failures,1error); default user clock config contaminated a separate clock selection (cleared-config10tests pass). No broad final review, installation, deployment, or tracker closure performed.

## Renewed authority | 2026-10-16T20:33:11Z

User resumed and renewed allocation, then edited stable goal ceiling to2MMtokens/4h. Preserve historical consumption; latest cumulative2MM ceiling supersedes original1MM. Conservative4h deadline from original19:41:41Z start is23:41:41Z; checkpoint by23:31:41Z. Earlier600k/700k planning checkpoints are superseded, not approval gates. At renewal root689,337 plus external native69,585 observed and200k reservedunknown. No claim that reservations prove exact total cost.

275 validated on contained launch/cleanup slice: native Codex/code-mode/shell/child and setup/build/test, effective kernel controls, public stop, sentinel, public unsupported/shared refusals. Full isolated1303testsPASS/1opt-in skip; installed35checks including livehostPASS. Sourcefrozen full run precedes ab7bf49 exactidentity-stop fix; focused37 and four actualOS/injectedtelemetry cases cover that change. The initial live-test cgroup-removal race remains retained as firstfailure, with exact-invocation same-deadline polling repair.

276 nowrunning: public lostlaunchresponse recovery proved on actualsystemd/guard/CLI with generic sleep+injectedaccounting; no native/provider substitution. Replacement invocation and wronggeneration remain unadopted. Native worker owns one actualblockedtool/TERMresistant-child/deadline/transportloss proof; host worker owns separate restart/BOOTTIME continuity tests only. Both fromab7bf49; primary retains production-source ownership. Native deadline packet: max1paidturn/75kestimated/120sec; unknownfinalusage reserves100k. One authoritativezero-effect startupretry only. No host suspend/reboot or shared-session/service effects.

277 pending (blocked276), supporting actual native sampledcap evidence already retained:22,874totalincluding12,160cachedinput againstcap1;22,873observedovershoot. Not a maximumovershoot bound. 278 pending. One wholebranchreview remains unused and occurs onlyafterallticketsvalidated. No deployment/merge/trackerclosure.
