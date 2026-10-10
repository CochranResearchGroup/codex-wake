# Plan0138 installed request/reply acceptance

Transition AWAITING_V2_EXECUTION → INSTALLED_BEHAVIOR_ACCEPTED. Release and
integration remain open. No manual reply, controller body relay or ambiguous
resend supplied this proof. The initial inbox-only exchange remains failed and
preserved in first-exchange-failure.md.

Original v2 request msg_afb5abf5776c430a82a81581d2174fcf submitted once under
attempt_3b714b08b9fa49dab71f17698fa15bf3, native queue receipt
01a12695-8514-7062-8332-e936b9eaedb1. The original closed recipient
01a12681-3c92-7b30-b5d7-e3a2dbbee7c8 was notLoaded before execution; its seed
01a12681-cce1-7832-afa3-bdc405ece189 and history remain present. Recipient turn
01a12695-8516-7342-8f8f-1e5195eb0461 completed, acknowledged the request completed,
and sent exactly one correlated notify reply msg_960e2b99980048088cc205b14a57fdde.

The stock default-footer defect held that original reply with zero dispatch
claims. After the reproduced bounded repair, ordinary installed worker4 delivered
it once under attempt_27f8e29119494addad3b89c438860e7e through tmux_notification_v1.
Worker4 finished normally after four ticks, submitted=1. Its original delegated
arm wake_a9eb98bdd2b14f19b41fb825d212de66 is submitted. Sender follow-up
01a1269d-4354-7af3-94d2-e85b29a6db3c completed in the original sender
01a12680-a480-7551-a5a7-f115f6357546 and reported exact P68_UNATTENDED_REPLY_V2.
The sender's initiating v2 turn completed before runtime activation.

Exact public states: request accepted/submitted/completed; reply
accepted/submitted/received. The sender attempted terminal acknowledgment without
a work claim and received claim_required. No terminal reply acknowledgment is
claimed, and no retry was made. This existing consumption rule does not invalidate
Plan0138's completed request/reply turns and exact-thread delivery criteria; it is
a retained limitation of the existing live-tab notification instructions, outside
this saved-recipient reopening change. Do not equate received with completed.

Installed candidate source 6b1b673c7c2cc3b0c2b2c7a0819bd9cddf7a8c57,
prefix ~/.local/share/codex-wake/releases/0.11.0-6b1b673. All80 package files match
source (parity-footer.json). Focused installed95PASS49.942s, with imports from
the immutable package, no source PYTHONPATH; installed-focused-footer.log.
Prior failed fixtures and live exchange receipts remain preserved. Hosted CI
waiting is operator-waived; these are focused and bounded live checks, not a
claim of comprehensive-suite or hosted-CI success.

Private receipts under ~/.local/state/codex-wake/plan0138/a2a/: original v2
request/reply/arm, activation-worker4, worker4 command/log, request-terminal-v2,
reply-terminal-v2, sender-return-thread and recipient-completed-v2-thread.
Full histories stay private; this artifact records only controlled test locators.
