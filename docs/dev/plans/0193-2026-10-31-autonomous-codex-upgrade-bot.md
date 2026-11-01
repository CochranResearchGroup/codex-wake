# Keep modified Codex current through deterministic patching and semantic completion

State: CLOSED
Owner: primary upgrade-bot coordinator
Specification: https://github.com/CochranResearchGroup/codex-wake/issues/444
Execution evidence: 0193-453-acceptance.md and 0193-upgrade-bot-ledger.json
Revision: operator correction, 2026-11-01; no runtime allowance created.

## Problem Statement

The operator uses modified Codex and needs it to keep up with official releases without personally maintaining merges. Most patch application should be deterministic; a coding agent should finish semantic conflicts, adapt changed upstream APIs and fix compilation failures when mechanical replay is insufficient.

The current effort has delivered supporting upgrade-controller code but has not delivered a qualified modified 0.166 package. Repeated cold compilation, host-tool drift and bounded attempts consumed the execution window. Passing intermediate tests, controller fixtures and closed supporting tickets have not established that the upgrade works.

## Solution

Deliver a practical upgrade loop: discover an official stable release, apply the maintained patch stack mechanically, use semantic repair where necessary, build the complete modified package, verify required behavior and make it available for future launches in the configured opt-in scope. Preserve the previous working build and existing sessions.

First finish the actual 0.166 port and produce a working identifiable package in disposable WSL. Use that successful procedure as the reference for the automation, then demonstrate the existing public upgrade-job interface performing the same journey. Direct completion is a delivery milestone and source of implementation evidence; it does not substitute for automated acceptance. Do not build a second orchestrator or require the operator to resolve routine conflicts, restart cold builds or approve ordinary repair steps.

## User Stories

1. As an operator, I want modified Codex to follow official stable releases, so that local features do not strand me on an old version.
2. As an operator, I want official release discovery, so that upgrades do not depend on my noticing a release.
3. As an operator, I want persistent opt-in scope, so that automatic selection happens only where I enabled it.
4. As an operator, I want deterministic patch application first, so that uncomplicated upgrades avoid semantic worker cost.
5. As an operator, I want ordinary three-way merging, so that independent upstream changes combine mechanically.
6. As an operator, I want a coding agent to resolve semantic conflicts, so that I do not have to rebase the patch stack manually.
7. As an operator, I want the agent to adapt changed upstream APIs, so that compiler errors are handled as normal upgrade work.
8. As an operator, I want repair to continue through actual build feedback within the configured allowance, so that the bot completes the merge rather than merely reports conflicts.
9. As an operator, I want local feature behavior preserved, so that an upgrade cannot silently replace modified Codex with stock Codex.
10. As an operator, I want evidence before retiring an upstreamed patch, so that the maintained stack shrinks without losing features.
11. As an operator, I want generated artifacts and lockfiles reconciled, so that the package represents a complete port.
12. As an operator, I want a complete working 0.166 package first, so that the present work produces a usable result.
13. As an operator, I want automation to reproduce the successful porting procedure, so that subsequent upgrades need little involvement.
14. As an operator, I want valid compiler and dependency work reused, so that successive stages and authorized recovery do not repeatedly pay for cold builds.
15. As an operator, I want cache storage bounded and reclaimable, so that keeping upgrades current does not fill my disks.
16. As an operator, I want source, toolchain and build inputs identified, so that reused artifacts cannot qualify the wrong candidate.
17. As an operator, I want independent behavioral review, so that semantic repairs cannot pass by deleting features or weakening tests.
18. As an operator, I want tests of the actual package, so that fixture success cannot stand in for a working modified executable.
19. As an operator, I want disposable installation qualification, so that my working credentials, sessions and services remain protected.
20. As an operator, I want exact build identity visible, so that I can distinguish official, modified and retained builds.
21. As an operator, I want successful builds selected for future launches, so that routine upgrades do not require a cutover ritual.
22. As an operator, I want existing sessions pinned, so that upgrading future launches does not interrupt current work.
23. As an operator, I want a compatible previous package retained, so that I can recover from a bad candidate.
24. As an operator, I want explicit progress, failure and intervention notices, so that work never stops silently.
25. As an operator, I want one easy disable control, so that I can stop owned upgrade work and prevent promotion.
26. As an operator, I want sensible explicit resource limits and measured build costs, so that runaway agents are prevented without routine operator friction.
27. As an operator, I want restart and handoff to preserve valid work and cumulative accounting, so that continuing does not require resource-reset rituals.
28. As an operator, I want a precise terminal reason and recoverable work when a real limit is reached, so that recovery can address the cause instead of blindly repeating the attempt.
29. As an operator, I want the same upgrade outcome through CLI, API and MCP, so that each surface controls the same job.
30. As an operator, I want completion judged by a working upgraded build, so that supporting infrastructure and test counts cannot be mistaken for delivery.

