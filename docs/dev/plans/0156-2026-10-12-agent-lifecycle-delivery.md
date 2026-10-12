# Plan0156 — Spawn, refresh and fresh-agent handoff

State: OPEN
Workflow: IN_PROGRESS
Owner: primary / ecochran76
Target: origin/main
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/248

## Current State

Execution started on `feat/agent-lifecycle` from origin/main a741010 under the
operator's execute-Plan0156 goal. Plan0157 is the serial critical path; 0158 then
0159 follow. Primary owns shared controller/CLI/MCP integration. One read-only
worker may inspect native contracts; it has no effect or implementation authority.
Checkpoint each child and before installed effects, with a 45-minute backstop;
stop and checkpoint before cumulative 2,000,000 tokens or six hours. Goal runtime
start is epoch1791817417; six-hour ceiling1791839017. Native goal counters are the
token authority. Two attempts per failing seam and one consolidated review plus
one remediation pass remain the campaign bounds. No completed criterion yet.
Public CLI/MCP are deterministic seams; native queued-message and owned TUI
readback are installed seams. Red/green commands belong in the evidence ledger.

Existing open/resume/close accepted; Plan0155 disposable probe complete. Same-thread
TUI restart retains its thread's MCP connection on installed Codex0.162.1; fresh
conversation loads the revised MCP. This plan specifies a future lifecycle product,
not a claim that the controller or goal migration is implemented.

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
