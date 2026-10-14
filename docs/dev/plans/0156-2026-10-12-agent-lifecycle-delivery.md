# Plan0156 — Spawn, refresh and fresh-agent handoff

State: OPEN
Workflow: IN_PROGRESS
Owner: primary / ecochran76
Target: origin/main
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/248

## Current State

2026-10-14 operator renewed resources again ("renew resources"). This window
supersedes the remaining prior allowance: 12:29:34–18:29:34 UTC, at most
2,000,000 attributable tokens. Same ACTIVE thread; native baseline583,915.
Preserve previous accounting: known native samples374,031 and conservative
100,000-token reservations for each of three completed external lanes; previous
window conservative total1,229,307 at renewal. Charge subsequent root deltas
and new external work to this window. Renewal preserves acceptance, scope,
review discovery and retry limits; existing uncommitted implementation is retained.

2026-10-14 operator explicitly renewed resources ("renew resources"). New
execution window: 10:38:06–16:38:06 UTC, at most 2,000,000 attributable tokens.
Thread 01a139e7-17bc-79c3-af66-0294a9a69e3f resumed ACTIVE; renewal baseline
28,639 native tokens. Count subsequent native deltas plus any external actor
usage in this window. Preserve all previous-window receipts and counters;
renewal does not reset acceptance, review discovery or retry history. Primary
owns issue255 then256 then257 on feat/agent-lifecycle. Checkpoint each bounded
slice and before native effects, with the existing 45-minute backstop.

Draft integration PR: https://github.com/CochranResearchGroup/codex-wake/pull/253
(base main, verified8d7763f at creation). Draft remains not merge-ready; full native
handoff acceptance and release gates remain open. No issue auto-close directives.

2026-10-13 latest: checkpoints25–26 remediate consolidated review SP-01
(late source accounting fences activation/continuation) and SP-02 (restart-safe
checkpoint qualification). Native installed13 at0e111f9, live-handoff05, still
fails preflight allowance174533>150000 after extra source reads; instruction
output no longer truncates. Source paused, target goalnull, exact turn interrupted,
no continuation/rollback acceptance. Checkpoint27 preserves this failure and
local full-suite diagnosis. Both native modes, refresh goal/instruction proof,
local release gates, integration/release/cleanup and issue closure remain open.

2026-10-13 operator-authorized resource reset/resume: new native goal window
start1791887366, deadline1791908966; stop/checkpoint before 2,000,000 tokens
or six hours in this window. Previous counters and expired fixture deadlines
remain historical evidence. Full scope and review/retry bounds unchanged.
Checkpoint16 reproduces and repairs acceptance-runner transient-hold teardown;
installed preflight/continuation remain unaccepted. Earlier execution snapshot:

Execution started on `feat/agent-lifecycle` from origin/main a741010 under the
operator's execute-Plan0156 goal. Plan0157 is the serial critical path; 0158 then
0159 follow. Primary owns shared controller/CLI/MCP integration. One read-only
worker may inspect native contracts; it has no effect or implementation authority.
Checkpoint each child and before installed effects, with a 45-minute backstop;
stop and checkpoint before cumulative 2,000,000 tokens or six hours. Goal runtime
start is epoch1791817417; six-hour ceiling1791839017. Native goal counters are the
token authority. Two attempts per failing seam and one consolidated review plus
one remediation pass remain the campaign bounds. Positive installed spawn and
installed refresh's stale-resource axis are proven; all child closeouts and
combined product/release acceptance remain incomplete.
Public CLI/MCP are deterministic seams; native queued-message and owned TUI
readback are installed seams. Red/green commands belong in the evidence ledger.

Existing open/resume/close accepted; Plan0155 disposable probe complete. Same-thread
TUI restart retains its thread's MCP connection on installed Codex0.162.1; fresh
conversation loads the revised MCP. This plan specifies a future lifecycle product,
the controller now implements guarded spawn and partial refresh. Goal migration
and actual successor preflight remain pending Plan0159 work.

## Operator requirements revision — configurable review and nested budgets

The operator clarified that handoff-writing and preflight-review skills must be
selectable, including Matt Pocock handoff and ask-Matt. Preflight must assess
actual objective progress, scope drift and unsupported completion claims, separate
from runtime readiness. Test count alone is not acceptance evidence.

The operator controls both session and cumulative objective token/time budgets.
Successors, reviewers, delegated work, retries and failed preflight count toward
the objective budget; transitions cannot renew it. Preserve prior accounting
when the operator explicitly extends or resets an allowance.

