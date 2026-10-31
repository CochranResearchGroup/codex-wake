# Plan0168 — Operational same-conversation self-refresh

State: OPEN
Owner: primary / ecochran76. Work item: #282.
Branch: fix/self-refresh-operational. Base: 27330f6. Target: origin/main.

## Current State

v0.17.3 is released/installed from exact mainfc4524d (PR287), correcting
fractional checkpoint percentages in MCP and CLI. Installed14focused tests,
110-source parity and27-tool controls pass; both whole skill dirs are synced.
Original fractional payload now reaches genuine host admission in private replay.
The new remote-view caller still has no production grant/enrollment. No host
resource grant, native goal, counter or allocation changed. Automatic new-session
bootstrap needs separate authorization/accounting design; source patch does not
claim to solve that setup hold.

Original production refresh remains terminal EXPIRED without reload, with receipt
hash unchanged. Plan/issue remain OPEN for production resource proof. No new
refresh intent or expiry was created; explicit new-expiry approval and shared idle
condition remain required. Current branch: docs/fractional-reserve-delivery;
basefc4524d. Earlier clock-dependent mailbox flake remains retained under v0.17.2;
no unrelated mailbox rerun was needed for this input-type correction.

## Original diagnostic baseline

v0.17.0 ships tool/skill discovery but global MCP lacks lifecycle scope.
Public installed reproduction returns lifecycle_host_scope_unavailable.
Source refresh requires exact idle ownership and does not defer an active self-call.
A new TUI alone may retain native MCP cache; actual selected-resource readiness is
required. No production profile/refresh/session changes in this repair yet.

## Scope and acceptance

Make the user's existing conversation self-refresh through an agent-facing path,
preserving native goal, counters, allocation and deadlines. Host owns caller,
workspace, endpoints, resource probes and operation grants. No shared-daemon
restart, unrelated-session termination or implicit new budget. Resource readiness
must prove new skill/catalog and actual MCP behavior; admission is not completion.
Unknown or unsafe ownership, pending work, drafts and stale resources hold.

## Work units

1. Freeze native reload capability and existing idle/ownership behavior.
2. Select smallest public repair; TDD active-to-idle defer only if required,
   with exact caller/grant, immutable checkpoint/expiry, independent controller,
   and replay/uncertainty guards. Configuration must not silently broaden spawn
   or handoff access or change legacy wake tool roots.
3. Isolated public CLI/MCP plus actual native/TUI zero-model acceptance; stale
   resource and unchanged-goal axes remain separate.
4. One bounded independent review, one remediation pass. Exact-main PR/CI then
   release/install/configuration. Production refresh only after prerequisites
   and restart-safe checkpoint; preserve same thread and original resource state.

## Execution bounds

Primary owns integration. One bounded worker /root/host_execution_adapter checks
local native schema read-only (no reload/turn/goal/provider effects). At most two
repair attempts per failing seam; no broad review restarts. Existing CodeGraph
source and public reproduction bound discovery; no duplicate exploration workers.
No provider calls planned. A missing native per-thread reload capability is a
named contract question, not permission to restart the shared server.

## Definition of done

Installed public readiness and completed same-conversation resource proof with
unchanged counters/deadline; repo/tracker reconciliation and exact runtime identity.
Any uncovered native capability is reported as a precise remaining boundary.

## Qualification decision frontier | 2026-10-18 UTC

Bounded native worker completed both owned-fixture attempts. Global
config/mcpServer/reload refreshes BOTH loaded conversations' MCP processes and
catalogs. thread/resume alone remains stale. thread/unsubscribe reports success
but does not unload; subsequent resume remains stale. Same IDs/paused goals and
zero model turns were verified; owned servers exited and all eight recorded PIDs
are gone. No production reload or session/goal mutations occurred.

Current production read-only inventory:62 loaded,49idle and13active. Exact native
API has no thread selector; a conversation-only refresh remains unsupported.
User is asked to choose shared reload scope (after idle check, with active peers,
or keep conversation-only unavailable). This is an explicit peer-effect boundary,
not a generic deployment permission request. No dependent effects before answer.
Idle checks cannot provide an atomic native CAS against a racing new turn.

Independent source repair: optional host --lifecycle-root keeps new lifecycle
journal separate from legacy wake-tool roots. Existing MCP public test augmented
for both scopes: red unknown flag; first green run exposed fixture caller missing
on the legacy probe; corrected fixture then3testsPASS. Legacy fallback preserved.
This checkpoint does not establish operational refresh or native MCP readiness.

## Approved shared scope and frozen implementation | 2026-10-18 UTC

User explicitly answered yes to enabling shared MCP reload after an all-idle
check. New refresh_mode shared_mcp_idle is a host-only, refresh-only profile.
It queues during the caller's active turn; an independent sessions refresh-watch
controller performs complete bounded inventory, checks all loaded conversations
idle again after goal snapshots, persists intent then calls the single native
reload. No TUI/client replacement, goal/turn mutation, budget allocation or reset.
A fixed expiry uses trusted initial UTC and same-boot CLOCK_BOOTTIME. Lost reload
responses reconcile only by read-only observation; the effect is not blindly
replayed. All observed native goals must preserve authority and nondecreasing
counters. Native skill catalog/hash and actual read-only MCP behavior must match
selected host proofs before completion. Shared reload has no atomic idle CAS;
racing starts after the final observation remain an explicit native limitation.

