# Multi-runtime wakes and agent exchanges

State: OPEN
Owner: ecochran76
Work item: CW-MR-172 (local intake in this plan; not posted to GitHub)
Lane: P172
Branch: docs/multiruntime-spec
Base: fcc996a
Target: origin/main
Integration: squash_pr
Priority: Approved next design slice; preserve existing lane priorities
Dependencies: None for specification; execution dependencies below
WIP limit: One primary ticket plus one independent subagent per other ready ticket, within available runtime capacity

## Current State

Latest: MR-03 is IN_PROGRESS. The source candidate adds schema7/runtime-envelope1,
host-approved managed-launch Grok bindings, shared clock eligibility and weak
terminal evidence. Source/isolated-wheel validation is being reconciled. Two
setup probes sent zero conversation prompts and cleaned up; both lacked a usable
active session when queried. The live acceptance gate remains open. The requested
one-recipient/five-minute/one-prompt extension requires its user response before
another dependent live launch. MR-04/MR-05 remain blocked on MR-03.
Only MR-03 was ready in this wave; no independent nonblocked ticket or subagent.
[MR-03 evidence](../verification/0172-2026-10-22-mr03-grok-wake.md).

MR-02 remains DONE for source and isolated artifact. Its final full suite1428
(1 skipped) and isolated wheel94 tests passed. Main integration/release/production
installation remain separate. [MR-02 evidence](../verification/0172-2026-10-22-mr02-runtime-seam.md).

MR-01 remains DONE for a managed-launch terminal route for Grok1.0.40/minimal UI.
Native live control and authenticated receiver/A2A receipts remain unqualified.
[MR-01 evidence](../verification/0172-2026-10-22-mr01-terminal-qualification.md).

The user approved the consolidated design brief on 2026-10-22 after resolving
Q1–Q12. This specification and its local ticket drafts are the repository-native
continuation. Product decisions are settled; Grok live-session behavior remains
unqualified. The initial planning slice changed no runtime or installed state.

Execution update: the user's “next ticket” directive assigns MR-01 to the primary.
MR-02–MR-06 remain dependency-blocked, so this wave has no subagents. Subsequent
waves assign one other ready ticket per independent agent, with disjoint write
ownership and primary reconciliation; shared journal/authority edits retain one
integration owner. This explicit direction supersedes the original serial WIP
preference without bypassing blocking edges.

Historical wave 1 result: MR-01's two disposable TUI launches both required interactive
sign-in. Native initialize/session-list worked, but no conversation was
available. Zero conversation submissions and fresh owned-process cleanup within
the five-minute probe bound. MR-01/MR-02 were BLOCKED at that checkpoint; this
readiness is superseded only by the authenticated result above.
[MR-01 evidence](../verification/0172-2026-10-22-mr01-grok-qualification.md).

GitHub Issues remains the canonical coordination ledger. A bounded read found no
matching open issue or PR. CW-MR-172 is the local intake fallback under the
work-item policy; neither this plan nor its child drafts claim remote publication,
assignment or ready-for-agent labels. A future authorized tracker publication
must preserve these locators and dependency edges.

Planning base is freshly fetched origin/main fcc996a (package 0.19.1). The original
main checkout at 43e3db2 has two unrelated policy commits and remains intact.
[Validation record](../verification/0172-2026-10-22-multi-runtime-spec.md)
distinguishes documentation checks from absent runtime proof.

## Problem Statement

Users need durable wakes and tracked agent exchanges between Codex and Grok,
then Claude Code and open-source/open-model terminal agents. Current transports
separate some delivery mechanics, but session discovery, caller identity,
readiness and acknowledgment still assume Codex. Scattering runtime checks
through the scheduler would make each new TUI harder to qualify and maintain.

A model provider, agent runtime and terminal host are different roles. Changing
the model behind one runtime must not require another Wake adapter or implicitly
replace the recipient's identity or resource allocation.

## Solution and Scope

Keep durable intent, trigger evaluation, trusted deadlines, cancellation, mailbox
work claims and recovery in Wake. Place runtime-specific session identity,
readiness, submission and reconciliation behind one small delivery interface.
Terminal hosts provide bound pane/tab lifecycle and inspection/input primitives;
they do not own conversation identity or grants.

First release: same-host exact visible-session wakes and bidirectional Codex/Grok
A2A request/claim/reply, discovery and recovery. Support the specified busy
policies and separately qualified terminal fallback. Broader spawn, refresh,
handoff and resource-control operations follow in separate vertical slices.
Their eventual cross-runtime scope is accepted; this first-release plan does not
claim to implement that entire program.

Use existing time/file triggers first. Do not introduce trigger semantics merely
to add a runtime. Cross-host deployment, Claude/Open-model production adapters
and a public plugin SDK are later work.