Approved correction policy: rejected outgoing work may receive bounded correction
within the existing objective, authority and remaining budgets. Scope expansion
or resource increases require an explicit operator decision. This revision does
not reset the current execution window or establish native acceptance.

The operator approved user defaults with per-objective overrides, overall
wall-clock time including waiting, and at most two automatic correction cycles.
Existing implementation and failed acceptance receipts remain historical
evidence; do not relabel them as meeting the new requirements.

### Revised solution and user stories

Expose an effective configuration before starting an objective: selected handoff
writer and preflight reviewer, their resolved instruction sources, session token
and time limits, objective token and time limits, original objective start and
deadline, and correction-cycle bound. Apply user defaults then explicit objective
overrides. Persist the resolved configuration with the approved objective;
configuration edits must not silently change an active assignment.

1. As an operator, select handoff-writing instructions such as Matt Pocock's
   handoff skill so the outgoing checkpoint follows my chosen process.
2. As an operator, select preflight instructions such as ask-Matt so the successor
   chooses a relevant review process instead of a hardcoded GitHub workflow.
3. As an operator, inspect the effective configuration before work starts so
   overrides and actual limits are visible.
4. As a successor, compare outgoing claims against the approved objective,
   acceptance criteria, actual changes and evidence before accepting the work.
5. As an operator, see runtime readiness separately from work acceptance so a
   successful launch or test count cannot masquerade as objective progress.
6. As a successor, perform at most two corrective cycles within approved scope
   and remaining resources, then checkpoint and stop if acceptance still fails.
7. As an operator, bound each agent goal session and the whole objective so
   multiple bounded sessions cannot create an unlimited execution loop.
8. As an operator, see all attributable model spend, including failed attempts,
   reviewers and delegated work, without double counting cumulative counters.
9. As an operator, retain original deadlines through waiting, controller restart,
   refresh, handoff and retry; unknown accounting holds new admission.
10. As an operator, explicitly extend or reset a budget without erasing prior
    usage or allowing an agent to authorize its own extension.

### Revised implementation decisions

Configured standalone spawn and refresh source coverage now binds approved host
objective configuration into immutable intents. Spawn reserves its session before
creation, requires a live resident supervisor, accounts active parent quota, and
stops exact owned turns/queued submissions at the original deadline. Final
standalone settlement waits for the owned rollout accounting marker; completed
receipt replay excludes later work. Refresh observes the same goal before stop
and after continuity without renewing a deadline or allocating another actor.
Source checkpoint evidence: docs/dev/evidence/plan0156/spawn-refresh-source-checkpoint.json.
This advances issue256 source behavior; installed combined proof and all wider
acceptance, integration and release gates remain open.

Issue255 implementation seam: `sessions configuration --profiles FILE --profile
NAME --thread-id ID` and host-bound `wake_sessions_configuration` read
`lifecycle_defaults`, overlaid by `continuations[ID].configuration`. Writer and
reviewer selections each contain `name` and absolute `path`; readback includes
actual UTF-8 instructions and SHA256. Limits use `session_token_limit`,
`session_time_limit_seconds`, `objective_token_limit`,
`objective_time_limit_seconds`, and `max_correction_cycles` (maximum2).
Handoff intent freezes the resolved revision. Native completed command evidence
must show selected instruction bytes read by writer and reviewer. Host preflight
workflow must match the selected reviewer name; no GitHub-only fallback remains.
The public receipt separates `runtime_readiness` from `work_review`; accepted
progress references host-approved criteria and existing evidence by path/hash.
Legacy preflight-only profiles cannot prepare a successor goal under the revised
contract. Issue256 now integrates durable objective accounting and atomic session
reservation with source pause, preflight, preparation, monitor and rollback.
Identical objective configuration revisions omit source thread/profile readback
fields so successors retain the same approved settings. A host `objective_id`
may be explicit; otherwise objective text and original start deterministically
identify the ledger. `sessions configuration` reads existing ledger state beside
prospective defaults, without applying changed defaults to active work.
Operator CLI `--apply-budget-authorization` requires an exact host
`budget_authorization` revision/action/approval; agent MCP cannot submit this
operation. `extend` preserves origin and increases ceilings; `reset` explicitly
replaces cumulative ceilings/deadline without zeroing usage or correction count.
Reset requires settled, known actors. Both operations retain original deadline
and attributable authorization history and reconcile exact replay idempotently.
Durable native goal aliases bind preflight offsets to their assigned actor so a
successor becoming the next source is charged once. Native refreshed sessions,
general spawn accounting and both-mode installed proof remain open.

