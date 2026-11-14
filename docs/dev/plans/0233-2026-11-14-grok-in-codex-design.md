# LOCAL-P233 | Grok inference in the modded Codex harness

State: OPEN
Workflow: CONFIRMED_IMPLEMENTATION_PACKET_PREPARATION
Work item: LOCAL-P233; related prior intake621 / draft622 is a separate CLI path
Owner: primary / ecochran76
Scope: provider and authentication design; no implementation before shared understanding
WIP limit: one coordinator; one completed read-only provider-auth fact discovery

## Objective and settled terminology

The operator wants Grok models to run inside the modded Codex coding harness,
analogous to its OpenAI model use. Codex retains the agent loop, tools, sessions
and worker management; Wake supplies the surrounding runtime tooling. This is
distinct from the earlier separate native Grok CLI/ACP worker proposal.

Existing GLOSSARY.md terms Coding harness, Model identity and Inference provider
already express this distinction. No competing glossary or speculative ADR is
needed. Hard-to-reverse provider/auth decisions will be recorded when settled.

## Current evidence

- The installed modded source revision f986f6ed supports custom model providers,
  Responses wire API, provider-specific credentials and capability overrides in
  codex-rs/model-provider-info/src/lib.rs. Configuration support alone is not
  qualified Grok tool/streaming/resume compatibility.
- Official xAI Build documentation describes Grok in a custom agent loop using
  the public Responses API at api.x.ai/v1 with API-key authentication.
  Source: https://docs.x.ai/build/overview
- Official Build enterprise documentation distinguishes its session inference
  proxy from the public API-key endpoint. Native account/session authentication
  is not established as interchangeable with public Responses authentication.
  Source: https://docs.x.ai/build/enterprise
- Current Grok FAQ describes a shared subscription allowance across products,
  including API usage. Exact account entitlement, credentials, quota attribution
  and custom-client access remain to be verified; do not infer billing from the
  words subscription or API key alone. Source: https://docs.x.ai/grok/faq
- Published native authentication documentation describes session login and
  refresh. It does not by itself qualify credential interoperability with Codex.
  Source: https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/02-authentication.md

Read-only sidecar /root/grok_provider_facts supplied bounded official-source
evidence and unknowns; primary accepted the auth/endpoint distinction and the
entitlement correction. No credentials, login or inference were accessed.

## Settled decisions: round 1

Operator answered `yes all` to Q1-Q3:

1. Account sign-in and verified existing entitlement lead the first version.
   Public API-key access is an explicit alternative, with no silent auth/billing
   fallback. Exact account access and quota attribution still require verification.
2. Grok is selectable for both the main conversation and individual workers,
   including an OpenAI parent with Grok workers. Existing OpenAI defaults remain.
3. Initial acceptance includes streaming, multi-turn tool use, terminal commands,
   file editing, MCP, interruption and conversation resume. Provider-specific
   extras are advertised only after separate qualification.

## New source evidence after round 1

Official Grok shell documentation explicitly describes direct inference using the
native login session: CLI inference proxy `/v1/chat/completions`, bearer session
credentials, the native-client authentication header and model-routing header.
This supports a direct provider design without running Grok's agent loop. It does
not establish general Codex Responses compatibility or concurrency-safe shared
refresh. Source: https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-shell/README.md#using-authjson-for-api-access

The focused authentication guide describes external credential updates and
refresh behavior. Use actual expiry metadata; older README claims about fixed
lifetime/auth precedence conflict with the focused guide. Never assume multiple
writers can safely rotate the same session store without qualification.

Grok keyboard cancellation and its persisted session format describe its own
harness. They do not prove server-side cancellation, zero later billing, rollback
of tool effects or native Codex resume compatibility. Codex must own its durable
history and interrupted-tool state for the chosen provider integration.

## Settled decisions: round 2

Operator answered `yes all` to Q4-Q9:

4. Reuse official Grok sign-in with shared login/logout behavior, coordinated
   refresh and no per-worker credential copies.
5. A unified model/account picker selects provider/account automatically. Workers
   inherit their parent's selection unless explicitly overridden.
6. Cross-provider changes create automatic linked continuations with portable
   messages/tool results. Preserve original history and opaque provider state;
   no extra confirmation. Ordinary same-provider model changes remain normal.
7. Quota/auth/provider failure returns a clear held state. The parent may
   explicitly reassign within existing authority. No hidden provider changes,
   indefinite retries or replay of uncertain work.
8. Existing Wake allowances cover the mixed-provider worker tree. Missing usage
   is never zero; strict accounting requirements hold until qualified.
9. Codex owns inference/tools; Wake coordinates accounts/auth/runtime. Put any
   necessary Grok-specific protocol adapter in Codex's provider boundary; a
   general translation gateway is outside the first release.

These trade-offs are recorded in ADR0006. Provider session and Provider handoff
are added to the existing glossary, preserving the concurrent unified-control
lane's unrelated Byobu environment terminology.

## Focused source evidence before round 3

- The official Build catalog has its own `x.ai/models/list` surface. Catalog
  visibility alone does not prove account entitlement or successful inference.
  Source: https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-shell/src/cli_models.rs#L74
- Official login code uses a persistent advisory auth lock, inode checks and
  atomic credential writes, accounting for single-use refresh tokens. Reuse the
  compatible contract rather than introducing an independent refresh writer or
  breaking a held lock. Source: https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-login/src/manager/lock.rs
- Login-change generations distinguish login, logout and token rotation. File
  absence is not confirmed logout: official reload behavior can retain cached
  refresh state. Explicit revocation needs a qualified semantic event/readback.
  Source: https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-login/src/manager.rs#L567
- Current upstream source mechanisms are not proof that the installed released
  binary shares the same contract. Pin and qualify the chosen revision/version.