## Current Repository Evidence

Paths refer to the fcc996a implementation base, not an installed Grok guarantee.

| Surface | Existing behavior and seam |
| --- | --- |
| [sessions](../../../src/codex_wake/sessions.py) | Combines Codex app-server threads and tmux metadata. Candidates and exact selection are distinct; labels/CWD alone do not prove a binding. |
| [native delivery](../../../src/codex_wake/native_delivery.py) | Codex exact-thread observation, optional same-thread resume, deadline holds, delivery and reconciliation. |
| [runtime identity](../../../src/codex_wake/a2a_identity.py) | Existing Codex namespace derives from canonical Codex home and model-provider metadata. Stored historical identities require compatibility. |
| [owning-client binding](../../../src/codex_wake/a2a_delivery.py) | Peer/process-generation checks, exact request and transport receipts, unsent versus uncertain outcomes. |
| [tmux A2A binding](../../../src/codex_wake/a2a_tmux_delivery.py) | Codex-specific empty-composer/identity checks guard a native Codex queue call. Its durable tmux discriminator does not mean generic keystroke delivery. |
| [dispatch](../../../src/codex_wake/injector.py) | Existing lifecycle locks, record classification, time qualification and transport dispatch. |
| [MCP](../../../src/codex_wake/mcp_server.py) | Codex caller conventions; host-delegated resource requests also verify native request metadata. Claimed IDs are not attestation. |

These delivery/identity files were compared with the earlier explored checkout:
they are unchanged except MCP, whose host-delegated caller/accounting changes
were inspected at the new base. Preserve that stronger admission path.

Installed Grok 1.0.40 help observed during the interview exposes session IDs,
resume, MCP, headless/stdio and a shared-leader option. No observation yet proves
that a second client can safely submit into the already-open TUI's conversation.
Do not turn saved-session resume or headless output into that proof.

## User Stories

1. As an operator, I can address an exact Codex or Grok recipient without
   accidentally selecting another conversation with the same tab name.
2. As an agent, I can register a wake that survives my initiating turn.
3. As an operator, I see the wake arrive in the recipient's already-open TUI.
4. As a Codex agent, I can assign scoped work to an enrolled Grok recipient.
5. As a Grok agent, I can assign scoped work to an enrolled Codex recipient.
6. As a sender, I receive a correlated reply and can distinguish retrieval,
   acceptance of work and completion.
7. As an operator, I can choose waiting, verified queueing or authorized
   interruption when a recipient is busy; waiting is the default.
8. As an operator, I see expiry instead of delivery to a substitute recipient.
9. As an operator, I can allow terminal inspection/input as a last resort for a
   runtime without automation-friendly controls.
10. As an operator, I know whether delivery was observed, queued, executing or
    acknowledged, without a stronger claim than the evidence supports.
11. As an operator, I can recover from an interrupted submission without replaying
    work whose acceptance is unknown.
12. As an operator, I retain existing Codex schedules, mailbox identities and
    allowances when adding or switching a model provider.
13. As an operator, I can use wakes/A2A even when that runtime lacks strict resource
    enforcement, with unsupported guarantees refused explicitly.
14. As an authorized agent, I can eventually spawn a separately granted recipient
    through a host-approved profile.
15. As a maintainer, I qualify a new runtime inside its adapter and capability
    contract without embedding its protocol or UI parsing in the scheduler.

## Implementation Decisions

### One delivery seam, substantial adapters

Expose four logical operations to the core. Exact language-level types may be
allocated during the Codex preservation slice; their semantics are binding.

| Operation | Input | Required result |
| --- | --- | --- |
| Resolve | Explicit runtime scope plus exact session reference or human selector | One exact recipient and binding evidence, or structured missing/ambiguous/unavailable outcome. |
| Observe | Exact recipient/binding and requested mode | Current identity/generation, readiness, supported capabilities and evidence freshness. Unknown is distinct from idle. |
| Submit | Exact recipient, durable attempt ID, payload/pointer, original deadline and explicit policy | Definitely not sent, submitted with typed evidence, or uncertain. |
| Reconcile | The original recipient and attempt | Attributable prior acceptance/evidence, definitive non-submission, or still uncertain; absence of evidence is not non-submission. |

Adapters own protocol requests, runtime paths, executable selection, status
translation, hook interpretation and UI recognition. They receive frozen host
scope and clocks rather than selecting new authority or time sources. Preserve
existing higher-level CLI/MCP workflows; runtime selection becomes explicit before
normalization. No concrete new command spelling is promised by this spec.

Lifecycle and resource controls are optional capability groups, not dozens of
mandatory delivery methods. No-op implementations must not advertise support.
This is an internal seam with built-in adapters, not a general plugin framework.