Correct verdicts require a host `correction_scope` and a frozen `correction_packet`
(approved criterion, relative paths, instructions, checked evidence path/hashes).
The controller admits a distinct native assignment in the exact owned receiver,
keeps its original session reservation/deadline, and asks for repair plus fresh
review. It preserves previous review receipts. Correction admissions use stable
keys and the objective's durable cycle counter; two repeated rejections end in a
terminal checkpoint without goal preparation or extra assignments. Out-of-scope
paths and changed/unavailable evidence cannot admit correction. This source proof
does not yet establish installed correction or context-replacement acceptance.

- Replace the single supported preflight workflow with configured instruction
  selection. Preserve host-controlled launch, grants, script approval and runtime
  ownership checks. Skills guide procedure; they do not grant capabilities,
  change scope or enlarge budgets. Missing or unreadable selected instructions
  block the affected transition; do not silently substitute another skill.
- Retain the mandatory checkpoint contract even when a selected writer uses a
  different presentation. Bind the checkpoint and review to exact source,
  successor, objective, configuration and evidence identities. Record the
  selected router's actual downstream review choice and evidence; invoking
  ask-Matt alone is not a review result.
- Record runtime readiness independently from a work verdict of accept, correct
  or blocked. Work review must state what changed, which acceptance criterion it
  advanced, evidence checked, scope deviations, unsupported claims, unfinished
  work and the justified next packet. A reviewer assertion alone cannot replace
  command, diff or native evidence.
- An accept verdict permits the authorized next packet only after runtime and
  budget gates pass. A correct verdict permits only a bounded remediation packet;
  it does not accept previous work. Count correction cycles at objective level
  across conversation replacement and controller restart. After two unsuccessful
  cycles stop and checkpoint. Scope/resource changes require the operator.
- Give each objective a durable identity, approved configuration revision,
  original wall-clock start/deadline and cumulative usage ledger. Count every
  assigned actor and attempt, including preflight and overlapping workers. Do
  not sum repeated snapshots of the same cumulative counter. Unsettled usage
  must be reconciled or conservatively reserved before admitting more work.
- Session allowance is bounded by both its configured limits and the remaining
  objective allowance. Reserve resources atomically before concurrent admission;
  reconcile actual usage afterward. Session and objective time deadlines are
  both enforced; overall elapsed time includes waiting and pauses. Context
  replacement does not reset either an existing session or the objective.
- At exhaustion, fence further model assignments, settle owned active work and
  preserve a checkpoint. Explicit operator extensions or resets append an
  attributable authorization revision retaining old spend, deadlines and
  receipts. Changing defaults alone does not renew an active objective.

### Revised testing and acceptance

Prefer the existing public CLI/MCP lifecycle seam, then verify an isolated
installed native transition. Tests assert observable decisions and effects,
not private implementation layout. Proposed seam remains subject to operator
confirmation in the skill's specification step.

- Effective configuration readback proves defaults and objective overrides,
  exact instruction selection and rejection of missing instructions before
  successor admission. Exercise a non-GitHub handoff/review selection.
- A ready runtime with unsupported completion claims receives correct or
  blocked, never accept. Demonstrate a meaningful change accepted against an
  objective and a scope-drifting/test-count-only packet rejected.
- Demonstrate bounded correction followed by acceptance, and repeated rejection
  stopping after two cycles across controller restart and successor replacement.
- Demonstrate two individually admissible sessions exhausting one overall
  budget; the next assignment is denied. Concurrent actors cannot over-reserve,
  failed preflight remains charged and replay cannot double-debit usage.
- Waiting past the original objective deadline prevents continuation despite a
  fresh session allowance. Unknown usage prevents new admission; an explicit
  operator extension retains the prior ledger and resumes only within its grant.
- Installed proof identifies actual selected instructions, actual review
  evidence/verdict, native goal limits, cumulative accounting and owned cleanup.
  Existing isolated refresh success does not prove this revised handoff contract.

### Proposed vertical slices and blocking edges

1. Configurable handoff and substantive preflight: effective configuration,
   selected writer/reviewer instructions, complete checkpoint and separate
   readiness/work verdict through public CLI/MCP. Blocked by: none for design;
   implementation follows confirmed specification and execution allowance.
