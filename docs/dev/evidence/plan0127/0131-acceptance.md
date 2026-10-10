# Ticket0131 complete installed lifecycle acceptance

Sourcec579ebe; private editable Wake0.8.0 candidate; Codex0.162.1. No implementation change was needed for this ticket. The installed product, real native agents and isolated scheduler performed the workflow.

| Criterion | Result | Evidence |
| --- | --- | --- |
| Open, ordinary native assignment, condition arm, sender ends, due execution/result, close | PASS | `0131-worker-open.json`, sender/worker native observations, `0131-final-lifecycle.json` |
| Exact native, tab and durable identities agree | PASS | `0131-identity-and-order.json`, initial sender turn, wake input/queue nonce, result file42 and sender pane |
| Pending guard; cancel separate from close; expiry; explicit same-thread resume | PASS | Final lifecycle commands return0/2/0/0; pane persists after cancel; current-source0130 busy/notLoaded expiry and exact headless resume receipts |
| Installed/source identity and independent Standards/Spec review axes | PASS | Sourcec579ebe and two-axis review below; preceding978-test suite and affected14 checks remain applicable |

Agent A natively assigned work to B, then registered one file-condition wake through the installed CLI and completed its initiating turn with `PLAN131_ARMED_IDLE`. B's terminal command slept20 seconds, wrote exactly42 and created the condition marker. The separate installed `codex-waked` service submitted the wake; A resumed17 seconds after its prior turn ended on the same native clock, read the result and returned `PLAN131_RESUMED_RESULT_42`. A's pane showed the result. No verifier action delivered the follow-up or manufactured its result.

A separate never-matching file wake targeted B. Ordinary close refused pending work. Explicit cancellation left the pane intact; subsequent ordinary close succeeded. Exact native conversation/read retained B's thread and completed work. The lifecycle root contains exactly the submitted condition wake and cancelled guard control.

## Primary review

Standards PASS: installed public interfaces and independent native/systemd/file/pane evidence agree. Real agent work replaces fixture-only acceptance. No helper-only implementation or service wrapper claims completion. The dedicated scheduler was stopped after the demo; fresh readback showed MainPID0, inactive and not-found after transient-unit collection.

Spec PASS: ordinary assignment used native `codex_tui.send_message_to_thread`, not a Wake mailbox. The durable condition survived the sender's completed turn and resumed its exact conversation. Closing preserved conversation; cancelling work was a distinct command. Acceptance, executed native turn and business result are distinct proof boundaries. Prior interruption, missing-target and expiry controls retain their separate receipts; they are not inferred from this successful flow.

## Limits

One qualified two-agent run with a file-existence condition, not every trigger/client/version combination. Network clock design and additional trigger classes are outside this plan. No shared daemon restart, host reboot or unrelated tab mutation. The global Wake installation remains unchanged; candidate release and legacy migration/retirement remain ticket0132 gates.