### Identity and caller admission

Use a namespaced opaque conversation ID, scoped to the runtime installation or
account, plus a live binding generation. Do not impose Codex UUID formatting on
other runtimes. A terminal pane, CWD, title, model name or screenshot cannot alone
establish conversation identity. Refreshing observation does not renew a grant.

Preserve existing Codex namespace derivation and all persisted actor keys; do not
re-hash old mailboxes into a new provider-neutral key. A model switch must not
silently mutate actor/accounting identity. Any necessary namespace evolution
requires explicit migration, retained provenance and compatibility tests.

MCP tool arguments or shell environment IDs remain claims. Runtime-specific
caller attestation and frozen host grants are checked before effects. Adding
Grok must not weaken native-metadata verification for existing delegated Codex
allocations. Launch profiles pin approved runtime/executable scope; supplied
text cannot select arbitrary commands, host policies or another user's endpoint.

### Busy policy

| Policy | Behavior |
| --- | --- |
| Wait (default) | Re-observe the same recipient until idle and eligible, within the original deadline. Unknown readiness holds. |
| Queue | Submit only to a qualified runtime queue, with exact recipient evidence and native expiry or equivalent enforced dequeue-time deadline. Accepted queue input is not execution. If expiry cannot be enforced, report queue mode unsupported. |
| Interrupt | Require explicit task/host authority, identify the exact active turn and supported cancellation semantics, then deliver only after a fresh eligible observation. Do not interrupt unrelated work. |

Checking idle followed by input is not an atomic guarantee. Report the actual
guarantee and hold on changed generation/UI state. Existing queues without
dequeue-time expiry must not acquire this guarantee by renaming a mode.

### Delivery method and terminal fallback

Prefer a qualified native control method. A host-approved profile may permit
automatic terminal fallback when the preferred method is unavailable *before*
submission, or definitive reconciliation proves the original attempt was not
sent. Any possible prior effect holds the original attempt for reconciliation;
transport switching must not create a second submission.

Terminal input requires a current process/session binding, user-owned host
endpoint, protected empty/eligible composer and a qualified runtime/version UI
recognizer. Recheck under the existing per-recipient/pane lock immediately before
input. Shell prompts, permission dialogs, unknown UI, existing user input,
replacement processes and ambiguous bindings refuse input. Use literal prompt
pasting without shell interpretation; terminal content cannot confer authority
or redirect an approved target.

Inspection may establish observed prompt acceptance without a receiver ack.
It cannot prove model execution, a work claim or completed work. Generic
automation-hostile TUIs are supported only once these minimum binding and
recognition requirements are qualified; "last resort" is not permission to guess.

### Durable attempts and evidence

Keep lifecycle status, submission certainty, transport evidence and A2A work
state separate. Record intent/attempt/recipient identity, selected method,
policy, capability version, observation freshness, original deadline and
attributable evidence references. Use bounded private artifacts for UI evidence;
do not commit production transcripts, screenshots, tokens or raw private data.

The evidence vocabulary includes observed prompt acceptance, runtime queue
acceptance, execution observed and receiver acknowledgment. Evidence is typed
and cumulative, not one Boolean success or a universal linear ranking.
Observed delivery terminates automatic resubmission of that attempt; no synthetic
receiver receipt is created. A late acknowledgment may strengthen the same
attempt without creating new work.

Before adding a runtime target, expand the record contract with a separately
versioned runtime envelope. The implementing slice allocates the schema version
against the then-current classifier, defines old-reader fail-closed behavior and
retains old-record read compatibility. This document does not change persisted
schema numbers or reinterpret legacy transport discriminators.

Cancel an eligible pending intent without deleting history. Cancellation cannot
retract a prompt already accepted; record the actual boundary. Crash recovery
must preserve uncertain attempts, resource counters and original expiry. Reuse
current trusted-time and relative-clock-continuity logic, never guest wall time
or a restarted delay.

### Cross-runtime A2A

Reuse the existing durable bus, correlation IDs, work-claim and receipt model.
Adapters deliver a bounded notification/pointer to the owning conversation;
mailbox authentication and claim authority stay in the bus. Both directions must
prove exact recipient authentication, claim-before-work and a correlated reply.

Weak terminal evidence may wake an agent that subsequently authenticates and
claims work. It is not itself an authenticated work receipt. Changing runtime,
opening a tab or receiving a notification does not transfer another actor's
permissions, tasks, allowance or caller grant.

### Capability reporting

Report runtime/version/method-specific qualification for discovery, exact live
delivery, queueing, interruption, saved resume, caller attestation, lifecycle,
usage sampling and strict enforcement. Keep "not qualified", "unsupported" and
"temporarily unavailable" distinct. Requested unsupported strict guarantees fail
explicitly. Sampled/best-effort modes require explicit selection and truthful
overshoot/accounting limitations.