2. Nested objective/session budgets: user configuration, durable accounting,
   reservations, deadlines, stop and explicit extension through the same public
   lifecycle path. Blocked by: slice1's configuration identity and readback.
3. Bounded correction and installed acceptance: exercise correction/accept/stop
   across successors, both tab modes, selected Matt workflows and actual native
   accounting; then reconcile integration/release gates. Blocked by: slices1–2.

The operator confirmed the public CLI/MCP seam, granularity and blocking edges.
Published specification: https://github.com/CochranResearchGroup/codex-wake/issues/254.
Approved slices: #255 configurable review, #256 nested budgets (blocked by #255),
and #257 bounded correction/native acceptance (blocked by #255 and #256).
All carry enhancement and ready-for-agent; readiness does not waive dependencies
or the execution-resource gate. Mutation/readback receipts are retained under
docs/dev/evidence/plan0156/configurable-review-issue-receipts.json.
Existing issues248–251 remain open; publication does not establish implementation,
acceptance, integration, release or a resource-window reset.

## Problem Statement

Operators and agents can open tabs but cannot request a verified agent spawn,
resource refresh or fresh-context handoff through one reliable procedure. A client
restart can look successful while its MCP connection is stale. Context renewal
can lose pending obligations or silently create new goal/resource authority.

## Solution

Provide three explicit lifecycle operations. An external lifecycle controller
records each intent, performs only its owned transition, verifies its result and
returns a durable receipt. Keep existing native thread/turn/goal primitives as
runtime authority; Wake adds coordination, evidence, recovery and tab attachment.

## Scope and user stories

1. As an operator, create a named tab in an existing approved workspace and launch
   Codex with a bounded assignment, then see exact identity and readiness.
2. As an agent, request a separate approved worker and deliver the initial task
   only after exact target readiness; no inherited peer identity or capability.
3. As an operator, refresh selected resources in the same conversation and see
   which skill/tool/config checks actually passed.
4. As an agent, preserve my unfinished work before requesting a refresh; do not
   lose drafts, active turns, pending replies or original wake deadlines.
5. As an operator, receive a stale-MCP result rather than a false refresh success
   or an automatic restart of a shared server.
6. As a context-heavy agent, write my own handoff checkpoint before ending.
7. As a successor, read that checkpoint, reconcile live state and run the
   ask-Matt-selected preflight before continuing authorized work.
8. As an operator, select a fresh context in the same owned tab or a new owned tab
   without confusing it with a same-thread resume.
9. As a goal owner, preserve objective, original approval and cumulative usage;
   give a new continuation allowance explicitly without erasing prior spending.
10. As a controller restarting after interruption, reconcile an exact existing
    transition instead of spawning duplicate tabs, turns, goals or messages.
11. As a peer, receive a meaningful routed result under the A2A response standard,
    and retain pending messages/claims that a fresh actor cannot inherit.
12. As an operator, close disposable agents without deleting their conversation
    history or disturbing unrelated tabs, services and goals.

## Implementation decisions

- Reuse native conversation, queue and goal methods; keep one small durable
  lifecycle journal and one external owner per transition. No general workflow
  engine, separate messaging broker or per-agent daemon.
- Proposed public operations: sessions spawn, refresh and handoff, with matching
  guarded MCP tools. Existing open/close remain compatible. Specify stable
  idempotency keys, exact source/target IDs, approved workspace/profile,
  checkpoint hash, requested resource checks, expiry and outcome evidence.
- Launch profiles are host-configured and bounded. No peer-selected credential
  paths, arbitrary shell launch strings, inherited parent identity or automatic
  A2A enrollment. Tab creation and task admission/execution are separate gates.
- Journal states: prepared, stopping, starting, awaiting_preflight, ready,
  completed, blocked, uncertain, expired. Persist target/pane/PID generation and
  submission receipt before advancing. An uncertain external effect requires
  reconciliation; no automatic replacement intent or alternate transport.
- Refresh requires a safe owned boundary (no active work/draft/pending obligation
  loss), actual client exit and exact-thread resume. Preserve original goal/wakes.
  Resource readiness must inspect actual loaded catalog/tool behavior, not merely
  file hashes, new PID or an agent's success sentence. Stale MCP blocks requested
  refresh success. No implicit fresh-thread fallback or shared daemon restart.
- Handoff requires an outgoing-agent-written checkpoint and an external verified
  transition. Prefer native fresh-thread creation plus exact queued handoff
  prompt to blind slash-key injection. An explicitly selected same-tab /new
  adapter must prove command acceptance and the new loaded identity; unpersisted
  fresh threads may need loaded inventory before their first message.
