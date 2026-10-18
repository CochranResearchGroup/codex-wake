# Plan0168 — Operational same-conversation self-refresh

State: OPEN. Owner: primary / ecochran76. Work item: #282.
Branch: fix/self-refresh-operational. Base: 27330f6. Target: origin/main.

## Current State

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