Full eventual lifecycle and resource support remains in scope for the program,
but no runtime must pretend to implement capabilities it does not possess.

## Testing Decisions and Acceptance

The runtime delivery interface is the shared behavioral test seam. Exercise
normal CLI/MCP callers where identity and grants matter. Inject clocks/protocol
dependencies inside adapters; do not reproduce implementation logic in tests.

Prior art: existing native delivery, sessions, owning-client delivery, tmux A2A,
saved-recipient, projection acknowledgment and scheduler-fault tests. Retain their
stronger Codex guarantees. Add only the missing cross-runtime risks.

| Criterion | Required evidence |
| --- | --- |
| AC1 | Installed-path durable wake to an exact open Codex TUI and an exact open Grok TUI; observable prompt and typed method evidence. |
| AC2 | Codex → Grok and Grok → Codex scoped request, recipient authentication, work claim, reply and correlation. |
| AC3 | Default wait and selectable queue/interrupt policies; qualified behaviors demonstrated and unsupported selections refused before effects. |
| AC4 | Terminal fallback independently proves profile activation, binding/composer guards, observed delivery and ambiguous-result no-replay. |
| AC5 | Expiry, cancellation, crash/restart, stale generation and uncertain transport outcomes retain the original intent without duplicate work. |
| AC6 | Existing Codex identities, grants, native wake and A2A behavior remain compatible; old/new-reader expectations are tested. |
| AC7 | Versioned capability/readiness reporting is usable through agent-facing CLI/MCP, without unsupported resource claims. |

Definition of done for the first release: all seven criteria qualified against the
declared source/installed versions, required checks passed, bounded live receipts
retained, and known method/runtime gaps published. A spec, fixture pass, queued
message or session resume is not live TUI acceptance.

Focused development: contract/changed adapter tests, target <=60s per red/green
selection. Presubmit: follow the repository CI environment and changed-surface
classification, including required matrix gates. Runtime/schema/identity changes
take the conservative full lane. Comprehensive/live qualification is opt-in and
separate from documentation checks.

First Grok probe budget: one serialized owner, at most two disposable recipients,
six synthetic prompt submissions total, five-minute wall-clock envelope, one
attempt per candidate method, no replay on uncertainty. Use explicit readiness
signals and exact process/session IDs. Stop with retained evidence if the
bounded run cannot prove the method. Provider dispatch, extra model/resource
cost and touching an existing user conversation require their existing exact
authority; the approved brief is not a new production grant.

## Execution and Blocking Edges

[Ticket index](0172-multi-runtime/README.md) contains one local draft per vertical
slice. No external issue has been created or changed.

| Ticket | Outcome | Blocked by |
| --- | --- | --- |
| MR-01 | Bounded Grok exact-open-session qualification and selected feasible route | None |
| MR-02 | Existing Codex wakes preserved through the shared runtime seam | MR-01 |
| MR-03 | Durable exact-open-Grok wake through one qualified method | MR-02 |
| MR-04 | Bidirectional Codex/Grok A2A request/claim/reply | MR-03 |
| MR-05 | Selectable busy modes and qualified terminal fallback across the two runtimes | MR-03 |
| MR-06 | Installed first-release acceptance and capability/support matrix | MR-04, MR-05 |

MR-04 and MR-05 are dependency-independent after MR-03. Under the user's parallel
wave directive they may run in independent agents with disjoint write ownership.
The primary freezes shared contracts, owns journal/grant integration and
reconciles both results. At the first wave only MR-01 was ready, so no subagents
ran; do not bypass prerequisites merely to create parallel work.

Future lifecycle/resource and additional-runtime slices are not preallocated
implementation tickets. Derive them from the accepted delivery seam and measured
capabilities, preserving the program scope.

## Risks, Limits and Further Notes

Grok's shared leader may not expose a safe already-open-session submission path;
MR-01 must determine that. Terminal UI changes can invalidate qualification.
Idle observation is inherently racy without a runtime atomic operation. Duplicate
prevention depends on conservative uncertainty handling, not an exactly-once
promise. Dequeue-time expiry may make queue mode unavailable on some runtimes.

This specification is approved direction, not an installed capability claim.
No remaining product questions are identified. Technical feasibility may narrow
a capability claim or require a recorded design revision; it does not authorize
silent fallback, weakened identity or a different recipient.

Approval provenance: Previews session 3c4638767588; brief artifact 705b7ef7fa0d;
Q4–Q9 response 3d1680afa12e4b83959f36a5c0f2277d; subsequent Q10–Q12 acceptance
and explicit brief approval in the user conversation. No tokens or raw private
questionnaire export are copied into Git.
