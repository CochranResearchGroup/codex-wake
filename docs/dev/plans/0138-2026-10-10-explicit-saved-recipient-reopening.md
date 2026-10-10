# Plan0138 — Wake an explicitly authorized saved conversation

State: CLOSED
Workflow: COMPLETE
Lane: P68
Branch: feat/saved-recipient-reopening
Target: origin/main
Integration: squash_pr
Owner: primary
Work-Item: docs/dev/plans/0138-2026-10-10-explicit-saved-recipient-reopening.md

## User decision

Approved2026-10-10: when the sender explicitly requests reopening, wake the same
saved conversation even when its tab is closed. Otherwise wait and explain why.
If it cannot reopen safely, hold visibly; never switch conversations or send twice.
This decision supersedes Plan0119's unconditional no-resume rule only for this
explicitly requested behavior. The ordinary default remains hold.

## Current state

Complete2026-10-10: PR232 integrated source79c8c29185c48e3d01eb125a91284f4373cdf999;
v0.11.0 released and global CLI activated from its immutable installed prefix.
closeout.md records criterion-by-criterion evidence and retained limitations.
Owned acceptance tabs/processes are closed; histories and failed samples remain.
The feature checkout is removed with its source branch durably retained. Wider
Plan0101/0119 remain OPEN. The following baseline describes the starting state.

Baseline main94dc58c, installedv0.10.1. Native scheduled wakes already accept
--resume-missing and persist same_thread policy. Existing fixtures exercise the
same UUID; actual closed-conversation completion is not established by those
fixtures. Agent-message delivery is a separate path; the native flag is not
proof of or automatic permission for mailbox delivery.

## Execution order

1. Qualify the existing scheduled-wake behavior with one disposable conversation:
   save its exact ID, close its tab preserving history, verify it is unloaded,
   register an explicitly authorized wake, end the initiating turn and observe
   one completed follow-up in that same conversation. Preserve the original
   record on failure; no manual reply/replay counts. Fix only reproduced defects.
2. After that passes, connect explicitly requested reopening to agent-message
   delivery using existing message authority and uncertainty handling. Persist
   the sender's choice with the original notification. Reopening does not grant
   mailbox access or authorize stale/replaced recipient identities.
3. Prove one unattended request/reply involving that closed recipient. Retain
   evidence of both completed turns, exact IDs and original message IDs. Close
   only owned test tabs and preserve conversations after acceptance.

## Acceptance and definition of done

- Default messages to closed conversations visibly wait without reopening.
- Explicit reopening uses only the original saved conversation; an unavailable,
  changed or unauthorized recipient remains held with an inspectable reason.
- Busy conversations and human drafts remain protected; cancellation, expiry and
  uncertain delivery retain existing safeguards. Never resend an ambiguous effect.
- Restart preserves the original request and reopening choice. Each operation
  retains original permission checks; no capability or actor-generation bypass.
- Installed normal-worker evidence proves actual completion, not merely loading
  a conversation or accepting a queue entry. Source fixtures support that proof.
- Exact source/release/installed identities, bounded failure receipts, cleanup and
  Standards/Spec review precede closure. HostedCI waiting remains operator-waived.

## Scope and bounds

One owner; one ready unit at a time. One discovery/review and one consolidated
repair pass per unit; unresolved blockers return precise evidence and held state.
No custom Codex patch, shared-daemon restart, implicit opt-in, arbitrary recipient
lookup, new conversation in place of the original, live user-conversation replay,
broad held-recovery campaign or unrelated worker rollout. No old goal restarted.
Wider Plan0101/0119 obligations remain OPEN independently of this bounded slice.

## Goal execution control — 2026-10-10

Goal: complete every Plan0138 acceptance criterion. Start1791645933; checkpoint
by18:15:33UTC (2h50), stop before18:25:33UTC (3h) or3000000goal tokens,
whichever first. get_goal usage is authoritative; no token-budget tool override
is inferred. Check usage/time at material boundaries and at least every20minutes.
One owner, one worktree lane, no parallel implementation; disposable recipients
are product acceptance actors. Source baseline d9354a8; installed0.10.1.

Critical path: closed saved native recipient → explicit agent-message permission
and integration → unattended installed request/reply → review/release/cleanup.
First primary-evidence deadline15:40UTC. Current acceptance unproven; no helper
or queue-accepted receipt substitutes for completed same-conversation turns.
Per unit: one discovery/review and one consolidated repair pass. Preserve failed
samples; stop/reframe that unit if an accepted blocker remains after verification.
Checkpoint fields: state_transition, acceptance_state, progress_classification,
evidence, material_blockers, next_action_or_stop_reason. Hosted wait waived;
all behavioral, source/release/installed and authority gates remain required.

Startup transition READY→ACTIVE; outcome_progress: disposable exact recipient
created and seed turn queued. Private runtime receipts under user state plan0138.
Next: after completed seed, close its tab, verify notLoaded and arm one original
explicit resume wake through normal installed supervisor. No live user-thread replay.

Unit1 PASS: native-acceptance.md proves completed follow-up in the original saved
thread. Unit2 source checkpoint: explicit message choice and original actor
generations persisted; dispatcher integrates same-saved-thread delivery only for
an offline original Byobu binding. Live-client composer path remains authoritative.
Original mailbox attempt fences all native effects; delegated reply arm remains
required. Focused91tests PASS28.619s before version packaging. Installed unit3,
serial review, release/identity parity and cleanup remain unproven.

Installed packet split after observed failure: preflight94controls qualified;
live exchange1 reopened and completed the saved recipient but its inbox-only
reply suppressed the return notification. first-exchange-failure.md retains the
exact original records and closed failure. Correct only trusted pointer CLI/version
and notify-reply instructions, then run one fresh v2 intent. Never modify/replay
the committed inbox reply. Acceptance remains full unattended request/reply;
another failure ends this local attempt and requires evidence-backed reframe.

Unit3 installed behavior PASS: installed-acceptance.md records both completed
original turns and one dispatch per notification. The original v2 reply was held
with zero claims by the reproduced default-footer defect; correcting recognition
continued that same intent, with no new request/reply/arm. Request state completed;
reply received and sender result turn completed. Terminal reply ack failed
claim_required and is explicitly not claimed. final-review.md adjudicates that
existing consumption limitation and close inventory warning as nonblocking for
this bounded saved-recipient spec; wider plans remain open. cleanup.md records
only owned idle-tab closure, preserved conversations and stopped test processes.
State INSTALLED_BEHAVIOR_ACCEPTED→RELEASE_PREPARATION; progress outcome_progress.
Source6b1b673, immutable installed95PASS49.942s/all80files match. Remaining gates:
published PR integration, release assets and final source/release/installed parity.

Final transition RELEASE_PREPARATION→COMPLETE: PR232 merged at79c8c29, released
tagv0.11.0 resolves to that commit; downloaded wheel/sdist SHA256 match originals.
All80package files match merged source, both release assets, final immutable
installation and acceptance candidate. Global CLI reports0.11.0 and send/reply
help exposes --resume-missing. All13running/inactive service PID/state snapshots
remain unchanged; no unrelated rollout. Clean published source0842532 retained,
feature checkout removed normally. closeout.md is the canonical completion audit.
