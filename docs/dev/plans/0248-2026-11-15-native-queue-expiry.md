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
an arbitrary subscriber's currentTime/read response. Authority is the existing Stable Time service, explicitly selected by the
operator on 2026-11-15.
No wall-clock fallback. Clock rollback, changed counter epoch or unavailable
post-restart evidence holds rather than extending the deadline.

Expiry/cancellation/admission selection must share the authoritative state
transition. Keep durable inspectable canceled/expired/admitted outcomes, including
original identities and reason, with already-admitted distinguishable from
pending cancellation. Do not claim cancellation undoes a running turn. Resolve
crash after admission before resend: no exactly-once claim from delete-after-start.

## Discovered implementation boundaries

The initial saved modified source f986f6ed53d6b324aedbd7e32991e0185eacae14
is version0.167 and is not the installed0.169 source. Correct native baseline is
upstream release tag rust-v0.169.0, peeled commit
d32063f96c2dff1dc96af839b3952abb6acfeda4. Its queue schema includes the
responsesapiClientMetadata field observed in installed0.169. The unrelated
provider lane remains untouched. Initial0.167 state-test compile is retained as
an invalidated input attempt; no0.167 build may qualify a0.169 installation.
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

## Stable Time integration decision (operator selected)

Use the existing audited Stable Time client validation rather than a second
interpretation of NTS/host-counter bounds. Native may invoke a pinned, host-owned
clock reader independently of Wake scheduling; no watcher heartbeat or queued
sender payload supplies clock authority. The native startup configuration owns
an absolute executable/config path. No shell, prompt interpolation or RPC-supplied
command. Missing reader/config, invalid output, timeout, changed epoch or stale
bounds holds bounded work. Existing snapshot fallback to plain NTP must never be
used by this reader. Bound output and elapsed transport time; account for time
between sampling, native reception and admission conservatively.

Persistence test seam: SqliteQueueStore public methods, real private SQLite,
reopen through StateRuntime; protects immutable original expiry and terminal
cancellation, not actual native model admission. Native admission seam: public
thread/queue methods plus actual core input history; protects expiry/hold/control
and restart reconciliation. Separate-UID live scenario is still required even
when both focused seams pass.

The first compile attempt could not locate cargo in the Cargo Signal process
PATH; retry uses its absolute installed executable. The first source compile on
0.167 demonstrated the missing methods but was invalidated as release evidence.
The identical state behavior test is rerun on the pinned0.169 tag before green.

## Implementation checkpoint

Clock reader process added in native_queue_clock.py, using an explicit absolute
Stable Time configuration with no plain-NTP fallback. Missing-config process
contract failed before implementation and passed afterward; existing native clock
validation5 tests pass. Real service read returned qualified finite bounds.

Native0.169 persistence now carries original immutable expires_at and terminal
canceled/expired/admitted outcomes with exact admitted turn ID. Immediate SQLite
transactions select one winner across connections and prevent terminal replay;
selection compares the original payload and expiry. Public queue persistence
selection10 tests passed after observed red cycles. This is storage proof, not
native deadline enforcement. Current patch in patches/codex/0248-native-expiry.patch
is explicitly incomplete and not qualified. Core guard red is compiling next;
no queue expiry field, capability or bounded Wake admission is active yet.

The release-tag lockfile required normalization of173 local workspace versions
from0.0.0 to0.169.0. Parsed comparison verified no dependency-pin changes.
Following stages use --locked. No native package or service has been replaced.

## Compatibility guard

Native bounded enqueue must use a distinct versioned method (proposed
thread/queue/bounded/add), not merely an extra expiresAt field on legacy add:
older native deserializers can ignore unknown fields and otherwise enqueue
unbounded input. The legacy method remains unbounded. Wake negotiates support
before I/O and bounded submission never falls back to legacy add. The new method
requires original expiresAt, and read-only reconciliation reports the same queue,
client and terminal turn identities. CLI/API/MCP share this distinction while
keeping existing explicit unbounded operator inputs usable.

## Downlevel storage safety gate

Before native bounded enqueue is exposed, quarantine bounded pending entries from
legacy queue readers. Merely adding an expires_at column to queued_items is
insufficient: older binaries ignore that column and could drain an expired entry
after rollback. The current storage primitive patch is therefore not activatable.
Implement a separate bounded pending partition (or an equally demonstrated
fail-closed downlevel representation), retain original IDs/outcomes, and qualify
actual old-binary non-delivery. Legacy unbounded queue inputs must remain usable.
Do not weaken this gate to a client capability probe or watcher-side timer.

## Native API checkpoint

Core queue regression20 PASS; persistence14 PASS after adding atomic lookup by
original client message ID across pending and terminal entries. Lookup reports
ambiguity rather than guessing or resubmitting. The native API family is
thread/queue/bounded/{add,list,read,delete,capabilities}. Read/delete share a named
inspection model. The first schema export detected a nested-response definition
collision; the inspection DTO correction is under regeneration.

Native public expiry is required expiresAtUnixMicros, preserving the original
accepted wake's microsecond precision without rounding or renewal. Storage
migration0008 converts the unactivated prototype's second values to microseconds
without changing their absolute instants, rejecting overflow. UTC bounds remain
seconds and are conservatively converted for integer-microsecond comparison.
The microsecond persistence regression14 PASS. The distinct-method protocol test
failed before implementation and passed afterward. No runtime/package changed.

Remaining: finish schema generation and compile RPC handlers; qualify complete
package/rollback in UID1017 with real Stable Time, then adopt the backend through
shared Wake CLI/API/MCP paths, review, merge and close695. Bounded Wake delivery
remains disabled. Current source patch is a recovery checkpoint, not a release.

Experimental schema export PASS after the shared inspection DTO correction.
Native source checkpoint7a8335c0a6 is preserved as an apply-ready binary patch
against d32063f96c and a private incremental Git bundle. Native server handler
build is running through Cargo Signal (not yet passing). Session-only build wake
registration was held with session_owner_unverified; no unattended continuation
is armed and no lifetime fallback was selected. Working runtime unchanged.

## Server build and timing boundary checkpoint

Native checkpoint23b3ff6af3 fixes the app-server steering match for
QueueAdmissionHeld. Server-build1 failed compilation on that missing exhaustive
case; server-build2 passed (exit0,80.095s). The only subsequent change is rustfmt
formatting of that match arm. Latest queue regression runs separately after the
microsecond/API changes; do not reuse the earlier queue20 result as proof of
this exact source. Private receipt root remains native-expiry-0248.

The Stable Time helper currently advances bounds to its own Windows-QPC
observation, but native has not qualified elapsed transport between that sample
and admission. Tokio's two-second timeout alone does not prove a suspend-safe
bound. Production activation remains forbidden until this gap is resolved.
The operator has been asked whether expiry governs atomic queue selection or
must be rechecked before model execution after a suspension. No answer has
been assumed, and the existing conservative contract remains authoritative.

Read-only delegated discovery identified that permission_wake already persists
a submission UUID before I/O but does not forward it or the original deadline;
ModeRuntimeAdapter's background turn/start path bypasses bounded queueing.
Shared adoption must address both and distinguish pending native ownership from
admission, execution and acknowledgment. Worker handles expiry_wake_contract
and expiry_clock_bounds returned source-grounded recommendations; neither made
edits, runtime effects or a formal review. Source and package qualification,
shared adoption, the requested formal review/TDD findings pass and issue closure
remain incomplete. No working runtime changed.
