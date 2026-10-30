# Cross-host controller specification

Status: IMPLEMENTING; specification accepted and implementation ledger authoritative for child delivery. Canonical specification: https://github.com/CochranResearchGroup/codex-wake/issues/393

Owner: controller coordinator. Scope and acceptance are below; done means accepted specification and reviewed implementation-ticket graph, not production deployment.

## Problem Statement

Operators need one coherent controller for coding agents across Windows, WSL and remote hosts. Split Wake/Profiles ownership, opaque runtime/build identity, stale tab observations and interface-specific control create friction and unsafe ambiguity. A disconnected caller must not duplicate work; handoff must not require resource-reset rituals. Controller policy and interventions must be visible and easy to deactivate.

## Solution

Codex Wake owns accounts/configuration/build selection, durable logical-agent inventory, cross-host operations, presentation organization, health and structured flows. Host-local execution authorities serve authorized clients through CLI, API and MCP with the same semantic contracts. Initial cross-host delivery includes SSH-backed access, directly authenticated HTTP/WebSocket, OAuth MCP, Windows/WSL/remote qualification and Codex Bots as an initial consumer. Deliver dependency-ordered increments: consolidation, cross-host control/health, flows, Grok.

## User Stories

1. As an operator, I want one package/configuration owner so competing launchers cannot silently change my environment.
2. As an existing Profiles user, I want compatibility commands and migration guidance.
3. As an operator, I want common skills/settings/MCP definitions with explicit scoped overrides and effective-value provenance.
4. As an operator, I want concurrent named accounts without copying their credentials or sharing private runtime state.
5. As an operator, I want to read permitted records across accounts and resume through the owning account/environment.
6. As an operator, I want visibly identified stock/modded immutable builds side by side.
7. As an operator, I want staged upgrades, pinned running sessions and explicit promotion/rollback.
8. As an operator, I want host and execution-environment identities distinct, including Windows and each WSL environment.
9. As a caller, I want equivalent operations through CLI/API/MCP on capable surfaces.
10. As a caller, I want SSH and OAuth-authenticated direct access with reusable scoped grants.
11. As an operator, I want searchable names/UUIDs to reveal accounts, context, bindings and fresh independent state dimensions.
12. As a caller, I want selectors pinned to exact identities so tab renumbering cannot redirect pending work.
13. As an operator, I want Byobu/psmux and structured stdio attachments organized without changing conversation ownership.
14. As a caller, I want a target's final answer returned to stdout or my agent session, with correlation and optional streaming.
15. As a caller, I want wait timeout/disconnect to preserve work and permit retrieval without replay.
16. As a Bots consumer, I want exact-TUI-loop responsiveness evidence that preserves drafts, history, queues and private input.
17. As an operator/model, I want clear controller policy, notification, intervention and deactivation state.
18. As an operator, I want bounded recovery only under explicit policy, evidence, cooldown and attempt ceilings.
19. As an operator, I want deactivation in one command without enrollment/reset rituals.
20. As a flow author, I want one versioned definition for declarative forms, SDK composition and inspectable agent proposals.
21. As a flow author, I want branches, foreach, parallel/join and waits with explicit typed outcomes.
22. As a flow author, I want foreach in new sessions, forks from a common pinned checkpoint, or successive prompts in one conversation.
23. As a flow author, I want deterministic Boolean evaluators and semantic turns calling reusable nested semantic functions.
24. As a flow author, I want optional token/time limits per iteration and overall, with cumulative nested accounting.
25. As a flow author, I want bounded safe retries, explicit uncertain effects and durable cancellation outcomes.
26. As an operator, I want Grok structured-runtime integration after the Codex baseline, with honest capability gaps.

## Implementation Decisions

### Resource model and operation boundary

Logical agents link explicitly related conversations/runtime instances; native identities/provenance remain intact. Stable Wake IDs bind scoped host/environment/provider/account/process/connection generations. Presentation attachments are independent resources. Inventory reports activity, responsiveness, attachment and control independently with timestamps and unknown/unsupported states. Resolve selectors once; reject ambiguity or stale replacement. A binding grants no authority.

One shared operation service owns validation, authorization, durable admission, execution correlation and results. Adapters translate presentation/transport only. Public operation envelopes include schema revision, operation/correlation/idempotency IDs, authenticated caller, resolved target/generation, authorization reference and typed input. Results distinguish submission, execution, delivery and acceptance; errors include ambiguous/stale/unauthorized/unsupported/unknown/uncertain-effect. Retries with the same idempotency key return/reconcile the original operation; changed inputs conflict. Structured control is preferred; terminal input fallback requires visible explicit bounded policy.

Organize commands by resources: hosts/environments, accounts/configuration/builds, agents/conversations/runtimes, tabs/attachments, wakes, operations/results, flows and policies. Concrete verbs and schemas must be enumerated consistently in implementation contracts; user examples are illustrative. Existing wakes, claims, briefs, jobs, attention, acceptance and resource-accounting owners remain authoritative and integrate through adapters rather than duplicated stores.

### Ownership, migration and builds

Wake absorbs Profiles package/configuration ownership; old commands become compatibility aliases. Shared base configuration accepts explicit host/provider/account overrides and reports provenance. Native credential stores remain in their execution environment; caller OAuth is separate. Cross-account permitted history is searchable/readable, resumed only through its owner. Migration inventories indirect links and competing writers, previews effects, validates disposable candidates and retains explicit rollback before separately authorized activation. Immutable named builds are pinned per runtime; promotion affects future launches. Existing activation follow-up and closed-tab/reboot recovery retain their own unresolved evidence boundaries.

### Cross-host authority and remote access

