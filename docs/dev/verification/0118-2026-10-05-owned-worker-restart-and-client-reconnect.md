# Owned worker restart and original-client reconnect

Parent Plan0119 / issue181. Exact source eb79e927fb227af3657d5b121aa17026294976d7,
stock Codex0.160.0, native privately installed CLI. No runtime source changes,
shared Codex daemon restart, custom Codex activation or identity substitution.

## Failed setup retained

continuation-v2/restart-1 admitted msg_1b0d2fa431004c58b538587abcbe66c1,
but reply-arm registration returned READER_CAPABILITY_UNAVAILABLE. The prior
bounded managed reader had exited. Launcher session71316 ended with assertion
failure before either worker was created. This is not a recovery pass.
Original B client was subsequently restored through native exact-thread resume
and binding. Original request, failed arm output and actor clock are retained.

The plan's no-other-error retry wording was too restrictive for this setup
failure; the second case below was a deliberate fresh qualification after
correcting reader lifecycle, under the user's full worker-recovery objective.
It did not replay the first send or arm key, or assume an ambiguous effect absent.
No further attempts are authorized by this two-case packet.

## Restart/reconnect PASS, second case

Actual B received setup before admission and then its original client exited.
Native worker PID8331 was started before actual A sent and registered its arm.
A then ended and its original client exited. Request
msg_033e100708534d728cd848557dfe8492 stayed accepted/deferred with zero attempts.
Both original client processes were terminal while the worker naturally ended.
PID8331 exited0; no residual process. Before/after snapshots preserve byte-equal
pending wake records, arm_wake_d4bbaa9a242646faae5807dbd9101545 and
wake_d4bbaa9a242646faae5807dbd9101545. Neither arm nor request was recreated.

New native worker PID14751 loaded the same durable state. Controller explicitly
resumed original A/B thread IDs and rebound their real new client generations;
there was no controller message turn or body relay after admission. Request
attempt_9d54adfeec7f4fffba9b09ae7edc4de9 submitted once. Actual B read/accepted
and sent one reply msg_7ca3258545f94c14b10351a54c81db72. Return
attempt_d2ab44185e8c4de68ae3525046ff676d submitted once. Actual A's product
notification turn read receipt_5dc4eafd7e1c4f41af922e8b47f2368f and verified
the local request correlation and actual challenge. Recipient state is received;
no extra A acknowledgement or reply was requested or emitted.

Actor-side monotonic before_send41415.322711661 to after_read41524.63606429
is109.313352629seconds, within120. Worker14751 exited0 after two submissions,
56ticks; no residual process. Both exact original clients are idle/ready again.
This proves bounded normal worker-process restart and original-client reconnect,
not forced-crash uncertainty recovery or automatic launch of disconnected clients.

## Evidence and remaining acceptance

Private source:
/home/ecochran76/.local/state/codex-wake/live-demos/20261004-wakeA-wakeB/tmux-plan119/continuation-v2/restart-2

Includes before-worker/after-worker-stop snapshots, native send/arm/read/reply
outputs, real actor turn JSON, both worker identities/logs/terminal receipts,
both new bindings, actor clocks and final-proof.json. Read-only native journal
inspection independently confirms exactly one submitted attempt per message,
actual reply read receipt, same arm and no residual workers. An initial verifier
asserted recipient='read'; corrected to the actual contract's 'received' plus
read_receipt. No mailbox state was changed by verification.

Cancellation and clean reconnect passed in verification0117. Normal public
release/install, explicit second root and unenrolled denial, installed rollback,
and30-minute bounded owned soak remain open. Plan0119 and issue181 stay open.
