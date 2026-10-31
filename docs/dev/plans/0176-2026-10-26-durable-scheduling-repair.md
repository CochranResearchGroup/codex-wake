# Durable scheduling repair / #360

State: OPEN
Owner: primary / ecochran76
Branch: fix/durable-scheduling-360
Baseline: origin/main1a315643c64c332d2ada289474c46bde42d50b63
Authority: operator asks to fix #360 against existing HF-13 durability specification and HF-20 daily occurrence work; wakes may be scheduled throughout supported durability span, independent of creating session/execution allowance. Preserve resolved HF-01 decisions; do not invent catch-up/overlap defaults.

Scope: reproduce the retained24h failure, verify due/expiry semantics, repair monitored-root/control wiring through supported host paths, and qualify exact-self schedule/inspection/cancellation/restart using fixture transport before reconciling existing live intent. Preserve original key, prompt, origin and deadlines. No duplicate reviews or unrelated queued dispatch; business review remains read-only and no block mutations.

Non-goals: shared native restart, governor activation, campaign renewal, guessed clocks, automatic Cloudflare/WordPress effects, second recurrence authority.

Acceptance: agent-facing future schedule has concrete due time, independent monitor ownership, usable scoped controls and faithful restart/lifetime semantics. Supported horizon and recurrence implementation status remain explicit; no persistence-as-delivery claims. Existing native persistent intent is reconciled rather than replaced.

Diagnosis loop: python3 /tmp/t360-repro.py reports existing ID/status/due/monitor and asserts armed monitored24h request. Qualified red retained /tmp/t360-repro-red-qualified.log; first probe used check_output on monitor's expected nonzero unavailable status, corrected to parse its diagnostic JSON.

Ranked hypotheses: missing selected-root coverage; qualified time not reaching/recovering resident MCP; TTL/due coupling truncating long-delay eligibility. Missing root/action grants is separately observed. Inspect each without broad activation of queued work. Current state: qualified red, source discovery started.

## Current State

Source repairs are integrated through PR361 (`02b68e8`) and PR362
(`e58d3a9`); terminal evidence reconciliation is integrated through PR363
(`65c4cca`). This plan remains OPEN because the expired shared-idle refresh
provided no successful resident catalog, scoped control or resource-continuity
qualification. The remaining supported connection refresh requires its own
existing authority; no retry, restart or recurrence acceptance is implied.
The dated observations below remain historical evidence, not current runtime
readbacks.

## Verified cause and first remediation

Root has no registered monitor and native MCP arguments omit wake-control host grants. Qualified source red additionally finds misleading registration metadata: valid original clock anchors saved but due display remains null and time reason is hardcoded unavailable. There is no24h scheduling limit; TTL already starts after due. Fixed receipt projections and explicit monitored/armed state, durable-loop distinction, owner-held readback, no-dispatch pending timer reconciliation, and agent control inventory dates. Public red/green regressions cover24h and3650d, late monitor arrival retaining oneID, exact-scope inventory/cancel, and original timer reconciliation without resubmission.

Live no-dispatch reconciliation at originalID now reads due2026-10-27T01:21:37.949431Z, expiry2026-10-28T01:21:37.949431Z. Original idempotency key, scheduling_intent, target, prompt, policy and attempts are byte/semantic preserved against private backup. Original target is exact SoyLei thread; no dispatch occurred. Original clock is qualified, so a missing clock alone is not the live cause.

Host activation scope is pending one async operator question: lifecycle root contains SoyLei and an unrelated older LitScout intent. The ticket prohibits enabling unrelated queued work. Preserve both; do not treat silence as permission. Source repair and fixtures continue independently. HF-13 is implemented; HF-20 still records recurrence-specific choices as its own unimplemented work, not a license to claim an installed native cron engine.

Validation: first focused34PASS7.025s; expanded59 run first found an inadvertently removed existing datetime import, restored with failure retained /tmp/t360-focused-full.log; successor59PASS8.659s. Red/green logs /tmp/t360-{future,monitor,reconcile,controls,owner}-{red,green}.log. Full required final checks pending.

## Host scope resolved without widening authority

Read-only eligibility using qualified clock proves the unrelated LitScout follow-up expired2026-10-25T18:19:10.335137Z. Its dispatch cannot be admitted, so the earlier scope question is unnecessary; no unanswered approval was inferred. Full active-record inventory contained only the two known intents. Registered native-lifecycle with the existing supervisor. Live readback: monitor_ready=true, supervisor source, loop mode; SoyLei pending/not_due attempts0; LitScout failed/expiry_reached attempts0. Both original grants/origins retained; no model/provider call or review dispatched.

Added optional private host control configversion2 with native_self roots/list/cancel. Existing common permission context qualifies exact creator+recipient, avoiding recurring per-UUID setup while preventing peer cancellation and root-wide actions. Public MCP test first red policy_denied, then intermediate fixture lacked the real root's adopted permission context (returned empty list); configured the fixture's public PermissionStore as the production root and obtained green. Missing native context, forged caller, peer ID, all-root and pause scopes refuse; all-cancel selects only own wakes.

Selected SoyLei thread is currently idle, but actual thread/mcpServer/reload dry-run is unsupported by the installed native daemon. No native restart or implicit shared fallback attempted. Existing MCP connections need their supported refresh path; fresh process qualification is separate from resident connection proof.

Source/public60-case selection PASS; curated evidence docs/dev/evidence/issue0360/acceptance.md. PR361 carries integration. Source check against HF-13/#360 confirms due/TTL and owner invariants, explicit version1 compatibility/version2 opt-in, peer filtering and effect-lock rechecks. Supported future calendar is explicit, not a24h limit. Final CI and installed connection cutover remain pending.

PR361 merged02b68e8 with identical CI-qualified treefad5868; full CI40265950701 PASS both Python versions,1728tests/1skip plus wheel gates. An install-identity follow-up advances the development version to0.22.0.dev1 so the existing mcp_catalog resource proof can distinguish a refreshed resident connection from olddev0. No behavior or wake schema change in this follow-up; exact catalog/skill and goal-continuity readbacks remain required.


## Reconciled deployment outcome — 2026-10-26

State remains OPEN; source repairs are integrated through PR361 and PR362. Main e58d3a9701a34e39f7d1ded2668a4f15a1cc18d4 is installed as0.22.0.dev1-e58d3a9. Both full CI matrices passed1728tests/1skip. Original SoyLei timer is monitored and preserved in place (due2026-10-27T01:21:37.949431Z, expiry24h later, attempts0). No original resubmission or expired LitScout revival occurred.

The existing shared-idle refresh issue360-shared-mcp-upgrade-dev1 expired at its fixed deadline without attempting reload. Terminal receipt contains no successful resource/goal-continuity qualification. Read-only native catalog remains0.21.2; actual agent-facing list still policy_denied. No retry, renewed allowance, native restart or governor activation. The callback delivered this continuation once; it does not establish resident refresh or daily recurrence acceptance. Own terminal observer stopped/disabled after reconciliation.

The remaining acceptance gate is a supported, authorized native connection refresh followed by actual catalog0.22.0.dev1, caller-scoped list/cancel and resource/goal-continuity proof. Do not automatically retry the expired intent. HF-20 recurrence remains separate. See docs/dev/evidence/issue0360/acceptance.md for exact boundaries and terminal evidence. No source changes were required in this continuation; this is an evidence-only reconciliation.
