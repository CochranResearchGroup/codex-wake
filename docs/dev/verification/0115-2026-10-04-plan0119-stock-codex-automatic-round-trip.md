# Plan0119 M1: automatic round trip on stock Codex

Result: M1 behavioral PASS on attempt2/3. M2-M4 remain UNPROVEN; Plan0119,
Plan0101/P63 and issue181 remain OPEN. No custom Codex activation or shared
restart. Official installed runtime remains0.160.0 on its original current link;
daemon updater settings remain absent.

Integrated Wake source:dcc893404252c68fcd2a6304919892b0c5e86361 via PR209.
PR207/b396ff2 added the explicit stock tmux adapter; PR208/bf51f50 corrected
bracketed paste; PR209 kept the clock guard while holding zero-effect worker
interruptions. Required hosted3.11/3.12 gates passed for each exact source.
Local transport/reply tests19 passed, full source suite901 passed; paste-focused
checks44 passed and clock/scheduler/transport checks30 passed. Hosted checks
cover final source904 tests plus installed compatibility/recovery/resource gates.
First bare-python test invocation lacked the source import path; subsequent local
checks used PYTHONPATH=src. Live commands used the installed private CLI, not
PYTHONPATH.

## Actual exchange

| Boundary | Exact evidence |
| --- | --- |
| Sender A | 01a10876-c7cf-7ae1-ad99-e9d829994e45, PID5322/start2076335 |
| Recipient B | 01a10876-e53a-7322-bf68-ff43e9b2f2dc, PID6145/start2077100 |
| Request | msg_c33d4cdf87544e138fedb286896fb9bb |
| Sender reply arm | wake_86ced80be2ac4c51933a8f477d8e1f23 |
| B read | receipt_19017bbc60c445988d78d8df1cf270c3 |
| B accepted work claim | receipt_f83ca241f7664bf69922526da1014c07 |
| Correlated reply | msg_fe28d90d70c144ae8cec2a07f6c6ba77 |
| A read | receipt_c0308cf295f14ff089e7dade82c44488 |
| A send/arm completed turn | 01a10919-bb5d-7ff0-a4f4-49fa425a94e3 |
| B automatic completed turn | 01a1091a-2c52-7dd0-8c7f-e56669ba2fc3 |
| A automatic completed turn | 01a1091a-c3ff-77e2-84fa-649e25e8e14e |

Worker PID94639 terminated normally after exactly two committed notification
submissions and66 ticks. Both mailbox attempts are submitted, each with its exact
thread and canonical message ID. The existing reply-arm record is submitted with
the actual reply/attempt receipt. The two automatic turns' user inputs are the
product-generated A2A_NOTIFICATION pointers. Both agents used their real context
and issued capabilities. B composed its own reply and echoed the challenge read
from the peer body. No controller prompt/body relay/foreground inbox polling
helper followed the admitted request. Only read-only operator observations and
receipt readbacks occurred.

Request-admission to A-read wall time56.006 seconds. Because host wall time steps
backward, deadline proof uses the persisted A-read monotonic clock checkpoint:
its wall value exactly matches the actual read receipt, and its monotonic value
is90.576 seconds after the controller bootstrap recorded BEFORE admission. This
is an upper bound below the120-second deadline, not a claim that wall time equals
elapsed time. Raw deadline proof was frozen before further mailbox operations.

## Preserved failures and limitations

The old demo bus's clock checkpoint was held; a fresh same-root/same-thread bus
also observed backward clock steps. Neither checkpoint nor host clock was reset.
The existing mailbox guard remains unchanged. An initial buffered-output bootstrap
failed before any A prompt; fresh process readback proved its worker terminal.
The successful native worker used PYTHONUNBUFFERED=1 for timely log observation.

A long setup prompt remained in B's composer under the original paste runner;
setup-only Enter submitted it before any mailbox send. The bracketed-paste fix
then submitted the fresh-bus setup through the product transport.

M1 attempt1 failed before admission: operator supplied120 rather than120s for TTL.
Exact authorized reconciliation proved zero envelopes/attempts. Attempt2 retried
the same original intent key; only one request and one reply were admitted.

A's extra completed acknowledgement of the result failed claim_required because
no accepted work claim preceded it. The sender read, exact correlation and deadline
criteria for M1 passed; do not claim that terminal acknowledgement succeeded.
Retain A-ack-reply.json and correct the workflow for later packets.

Tmux safety checks are observational before paste. M2 must still demonstrate
busy/draft/unloaded/identity/cancel/expiry behavior; this receipt does not claim
atomic exclusion of simultaneous human input. M3 lifecycle and M4 released
installation/second-root/rollback/30-minute workload remain open.

## Restart locators

Execution worktree:codex-wake-p63-feature-successor, checkpoint branch
feat/p63-live-stock-checkpoint. Native installed CLI:
/tmp/codex-wake-plan119-tmux-venv/bin/codex-wake. No global Wake install changed.
Private evidence root:
/home/ecochran76/.local/state/codex-wake/live-demos/20261004-wakeA-wakeB/tmux-plan119/.
cli-and-authority.json names the fresh bus, operator capability, issued A/B
capabilities, bindings, wake root and independent sender authority.
M1-mailbox-proof.json, M1-deadline-clock-proof.json, M1-reply-arm-record.json,
M1-A-send-turn.json, M1-A-reply-turn.json and M1-B-thread-full.json retain proof.
Earlier multi-turn readbacks were truncated; single-turn readbacks preserve the
actual inputs/commands/timing. Worker-M1-2 process/log artifacts retain ownership
and terminal result. Original demo bus remains paused and unchanged in history.

Next bounded packet: M2 live busy and owned draft fixture, then original delivery;
use new artifact paths and request-specific reply intent keys so M1 evidence is
not overwritten. Do not resume custom runtime activation.

Memory disposition: unavailable; no reviewed Codex Wake Graphiti target group.
No Graphiti write attempted.

## M2 attempt1 checkpoint

Request `msg_fc72c5646e8b4502bcc382fd38399b3e` was admitted while B's
Byobu window was renamed/moved with its original thread, PID6145 and pane%72.
The protected composer remained untouched by the worker; the request expired
and was suppressed with zero transport attempts. This is a safety observation,
not M2 acceptance. The observer started too late to capture the busy transition,
and the owned draft fixture was only partially inserted. It refused to clear
text that did not exactly match its full fixture. No reply occurred.

Private `tmux-plan119/M2-1/guard-observations.jsonl` retains observations;
`cleanup-proof.json` records exact original/visible owned fixture reconciliation,
clearing only that fixture, restoration of window@72 to index18/namewakeB, and
terminal workerPID89282. Retry requires observing before admission and verifying
the actual fixture before using it. M2 attempt1/3 consumed; M2-M4 remain open.
