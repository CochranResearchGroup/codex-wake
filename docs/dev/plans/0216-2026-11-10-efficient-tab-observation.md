# LOCAL-P216 | Efficient tab observation and stable formatting

State: OPEN
Owner: primary / ecochran76
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/540
Domain authority: GLOSSARY.md
Scope: approved specification and seven implementation tickets; user authorized implementation and closure on 2026-11-10. No merge/deploy authority in this slice.

## Current State

Research completed in notes/0011-2026-11-10-tab-observation-efficiency-research.md.
Stock tmux/Byobu already supplies metadata notifications; source shows Codex
status broadcasts, not yet passive-stream runtime acceptance. Current observer
spawns isolated probes, can walk panes twice, loses process-local caches between
cycles and couples trait inventory with exact health and visible-error inspection.
Original formatting process/fsync overhead has separate deployed fixes. Slate is
selected on44tabs, automatic monitor stopped. This interview decides efficient
observation behavior and acceptance; no new runtime mutation or theme change.

## Settled context

- Keep stock Byobu/tmux; Wake owns observation/caching/rendering changes.
- Preserve stock Codex and independent sessions/processes; qualify existing passive
  protocol before considering a native harness change.
- Preserve approved Slate/Dusk/Graphite presets, compact labels and no STALE text.
- Existing domain separates activity, responsiveness, visible error and authority.
- Source availability and fixtures do not prove installed passive event delivery.

## Settled decisions — round one

1. Activity latency: recommended roughly1second after supported native events,
   with a measured normal-load acceptance target rather than a repaint poll.
2. Automatic evidence tiers: recommend activity continuous; exact health on explicit
   request plus bounded background sweep; visible-error checks separate and cheap.
3. Scale and cost: recommend qualification at100tabs acrossmultipleterminal/native
   sessions; one shared observer perhost with fixed bounded adapters/workers;
   measure incremental CPU/RSS rather than one watcher or MCP server pertab.
4. Missing evidence and display: recommend stable palette/name/type; quiet unknown
   activity/health when source lost, diagnostics in inspect, automatic reconnect.
5. Release behavior: recommend zero agent/session restarts, preserve existing
   formatting baseline and on/off rollback; qualify private and live-read-only
   observation before enabling continuous updates fordefault.

Operator accepted all five recommendations ("yes all"). Activity roughly1second
when events are available; separate continuousactivity/backgroundexacthealth and
visibleerrorchecks; qualify100tabs acrosssessions/accounts withsharedbounded
observers; source loss quietly removes uncertain indicators while preserving
palette/name/type; rollout preservesagents, originalbaseline and on/offrollback.

## Settled decisions — round two

6. Resource targets: recommend100tabs, <=1% ofoneCPUcoreidle and<=5% ordinaryactive
steady-state over60s, <=256MiB aggregate incrementalobserverRSS including workers;
measure coldstartseparately, no silentbudgetincrease. Activitygoal~1s,p95<=2s for
qualified event path. These are proposed acceptance targets, not existing proofs.
7. Responsiveness schedule: recommend no more than once60sperknownagent bydefault,
explicit requests immediate withinbound; unavailablechecksunknown, budgettakesprecedence.
8. Visible errors: recommend nativeevents wherequalified; otherwise changed-screen
localredactedclassification, about5sforactive/dirtytabs, boundedslowerfallback where
changeeventsareunqualified. No stored rawscreen/draft/history or synthesized input.
9. First delivery: recommend WSLtmux/Byobu+stock/moddedCodex qualification; preserve
existing Grok/SSH detection and knownunknowns, psmuxfallback capability; qualify
newWindows/Grok/Claude/openharness eventadapters independently ratherthan claiming
unsupportedparity or requiring modifiedByobu/Codex.
10. Diagnostics: recommend one humanreadable observerstatus plus JSON/API/MCP
parity, reporting cost, sourceconnection/cacheage/unknownreason and overload;
no routine needforworkspaceIDs or opaquebackgroundprocess inspection.

Operator accepted Q6–Q10 ("ye sall"). Resource and latency numbers are acceptance
targets, not claims of current performance. Health/errorchecks remain separate
and bounded; firstreleaseWSLnativeCodex, existingothercapabilitypreservation;
readablestatus plus JSON/API/MCP parity accepted.

## Derived consistency requirements

Accepted source-loss behavior requires reconnect to establish fresh source/binding
identity and a bounded baseline before trusting event deltas. PID/window/name
reuse must invalidate affected entries; a failed check is not a fresh negative.
A newly observed error clears only on fresh source evidence of resolution/absence;
source loss removes the uncertain cue but retains attributable last-known detail.
Observers never resume conversations, launch modelturns, inject input or acquire
controlling-client custody merely to obtain metadata. These preserve existing
runtime authority/domain rules rather than introducing operator policy choices.

## Settled decisions — round three

11. Unsupported/losteventfeed fallback: recommend automatic inexpensive batched
metadata reconciliation within accepted budgets; explicitlydegraded diagnostics,
no repeatedfullpane/health investigation everyrepaint. Eventlatencytarget applies
onlyqualifiedeventpaths; fallbacklatency reported honestly.
12. Observer lifecycle: recommend one host-managed owner starts with existingWake
monitoring whenenabled, survivesclientdisconnect, reconnects existingservers after
restart, and doesnotstartper-tabagents/daemons or modify stockByobu/Codex.
13. Independent controls: recommend monitoring pause/resume doesnotalterpalette or
terminateagents; formattingrollbackrestoresoriginalsettings andreenablekeepspreset.
Keephealth/erroractivitychecks independently configurable withsafe defaults.
14. Budgetoverload: recommend coalesceevents, prioritisecurrentlyactive/changedtabs,
rotateslowchecks fairly andbackoff withinfixedbounds. Neverdrop observederror
silently or mark skippedworkfresh; exposebacklog/lastacceptedobservations.
15. Releasegate: recommend 100tabprivate/nativeacceptance foridle/activebursts,
reconnect/death/PIDreuse/sourcefailure/rollback; thenactual44+tabread-onlylive
qualification understatedbudgets. No agentrestart, syntheticproviderturn or silent
resource-budgetincrease. Autoenabledefaultonlyafterpassingandreportingreceipt.