## Implementation Decisions

- Retain the existing upgrade-job boundary, account/build controller, patch source, package staging, qualification, notices, selection and rollback owners. Tighten their integration instead of adding a parallel pipeline or account store.
- Treat semantic completion as normal execution: inspect unresolved merges, edit code, compile, diagnose actual errors and iterate within explicit cumulative limits. A conflict or compiler error alone is not an operator approval gate.
- Sequence delivery around observable outcomes: complete and launch the actual modified 0.166 package; capture the successful procedure and required inputs; reproduce it through the assembled public job path; qualify future-launch selection and rollback. Existing valid controller work is reused.
- Maintain reviewable feature intent for each patch. Mechanical application and semantic edits must preserve it. Retire a patch only when upstream equivalence is demonstrated. Changed source or tests invalidate affected review and qualification.
- Use an independent reviewer for behavioral preservation and test changes. Review must evaluate actual source and feature intent; successful worker exit or a generated report alone is insufficient.
- Identify source revision, patch state, generated outputs, toolchain, target, build profile and consequential compiler inputs. Reuse only compatible artifacts through supported build tooling. Cached generation and compilation must be labelled as reuse, not falsely reported as fresh execution.
- Use a declared bounded compiler cache across verification, packaging and compatible authorized continuation. Keep it outside disposable job scratch space. A terminal hold must not unconditionally destroy valid reusable compilation. Bound cache size and retention, make cleanup inspectable, and preserve rollback packages and evidence. Cache loss is recoverable by rebuilding; a cache is not acceptance evidence.
- Preserve isolated, identified host tools or revalidate their identity before use. Report host prerequisite drift explicitly without silently changing the candidate, weakening checks or repeatedly starting coding workers to fix an environment problem.
- Set practical execution limits from observed cold/warm build costs and separate semantic effort, compilation, cache storage and cleanup. Keep limits explicit and cumulative. No silent renewal, deadline reset, governor insertion or revival of expired jobs. When the actual allowance is exhausted, stop owned execution, explain the remaining work and retain reusable artifacts for a separately authorized continuation.
- Persist enough state to reconcile an interrupted stage and reuse valid work without duplicate submissions or promotions. A restart or handoff is not a new full allowance. Unknown stage results remain unknown until reconciled.
- Bind the complete immutable package and qualification to exact source, tests, patch intent, toolchain and configuration identities. Claim only supported native behavior; retain unresolved capability boundaries explicitly.
- Qualification uses disposable WSL, actual launcher/account wiring and synthetic histories. Designated authenticated test accounts are used only for metadata checks; qualification canaries submit zero provider model turns. Authorized coding/review contexts are source-maintenance work and are accounted separately.
- Promote atomically for future launches only after current review, compatibility, qualification, enabled-policy and target checks. Existing clients remain pinned. Retain supported compatible rollback and refuse incompatible history downgrades clearly.
- Publish durable phase/status and attributable notices through the existing surfaces. A limit, authentication failure, disable, uncertain result or failed notice delivery must be explicit. Disable fences promotion and terminates only owned work.
- Run applicable validation locally under the existing GitHub CI cost policy. Report source integration, direct package completion, automated acceptance and production activation as distinct outcomes.

## Testing Decisions

