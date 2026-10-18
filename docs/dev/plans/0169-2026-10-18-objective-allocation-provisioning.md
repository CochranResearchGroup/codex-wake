# Plan0169 — Automatic caller provisioning with allocation continuity

State: OPEN
Owner: primary / ecochran76.
Branch: fix/289-allocation-campaign-control. Base: 89e3eb8. Target: origin/main.
Work item: #289, https://github.com/CochranResearchGroup/codex-wake/issues/289.
Product contract and testing seam: confirmed by user; ADR0002.
Tracker state: OPEN (ready-for-agent). Implementation: in progress; controller regression reproduced.
Plan version: 2; includes operator clarification on campaign-scoped graceful shutdown.

## Current State

2026-10-18 v2: the user explicitly requires graceful campaign winddown, followed
by goal pause and bounded interruption after the checkpoint grace/reserve, while
the halted conversation remains idle and able to answer the operator. The old
controller interrupts every later active turn, including operator replies after
pause. Public regression reproduced that failure. Current caller enrollment also
reproduces missing host grant (`held`, `armed:false`); no host policy was changed.

Integration checkout: `/home/ecochran76/workspace.local/codex-wake-allocation-control`,
base `dbd37ca09f9a13f4ae54b98f8f8ea4b0888a86c5` (spec over main89e3eb8).
Owner: primary. Serial path: control regression -> bounded grace -> native
provisioning capability -> authority/accounting -> integrated validation/review.
One read-only independent native capability investigator is allowed by policy0021;
its runtime handle is `/root/native_authority_capability`. No other workers.

### Execution ledger

- Campaign stop ownership: running; red public controller test caught interruption
  of `operator-reply` after verified pause. Local fix scopes interruptions to
  persisted stop turns; 11 existing/new controller tests now pass.
- Graceful failure winddown: pending; preserve hard deadlines, queue a checkpoint,
  pause campaign continuation and interrupt only observed campaign turns at grace.
- Provisioning trust capability: running; no automatic grant effects before proof.
- Allocation continuity / accounting: pending behind trusted admission; long-history
  accounting failure is separate from grant absence and remains unqualified.
- Public MCP / installed qualification / review: pending.

Bounds: primary stop/checkpoint before2Mtokens or6h from native goal creation
1792332310; hard deadline1792353910 (2026-10-18T20:05:10Z). Requested reserve10%
and900seconds; MCP enrollment failed, so no armed external enforcement claim.
Reconcile `get_goal` after material packets and retain a bounded read-only/source
repair loop; do not mint a production grant to avoid that error. Max2 attempts
per unresolved probe,1 broad review plus1 remediation, checkpoint at each material
transition. Current discovery bound:6 focused graph calls and35KiB focused source
per unresolved question before reassessment. Initial source discovery exceeded
that source target through capped tool output; subsequent reads are narrowed.


v0.17.3 corrects fractional checkpoint percentages. Existing MCP goal-limit
admission requires an exact caller grant; a new conversation does not inherit
one. Native supervision receipts are indexed by caller and retain same-session
replacement-goal usage; they do not provide an objective-owned cross-conversation
allocation ledger. Private policy differential reproduced missing newcaller
refusal independently of schema/cache. Plan0168 caller-admission evidence owns
that diagnosis. Plan0168 remains OPEN for its separate production refresh gate.
No current grant, enrollment, goal, allocation, monitor or MCP cache changes are
part of this specification. The mistaken instruction to bypass the external
monitor was retracted as intended for another conversation and grants no override.

## Problem Statement

A user supplies token/time limits and expects the existing dev agent to register
them and work. Today a new native conversation can repeatedly stop at missing
host setup even after installation and an explicit user allocation. Manually
copying grants is error-prone and cannot establish whether the new conversation
continues an old allowance or has an explicitly renewed one.

## Solution

Use the existing MCP goal-limit workflow to provision the verified caller from
verified user resource authority, attach it to one objective allocation and
verify accounting plus the independent watcher before continuation. A successor
retains the same cumulative usage and deadline unless the user explicitly renews
or resets that named allocation. Missing or ambiguous evidence gives a specific
hold and recovery action; repeated calls never create another allowance.

## User Stories