Operator accepted Q11–Q15 ("yes all"). Automatic low-cost fallback; sharedhost
lifecycle/reconnect; independent observer and palette controls; bounded fair
coalescing/backoff with explicituncertainty; private100tab plus existinglive-tab
qualification before defaultcontinuousactivation are settled.

## Consolidated shared understanding (confirmation pending)

Wake will replace repeated whole-workspace investigation with a shared persistent
observation cache and qualified passive tmux/Codex event adapters. StockByobu and
stockCodex remain unchanged. Discover/reconcile bounded metadata, collect pane
identity once, enrich existing observations, reuse generation-checked hash/native
metadata, and render only dirty tabs. Deep exacthealth and visibleerrors remain
independent observations/schedules; activity is not responsiveness or authority.

First release qualifies WSLtmux/Byobu andstock/moddedCodex acrossaccounts/sessions;
existingGrok/SSH/psmuxcapabilities andexplicitunknowns remain, withnewadapters
qualifiedindependently. No observer may resume/modelprompt/injectinput/takecustody
solelyforobservation. Cacheidentity checks include sourcegeneration, processbirth,
window/paneidentity and buildmetadata; sourcefailure/reuse cannotborrowevidence.

Acceptance:100tabs; ordinaryeventupdategoal~1s,p95<=2s forqualifiedeventpaths;
steadyidle<=1%oneCPUcore/ordinaryactive<=5%onecore over60s; totalincrementalobserver
RSS<=256MiB includingworkers. Measurestartupseparately andrecordalllimits. Exact
healthbackground<=once60speragent, immediateboundedexplicitrequests; visibleerror
~5sforactive/changedtabswherequalified. Resourcebudgettakesprecedence; fallback
latency/unknown/degraded state reported honestly. No silentlimitincrease.

Palette/name/qualifiedstabletype staysteady. Removeuncertainactivity/attention
cues onsourcefailure; noSTAL-label, blanketdimming orfrozenrunningclaim. Clearerror
onlyfreshresolution/absenceevidence; retain redactedattributabledetailininspection,
never rawscreen/drafts/history. Quietvalidlongturns do notexpiremerelyduetolackof
transitions. Recoveryre-seedsbaselinebeforeacceptingdeltas.

One host-managedowner startswhenmonitoringenabled, survivesclientdisconnects,
reconnectsautomatically andusesboundedsharedworkers ratherthanper-tabprocesses.
Activity/health/errorchecks independentlyconfigurable. Pausemonitoring leaves
palette; formattingrollback restoresoriginalbaseline; reenablekeepspreset.
Readableobserverstatus plusJSON/API/MCP parity shows cost,sourceavailability,
cacheage,backlog andunknownreason withoutopaqueIDroutinework.

Isolated100tab idle/burst/reconnect/replacement/failure/rollback acceptance precedes
existing44+tab read-onlylivequalification underthesamecaps. No artificialprovider
requests/agentrestarts. Passingreportedreceipts required beforecontinuousdefault
activation. Slate/Dusk/Graphite andexistingoriginalsettingscustody preserved.

Decision frontier: empty. Await operator confirmation that this consolidation
matches intent; then formal spec/tickets are next, not implementation under this
interview. Productcode/liveconfiguration have not changed during this interview.

## Scope, non-goals and definition of done

Reach confirmed shared understanding, recording accepted decisions and remaining
frontier. Then formal spec/tickets under explicit next scope. No implementation,
provider calls, live capture, process restarts, new native service or monitor
activation during interview. Root policy and operator authorization remain primary.
Graphiti historical lookup skipped: supplied decisions/current research suffice.
Memory disposition forbidden: no explicit memory-write request.

## Execution ledger

Authoritative specification: evidence/plan0216/spec.md; parent #540 remains open.
Integration branch feat/efficient-tab-observer, worktree /tmp/codex-wake-observer-0216.
Fixed review base fa2363c24bf921ecf0bd8390739e96041e620e8f.

| Ticket | Owner | State | Dependencies |
| --- | --- | --- | --- |
| #541 cached inventory | primary | locally validated; integrated | none |
| #542 native feed | /root/native542 | implementing | none |
| #543 tmux feed | /root/tmux543 | implementing | none |
| #544 observer lifecycle | pending | blocked | #541 #542 #543 |
| #545 tiered checks | pending | blocked | #541 |
| #546 stable projection | pending | blocked | #541 |
| #547 installed acceptance | pending | blocked | #544 #545 #546 |

No nested delegation; three implementation lanes maximum. Inherited model/effort
for bounded implementation workers; deterministic tool checks qualify their work.
No comparative model-calibration or allocation-savings claim.
Validation: focused development budget 180 seconds per invocation; Python3.11/3.12;
blocking affected presubmit once integrated; comprehensive and provider runs excluded
unless a concrete unresolved risk requires widening. Hosted CI skipped by policy.
After all seven accepted closures: one broad Standards/Spec review, then one bounded
TDD remediation pass, followed by focused regression checks and draft PR.