- Checkpoint contains objective, original authority locator, exact repo/worktree
  and commit/dirty-work disposition, acceptance remaining, evidence, pending
  wakes/messages/claim holders, resource accounting, fixed expiry, hard stops,
  next packet and reply route. Exclude secrets and raw private transcripts.
- Successor preflight reads canonical sources and current runtime first. Ask-Matt
  chooses applicable validation/review skills; invoking a router is not a health
  check or new approval. Store actual command/tool evidence and an explicit
  continue/blocked result before opening the continuation gate.
- New actor identity does not inherit capabilities or exclusive work claims.
  Leave original obligations attributed and fenced unless a supported explicit
  operator transition exists. Missing transfer support blocks only that affected
  handoff; no impersonation or replay. Native assignment needs no automatic bus
  enrollment when tracked A2A is not requested.
- Goal continuation preserves its approved objective and previous spending. Do
  not reset/clear an unfinished old goal or activate two autonomous owners. Native
  goal mutation provenance must reflect actual user authorization. The current
  protocol exposes tokenBudget but no wall-time budget field; controller enforces
  fixed approved time bounds independently using admissible time/continuity.
  Unknown usage/time or exhausted allowance holds continuation. A new successor
  window stays within cumulative caps unless the operator explicitly enlarges
  them. Fresh context does not authorize replenishment.
- Failure preserves checkpoint, original conversation and uncertain receipts.
  Retry the identical intent only when reconciled safe; rollback reattaches the
  old conversation without activating a second owner. Bounded attempts and fixed
  expiry survive controller restarts.

## Testing decisions and acceptance criteria

Use public lifecycle CLI/MCP calls, native thread/turn/goal readback and actual
owned TUI processes as the seam. Existing session lifecycle, message claim and
native delivery checks are prior art. TDD applies to production behavior, one
meaningful regression at a time; mock passes do not establish installed proof.

- Spawn: real tab/client, exact identity, initial prompt received/completed;
  duplicate and interrupted-intent reconciliation produce no duplicate effect.
- Refresh: old generation gone, same thread and goal unchanged, real updated
  skill/catalog and MCP resource proof; stale-tool fixture produces a blocked
  result. Active turns/drafts/pending obligations protected.
- Handoff: actual outgoing checkpoint, fresh loaded identity, successor reads
  exact hash, preflight evidence, one continuation owner and bounded authorized
  goal activation. Original pending work is preserved and separately attributed.
- Each slice covers unknown response, restart at effect boundaries, timeout,
  missing profile/capability, split/ambiguous pane and rollback without blind
  resend. Use deterministic fixtures then a bounded owned installed live run.
- Validate released/installed package, skill guidance and MCP discovery together
  before marking the final lifecycle product accepted. Skip hosted CI waiting
  under standing operator instruction; required local checks still run.

## Non-goals

No automatic global daemon restart, unrestricted delegation, auto-enrollment,
automatic worktrees, user quota reset, destructive conversation/history removal,
periodic refresh loop, context threshold guessed from transcript length, new time
service, or claim that /new alone transfers a goal or authority.

## Execution sequence and blocking edges

1. Plan0157: spawn through CLI/MCP with owned journal and exact initial task proof.
2. Plan0158: same-thread refresh and truthful stale-resource result, blocked by0157.
3. Plan0159: fresh-agent handoff/preflight/bounded goal continuation, blocked by0157.

Spawn is the initial ready frontier. Refresh and handoff share controller/skill
surfaces; primary owns integration and executes them serially (refresh then
handoff). Refresh completion is not an artificial dependency of handoff. Each
slice supplies its own installed evidence; last slice reconciles combined product
acceptance and installed skills/MCP. Maximum two correction attempts per seam,
one consolidated Standards/Spec review and one remediation pass; then reframe
or record the exact blocker rather than looping. Checkpoint after each slice.

## Definition of done

All three child criteria, cumulative authority/accounting, installed runtime
acceptance, release/rollback and exact process cleanup pass; receipts published;
root clean current main. Close tickets individually from actual evidence and
close this parent only after combined product acceptance. Plans/tickets alone do
not implement the feature or authorize broader runtime effects.

## Primary sources

Plan0155 findings and runtime summary record the real experiment. Retained
prototype branch: prototype/agent-lifecycle at 5e1b0ac. Installed Codex schema
confirms distinct goal mutation origin and absence of a goal-set wall-time field.