1. As a user, I want token/time limits to enroll my current dev conversation without manual UUID setup.
2. As an agent, I want one enrollment workflow that provisions and validates enforcement before resource-limited work.
3. As a user, I want fresh context on the same objective to retain prior spend and the original deadline.
4. As a user, I want unrelated objectives to retain their separate authority and counters.
5. As a user, I want an explicit renewal applied only to the named objective or continuation.
6. As a user, I want allocation history retained when an explicit renewal or reset occurs.
7. As an agent, I want an ambiguous continuation to identify the missing link and a concrete recovery action.
8. As an agent, I want to distinguish missing authority, not enrolled, unknown accounting and watcher failure.
9. As an operator, I want a caller's claim checked against trusted native identity and user request evidence.
10. As an operator, I want quoted instructions, peer messages and checkpoints to be insufficient to mint resource authority.
11. As a user, I want fresh input plus output and attributable delegated/retried work charged once; cached input is excluded unless explicitly selected.
12. As an agent, I want replay, restart, goal replacement and context changes to preserve the same allocation.
13. As an operator, I want concurrent requests and successor races unable to multiply the allowance.
14. As an agent, I want fractional checkpoint reserves such as17.5percent to remain supported.
15. As a user, I want checkpoint requests followed by verified native goal pause and exact-turn interruption at exhaustion.
16. As a user, I want unrelated conversations and the shared Codex server preserved.
17. As an operator, I want existing explicit grants to remain usable without silent migration or reset.
18. As an agent, I want public status to explain the governing objective, original deadline, charged usage and readiness.

## Implementation Decisions

- Allocation authority belongs to the named objective; caller identity identifies
  a participant, not a new allowance. Preserve separate allocation and caller
  records. Same-session replacement goals retain existing behavior.
- Extend the existing goal-limit MCP enrollment/status workflow rather than
  requiring agents to enumerate tabs, repair identities or edit host files.
  Host endpoint/home/path selection remains operator-controlled.
- Automatic provisioning follows verified user allocation evidence for the
  verified caller. Model claims, existence of a conversation, tab/CWD similarity,
  peer bodies and a checkpoint alone cannot authorize it.
- A host-verifiable request reference binds source, scope, limits and renewal
  intent. An objective/allocation reference binds a continuation. References are
  evidence handles, not authority supplied by the caller. Reuse one reference
  for retries; unsupported or ambiguous evidence holds without a grant write.
- Qualify the native identity/request-evidence adapter before implementing the
  automatic effect. Stock shared MCP caller attestation and supported native
  message references are not yet established. If unavailable, surface the exact
  missing prerequisite and supported setup path; never fall back to trusting a
  caller-selected UUID or reading arbitrary rollout text as authorization.
- A first verified allocation creates a durable objective identity. Verified
  successor links attach to it without changing limits, time origin or previous
  usage. Continuity must come from attributable authority, not inferred location.
- An explicit renewal changes only its named allocation. A fresh allocation or
  counter/time-origin reset must be explicit in that user instruction; an
  ambiguous increase/renewal/reset holds for clarification. Preserve previous
  generations and cumulative history; never overwrite old receipts as a reset.
- Charge attributable fresh input plus output once across original and successor
  sessions, excluding cached input by default and including delegated work.
  Cache-inclusive accounting requires explicit selection; persist that basis. Missing histories, uncertain final
  accounting or unverifiable lineage hold admission rather than assigning zero
  prior spend. Bound scans and retain authoritative accounting anchors.
- Persist admission idempotently and fence concurrent participant/renewal updates
  against one objective allocation. A timeout has a reconcilable state; retry
  cannot multiply budgets, attach twice, extend a deadline or replay a renewal.
- Return a structured reason, affected allocation/caller, missing evidence,
  whether an effect was attempted and concrete next action for every hold.
  Automatic provisioning, enrollment, accounting qualification, watcher health,
  work admission and stop proof remain distinct readiness boundaries.
- Keep existing armed/checkpoint_requested workflow and sampled-token limits.
  Exhaustion stops registered conversations within the verified objective scope;
  no arbitrary process/descendant termination or exact token ceiling is claimed.
- Existing explicit grants remain valid. Legacy caller receipts are not silently
  merged into a shared allocation; conversion requires qualified authority and
  complete accounting, with retained legacy evidence and rollback receipts.
