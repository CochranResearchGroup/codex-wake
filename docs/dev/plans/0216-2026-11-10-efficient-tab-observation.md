# LOCAL-P216 | Efficient tab observation and stable formatting

State: CLOSED
Owner: primary / ecochran76
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/540
Domain authority: GLOSSARY.md
Scope: approved specification and seven implementation tickets; initial delivery complete. Subsequent operator instruction explicitly authorizes PR review, merge, deployment and activation.

## Current State

PR551 merged6f95f90 after main CLI reconciliation and exact315member installed
qualification. During authorized activation, live title changes exposed formatting
CLI pin races; issue552/PR553 fixed only title-sensitive formatting pins with real
red/green process-birth-fenced regressions. Final0.22.0.dev4 sourcebfc1bbce is
deployed,315installed members match qualified wheel; nine launchers/completion,
sevenaccounts,tenprotectedfiles and27nativeprocesses preserved.

Slate and the shared1stick monitor are ENABLED on46tabs with activity/health/errors
on, connectednative/availabletmux sources,freshsnapshot,noformattingfailures.
Historical namespace baseline is archived privately; currentnamespace captures its
own original settings. RealCLI rollback restored46windows andsessionoptions
exactly; reenable appliedSlate. Dev3 live60s measured2.06017%onecore/46.1MBownedRSS;
dev4 carries performance evidence only for unchanged observer hotpaths. Its exact
separateUID installed formatting regression/fourtransports pass. Source232tabtests
passbothPython. Natural live native transitions remain unobserved, not claimed.

Parent540 remains OPEN. Original single broadreview/singleTDD counters remain1;
issue552 is a bounded deployment blocker repair, not a repeated broad discovery.
Canonical deployment evidence: evidence/plan0216/deployment.json and
integration551/title552/. Original dirty checkout and recovery worktrees retained.

Historical interview context: research completed in notes/0011-2026-11-10-tab-observation-efficiency-research.md.
Stock tmux/Byobu already supplies metadata notifications; source shows Codex
status broadcasts, not yet passive-stream runtime acceptance. Current observer
spawns isolated probes, can walk panes twice, loses process-local caches between
cycles and couples trait inventory with exact health and visible-error inspection.
Original formatting process/fsync overhead has separate deployed fixes. Slate is
selected on44tabs, automatic monitor stopped. This interview decides efficient
observation behavior and acceptance; no new runtime mutation or theme change.

## Qualification repair: retained read-only formatting

Owner: primary integration; delegated #546 implementation. Source evidence:
qualification547/36f42dbe-installed-canonical.json records0.60seconds of child CPU
in60seconds of ordinary activity. Decoder and redundant-redraw repairs help but
do not yet satisfy5%. A realtmux prototype shows retained reads avoid repeated
native reader startups; this is not whole-owner acceptance.

Add one lazy read-only formatting channel per retained workspace, bounded by the
existing finite command, byte and deadline budgets. Its small interface hides
framing, exact socket ownership, lifecycle and error handling. Fixed managed
show-options/display-message requests use unpredictable response markers so
literal option text resembling control frames stays data. No write, capture,
input or arbitrary-command interface is added. Existing writers and generic/psmux
adapters retain their paths. The metadata event feed remains separate. Expose
bounded channel cost/status and close owned clients on replacement and stop.

Required evidence: actualnative hostile-literal roundtrip, command rejection,
identity replacement, timeout/capacity failures, attached-client preservation,
monitor lifecycle cleanup, bothPython checks, then one new exact installed
100tab60+60second gate. Preserve failed receipts. CPU1%/5%, RSS256MiB andp95<=2s
remain fixed; source/fixture proof does not substitute for installed or live proof.

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

## Consolidated shared understanding (confirmed)

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

Decision frontier: empty. The operator subsequently approved consolidation,
formal specification, tickets and implementation. No product code or live
configuration changed during the interview; implementation follows below.

