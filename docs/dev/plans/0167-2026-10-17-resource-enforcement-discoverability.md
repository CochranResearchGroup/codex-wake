# Plan0167 — Resource enforcement discoverability and first use

State: CLOSED
Owner: primary / ecochran76. Work item: #279; related #274, #278.
Branch: feat/objective-enforcement. Base:7dfb868.

## Original audit scope and acceptance (completed)

Audit how an agent discovers resource enforcement from a user-supplied budget.
Improve shipped skill triggers, packaged instructions, MCP tool descriptions and
operator release checks. Verify public tool discovery and relative skill links.
Do not change authority or containment semantics, install production skills,
restart user clients, merge or release. This is a requested onboarding audit, not
a second broad review of Plan0166.

## Audit findings at49a5260 (historical)

Discoverability gaps confirmed: resource enforcement absent from skill metadata
and MCP descriptions; detailed controls guide lacked a portable agent workflow.
Corrections add resource-limit triggers, inspection/decision steps, caller/TUI
coverage boundaries, missing-control behavior and release synchronization checks.
Public MCP catalog regression observed red, then three lifecycle MCP tests passed.

A release-blocking functional onboarding gap remains: an ordinary MCP caller's
first strict spawn reads its native goal before creating the dedicated executor.
Operator bootstrap worked in prior acceptance; it is not an agent authority
fallback. A zero-model-call public CLI reproduction preserves this ordering.
Private strict-home MCP services are also refused unless a control route is
separately qualified. No self-service release claim is justified yet.

## Superseded next packet | strict bootstrap

Design and implement an explicit caller-authorized bootstrap/control route,
retaining host-selected objective/profile, original limits, ownership and prior
spend. Prove cold first launch through the actual agent surface, unsupported
setup refusals, counted work, independent stop and unrelated preservation.
Do not bypass source-goal checks or let callers choose another objective through
an undocumented CLI route. Close this plan only after that proof, or record an
explicit decision to release operator-only support with honest agent guidance.

## Design interview | clarified user experience

User clarified that the desired workflow stays in the existing dev tab and its
native /goal. The agent registers session limits through Codex Wake MCP; an
independent enforcer observes elapsed time and token usage, first sends a
stop-and-checkpoint request, then pauses the goal. This is goal supervision,
a separate guarantee from dedicated OS execution containment. No session
migration or separate worker/tab management is assumed for this requested path.

The prior strict-MCP bootstrap gap remains factual, but fixing it alone would
not deliver this clarified existing-goal workflow. At this interview checkpoint those decisions remained open; the final confirmed
contract below supersedes it and authorizes implementation.

## Settled decisions | interview round two

User accepted native goal pause plus exact active-turn interrupt when required,
without terminating the shared Codex server or unrelated processes. A failed
control response remains an explicitly unverified stop. User also accepted a
checkpoint reserve inside the original budget: the original limit still pauses
the goal if checkpointing is ignored or unfinished. ADR0001 records this boundary.

The next interview round considered the5%token/60s checkpoint trigger and
cumulative goal-start accounting; both were subsequently confirmed below. Read-only owned-fixture investigation confirmed thread_goal_updated
history can anchor some settled goal boundaries:55175→145652 cumulative gives
90477 while native goal display gives1869. General active-goal baselines and
delegated aggregation are not yet implemented or qualified; no assumption that
parent totals can safely be added to child totals is permitted.

Prior domain rules continue to apply unless explicitly changed: historical
consumption survives resumption, and only explicit user renewal increases
authority. The final confirmation below closes that interview gate.

## Confirmed implementation scope | existing session supervision

The user confirmed the complete checkpoint reserve and accounting contract:
request checkpoint when either 5% of token allowance or 60 seconds of time
remain, whichever condition first holds. Both reserves consume the original
allowance. Explicit overrides are displayed at enrollment. There is no promise
that checkpointing finishes before the stop condition.

Account cumulatively from the original goal start, including cached input and
attributable delegated work exactly once. Registration and resumption do not
reset consumption or the deadline. Unknown accounting holds continuation;
only explicit user renewal increases authority. This confirmation authorizes
implementation through the public MCP surface, replacing the audit-only scope
above for this new packet. Production installation and release remain separate
from disposable validation.

### Remaining scope decision

Native 0.163 goal/set has no expected-goal identity or revision. Exact-turn
steering and interrupt are available, but read-before/read-after cannot remove
a goal-replacement race for pause. Asked whether limits remain authoritative
across replacement goals in the same session until explicit renewal/clear.
Dependent pause semantics wait for that answer; unrelated sessions remain
outside the registered authority.

### Work units and bounds

1. Freeze enrollment, accounting and controller contracts; retain native API
   evidence and verified issue #279 readback.
2. Public enrollment/readback red-green slice: host-scoped identity, durable
   limits, qualified baseline and live controller readiness.
3. Independent checkpoint/pause red-green slice: persisted delivery intent,
   exact active-turn controls, original caps and truthful uncertain effects.
4. Qualify historical and delegated cached-inclusive accounting; unsupported
   history holds rather than using discounted native goal counters.
5. Validate disposable native workflow and discovery documentation, then one
   bounded review of this new feature and one remediation pass. Preserve prior
   strict-mode proof; do not reopen its completed broad review.

Primary owns integration and shared interfaces. One read-only fact lane,
/root/native_containment_probe, examines version-matched accounting only;
no native/provider effects or implementation writes are authorized to it.
Each implementation slice uses one failing public-seam test followed by the
smallest passing change. Definition of done: every #279 acceptance criterion
has current public/native evidence or an explicit unresolved gate; docs cannot
claim supported enrollment before that evidence exists.

## Final authority decision | confirmed