- Missing/stale MCP tools produce a version/setup hold. Automatic shared reload,
  expanded refresh approval and automatic goal resume are not part of enrollment.

## Testing Decisions

Proposed primary seam: actual public MCP enrollment/status through CLI and an
independent watcher, against deterministic native identity/request/usage fixtures.
Exercise an original conversation and a successor sharing one objective, with
an unrelated conversation as a control. Observe only public outcomes and native
control effects; helper mocks or private-ledger shape are not acceptance proof.
Existing public goal-limit stdio, controller and rollover qualification tests
provide the harness; extend them with multi-conversation authority/accounting.

Blocking acceptance scenarios:

- Verified user limits plus a verified ungranted caller provision/enroll without
  manual policy edits; readiness requires qualified usage and a fresh watcher.
- Repeating the same request in another process returns the same allocation,
  counters, deadline and effect disposition.
- A verified successor charges prior and new usage once; replacement goals,
  restart and repeated handoff cannot replenish the allowance.
- A copied tab name/CWD, forged caller/reference, peer quotation or missing user
  authority produces a precise no-effect hold, never a default grant.
- Missing/ambiguous allocation links, unqualified usage, stopped watcher and
  unsupported identity evidence each hold with distinct actionable recovery.
- An explicit scoped renewal/reset changes only the named allocation, applies
  once and retains its old generation. Another objective remains unchanged.
- Concurrent original/successor enrollments and renewal races retain one budget;
  crash/restart before or after grant persistence reconcile without duplicate
  authority. Unknown effects never authorize a new identity or allocation.
- A 17.5% reserve reaches the correct checkpoint threshold; checkpoint time
  consumes the existing allowance. Exhaustion pauses the verified registered
  goal(s) and interrupts exact active turns; unrelated conversation untouched.
- Legacy grants continue working; unqualified legacy migration holds.
- Stable clock/counter fixtures prove deadline continuity and unknown-time holds.

After source qualification, add a bounded installed native acceptance using only
owned test conversations and explicit test-user authority. Demonstrate original
and successor continuity with an unrelated control, without model/provider work
or production session changes. Prove cleanup with a fresh process census.

Testing seam confirmed by the user on2026-10-18: public MCP original/successor
allocation continuity with an unrelated conversation as a control.
No acceptance execution or native effects are authorized by this document alone.

## Execution Packets

1. Qualify trusted native caller/request evidence and continuation references.
   Outcome: deterministic public acceptance fixture plus supported evidence
   contract, or precise blocked capability. No grant effects before qualification.
2. Implement objective allocation identity, idempotent user authority and replay
   under the public enrollment seam, with negative authority cases first.
3. Implement successor accounting and scoped renewal, including concurrency,
   incomplete histories and legacy migration holds. Preserve cumulative history.
4. Integrate watcher/native controls and actionable status. Update discovery and
   instructions so agents use this automatically for user-specified limits.
5. Bounded review and installed qualification; exact-main release/install only
   after gates. Production provisioning remains a separately evidenced admission,
   never a claim inferred from shipping a package.

Owner: primary. Critical path is serial: evidence qualification → authority ledger
→ accounting/renewal → enforcement → acceptance. Independent documentation and
fixture preparation can be split later only when repository rules permit it;
no worker or parallel runtime authority is granted here.

## Additional v2 acceptance: campaign control

- A reserve request steers only the observed campaign turn to checkpoint; consumes
  the original allowance and never launches another model turn.
- Missing accounting/controller qualification holds product continuation but permits
  bounded setup diagnosis, checkpoint writing and operator replies. Installed agent
  instructions must distinguish these from resuming autonomous campaign work.
- A loss of qualification with an active campaign starts one persisted bounded
  winddown window, capped by the original time deadline. Repeated polls, process
  reconstruction and enrollment cannot restart it. Exact grace is exposed in status.
- At grace expiry or allocation exhaustion, pause the campaign and interrupt only
  its captured exact turns. Once paused, operator reply turns are left alone,
  including after controller reconstruction, boot mismatch or revoked grants.
- Re-activating the campaign without renewed authority remains held and paused;
  acknowledging an operator message does not reset or resume the allowance.
- Preserve uncertain native effects and verified stop ownership; no broad session,
  shared server or descendant process termination.

## Out of Scope

