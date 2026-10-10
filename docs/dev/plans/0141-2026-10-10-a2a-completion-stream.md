# Plan0141 — Finish usable agent-to-agent messaging

State: OPEN
Workflow: IN_PROGRESS
Owner: primary
Lane: P71
Branch: docs/a2a-completion-stream
Target: origin/main
Integration: sequential_ticket_prs
Work-Item: docs/dev/plans/0141-2026-10-10-a2a-completion-stream.md
Supersedes: Plan0119 execution sequencing only; preserves Plan0101/0119 acceptance
Depends-On: Plan0138, Plan0139, Plan0140 completed evidence

## Current State

Planning baseline main78ff33c; active released CLI0.11.1, source2e87f66.
Plan0138 ships explicit same-saved-recipient reopening. Plan0139 ships claim
instructions and ordinary close inventory. Plan0140 completed diagnosis: a native
completed turn contains the original notification while screen visibility stayed
uncertain; screen scroll and wrapping mechanisms reproduced. The exact original
capture is missing. Original message/attempt remain held and are never replayed.
Verification0122 accepts earlier live cancellation, reconnect, owned-worker restart,
multiroot, rollback and thirty-minute soak on their recorded source/version.
Plan0101/0119 remain OPEN; their stale sequencing is replaced by this plan.
Ticket0142 DONE after PR234/0076ae4, installed117 tests and actual native
submission/claim/completion/no-force cleanup. Active user goal now authorizes
Plan0141 execution with stop/checkpoint before2milliontokens or4hours. Next0143;
globalCLI remains0.11.1 until0144. Original old allowances remain historical.

## Problem statement and solution

Users need agent-to-agent messages to reach the selected conversation, be claimed
and completed, survive normal lifecycle changes and expose honest failure history.
The work stream currently ends at closed repair/diagnosis packets and leaves recovery
obligations without a current sequence. This plan owns the remaining sequence through
verified final installation, cleanup and requirement-by-requirement campaign closure.
Native queue receipts replace fragile live-tab screen evidence; held recovery and
processing ownership receive separate complete tickets. Earlier accepted work is
reused when its source, scope and freshness still qualify the corresponding claim.

## User stories

1. As a sender, I select an exact tab/thread and get an attributable admission.
2. As an idle recipient, I receive the notification despite screen scrolling/wrapping.
3. As a human, my draft or approval prompt prevents notification submission.
4. As a recipient, I acquire my work claim before processing and acknowledge completion.
5. As a sender, I receive one correlated reply after ending my initiating turn.
6. As an operator, I see uncertain effects held rather than automatically resent.
7. As a sender, I explicitly opt into reopening the original saved conversation.
8. As an operator, I distinguish a closed tab from a genuinely server-unloaded thread.
9. As an operator, I recover missing-state uncertainty without reviving old authority.
10. As a restarted worker, I cannot steal an existing claim or repeat completed work.
11. As a user, I run the released CLI with inspectable history and rollback targets.
12. As an operator, I know which mandatory obligations are complete and which remain.

## Implementation decisions

Use the existing dispatcher, notification binding and native queue contract; no
new Codex patch or parallel messaging framework. Native acceptance validates exact
thread and queue receipt. Keep immediate idle/composer/process/identity/expiration,
capability and reply-arm checks. Queue acceptance proves submission, not processing
or atomic idle safety; document the pre-submit race. Ambiguous entered effects stay
held with no second transport. Saved-recipient reopening retains explicit opt-in.
Recovery never treats unavailable post-backup state as absent or completed. New
authority and audited explicit disposition must fence old actors and notifications.
No schema change is assumed; any necessary change must declare migration/rollback
within its ticket. Existing GLOSSARY.md is terminology authority.

## Sequence and blocking edges

| [0142](0142-2026-10-10-native-live-submission.md) Native submission for existing live tabs | none | DONE |
| [0143](0143-2026-10-10-native-live-safety-and-round-trip.md) Qualify normal request and reply after transport change | 0142 | READY |
| [0144](0144-2026-10-10-release-native-live-submission.md) Ship and activate qualified native live submission | 0143 | BLOCKED |
| [0145](0145-2026-10-10-server-unloaded-recipient.md) Qualify explicitly reopened server-unloaded recipient | 0144 | BLOCKED |
| [0146](0146-2026-10-10-held-recovery-disposition.md) Make held recovery disposition explicit and safe | none | READY |
| [0147](0147-2026-10-10-processing-claim-generation-recovery.md) Recover processing ownership across generations | 0146 | BLOCKED |
| [0148](0148-2026-10-10-remaining-fault-and-ancestry-proof.md) Finish remaining fault and session-isolation proof | 0142, 0146, 0147 | BLOCKED |
| [0149](0149-2026-10-10-final-campaign-acceptance.md) Close the work stream from complete evidence | 0143, 0144, 0145, 0146, 0147, 0148 | BLOCKED |

