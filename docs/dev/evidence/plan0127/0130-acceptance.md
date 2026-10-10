# Ticket0130 native recovery acceptance

Installed editable candidate uses Codex0.162.1 and the source hashes in `0130-source-identity.json`. Existing discovery remains history-free. Explicit recovery observes only the durable wake's exact thread and stores evidence identities rather than conversation bodies.

| Criterion | Result | Evidence |
| --- | --- | --- |
| Interruption before submission and after acceptance before recording | PASS | `0130-before-submission-armed.json`, `0130-before-submission-restarted.json`, `0130-after-acceptance-restart.json`, `0130-after-acceptance-reconciled.json` |
| No blind resend; unresolved effects inspectable | PASS | `0130-after-intent-unresolved.json`; public `native reconcile WAKE_ID`; duplicate-turn regression |
| Busy, detached and restarted-client qualification | PASS | `0130-busy-held.json`, `0130-busy-expired.json`, `0130-busy-native-turn.json`, detached receipts, client restart receipts |
| Actual scheduler process restart with disposable state | PASS | Before-submission systemd restart; `0130-auto-reconcile-armed.json`, `0130-auto-reconcile-result.json` |

After a crash before the uncertain intent is written, a fresh installed scheduler safely submits once. After the intent is written but before the external call, absent native evidence remains unresolved; inspection never retries. After queue acceptance but before the accepted record is written, a separate systemd scheduler finds exactly one matching completed turn and records acceptance without resending. The queued submission's stable nonce and exact payload hash are persisted before the external call. Queue and turn identities are reconciled; multiple distinct native turns remain uncertain, even if a client identity repeats.

Default unavailable/notLoaded targets remain pending until expiry. `--resume-missing` explicitly resumes that same saved conversation without creating a tab or replacement thread. The installed headless resume control executed its requested response, preserving the exact thread ID and unchanged tmux windows. Busy controls consume no native queue attempt and expire independently of recipient completion.

Validation:978 Python tests passed in91.731 seconds;56 focused native/scheduler/lifecycle/shared-reader tests passed. A final correction includes endpoint location within the observation deadline;14 affected native/lifecycle checks pass. Compilation and diff hygiene pass. Fault injection uses the retained private `0130-fault-injection.py` harness around real installed daemon record writes. Production contains no fault switch; native queue effects and native execution are real.

## Adjudicated primary review

Standards PASS: existing durable records, lifecycle locks, scheduler and native interfaces are reused. The native connection helper moved to a bounded protocol adapter for shared lifecycle/recovery use; the read-only discovery reader was not broadened. No broker, daemon patch, new database, shared restart or unrelated service change.

Spec PASS: missing-target resume is explicit and same-thread only; uncertain submission cannot fall back or resend. Acceptance, observed turn completion and acknowledgment remain separate. `turn_completed` reports the native turn status, not business success or acknowledgment. Each accepted submission has exact native attribution. Unresolved records remain inspectable under the public CLI.

## Retained failures and limits

The first post-acceptance restart observed no native evidence yet. Its test assertion expected instantaneous visibility and failed; the wake correctly stayed uncertain. A subsequent exact-thread observation confirmed one completed turn, and a separate delayed systemd control proved automatic reconciliation. Both samples are retained.

The first client restart control expected unavailable state solely from a closed tab. It observed native submission instead. A visible client and native availability are different boundaries: the resumed tab showed the one completed response. The separate notLoaded control proves default hold/expiry. No criterion was weakened to treat a replacement thread as success.

Recovery observations have a ten-second total budget and ten queue pages of at most100 entries. Unsupported, unavailable, oversized or ambiguous evidence holds uncertainty; absence is never proof of non-acceptance. Uncertainty is not converted into a harmless expiry. Existing legacy uncertain records can be matched by exact wake/root/prompt; no historical native identity is invented. Normal accepted records are not continuously refreshed for execution status. This is not an exactly-once guarantee or a shared-daemon/host restart test.

Candidate remains unreleased. Full lifecycle and migration/retirement tickets0131–0132 remain open.