## Interview scope, non-goals and definition of done (historical)

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
| #541 cached inventory | primary | CLOSED; integrated and qualified | none |
| #542 native feed | /root/native542 | CLOSED; integrated and qualified | none |
| #543 tmux feed | /root/tmux543 | CLOSED; integrated and qualified | none |
| #544 observer lifecycle | /root/native542 | CLOSED; integrated and qualified | #541 #542 #543 closed |
| #545 tiered checks | /root/checks545 | CLOSED; integrated and qualified | #541 closed |
| #546 stable projection | /root/tmux543 and serialization546 | CLOSED; integrated and qualified | #541 closed |
| #547 installed acceptance | /root/accept547_resume | CLOSED; final post-TDD qualification | #544 #545 #546 closed |

No nested delegation; three implementation lanes maximum. Inherited model/effort
for bounded implementation workers; deterministic tool checks qualify their work.
No comparative model-calibration or allocation-savings claim.
Validation: focused development budget 180 seconds per invocation; Python3.11/3.12;
blocking affected presubmit once integrated; comprehensive and provider runs excluded
unless a concrete unresolved risk requires widening. Hosted CI skipped by policy.
After all seven accepted closures: one broad Standards/Spec review, then one bounded
TDD remediation pass, followed by focused regression checks and draft PR.

### Integrated presubmit checkpoint

Source72bda0b7: Python3.11 affected tab selection185PASS/51.116s; Python3.12
185tests/57.418s with one formatting CLI status test error. IsolatedretryPASS
does not clear first failure. Causal real-monitor probe confirms test SIGSTOP
can freeze formatting lock: public CLI exit3, reason formatting_busy, phase
uncertain, result null. Product correctly refuses concurrent effect; #546
reopened for test readiness-barrier repair. No product/source image change
needed. First candidate wheel retained. #547 runs provisional100tab windows
underUID1017; acceptance waits correctedfixture green. Static global undefined
name lint, compileall, policy wiring, generated references and whitespace PASS.

### Actual-owner resource checkpoint

First exact72b package100tab driver: idle4.753%FAIL, active3.834%PASS,
RSS37MiB/p95.075secPASS. Actualinstalledmonitor+Slate then exposed additional
formatting costs; diagnostic sourceoverride after observer fixes remains over
CPU caps. No successful fullresource acceptance claimed. #541/#544/#546
reopened for bounded qualification repairs; #547 retains every first failure.
Observer fixes0ee92b48: freshJSONpubliccopies, typedownedTmux proxy restores
redactederrors,2scommanddeadline avoids false1stick reconnects. Nullrenderer
fix4c15717d preserves uncertain/resultnull JSON and exit3 without crashing.

Root cacheJSON experiment did not establish a qualified improvement and was
reverted before shipping. Actualserve profile instead identifies66whole-state
saves/23refreshes,5.794s json.dump and3.3million streamwrites, plus session-option
subprocess overhead. Originalformatterworker repairs only measured hot paths;
original baseline durability/manual custody/rollback stay required. Finalgate
must measure actualinstalledmonitor+Slate100tabs, ownedlive/reapedhelpers,
60sidle/60sactive with unchanged1%/5%onecore and256MiB thresholds.

### Frozen steady-only diagnosis checkpoint

Rootproductsourcebb54d262 includes boundedcontrol replies, formattermemo/batching,
retainedmetadata-fencedprocesscache and deduplicatedrootbirthchecks. Candidate
wheel1 remains exact72b source; no additional wheel rebuilt while CPU gatesfail.
Combined2ce sourceoverride with a deterministic startupbarrier measured
4.591%idle/8.784%active, p951.073sec, all20ordinaryeventsprojected; no gatepass.
Readiness requires100bound/allnativeconnected/tmuxavailable/formattingfixture
applied with nofailures, then a strictly newer qualifying publicsnapshot.
Sourceoverride diagnostics can never pass installed acceptance.

Nextpacket: separate actualserve idle/active profiles after thatbarrier, owned
UID1017 SIGUSR handlers only; no productprofilinghooks. Source2ce frozen for
causality; newerroot birth-dedup does not change algorithms materially. No
broadreview or postreview TDD remediation has run; eachreservedcounter remains0.
