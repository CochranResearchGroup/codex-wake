# Autonomous upstream Codex upgrade bot

State: PLANNED
Owner: primary upgrade-bot coordinator
Specification: https://github.com/CochranResearchGroup/codex-wake/issues/444
Related work: #369, #377, #393, #413
Design: confirmed by operator, 2026-10-31; acceptance seam confirmed.

## Problem Statement

Frequent upstream Codex releases make manual maintenance of the modified build expensive. A deterministic patch replay can fail even when most changes merge mechanically. The operator needs a bot that resolves semantic conflicts, proves required capabilities, and makes qualified builds available without repeated intervention, while preserving a working version and exposing every failure or intervention.

## Solution

Provide a persistently opt-in upgrade bot using existing build, staging, selection and rollback machinery. It discovers official stable releases, creates an isolated candidate, attempts deterministic replay and three-way merging, and delegates necessary semantic repairs to a bounded coding worker. An independent reviewer evaluates behavioral preservation. The bot builds and qualifies the exact package in disposable WSL, then automatically selects qualified builds for future launches within its configured target scope. Existing sessions remain pinned. One disable control stops owned work and prevents promotion; durable job state and visible notices explain progress and failures.

## User Stories

1. As an operator, I want automatic official stable-release discovery, so that upgrades do not depend on an agent handoff.
2. As an operator, I want persistent opt-in configuration, so that the bot's operating scope is explicit.
3. As an operator, I want stock and modified build identities retained, so that upgrades cannot silently substitute a stock backend.
4. As an operator, I want deterministic patch replay attempted first, so that simple upgrades use no semantic repair worker.
5. As an operator, I want autonomous semantic conflict repair, so that upstream changes do not routinely require manual rebasing.
6. As an operator, I want patches retired when upstream demonstrably supplies equivalent behavior, so that the maintained patch set stays small.
7. As an operator, I want independent review of repairs and test changes, so that the worker cannot declare success by weakening requirements.
8. As an operator, I want missing capabilities to reject a candidate, so that upgrades preserve the modified product.
9. As an operator, I want complete immutable package provenance, so that qualification identifies the exact executable set.
10. As an operator, I want disposable installed-path qualification, so that working credentials and histories remain protected.
11. As an operator, I want metadata-only checks using designated authenticated test accounts, so that account switching and reconnect are tested without model turns.
12. As an operator, I want authentication expiry reported explicitly, so that it cannot cause hidden retries or credential substitution.
13. As an operator, I want qualified builds automatically selected for future launches, so that routine upgrades require no cutover ritual.
14. As an operator, I want active sessions pinned to their builds, so that promotion does not interrupt ongoing work.
15. As an operator, I want a retained compatible rollback, so that a failed candidate cannot strand new launches.
16. As an operator, I want durable CLI/API/MCP job status, so that every surface reports the same outcome.
17. As an operator, I want visible notices in registered operator sessions, so that held jobs and promotions are never silent.
18. As an operator, I want bounded repair and build resources, so that the bot cannot run away.
19. As an operator, I want disable to stop owned workers and promotion, so that deactivation is immediate and easy.
20. As an operator, I want crash recovery to reconcile completed or uncertain stages, so that restarts do not duplicate effects or reset budgets.
21. As an operator, I want superseded releases recorded and the newest stable processed next, so that the bot does not accumulate an unnecessary backlog.
22. As an operator, I want retained packages separated from disposable caches, so that storage cleanup preserves rollback and evidence.
23. As an operator, I want the full 0.166 port exercised first, so that acceptance includes genuine upstream conflicts.

## Implementation Decisions

