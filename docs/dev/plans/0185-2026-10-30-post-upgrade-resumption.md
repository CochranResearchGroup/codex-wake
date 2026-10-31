# Post-upgrade work resumption

State: CLOSED
Outcome boundary (preserved): COMPLETE — isolated native qualification; working rollout not performed
Owner: primary / wake2
Authority: operator approved Ask Matt recovery contract and implementation on2026-10-30.
Native base: dfde754e597f0b4766f5b22fbeb990d2e78fe151.
Depends on: Plan0184 native checkpoint gate. Separate prior work remains untouched.

## Current State

The qualified native 0.165.0 package checkpoints active work, replaces the daemon, and automatically continues eligible conversations from durable handoffs. Native startup recovers after updater disappearance or an accepted-turn crash. The 13 public runtime scenarios, scoped checks, review and preserved failures are recorded in [the qualification packet](../evidence/plan0185/qualification.md).

CLI SHA256 `4a38fa1793575c706630fc5765e59e3ad327b486ba637383bc81766f05ff476f`; native local custody commit `6efee650fb0633a229adbd33bb826e3f85b899a3`. Only UID1017 laboratory effects were performed. Working installation remains untouched, governor masked/inactive, protected hashes unchanged, and dummy process census empty. Independent Plan0183 real-model quality remains OPEN.

## Contract

After matching replacement binary is serving native control requests, read durable handoffs and resume only work paused by that upgrade. Previously paused/blocked/exhausted/idle work stays stopped. An active native goal briefly idle between turns remains owned work if its original goal was active. Preserve thread identity, root turn attribution, permissions, objective, goal identity, consumed tokens and ceiling; no allocation/deadline renewal. Existing external supervision retains authority; no controller is disabled or recreated. Changed/unknown resource authority holds resumption. Pending external operations are reconciled before repetition through explicit recovery context.

Use one durable operation/thread record, independent of terminal attachments. Concurrent recovery attempts must not create multiple continuations or steer user work. A persisted dispatch intent with no provable acceptance is held as unknown; never infer non-submission from absent history. An accepted continuation remains accepted across response loss and crashes. Native startup recovers pending operations; no operator wake ceremony. Explicit user/governor goal changes after checkpoint, including paused-to-paused, cancel automatic recovery. No swallowed history append or wall-clock timestamp comparison may serve as the sole cancellation proof.

Keep the upgrade barrier through recovery and block automatic goal starts during incomplete startup recovery. Reuse cold daemon resume, permission validation, root-turn metadata, and continue_turn_if_idle's latest-turn guard. Goal activation can itself start work, so activate only under this barrier with one explicit internal continuation. Retain a durable goal-control generation for external goal set/clear to fence later pauses. Failed starts/rollback/mismatched target binary never wake work. Older servers lacking recovery sealing may complete cooperative checkpoint installation but remain paused with an explicit compatibility result; no unsafe automatic fallback.

## Execution and seams

One primary serial implementation lane; one bounded read-only discovery worker for existing native idempotency/goal behavior (returned facts retained here). No parallel writes. Continue this session while it retains the implementation's primary context.

1. R1 — Actual supported upgrade and model-facing continuation, same goal/root/thread and checkpoint. Observe red on current candidate before minimal recovery implementation.
2. R2 (blocked by R1) — Durable startup recovery and duplicate/response-loss/crash reconciliation at native recovery RPC and supported startup seams. Claim states: sealed, dispatching, resumed, held, skipped; operation phases include installing/recovering/recovered/recoveryHeld. Unknown remains explicit.
3. R3 (blocked by R2) — Negative eligibility: original pause, idle session, user/governor pause after checkpoint, spent budget, superseding work, invalid handoff and wrong/failed binary. Preserve watcher/allowance files.
4. R4 (blocked by R3) — Exact immutable complete package in UID1017: multiple real tabs, fresh launch, rollback, interrupted coordinator/server, final process census. Native component/protocol checks, independent Standards and Spec review, local source custody and truthful closeout.

Test existing public native RPCs and updater first; one deep recovery RPC is justified because ordinary turn/start only correlates clientUserMessageId, does not deduplicate and can steer. Native queue insert creates a fresh ID and also lacks idempotent enqueue. Existing crash recovery consumes its snapshot before replay and cannot prove exactly-once acceptance; reuse its safe continuation primitives without inheriting that loss window. Discovery worker used two bounded read-only packets and no runtime effects; primary owns decisions.

## Non-goals and limits

No working-host cutover, upstream OpenAI push, generic queue redesign, automatic grant renewal, whole-workspace Rust suite, Windows runtime acceptance, or fully automatic downstream build registry transaction. Provider fixtures are explicitly scripted localhost; independent real-model quality remains a separate unproven gate. Preserve old failed receipts and Plan0184 PID-time flake.

## Definition of done

Native work resumes from the operation's checkpoint after healthy upgrade/startup; one continuation per conversation regardless of tab count; interruption/retry cannot duplicate uncertain delivery; negative cases remain paused with visible reasons; counters and authority remain unchanged except actual continuation usage; exact package and public paths qualified in the separate Linux account. Retain all evidence and one explicit memory disposition. No implementation-only pass or updater exit alone counts as acceptance.

## Acceptance and remaining boundaries

R1–R4 accepted for the exact isolated package: normal update/resume, original tabs and mirror, root/counters, replay, fresh launch and rollback; response loss and same-ID crash recovery; later/original pauses, native budgetLimited, external deadline, changed handoff and target bindings; actual failed replacement followed by startup recovery. First adoption from a checkpoint-only daemon was separately qualified with a real executable change and live replacement notices in original/fresh tabs; it deliberately stays paused without recovery seals.

Focused selected checks passed; all earlier reds, stale/zero-test attempts and fixture failures remain attributable in user state and the acceptance packet. No full suite, working rollout, Windows run or independent real-model qualification is claimed. One unavailable memory disposition was recorded because project routing remains unresolved; client-side provenance stays outside Git.