User confirmed that limits persist across replacement native goals in the same
session unless the user explicitly resets counters/allocation. No further design
approval is pending. A host-approved allocation generation identifies explicit
reset authority; merely changing native goal, caller intent, registration or
resumption does not reset counters. The controller may pause the current goal in
the exact registered session, resolving the missing native goal-CAS limitation
without broadening authority to other sessions.

## Frozen implementation seams | #279

- `wake_goal_limits_set`: caller_thread_id, token_limit, time_limit_seconds,
  optional checkpoint_token_percent (default5), checkpoint_seconds (default60).
- `wake_goal_limits_show`: caller_thread_id. Neither exposes host paths, endpoint,
  another target thread, or a reset switch. Host-only --goal-limits-policy and
  --wake-root are forwarded to `goal-limits set|show` CLI commands.
- Private host policy version1, callers keyed by UUID. Each grant specifies
  app_server, codex_path, codex_home, allocation_id, max_tokens, max_seconds,
  optional rpc_timeout. A changed host allocation_id represents explicit user
  reset authority. Repeated enrollment under the same generation preserves the
  original accounting anchor, spent tokens and deadline, and may only tighten.
- Public Python seam `goal_supervision.enroll(root, policy_path, caller_thread_id,
  token_limit, time_limit_seconds, checkpoint_token_percent=5,
  checkpoint_seconds=60)` and `show(root, policy_path, caller_thread_id)`;
  exported controller `watch(root, interval=1)` and `poll(root)` use persisted
  host scope. `goal-limits watch` is an independent foreground service process,
  requiring live owned-process heartbeat before armed enrollment.
- Accounting seam `goal_usage.observe_usage(codex_home, thread_id,
  goal_created_at, *, reset_anchor=None)` returns state (`qualified`/`unknown`),
  used_tokens, anchor, reason, sampled=True. An explicit reset anchor is a
  persisted response-identity set plus time boundary produced by initial
  observation; implementation must refuse unqualified history, descendants or
  fork inheritance. Native goal display counters are never substituted.
- Enrollment receipt states: held, armed, checkpoint_requested, stopped,
  stop_unverified. Durable intent precedes native effects. Original deadline is
  based on original goal start; controller restart cannot renew it. Sampled token
  observation does not promise an exact ceiling. Native pause/turn interruption
  does not promise termination of arbitrary tool processes.

Primary owns MCP/CLI wiring, shared docs and integration. Bounded disjoint lanes:
core controller and accounting each in their own worktree; public-seam tests
belong to each lane. One red-green behavior at a time, two attempts per slice;
one fresh review then at most one remediation pass for this feature.

## Implementation and acceptance checkpoint | 2026-10-17

Implementation is complete for the frozen native-session contract. Work item279
covers the public MCP/CLI controller, cached-inclusive accounting and discovery.
Limits persist across replacement goals and resume; host allocation generation
is the explicit user-reset boundary. Source checkpoints6b4b233 (reviewed core),
977664a (actual active controls) andb6fd05c (actual native delegated accounting)
retain evidence. Version0.17.0 is prepared for release; production remains0.16.0
until protected-main integration and exact-prefix rollout succeed.

- Full documented-isolation regression:1349 tests PASS, one optional host skip,
  327.697s. Initial host-configured runs fail the documented existing Stable Time/
  registry fixture boundary; retained, not erased. Later final CLI refusal and
  cross-process fixture changes pass24focusedtests. Installed core/accounting21
  pass after fixing the fixture's parent-only native RPC mock race using a real
  local Unix protocol server shared with the watcher.
- Candidate wheel109Python sources match; installed public MCP→CLI→watcher
  protocol qualification passes. Portable whole-skill copy resolves all links.
- Actual Codex0.163 idle controller stop and active-turn checkpoint/pause/interrupt
  pass with no external provider calls. Local Responses data is injected, not
  billing. Checkpoint acknowledgement is delivery, not an authored artifact.
- Actual native delegation publishes90 injected cached-inclusive tokens exactly
  once (20+40root,30child). This native fork did not copy prior parent counters;
  inherited-record dedup remains fixture-qualified. Root-native stop does not
  establish separately running child-session termination; public readback and
  guide state this explicit scope. Dedicated containment remains separate.
- One independent drift review found F1, accepted blocking and fixed by observed
  pause epochs. Closed-world independent verification passed; no new broad pass.

Remaining delivery unit: publish the final coherent source, protected-main PR/CI,
then exact-main release/install plus whole-skill/client synchronization under the
user's standing install/deploy/reconcile instruction. Preserve all unrelated
sessions and services. Do not call source acceptance a production rollout.

## Delivery qualification repair | 2026-10-17

F2 found that the actual host history exceeded the bounded directory scan.
Commit90de1ac uses the native SQLite thread index read-only, then revalidates
canonical rollout metadata and spawn coverage. Missing/conflicting history still
holds unknown. Independent closed-world source verification resolved F2; all25
focused public tests pass. The real-home read-only performance probe reaches
original-boundary validation in0.9783s; this is not live enrollment acceptance.
A separate host-only MCP goal root preserves existing legacy tool scope.

## Delivery closeout | 2026-10-18 UTC

PR280 merged3cdc037; v0.17.0 released and installed from that exact main commit.
Final hosted CI passes1,351 tests with one optional host skip on both Python
versions. Published asset download hashes match. Installed109sources,27MCPtools,
whole skill copies and fresh independent service heartbeat qualify delivery.
Existing clients need MCP refresh; no current goal enrollment, counter reset,
shared-server restart or unrelated service restart occurred. Limits carry forward
until an explicit user reset. Full receipts: evidence/plan0167/acceptance-summary.md.