- Prefer one primary seam: request an upgrade through the existing public durable upgrade-job interface and observe the exact modified package, its installed behavior, scoped selection, preserved prior build and rollback. CLI/API/MCP share this owner; they are not separate engines to qualify independently with invented fixtures.
- Retain the previously operator-confirmed public job boundary. The refinement makes successful complete-package delivery the principal acceptance signal; a seam-check question was presented during this revision. An additional unattended next-release demonstration is not assumed without an operator decision.
- First reproduce the real 0.166 port using actual source, actual semantic fixes and actual build tools. Retain compiler failures and final successful commands. Launch the complete package and inspect its identity before claiming this milestone.
- Then demonstrate the assembled automated path on official 0.166 and the maintained feature stack. A package manually substituted into a job, a precomputed success report or a fixture executable cannot satisfy this demonstration. Reuse of declared valid inputs and compiler artifacts is allowed and must remain visible.
- Retain focused deterministic tests only for consequential behavior: clean replay without a coding worker; semantic conflict/compiler repair reaching a build; missing-feature/review rejection preserving the working version; stale-cache invalidation; reuse across compatible stages/authorized recovery; disable and cumulative-limit preservation. Assert external outcomes instead of private methods, journal layouts or test counts.
- Use existing build/account acceptance, package-identity checks, native capability probes, installed history/reconnect journeys and selection/rollback regressions as prior art. Do not create another test framework or broad fixture campaign.
- On the exact complete modified package, verify claimed native capabilities, synthetic default/account/shared history visibility and resume, account ownership, reconnect, failed-start preservation and compatible rollback. Report unsupported recurrence, raw orphan-output and HF-20 boundaries explicitly rather than passing them by proxy.
- Measure cold and warm elapsed time, coding/review usage, compiler concurrency, cache occupancy/reuse and final owned processes. Evidence must show whether compilation progresses and where time is spent, not merely whether a wrapper remains running.
- Final acceptance requires: a complete identified modified 0.166 package; actual successful launch and claimed capability checks; the public bot producing and qualifying that package from official source plus the maintained stack; scoped future-launch selection; previous-session pinning and compatible rollback; visible terminal outcome and clean owned-process census. Preserve the current working build on every failure.
- Applicable local checks and one final bounded review/remediation pass remain required. Supporting tests do not replace end-to-end acceptance. No paid hosted CI, production credential/history copying or provider-model canaries.

## Out of Scope

A new general-purpose controller, competing orchestrator or account store; unrelated fixture expansion; running-daemon replacement; business/provider experiments; automatic resumption of old goals; silent governor activation; renewal of expired allowances; production installation or activation by this specification; production credential/history copying; model-turn qualification canaries; broader account migration; arbitrary upstream writes. This specification does not claim that unbuilt recurrence or raw orphan-output/HF-20 capabilities already work.

## Further Notes

This revision sharpens existing specification #444; it does not start a competing program. Plan0193 remains the execution authority. Children #447–#452 retain their integrated/validated/closed outcomes unless concrete regressions invalidate them. #453 remains blocked/open because installed 0.166 acceptance has not passed. Do not close it based on this document.

Observed baseline: the corrected 0.166 source is retained; actual protocol tests4passed/1ignored and app-server TUI-health3passed. The last bounded retry reached its deadline during turn-admission compilation. Independent review, complete package, installed qualification and promotion were not reached. Owned cleanup completed and selected0.165 remained intact. This is partial evidence, not success or proof that the port is infeasible.

Definition of done: the operator can obtain and launch the complete modified0.166 build, and the existing bot demonstrably performs deterministic patching with semantic completion through package qualification and configured future-launch selection, retaining a working rollback. Exact evidence and remaining boundaries are recorded. Production activation remains separate.

Next bounded planning action: reconcile unfinished #453 work with the measured build/cache blocker, identify the minimal implementation changes and practical execution envelope, then complete the real port before expanding supporting infrastructure. This specification grants no new runtime allowance and does not revive any expired attempt. #369 remains broader coordination; #413 running-daemon recovery and #380 production activation remain separate.

<!-- idempotency:codex-wake-autonomous-upgrade-bot-spec-20261031 -->
<!-- revision:working-modified-build-first-20261101 -->


## Approved delivery graph | 2026-11-01

#455 direct complete166 package (primary; no blockers) and #456 compatible
compiler reuse (cache456; no blockers) start in parallel. #457 automated
patch-to-package is blocked by both; existing #453 final installed qualification
is blocked by #457. Native tracker edges are published. Existing447–452 retain
closure. One final broad review and one TDD findings pass remain after acceptance.
Old native jobs remain expired/frozen; new direct455 work does not mutate them.


## Current State

Delivery accepted and closed2026-11-01: #455/#456/#457/#453 are closed. The
actual public semantic job produced and independently reviewed complete166;
fresh installed A-B-A/all11 native checks, future selection, old-session pinning,
public future launch/reconnect and actual compatible rollback passed in WSL.
See [native acceptance](../evidence/issue0444/native453-acceptance.md).

One final broad review and one bounded TDD findings pass resolved twoP2 issues;
[review evidence](../evidence/issue0444/final-review.md) identifies frozen base,
source commits and passing local checks. No second review or allowance renewal.
Final disposable selection is retained165 after deliberate successful rollback;
qualified166 remains available. Production and the separate #413/#380/raw-orphan/
recurrence/HF-20 boundaries remain outside this closed delivery. Older baseline
and failed-run text above is retained history, superseded by this current state.