Controller runs independently of the resource enforcer so large shared reloads
cannot block enforcement polling. Controller shutdown fences later requests.
Legacy client refresh remains unchanged; optional lifecycle-root isolates journals.
Public CLI tests cover active source, active peer, racing peer, lost response,
stale resource expiry, counter reset rejection and controller shutdown. Existing
legacy tests require the documented private XDG/empty Stable Time environment;
initial inherited-host failures remain retained and isolated selection passes.

Primary owns source. Worker /root/host_execution_adapter owns only the two-thread
native acceptance script (4855bdf,1b6acee). One independent bounded new-source review
is assigned to /root/goal_supervision_review after the source freeze. No broad
historical feature review is reopened. Deployment still follows exact-main CI.

## Source/native acceptance checkpoint

Frozen source332c035 received one independent Spec/Standards pass. Sole accepted
F1 was native source/profile workspace binding;944572f fixes it before effects
and proof. Independent closed-world verification:9publictestsPASS7.400s, no
introduced regression. Discovery/remediation counts remain1/1.

Actual native public MCP acceptance on candidate944572f passes in3.882s: queued
admission, separate refresh-watch process, one acknowledged shared reload, selected
skill and actual MCP v2 behavior on both loaded conversations. Same native IDs,
exact paused goals/counters and fixed expiry retained;0modelturns. All owned
processes exited and fresh census is clean. First fixture failed before admission
because of an unsupported legacy codex_home field. That first fixture also made
an unexpected provider warmup connection which received HTTP401; zero turns were
separately audited. Second fixture is configured exclusively for a loopback-only
no-auth provider with websocket warmup disabled. Both allowed attempts consumed;
raw/curated first failure and successful readbacks retained. No production reload.

A public setup-refusal test then exposed empty CLI stdout on missing monitor;
shared mode now returns structured shared_refresh_unavailable (no false effect
uncertainty).10focusedpubliccasesPASS. Native valid-profile behavior is unchanged.
Documentation now exposes self-refresh near skill entry, states the shared scope,
queued/completed distinction and native idle-race limit, and gives managed setup.
Production install/queue and exact-main delivery remain open gates.

## Presubmit environment correction

The first hosted run failed8shared fixtures under default umask022: the fixture
had not pre-created the required private runtime root. Its early guarded request
could create a nonprivate parent before monitor startup. The actual native
fixture already created that root0700. A deterministic umask022 public reproduction
failed; fixture setup now creates0700 explicitly.10publicchecks pass under022;
privacy checks remain unchanged. Early warm/slow-start probes under local077
passed and remain retained. The source setup guide now includes install -d -m700.

The initial local full run1360cases failed6refresh checks and one mailbox outbox
observation while source/tests changed during the run. It is retained, not a final
frozen-build acceptance claim. The mailbox case passes its direct rerun. Final
frozen hosted CI and installed selection own the release gate;57 installed focused
checks and110-source parity/MCP27-tool controls pass on e4d6f12.

## Exact-main delivery and deferred production proof

PR283 merged2e3e931 after hosted run39085689031 passed1361tests (1skip) on
Python3.11 and3.12 plus installed release gates. Published v0.17.1 wheel/sdist
were downloaded and hash-matched. Installed exact-main prefix
/home/ecochran76/.local/share/codex-wake/releases/0.17.1-2e3e931 passes110Python
source parity,27-tool controls and actual mailbox smoke. Five stable entrypoints
and both complete skill directories updated with backups. Native skills/list
sees the new enabled descriptions and exact paths.

Global MCP preserves goal flags and adds separate lifecycle root/registry. One
exact caller owns self-refresh configuration/refresh only; native workspace,
endpoint, explicit shared-idle approval, skill digest and actual MCP read-only
configuration response are bound. Separate refresh servicePID42165 active.
Unenrolled goal watcher updated to same releasePID42551; no enrollments reset.
Unrelated supervisorPID60043 preserved. Original native goal remains complete
with tokens1668856,time7567,createdAt1792179701,updatedAt1792189697; no goal write.

Public production MCP admits plan0168-production-self-refresh-v0171 as queued
through2026-10-18T02:19:21Z. Monitor observes62loaded, at least1busy; no reload
attempt. The current active turn itself prevents reload. Checkpoint/receipt and
verified persistent continuation are located in deployment-queued.json. Native
file wake initially retained pending_time, then supervisor recovered bounded UTC
and reports pending/not_due because terminal marker does not exist. Helper only
writes that marker on completed/blocked/expired or bounded timeout; it performs
no native effects. Wake continues the same thread to reconcile; never requeue,
extend expiry, reopen goal, reset counters or force idle.

Actual production completion remains OPEN; queued admission is not readiness.

## Terminal wake reconciliation and timeout repair