- Reuse the Wake-owned account/build controller and existing stage, selection, archive and rollback primitives. Do not add a competing account store or launcher owner.
- The public upgrade-job interface is the principal seam, shared by CLI/API/MCP. Discovery, repair, build and qualification executors sit behind that interface; exact verb spelling follows the controller command tree during implementation.
- Persist job identity, release/source/package digests, original scope, policy generation, cumulative usage/deadline, worker ownership, review findings, qualification receipts, promotion state and uncertainty. Status distinguishes queued, discovering, applying, repairing, building, reviewing, qualifying, promoting, succeeded, held, failed, stopping, disabled and superseded outcomes; terminality and allowed transitions are explicit and versioned.
- Discover official stable releases only. Deduplicate release/policy/patch identities. Finish the current bounded attempt before processing the newest available stable release; preserve skipped-release history. A failed unchanged candidate must not acquire a fresh budget merely because polling repeats.
- Defaults: one candidate at a time, three semantic repair attempts, two hours total per release job, two compiler jobs, and 24 GiB temporary build storage. Limits are visible and configurable. Retries, restarts and handoffs preserve cumulative usage. Budget exhaustion produces a durable reason and retains the selected working build.
- Deterministic replay includes ordinary application and three-way merge with explicit unresolved-conflict detection. Exit status alone is insufficient: a check may emit conflict diagnostics despite returning success. Regenerate derived protocol bindings/schema and reconcile lockfile changes before build qualification.
- Semantic repair may rewrite or retire patches only with evidence of preserved required behavior. Bind independent review to candidate and test digests; further edits invalidate affected review/qualification. The worker cannot waive capabilities or weaken acceptance to obtain a pass.
- Required behavior includes scoped MCP reload, durable notices, caller/accounting continuity, orphan-output handling, exact TUI responsiveness and the recovery capabilities claimed by the selected manifest. Claimed unsupported behavior is not silently accepted.
- Qualification uses the exact immutable complete package in disposable WSL, actual launcher/account wiring, synthetic histories and designated disposable authenticated accounts. Authenticated canaries are identity/switch/restart/reconnect metadata only: zero provider model turns. Scripted local-provider and provider-free fixtures remain separately identified evidence.
- Promotion is an atomic tenant/target-scoped selection for future launches after current compatibility, review and qualification checks. Revalidate enabled policy, target identity, generations, package digest and scope immediately before selection. Existing sessions and shared daemons are not replaced by this bot.
- Preserve known-good complete packages and schema-compatible rollback. An incompatible downgrade must refuse clearly rather than mutate histories. Qualification does not imply all future schemas permit rollback.
- Disable is durable, immediately fences new stages and promotion, then cleanly terminates only owned repair/build workers and retains evidence. Define crash-safe reconciliation for a selection committed just before disable; report its actual order rather than claim it never happened. No unrelated session is stopped.
- Publish durable activity through CLI/API/MCP plus attributable notices in registered operator Codex sessions. Held/failure/promotion notices are immediate; delivery failure is observable and does not erase the job state. Notices do not submit model turns. No external messaging service is included.
- Temporary build storage is monitored independently from retained packages/evidence and shared dependency caches. On limit, stop owned work and report; never delete rollback packages or unrelated cache contents to make room.
- Manual resource monitoring remains the mode. Updater-specific explicit limits neither enable the governor nor renew any external grant.

## Testing Decisions

- The operator confirmed the public durable upgrade-job boundary, with injected release, worker, build and qualification executors for deterministic regressions and a real installed disposable WSL acceptance of the complete 0.166 port.
- Test externally visible outcomes, preserved build selection, immutable provenance, worker ownership, notices and cumulative budgets rather than private implementation layout.
- Reuse controller build/account acceptance, existing staged-upgrade failure and tenant-selection/schema regressions, native capability acceptance and installed recovery/rollback journeys as prior art.
- Cover clean application, three-way merge with unresolved conflicts even on exit zero, semantic repair success/failure, redundant-patch retirement, missing capabilities, review rejection, generated-artifact drift and package mismatch.
- Cover worker death, process restart, delayed results, release deduplication, newer-release arrival, retry budget preservation, deadline uncertainty, disk exhaustion, disable versus stage/promotion races, and uncertain selection reconciliation.
- Cover test-account authentication-needed with no production credential fallback and zero unintended model requests; switching/restart/reconnect preserve owning account and histories.
- Qualify future-launch selection, existing-session pinning, failed-start preservation, compatible rollback and clear incompatible rollback refusal. Finish real acceptance with an owned-process/resource census.
- Run applicable checks locally; record commands, results, source/package identities and environment differences. Do not enable paid hosted CI.

## Out of Scope

Production activation by this planning task; running-daemon replacement; automatic recovery of old goals; governor activation; grant renewal; production credential/history copying; model-turn canaries; external messaging; business/provider experiments; arbitrary upstream repository writes; unrelated account migration.

## Further Notes

Current State: interview complete; existing discovery/staging/selection primitives exist. The durable autonomous orchestrator and semantic repair-to-promotion loop are not implemented. This document extends earlier explicit-activation policy only for a configured opt-in future-launch scope; it does not silently alter installed policy.

Reconciliation: #369 remains broader coordination. Closed #377 retains its accepted staging/rollback outcome. The Wake-owned controller delivered in #393 supplies account/build surfaces. Open #413 gates running-daemon recovery; it is not a prerequisite for a bot that leaves running daemons untouched. Production profile activation remains separately gated by #380. Existing parents are not edited or closed by this specification.

Baseline: official 0.166 commit 6ff1e1ca3b30fc8b914720681fcf5fe62e95f856. Narrow 42-path source/test replay has README conflict after three-way merge; larger 69-path recovery/health replay additionally conflicts in turn-admission code and tests. Generated bindings and lockfiles were excluded from that preliminary check; compilation/runtime acceptance remains outstanding. That check is input evidence, not upgrade qualification.

Acceptance criteria: the public job path discovers, repairs, builds, independently reviews, qualifies and selects a complete 0.166 candidate for future disposable launches; required capabilities, budgets, disable fencing, account isolation, notices and rollback behavior pass named regressions. Source integration and production activation remain separate outcomes.

Definition of done: approved child outcomes integrated with local checks, an immutable 0.166 installed acceptance receipt, review disposition, rollback and teardown evidence, truthful remaining boundaries and reconciled execution records. This planning artifact alone is not delivery.

Critical path: durable job slice → semantic worker and disposable qualification → qualified selection → integrated 0.166 acceptance. Independent low-conflict tracks after the job contract: repair worker, qualification executor and scheduled discovery. Primary coordinator owns integration.

Next action: approve the proposed vertical ticket graph, then publish children and their blocking edges.

<!-- idempotency:codex-wake-autonomous-upgrade-bot-spec-20261031 -->