Execution priority0142→0143→0144→0145→0146→0147→0148→0149. Ticket0146 is
independently unblocked but does not displace the live submission critical path.
Only one substantive ticket IN_PROGRESS at a time. Recovery contracts and live
transport share authority boundaries, so implementation is serialized. Read-only
ledger preparation could be disjoint; no agents or parallel lanes are requested.
Each ticket is one checked-in repo-native work item, with outcome, owner, blockers,
public test seam, bounds and terminal condition. No remote issue is created by this
planning task; issue181 remains unchanged. The user approved the four-stage flow:
repair, installed qualification, ship, then outstanding-obligation completion;
its final stage is decomposed here into unloaded, recovery, claim/fault and closure
outcomes. No speculative prefactoring ticket precedes a behavior result.

## Requirement and evidence ledger

| Requirement family | Existing evidence and its exact limits | Remaining owner |
| --- | --- | --- |
| Selectors, enrollment, envelopes, permission, replies, FIFO/idempotency, limits, receipts | verification0106 maps original families; later0107-0110 and0122 qualify bounded implementations and installed/live packets | 0148 reconciles every original row; 0149 final identity |
| Actual unassisted request/reply; reconnect/restart; multiroot and denial | verification0122 PASS on recorded0.7.1/workload | 0143 validates changed transport; 0149 rechecks invalidated gates |
| Retention, backup, equivalent restore, held damaged-source recovery | verifications0107/0108/0109/0110; hold release not qualified | 0146/0147/0148 |
| Release, installed rollback and resource/soak | verification0122 and Plan0138/0139 closeouts; version/workload-specific | 0144,0149; reuse without claiming stale version proof |
| Explicit same-saved-thread reopening | Plan0138 completed native/installed exchange, default hold | 0145 reconciles genuinely notLoaded status evidence |
| Result claims and ordinary closure | Plan0139 actual consumption and separate no-force control | 0142/0143 preserve behavior |
| Live submission evidence | Plan0140 diagnosis; original uncertainty retained | 0142 native queue receipt |
| Hold release, unknown gaps and legacy notification fencing | verification0110 held recovery only | 0146 |
| Cross-generation processing ownership | verification0122 explicitly excludes broader recovery | 0147 |
| Broader ancestry, interruption/writer and compatibility fault cuts | verification0106 original requirements;0122 retains these gaps | 0148 |
| Overall Plan0101/0119 definitions of done | Current state NOT COMPLETE | 0149; no mandatory row may disappear |

## Testing decisions

Test externally visible message, claim, hold, notification and close behavior through
public dispatcher/mailbox/CLI seams. External-runtime fixtures replace native queue,
pane and process boundaries; avoid database queries as passing oracles. Use existing
live/saved transport, claim and session tests as prior art. The approved repair's
public seams already match the requested behavior; no new test interface is needed.
Installed qualification unsets source PYTHONPATH and binds results to immutable
source/version. Live receipts distinguish admission, submission, recipient outcome
and native completed turns. Freeze finite inputs/limits before each packet; stop on
ambiguous effect, reconcile exact original IDs and never create a replacement intent
to hide failure. Reuse earlier acceptance only with explicit source/scope/freshness
mapping. Hosted CI waiting remains user-waived; no hosted pass is inferred.

## Authority, boundaries and stop conditions

User approved writing this completion plan and ordered tickets2026-10-10. The plan
organizes execution; readiness does not independently grant effects. Routine bounded
implementation under standing messaging authorization follows registered tickets.
Only owned disposable acceptance threads, workers and stores may be touched. No
production damaged-store recovery/hold release, unrelated thread messaging or shared
service restart is authorized here. A genuinely required such effect is prepared as
a concrete reviewable operation, then the missing authority is stated explicitly.
Preserve LitScout repair, every unrelated session and all old failed/uncertain
receipts. No replay or manual completion of Plan0139's old uncertain message.
No cross-user federation, broadcast, autonomous spawning, optional MCP facade,
custom Codex patch, fresh blanket soak or speculative infrastructure expansion.
A bounded verified blocker remains OPEN with exact missing proof/action. Neither
deferral nor a new filename resets review/retry history or closes a required gate.

## Definition of done and restart procedure

All eight tickets DONE with their exact evidence; every original mandatory family
has qualifying proof on the applicable source/installed identity; remaining changes
are reviewed, integrated, released and rollback-qualified. Owned cleanup is verified,
root main is clean/published and necessary branch custody is durable. Only then close
Plan0119 and Plan0101 under their own definitions and this plan. Preserve held old
effects as held when that is the contract; never claim recovered processing from
receipt visibility. Optional features and indefinite scale are excluded.

A fresh session reads this plan, its next unblocked ticket, applicable policies,
active-lane catalog and exact Git/installed identities. It reconciles source/receipts
before using old evidence, starts only one owned ticket, and updates status/proof as
it progresses. Next concrete action: register an isolated ticket0142 implementation
branch, read TDD, and write the public native-receipt regression before changing code.
