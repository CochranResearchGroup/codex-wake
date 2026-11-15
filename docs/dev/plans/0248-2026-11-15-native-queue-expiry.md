# 0248 — Native bounded queue expiry (#695)

State ACTIVE. Owner root/ecochran76; WIP1. Branch feat/native-expiry-695.
Parent #610. Preserve unrelated work and the working daemon. No working-host
native upgrade until exact complete package and rollback pass separate-UID
qualification and applicable installation authorization is established.

## Scope and contract

Persist an optional original absolute expiresAt on bounded queue entries,
with exact thread, queue and client identities. Omission retains legacy unbounded
operator queue behavior. A deadline is immutable through update, retry, restart,
reconnect and reconciliation. Never renew it from the current time.

Use negotiated versioned capability before Wake transmits bounded input. Unknown
or old native backends remain pre-I/O refused. An advertised field alone does
not establish accepted qualification. Existing bounded Wake admission stays
closed until actual native enforcement is qualified.

At the model-turn admission boundary, independently qualified UTC bounds decide:
upper < expiresAt permits admission; lower >= expiresAt expires; a straddling
interval or unavailable/stale/untrusted evidence holds. Equality never permits
start. Obtain time from host-owned authority, never prompt/sender metadata or
an arbitrary subscriber's currentTime/read response. Proposed authority is the
existing Stable Time service; operator clock-source selection is pending.
No wall-clock fallback. Clock rollback, changed counter epoch or unavailable
post-restart evidence holds rather than extending the deadline.

Expiry/cancellation/admission selection must share the authoritative state
transition. Keep durable inspectable canceled/expired/admitted outcomes, including
original identities and reason, with already-admitted distinguishable from
pending cancellation. Do not claim cancellation undoes a running turn. Resolve
crash after admission before resend: no exactly-once claim from delete-after-start.

## Discovered implementation boundaries

Modified Codex source f986f6ed53d6b324aedbd7e32991e0185eacae14 has queue API;
upstream main inspected bdd282f3bb lacks that same extension. Current provider
lane is a separate active checkout and must not be edited or silently adopted.
Native ext/queue/service owns process-local dispatch lock and queue selection;
thread-store QueueStore and state queue runtime own persistence. Existing dispatch
starts a turn and only subsequently deletes the queued item. A superficial
extension-only timestamp check leaves admission delays and crash uncertainty.
Core session/turn_input owns idle-turn reservation and eventual task startup;
this is the consequential admission boundary. Existing TimeProvider returns a
point estimate and may ask a client subscriber, so it cannot establish qualified
UTC bounds for this safety contract.

## Execution and acceptance

1. Settle host clock integration; define a small native qualified-bounds seam,
   persisted outcomes and core admission guard before exposing capability.
2. One public queue behavior red/green at a time through existing native harness:
   expired work never starts, uncertainty holds, unexpired control starts,
   exact cancellation reports correct outcome, original deadline survives reopen.
3. Generate v2 schema/SDK artifacts and document compatibility. Add Wake adoption
   only behind negotiated enforcement and existing actor/target/operation checks.
4. Assemble complete pinned package through Cargo Signal; qualify in real
   separate UID1017, including watcher loss, restart/reconnect, active clients,
   original-ID reconciliation, cancellation and rollback with synthetic history.
5. Review once on standards/spec axes, resolve findings with focused red/green,
   record local checks (no paid hosted CI), integrate source and evidence, retire
   owned resources after remote custody. Close #695 only after all acceptance.

No mock-only native claims, synthetic qualified clock in live acceptance,
production policy changes, incidental provider changes or fixture framework.
Memory writes forbidden absent explicit user request.