Each operation has one execution authority. Register hosts and environments; authorized fleet inventory retains stale/offline observations. Offline mutation queueing is explicit, preserving pinned target, authority and expiry. Reconnect does not create work or renew allowances.

API/MCP share one Wake protected resource with exact issuer/audience validation. OAuth uses identifiable owner and service/client principals, reusable operation grants constrained by target scopes, and independently revocable grants. Separate observation, input/control, recovery and administration. SSH principals map explicitly to the same checks without automatic owner privileges. General on-behalf-of delegation is deferred. Token rotation/reconnect reauthenticates and explicitly rebinds existing operations; transport identity does not establish TUI generation. Revocation blocks new privileged steps and reconciles/requests cancellation of work solely owned by the revoked grant, preserving uncertain outcomes and unrelated work. Trusted ingress must preserve verified principal context and reject untrusted identity headers; provider credentials never transit controller clients.

### Health, notifications and recovery

Bounded on-demand and configurable scheduled read-only checks expose deadlines and freshness. Bots positive evidence must originate in the exact controlling TUI loop, bound to conversation/account/backend/channel/process birth/boot/connection generation. Background listeners, daemon metadata, queue receipts and notices are insufficient. Loop-stalled/background-healthy must fail the positive test. Checks preserve private input/drafts/history/queues and create no model turn, notice append or resume. Repeated unknown yields visible suspected-unresponsive/escalation, never automatic restart authority.

Observation is default. Explicit recovery policies declare evidence, action sequence, scope, cooldown and attempt ceiling; ambiguity/exhaustion stops escalation visibly. Model-readable status plus persistent operator status and clear controller notifications in modded Codex cover activation/action/reason/outcome/deactivation. Notifications are distinct from read-only probes and not proof of consumption. One-command scoped deactivation immediately prevents new automatic actions, reconciles in-flight effects and preserves observation/accounting; no reset/enrollment ritual.

### Durable flows and conditions

One versioned typed definition is consumed by declarative/SDK/proposal interfaces. Runs pin versions and memberships; edits affect future runs unless explicit checkpoint migration is admitted. Foreach explicitly selects new session, fork-from-pinned-checkpoint or sequential prompts; unsupported modes are rejected before effects. Default join waits for siblings then reports aggregate failure, preserving individual outcomes. Only declared join conditions release dependents.

Deterministic predicates and semantic turns return typed true/false with separate unknown/error/timeout. Semantic functions are named/versioned with typed inputs/results, declared tools/effects and nested calls. Conditions default to observation; actions require explicit inherited authority and appear in traces. AND/OR short-circuit left-to-right; explicit parallel evaluation declares effect/join behavior. Unevaluated operands remain marked. Unknown/error must never be coerced to false; default propagation suspends dependent branching pending explicit handling.

Optional token/time limits apply to iterations and overall structures; child limits tighten parent limits and all nested/retried work charges cumulative totals. Finite call-depth or call-count bounds prevent unbounded semantic recursion. Unsupported exact metering/enforcement is disclosed before execution; estimates require explicit policy. Limit reached stops new scoped work and requests cancellation, recording confirmed/uncertain outcomes. Retries are opt-in, bounded and safe/idempotent; uncertain effects reconcile first.

Response-requested waits for final answer by default; supports streaming and durable handle/retrieval. CLI answers use stdout/progress stderr; agent replies correlate to the initiating binding. Timeout ends waiting, not target work. Reconnect delivers only to the original authorized binding or explicit successor, with duplicate suppression. Flow cancellation stops new scheduling and requests cancellation of active owned work; no implied rollback. Budgets and permissions survive handoff/replacement.

## Testing Decisions

Primary seam is the public operation service exercised through equivalent CLI/API/MCP adapters, with injected host/provider/clock/effect boundaries. Assert externally visible state, effects, receipts and authorization rather than internal calls. Reuse existing managed-agent, tab-target, wake-control, native-delivery and daemon integration-test patterns; preserve their existing authority boundaries.

Consolidation gates: concurrent accounts, effective config, permitted history/resume ownership, stock/modded identity, migration preview, indirect-link/writer detection and rollback. Cross-host gates: disposable Windows/WSL targets, callers from both sides and separate remote host, SSH plus direct OAuth/API/MCP, Byobu/psmux and structured paths, stale generation, revocation, offline/reconnect/no duplicate work. Bots gates: exact-loop negative test, private-input/draft/queue invariance, PID reuse/wrong target/expired challenge/concurrent bounded requests and actual packaged Wake-to-Bots boundary.

Flow gates cover every construct/mode, nested semantic functions, short-circuit/unknown outcomes, limits/accounting across retries/handoff, safe cancellation and late correlated answers. Grok gates cover capability negotiation and structured control with honest unsupported states. Distinguish provider-free CI, packaged disposable evidence, installed compatibility and production activation; no live provider experiment is authorized by this spec.

## Out of Scope

Production migration/activation without separate authorization; credential replication; implicit authority/resource renewal; hidden governor activation; automatic business/model work; parked OpenClaw; general delegated token exchange in initial delivery. Existing closed-tab/reboot recovery is not declared implemented. No claim that all stock/modded/provider combinations support native forks or exact token limits.

## Further Notes

Authority: [closed architecture map](https://github.com/CochranResearchGroup/codex-wake/issues/381) and its ten linked decision tickets, including both flow resolution comments and Bots consumer input. Source research branches remain evidence and are not merged. This spec freezes product decisions; implementation tickets must resolve concrete schemas/defaults under these constraints and report conflicts rather than silently weaken requirements.

<!-- idempotency:controller-spec-20261030 -->
