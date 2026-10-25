# Combined candidate final review and adjudication

Fixed point98b57a6f314dc82c6e687921b4edccc0bf2a1e55; reviewed runtime
9521bf1ba499d6efa51cb324543275e58a3963b0. Nonempty comparison:
`git diff 98b57a6...9521bf1`; commits `git log 98b57a6..9521bf1 --oneline`.
One broad review, two independent axes. No second broad review is planned.

## Standards

Reviewer combined_native found zero confirmed hard violations. Its authored native
qualification subset limits independence there; it emphasized Python integration.
Primary accepts two candidates as nonblocking_backlog: recovery's knowledge of
supervision storage/locking (possible Feature Envy, architecture policy0014) and
renewal `_snapshot` name hiding substantial admission qualification (possible
Mysterious Name). Neither demonstrates incorrect behavior; structural changes are
excluded from the bounded correctness remediation. Existing owning-module public
workflow remains the caller interface. Native static/artifact qualification is
reported separately, not mislabeled independent review of the author's own patch.

## Spec

Reviewer combined_final_spec proposed two blockers. Primary verified both against
frozen sources and accepts both as blocking:

1. Notice identity ignored `active_stop_id`, using immutable first_stop fallback.
   Spec lines78–81 require exact stop-episode correlation. The public recovery
   fixture reproduces wrong episode IDs; repeated control readback must also keep
   one notice within an episode even when captured turns are refined.
2. Successful recovery had history but no reachable recovery notice. Issue343
   explicitly requires correlated recovery notices. The public CLI recovery
   fixture reproduces zero such notices. History/tool output is insufficient.

One accepted-findings TDD pass addresses these only: honor active episode/current
reason, keep semantic identity stable as control readback refines captured turns,
and journal recovery through the existing durable presenter. Native activation
remains a separate gate. Red/green receipts and final checks follow in the plan.

Accepted findings: Standards2nonblocking (highest: architectural knowledge
coupling); Spec2blocking (highest: suppressed/stale repeated-stop notice).

## Remediation result

Single bounded TDD pass committed5baf7ad3866cc0b765bab29978d31487fb3dc2d3.
The existing public CLI recovery regression was extended rather than adding an
implementation-coupled proxy. Before episode correction, assertions returned
immutable first-stop arrays instead of the two real episode IDs. Initial candidate
fix exposed duplicate notices as captured turns changed within one episode;
semantic hashing now excludes that refinable metadata for modern episode IDs.
After episode assertions passed, recovery assertion remained RED:0notices versus1.
The existing recovery kind is now journaled from successful recovery and bound to
its retained recovery event's stop episode/reason. The native goal stays paused.
Focused notice/watcher/recovery/renewal/engagement/restart-fault32tests pass both
Python3.12(62.314s) and3.11(64.090s). This is accepted-blocker remediation verification,
not a second broad review. Native recovery-path acceptance is separately pending.
Final counters: review1/1, findings-TDD1/1.

During native verification of the accepted recovery-notice blocker, actual Unix
socket outage exposed a causal presentation defect: a failed read-only capability
probe was cached as unsupported after reconnection. Original native attempt1
receiptfe499c58278df4c309eaeebc46e7a1fc787fdb027ea7328c4ab7b021aaf32788
is retained. No recovery effect was attempted. This remains inside the same
findings-remediation pass, not another broad review or unrelated cleanup.

Public notice regression RED reproduces unsupported instead of retryable pending.
An initial fix still failed because WakeError inherits ValueError; that54.156s
33-case failure is retained. Runtimec94fb30 separates explicit method-not-found
from transport failures. Read-only failure leaves the unsubmitted notice pending
with zero attempts; ambiguous append remains unknown/readback-only. Eight notice
and actual Unix protocol tests pass0.608s; broader affected checks and repeated
real socket-outage verification are pending. No fixture bypass or manual delivery
was introduced to make the real recovery scenario pass.

Final affected selection passes81tests onPython3.12/3.11 in74.027s/75.200s.
Selection includes notice,recovery,watcher,renewal,engagement,restart-fault, native
protocol/delivery/intent-recovery,strict-execution and scoped-refresh suites.
Python3.11 emitted handler-close diagnostics during intentional RPC rejection
and an existing WebSocket deprecation warning; terminal suite isOK, not a retry.
Real native recovery attempt2 GREEN18.241s/3setupPOSTs on exactc94fb30 and299native;
receipt a30035ff5558c2fdb5e7ce1a4c8007720400ed7a2fa4b7ac586a671bda4ca939.
Both actual outage stops and recovery are visible in native context/stockTUI,
with separate episode IDs/current reasons, original20spent/budget/history/peer
unchanged. No added model requests. Installed162sourcehashesmatchafterrun and
owned processes/clock relays are absent. Accepted blockers are addressed and
verified; source publication does not activate shared production services.