Shared Codex restart/reload, arbitrary caller-selected host paths, tab/CWD-based
allocation inheritance, automatic goal resume, implicit resource renewal,
production counter repair, OS memory/CPU containment, arbitrary process stops,
retroactive fabricated user authority and execution of remote-view product work.

## Definition of Done

The public installed workflow automatically provisions a verified caller from
verified user allocation authority, admits work only with qualified accounting
and a fresh watcher, preserves objective-wide cumulative usage/deadline across
verified successors, applies scoped explicit renewal once and makes holds
recoverable. Deterministic public tests and bounded owned-native acceptance
prove the behavior and unchanged unrelated authority; exact-main delivery and
repo/tracker reconciliation record their separate completion boundaries.

## Further Notes

Confirmed user decisions: automatic verified provisioning; actionable ambiguous
continuation holds; cumulative usage/deadline preserved without explicit renewal;
renewal limited to its named objective/continuation. This product contract does
not establish that native APIs already expose the needed trusted evidence.
The old Plan0168 production refresh remains expired with no new retry authority.


## Checkpoint v2 — resource stop, 2026-10-18

State transition: active -> paused at explicit user token stop. Source changes
are uncommitted on fix/289-allocation-campaign-control (base dbd37ca). User's
2M-token limit was exceeded: repaired read-only `observe_usage` qualifies
6,040,982 cached-inclusive tokens for goal1792332310. Native `get_goal` earlier
reported156,997 tokens; that display was not a substitute for the accounting
contract. Primary checked the qualified cumulative total too late. No fresh
allocation or counter reset is authorized. Stop source work; retain chat for
operator replies. No release/install or native production changes performed.

Acceptance evidence: 29 focused tests pass in3.524s (goal_limits_mcp,
goal_supervision,goal_usage); original operator-reply failure and accounting
payload failure were observed red before green. Source old-session accounting
now qualifies1,034,781 tokens in0.226s instead of usage_history_byte_limit; this
was read-only and does not repair its production receipt. Integration,
installed/native acceptance, broad presubmit and review remain pending.

Changes: persisted campaign stop-turn ownership, recovery using legacy effect
turns, operator replies preserved after pause, accounting-loss winddown bounded
by60seconds/configured reserve/original deadline, repeat enrollment cannot renew
grace, explicit campaign resume is paused again, streaming accounting retains
usage events separately from bounded scanned payload volume, missing-grant MCP
error reports exact no-effect host prerequisites and permits operator interaction.
Installed skill text is unchanged and must be updated to distinguish campaign
holds from operator replies before delivery. No automatic provisioning effect
has been implemented. Main and specification checkouts remain untouched.

Read-only investigator /root/native_authority_capability established that stock
shared MCP has no qualified authenticated caller/operator request bridge.
Native dynamic-tool requests include threadId/turnId/callId separately from model
arguments; persisted userMessage lacks authenticated origin and injection APIs
exist. NEW UNQUALIFIED LEAD: installed0.163 hooks expose userPromptSubmit and
preToolUse handlers, including command/MCP handler variants and trusted metadata.
UserPromptSubmit can also fire for automated Wake submissions. Next investigation
must qualify actual provenance, not assume hook event name proves human origin.
Generated schemas: /tmp/issue289-native-schemas. Investigator asked to stop at
this checkpoint. Do not discard this hooks lead or claim provisioning impossible.

Progress classification: outcome_progress for source controller/accounting repairs;
resource compliance regression for checking cached-inclusive spend too late.
Next action: operator disposition of exhausted allocation, then complete trusted
hook bridge qualification, remaining admission/continuity packets, skill updates,
installed public qualification and bounded review. No automatic goal resume.


## Checkpoint v3 — user corrected accounting and resumed

The user explicitly clarified that cache-inclusive accounting is the wrong
default and continued the goal. The prior v2 exhaustion conclusion is withdrawn:
6,040,982 was a cache-inclusive diagnostic total, not the requested fresh-token
allowance. No fresh allocation or time-origin reset is implied. Source read-only
qualified accounting reports230,812 fresh tokens at2026-10-18T14:31:32Z, original
time deadline2026-10-18T20:05:10Z. Native goal status activation remains host-owned;
this agent has no update_goal resume operation. The user sent explicit active
status. Continue under the unchanged2M fresh-token /6h limits.

