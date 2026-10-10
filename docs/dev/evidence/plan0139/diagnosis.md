# Plan0139 reproduced failures and minimal repairs

Baseline main914d3dd; governing specification Plan0139. One owner, sequential
diagnosing-bugs/TDD loops. Existing GLOSSARY.md is the domain authority. Graphiti
doctor was healthy, but bounded atlas discovery returned only an unrelated cloud;
no relevant reviewed Codex Wake group or prior diagnosis was available.

## U1 notification consumption

Public delivered-pointer regression:
`PYTHONPATH=src python3 -m unittest tests.test_a2a_tmux_delivery.TmuxDeliveryTests.test_result_notification_instructions_allow_claim_then_terminal_ack`
Red claim_required1error0.207s; green1PASS0.271s. Public saved-dispatch regression:
`PYTHONPATH=src python3 -m unittest tests.test_saved_recipient_delivery.SavedRecipientDeliveryTests.test_saved_result_pointer_claims_before_terminal_ack`
Red claim_required1error0.418s; green1PASS0.330s. Pointer commands drive the real
public mailbox ack sequence, with transport peers isolated; body stays absent.

Minimized read→completed acknowledgment reproduces claim_required. With the same
recipient, read→accepted(claimed=true)→completed succeeds. This falsifies lack of
recipient authority and reading-as-claim; missing claim instructions are confirmed.
Both transports now share the explicit accepted/ownership/completed procedure,
stop on claimed=false or failed/ambiguous commands, retain untrusted-body and
independent reply-reopening boundaries, and name their installed worker CLI.
No mailbox claim semantics or permission checks were relaxed.

Focused source command: `PYTHONPATH=src python3 -m unittest tests.test_a2a_tmux_delivery tests.test_saved_recipient_delivery tests.test_a2a_mailbox tests.test_messages_cli`
49PASS10.878s before U2/new guards. This is focused coverage, not comprehensive.

## U2 ordinary close

Public regression:
`PYTHONPATH=src python3 -m unittest tests.test_session_lifecycle.SessionLifecycleTests.test_terminal_mailbox_receipts_allow_ordinary_idle_tab_close`
Initial inbox-only terminal fixture exposed an extra receipt_signal blocker;
adding the observed scheduler deferral followed by cancellation reproduced exact
inventory_unavailable1error0.232s. Green1PASS0.347s; public pending-work=[] and
ordinary sessions close succeeds with forced=false after terminal work.

A minimized public send→scheduler defer→cancel retains a scheduler receipt.
Targeted disposable-store inspection showed notification recipient=[runtime,
recipient] and receipt_signal actor=scheduler. The original scanner interpreted
all publication actor keys as tab identities. Restricting only the outbox arm of
the scan to notification records eliminates the false blocker and parser failure;
receipt publication remains durable and unchanged. Actual pending wake records
and message/notification work remain independently guarded.

Focused source command: `PYTHONPATH=src python3 -m unittest tests.test_session_lifecycle tests.test_a2a_mailbox tests.test_a2a_scheduler tests.test_a2a_scheduler_faults`
43PASS7.856s before the two additional guard checks. Public guards verify an
uncertain notification still blocks after recipient completion and cancellation
still fails effect_uncertain; malformed actual notification attribution still
fails inventory_unavailable. Final two guards2PASS0.371s. Initial guard fixture
omitted notify enrollment and then assumed uncertain cancellation was permitted;
both fixture mistakes were corrected, without weakening production guards. Failed
fixture outputs remain private rather than being presented as product regressions.

Raw red/green/focused logs remain under ~/.local/state/codex-wake/plan0139.
No temporary debug instrumentation or live old-record mutation was introduced.
Installed commands, serial review, release and integration remain pending.