## Settled decisions: round 3

Operator answered `yes all` to Q10-Q16:

10. Distinguish account-accessible, qualified model choices from unavailable,
    stale or unverified choices. No guessed model IDs or invisible substitution.
11. A selection change during a turn is staged for the next safe turn boundary.
    Changing selection does not interrupt work; Stop remains explicit.
12. Handoffs carry objective, constraints, active context, completed tool results
    and workspace/checkpoint references, compacting older history. Preserve full
    source history; exclude credentials and provider-private reasoning state.
13. Logout/revocation blocks new Grok turns and requests interruption of this
    harness's active Grok work. OpenAI work continues; interruption uncertainty
    remains explicit.
14. Stop uses Codex local interruption semantics, preventing further local tool
    scheduling. Provider completion/usage uncertainty is separate. Resume uses
    durable known state without replaying uncertain actions.
15. First rollout targets one existing modded profile after required package,
    isolated upgrade/rollback and bounded real-provider workflow qualification.
    Preserve OpenAI defaults/unrelated sessions; defer fleet rollout.
16. Label accounts explicitly and inherit the exact selected account. An account
    change uses the linked-handoff rule; no automatic account substitution.

Inference selection is now recorded as model plus provider account in the existing
GLOSSARY.md, distinct from observed model identity and verified readiness.

## Derived invariants, not additional user choices

- Handoff compaction is automatic, but failure to preserve the required objective,
  constraints, attribution or allowance holds the handoff and retains its source.
  It does not silently drop those already-required elements or reset allowances.
- Provider-private reasoning/opaque continuation data stays attributable to its
  source. No auth-store credentials are copied into conversation context.
- Shared refresh must honor the qualified native lock/rotation contract; unknown
  ownership or incompatible store versions hold rather than spawning another
  writer or breaking a lock.
- Usage reconciliation can release a strict-budget hold only from qualified
  evidence or a separately explicit operator mode/allowance decision. Missing
  usage never grants free work or a fresh allowance.
- Account/provider choices and actual observed identity remain distinguishable in
  records and UI; an unresolved identity/capability is not reported as ready.

## Settled decisions: round 4

Operator answered `yes all` to Q17-Q21:

17. Disable unsupported optional features individually with a clear reason. A
    model missing required baseline functionality is unavailable for that workflow.
    No simulated success or silent fallback.
18. A request for a Grok worker without a model uses an explicitly configured,
    validated account default. Record and pin the resolved model for accepted work.
19. Acceptance may run bounded coding, MCP, mixed-worker, handoff, interruption and
    resume checks in a disposable workspace. Forced logout/revocation tests remain
    isolated from everyday account sessions.
20. Done means reviewed, merged, qualified and deployed to the selected modded
    profile: one broad review and one bounded TDD remediation pass. Source tests
    alone are insufficient; no repeated broad-review loops or fixture frameworks
    as deliverables.
21. Supersede separate CLI-worker draft622/intake621, preserve evidence and retire
    only its task-owned idle runtime after fresh active/uncertain-work checks.
    Browser Grok and unrelated sessions remain untouched.

## Complete shared understanding

- Grok inference runs inside the modded Codex harness. Codex retains tools, MCP,
  conversations and mixed-provider worker management; Wake coordinates accounts,
  native sign-in, refresh and runtime controls. No general translation gateway or
  second Grok agent loop is part of this release.
- Reuse official Grok provider sessions with qualified coordinated refresh and
  shared logout semantics; no worker credential copies. Verify actual entitlement
  and quota attribution. API-key access is explicit, never an automatic fallback.
- One model/account picker serves main conversations and workers. Preserve
  existing OpenAI defaults. Workers inherit exact inference selection unless
  explicitly overridden; configured Grok defaults are validated and resolved
  selections are pinned for accepted work.
- Provider/account changes occur at a safe turn boundary through an automatic
  linked continuation. Carry bounded portable working context and completed tool
  results; preserve source history and opaque provider state. No extra handoff
  confirmation, credential copying or silent loss of required task constraints.
- Provider/auth/quota failures are actionable holds. Parents may explicitly
  reassign under existing authority. No hidden provider/account switches,
  indefinite retries or replay of uncertain work.
- Existing Wake allowances cover the mixed tree. Missing usage is not zero;
  strict-budget work holds until its accounting is qualified. Stop prevents
  further local tool scheduling, retains provider uncertainty and preserves
  durable resume state. Logout interrupts only this harness's owned Grok work.
- Required acceptance covers streaming, multi-turn coding tools, terminal/file
  edits, MCP, mixed-provider workers, handoff, interruption and resume. Optional
  capabilities are individually gated; required-capability failures block ready
  status. Qualified package upgrade/rollback precedes a bounded live disposable
  workflow, then rollout to one existing modded profile without changing OpenAI
  defaults or unrelated sessions.
- Complete through PR/review/one bounded remediation, merge, qualification and
  deployment. Retire the superseded task-owned CLI setup only after safe readback;
  keep its evidence and leave browser Grok untouched.

The operator explicitly confirmed the complete shared understanding and invoked
to-spec, to-tickets and implement-spec, with ticket closure, one broad review and
one bounded TDD remediation. The design frontier is closed; engineering discovery
cannot silently weaken these requirements.

## Current State

All21 decisions and the complete shared understanding are confirmed. The frozen
spec draft, eight ticket drafts and execution ledger are prepared. The invoked
skills require one concrete check of proposed public test seams, ticket graph and
fixed review bases before publication/dispatch; this does not reopen product
requirements. Primary takes auth ticketT1; native providerT2 and retirementT3 are
initially independent delegated tickets. Preserve unified-control design0234 and
its unrelated glossary edits. No implementation or new provider login/inference
has started in this packet.