New enrollment defaults to fresh tokens; cache-inclusive is explicit opt-in.
Persist basis on the supervision receipt; preserve legacy basis unless explicitly
changed. A qualified basis change re-evaluates the same original history and
retains prior accounting, original deadline, generation and stop latch. Never
silently compare counters in different units or infer a reset/resume.

Validation:30 focused controller/accounting/MCP tests pass in3.969s. The fresh
accounting test failed before the source change. Additional public packaged
qualification and one bounded Standards/Spec review remain pending.

Native investigator completed two bounded reads; source-backed capability report
is `/tmp/issue289-native-schemas/authority-capability-report.json`. Hooks provide
native caller/tool IDs and updatedInput, but UserPromptSubmit lacks authenticated
operator origin and also fires on automated Wake submissions. Goal-set origin is
caller supplied and absent from goal readback. Automatic grant creation remains
blocked on an authenticated operator-ingress receipt; no grant effects attempted.
Next safe units: packaged shutdown/accounting qualification, skill correction,
bounded review and recoverable source checkpoint. Wider289 remains incomplete.


## Pending authorization-contract decision

The primary asked the operator whether to allow private host-delegated enrollment
within fixed resource ceilings, instead of requiring per-session grants backed
by authenticated prompt-origin evidence unavailable on stock0.163. No answer has
been assumed. Current ADR0002 operator-origin requirement remains in force.

Concrete proposed boundary: an operator-owned policy delegates enrollment into
one named objective allocation with fixed limits/deadline and host endpoint/home;
a trusted native hook binds the actual caller/tool invocation to the request.
It permits participant enrollment, not minting another allowance or extending the
original one. Successors use the allocation reference; ambiguous links hold.
Private host policy is the authority, not unsigned prompt text. Other objectives
and old grants are unchanged. The reviewable effect would be a caller enrollment
receipt under that delegated allocation; no production mutation before this
contract change is accepted and the public negative cases pass.

Until that decision, continue only the independent reviewed control/accounting
repair. One Standards/Spec review (/root/control_repair_review) found no candidates
in that bounded surface. Two isolated installed MCP/controller scenarios passed
with fresh accounting and surviving operator turns; test watchers exited0 and
fresh /proc readback confirms both exact PIDs absent. Receipts are under
`docs/dev/evidence/plan0169/`. Production installation remains unchanged.


### Validation checkpoint v3a

Public installed candidate: `/tmp/cw289-installed`, wheel SHA/source hashes bound
in evidence/plan0169/installed-{fresh,grace}.json. Both scenarios PASS: an
independent watcher observes checkpoint then pause/exact-turn interruption;
operator reply remains active under repeated polling with paused goal. Fresh
scenario includes5000cachedinput per response and charges40then110 fresh tokens.
Accounting-loss scenario observes winding_down before stop; original deadline
not extended. Both watchers exited0; fresh exact-PID census confirms absence.
Production installation was not modified. The two initial script invocations
against the old editable main environment failed (charged5040 at enrollment),
which is retained red evidence; the qualification intentionally drops PYTHONPATH
and must use the candidate's installed interpreter.

Presubmit:1369 tests ran in127.152s;76 failures,4 errors,1 skipped.23 unchanged-main
time/migration tests reproduce11 failures and3 errors. Full main baseline is now
running to classify the entire failure set; no full-suite PASS claim. Policy
wiring and compileall pass. Planning audit no longer flags0169; remaining0166,
0167,0168 deterministic-state findings are untouched older metadata. The first
unowned detached unittest launcher produced no result and its PID is absent;
only owned exec-session92559 is the completed candidate presubmit evidence.
Read-only current accounting at latest check312,644 fresh tokens, below2M.


### Validated bounded repair checkpoint

Full unchanged-main baseline completed1363tests/124.088s with the same76failures,
4errors,1skip. All80 failure/error identifiers exactly match candidate1369tests;
no new failed identifier. No full-suite pass or release gate waiver is claimed.
Compact comparison is evidence/plan0169/presubmit-comparison.json. Six additional
regressions and the isolated installed scenarios pass; source repair is reviewed
and preserved, production remains unchanged. Native actual-client acceptance and
self-provisioning remain open. Pending operator decision is unchanged and is not
inferred from silence. No production resource policy or counters were modified.