Wake635ecf6b was submitted as a2542654-9265-4585-89a9-60ba6425a26c. Terminal
marker is true: expired/expiry_reached. No reload_attempted marker exists. Actual
source catalog remains25tools and lacks goal tools; original complete goal and
all its counters are unchanged. Last observed busy thread01a1178a maps to
im-receipts and is still active at readback; this is an observation, not proof
that it caused the timeout. Runtime journal did not retain the timeout exception,
so the precise production request which timed out is unproven.

Public CLI plus independent watcher regression: injected native thread/read
exceeds the1s RPC cap while intent expires in2030. Before correction it becomes
expired (red1case1.728s). Remove the unconditional TimeoutError expiry branch;
use the existing guarded observation failure/deadline handling. Same intent
then completes once with original expiry, same goals and no goal writes/turn
starts.11shared checks PASS8.289s, including real expiry/lost-response continuity.
Source fix does not revive historical terminal receipts or renew any allocation.

Current gate: exact-main v0.17.2 patch delivery and installed proof; production
retry requires explicit user approval of a new fixed expiry. No global restart,
peer interrupt or force-idle action is authorized.

## v0.17.2 exact-main delivery

PR285/head900ae29 passed hosted run39088839465:1362tests (1skip) each on3.11
and3.12, installed gates PASS. Merged exactmaincdb499e2aca5a9bf7169cbe0e69009b9fb8bcbb8
owns releasev0.17.2 wheel/sdist; downloaded bytes match both local artifacts.
Prefix /home/ecochran76/.local/share/codex-wake/releases/0.17.2-cdb499e has110
Python source matches. Installed public shared11testsPASS8.839s, using a copied
test harness outside source so both CLI parent and separate watcher import the
installed package. Controls/MCP27tools PASS. Both full skill directories remain
byte-identical to release source; no skill rewrite was necessary.

Broader private-bus installed MCP smoke initially refused wake_messages_reply
with clock_anomaly/clock continuity uncertain, reconciliation_required=false.
Failure retained in v0172-mcp-first-failure.json; no production effect. One
fresh private-fixture diagnostic recheck passes5.920s,0native turns/notifications,
0remaining children and fixture removed. Clock-dependent flake remains disclosed;
mailbox/clock code unchanged. No broader probe or retry was performed.

All5stable entrypoints now select0.17.2. Independent shared-refresh service
PID20264 runs exactnewprefix after verifying every intent terminal. Host
self-refresh proof expects actual0.17.2 configuration response, with caller/
workspace/scope grants unchanged. Resource watcher42551 stays on0.17.1 and
supervisor60043 is preserved. Historical expired receipt SHA256 unchanged,
no new intent/reload/goalwrite/counter reset. Actual cache25tools confirms no
production resource proof. User-approved new expiry plus idle condition is the
remaining gate. Plan0168 and work item282 remain OPEN.

## New-caller resource admission diagnosis | fractional reserve correction

User invoked diagnosing-bugs for repeated remote-view host refusal. Exact
read-only installed MCP reproduces newUUID missing host grant; a same-process
private-policy differential isolates that key as the cause. It is a new
conversation, not resume of the previously granted UUID. No live grant changed.

Separate actual captured set call uses17.5percent for350k-token reserve. MCP
schema and CLI parser wrongly reject fractions already supported by backend.
Public stdio regression is red twice (schema then CLIparse); both input types
fixed,14focused checks pass. v0.17.3 patch delivery tracked on
fix/fractional-checkpoint-reserve, base8318923. Evidence in caller-admission/.
No automatic grant inheritance, enrollment, counter reset or native goal change
is part of this correction. Original production refresh remains terminal.

## v0.17.3 fractional reserve delivery

PR287/headdb3ea76 passed hosted run39090662722:1363tests each on3.11/3.12
(1skip), installed gates PASS. Exact mergedmainfc4524d01b8a607d02fa20bab722332a6ec720fd
owns v0.17.3 release; wheel/sdist download hashes match. Versioned installed prefix
/home/ecochran76/.local/share/codex-wake/releases/0.17.3-fc4524d passes110Python
source parity,14installed MCP/CLI/supervision tests5.684s and27-tool controls.
Copied qualification harness runs outside source so child imports are installed.

Original actual caller/2M/6h/17.5percent/900seconds payload replay against a copy
of host policy and private root now reaches goal_limits_unavailable/held from
the missing grant, with zero enrollment receipts. MCP schema is numeric and
actual CLI accepts fractions. The missing grant is deliberately preserved, not
relabelled as enforcement success. Source/backend range/finite checks remain.

Five stable entrypoints and independent shared-refresh monitorPID10896 now use
release prefix. Both full skill directories synced with backup and byte parity;
10relative links valid. Fresh standalone configuration is0.17.3/27tools. Goal
watcher42551 and supervisor60043 preserved. Production goal-policy hash and old
expired refresh receipt hash are unchanged. No production grant, enrollment,
goal resume, counter reset, shared reload or refreshed expiry. Actual existing
MCP connections may retain old schema until refresh; no new refresh authority
is inferred. caller-admission/v0173-delivery.json owns runtime locators.
