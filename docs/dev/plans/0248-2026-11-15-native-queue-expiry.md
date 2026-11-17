# 0248 — Native bounded queue expiry (#695)

State: OPEN
Owner root/ecochran76; substantive WIP ceiling3 for the remaining-ticket batch.
Branch feat/native-expiry-695.
Parent #610. Preserve unrelated work and the working daemon. No working-host
native upgrade until exact complete package and rollback pass separate-UID
qualification and applicable installation authorization is established.

## Current State

Native `9af0e8e48d` is committed clean and source-validated: final native-send
admission after HTTP authentication/preparation and inside the WS sender;
non-consuming pending preflight, UNKNOWN retains original pending state, known
expiry is terminal before first attempt, bounded WS publication waits for send.
249 affected controls pass (26queue+2clock+221API), with behavioral red/green
evidence. Final batch review against Native075/Wakef8e completed once: Standards
low private-helper cleanup deferred; Spec no source findings. One bounded
findings pass required no behavioral change or manufactured test. Package5
assembly passed1176.072s and exact six-file hashes match under UID1017 before
and after installed acceptance. Nine installed gates pass, including a retained
adapter float-representation failure repaired in Wakeff9b9c01 and only that
failed gate replayed. Nonzero nativegoal25tokens/2000budget survive rollback and
re-upgrade. Working daemon unchanged; parent695 remains OPEN for production
adoption and original Python failure. Package4 receipts below are historical.

Native `075639f50a` retains bounded queue enforcement and adds conservative local
package replacement: an identical full package is pinned without restarting or
retargeting the running daemon; a different running package requires explicit
checkpoint and stop. Two real UID1017 reproductions established unconditional
force-stop, including same-binary reinstall; the managed-PID regression is red
before the fix, then green, with all 8 preparation controls passing.
Package 4 assembled in 1432.524 seconds, with all 6 hashes verified under UID1017. Both
original live updater reproductions pass: different-package refusal and identical-
package pinning preserve the active turn, exact PID and selection. The exact
package also passes the actual launcher and real-clock queue/restart journey
in 51.626 seconds; final case-owned processes: 0. See the
[partial acceptance receipt](../evidence/issue0695/package4-partial-acceptance.json).
The production restart path and cooperative recovery protocol are not qualified.

Packages 3 (`db4dcfc839`) and 4 (`075639f50a`) passed real UID1017 Stable Time
expiry/cancellation/control,
unknown-clock hold and original deadline/client identity after restart. Expired
and canceled inputs never reached model/history; controls did. All case-owned
processes stopped. This does not qualify arbitrary suspend/send delay or the
remaining upgrade gates.
The approved read-only clock enrollment and pinned helper remain unchanged.
Production bounded Wake delivery stays refused. Installed preparation expiry,
private-owner normal-exit recovery, stopped account/default/shared native-home
rollback, failed-start repair and same-client reconnect now pass. Shared pending
cancellation source and isolated installed adapter seam also pass; production
factory remains disabled. The former package4 transport blocker is documented in
transport-boundary-blocker.json and addressed by Native9af source; exact package5
qualification now passes in UID1017; working installation remains separate.
Operator accepted final native transport-send admission on 2026-11-16.
Recheck after authentication, preparation and transport waits, immediately before
the native sender writes. Unknown/expired time prevents sending. Remote model
start, network delay and an OS pause between final sample and syscall remain
explicit limitations; no provider-side enforcement is claimed.
One earlier formal review/TDD cycle is retained. The newly requested final batch
cycle remains pending until the blocked timing ticket resolves.


Full matrixv4 atWakeaf1c8dde exceeded2400seconds onPython3.11; four assertions
failed before timeout, andPython3.12 did not start. Exact orphan unittest child
was terminated and absence verified. Focused reproduction confirmed stale command
coverage, a malformed CLOSED annotation in the peer plan header, and refresh tests
reading operator wake roots through inherited XDG_CONFIG_HOME. Generated coverage
and the deterministic header are repaired; refresh tests now isolate their config,
with29 controls passing onPython3.11 and36 affected module checks onPython3.12.
The original preflight subcase passes alone and its 51-test module passes in
145.032 seconds. The corrected original-order prefix also passes 214 tests,
including that case, in 186.405 seconds. Its earlier full-suite failure remains
unexplained and is not erased.
Retain all failures; no full-green claim.
Working daemon1879 retains its original hash. #695 remains OPEN; no working native
installation, merge, deployment or closure is claimed.

## Scope and contract

Persist an optional original absolute expiresAt on bounded queue entries,
with exact thread, queue and client identities. Omission retains legacy unbounded
operator queue behavior. A deadline is immutable through update, retry, restart,
reconnect and reconciliation. Never renew it from the current time.

Use negotiated versioned capability before Wake transmits bounded input. Unknown
or old native backends remain pre-I/O refused. An advertised field alone does
not establish accepted qualification. Existing bounded Wake admission stays
closed until actual native enforcement is qualified.

At final native transport-send admission, independently qualified UTC bounds decide:
upper < expiresAt permits admission; lower >= expiresAt expires; a straddling
interval or unavailable/stale/untrusted evidence holds. Equality never permits
start. Obtain time from host-owned authority, never prompt/sender metadata or
an arbitrary subscriber's currentTime/read response. Authority is the existing Stable Time service, explicitly selected by the
operator on 2026-11-15.
No wall-clock fallback. Clock rollback, changed counter epoch or unavailable
post-restart evidence holds rather than extending the deadline.

Operator decision, 2026-11-15: recheck the original expiry before model execution.
Earlier queue selection does not preserve eligibility across a suspension or
delayed turn preparation. Unknown time holds, proven expiry is terminal, and
expired input must not leak into a subsequent turn through retained history.
The early core idle-reservation check alone does not satisfy this boundary.

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

## MONITOR-CLOCK-01 | Stable Time monitor freshness

Owner root; DONE for source repair and bounded acceptance, parent #695 OPEN.
Commit9a670307 is integrated into the existing lane with matching remote custody.
The temporary continuation checkout used during frozen matrix v3 was removed
without force after verification. No installed-service or native acceptance claim.

Seam: public TabMonitor refresh/status across independently constructed readers,
plus the actual private background owner with the configured real clock. This
proves retained-frame freshness, not every nested trait's timer or native expiry.
One red/green slice first adds explicit clock-provider injection and persisted
counter evidence; the next proves default configured-clock expiration without
waiting for wall time. Counter-only authenticated evidence suffices for elapsed
age; guest UTC and plain NTP do not. Changed epoch/frequency, rollback, unavailable
evidence and invalid rate hold freshness stale, without rebasing the saved frame.

Compatibility: snapshot schema1 gains clock_counter and observed_at_time_basis.
Default status reports freshness_basis and an upper age_seconds bound, or null
when continuity is unknown. Older frames remain readable but stale until observed
again. Explicit internal point-clock injection remains labeled injected_clock;
portable controller operations cannot select this constructor seam. Wall sample
timestamps remain diagnostic metadata; this slice is not a global clock migration.
Definition of done: public regressions and affected callers pass, real configured
clock readback succeeds, the owned test process is gone, and source custody plus
temporary-checkout cleanup are verified. Wider #695 acceptance remains separate.

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
The operator selected a final recheck before model execution after suspension.
The earlier queue-selection check is insufficient. The helper transport interval
still requires qualification; this decision does not qualify a clock source.

Read-only delegated discovery identified that permission_wake already persists
a submission UUID before I/O but does not forward it or the original deadline;
ModeRuntimeAdapter's background turn/start path bypasses bounded queueing.
Shared adoption must address both and distinguish pending native ownership from
admission, execution and acknowledgment. Worker handles expiry_wake_contract
and expiry_clock_bounds returned source-grounded recommendations; neither made
edits, runtime effects or a formal review. Source and package qualification,
shared adoption, the requested formal review/TDD findings pass and issue closure
remain incomplete. No working runtime changed.


## Final model-send check implementation

Native e1832b9895 moves bounded admission from early idle reservation to the
HTTP/WebSocket request send path, after request preparation and authentication.
Pending input and hook-derived response items stay in a turn-local staging area,
outside reusable/persisted model history. The first request uses the staged
projection; eligible native admission is recorded with its original turn ID,
then staged history is published after the stream attempt. Refusal discards the
staged projection. TurnStarted denotes preparation, not admitted input.

The public queue/model-request regression failed before this change: expiry
raised by a real prompt hook still allowed a model request. It now passes and
proves no expired prompt or derived hook context in either the next control
turn or a reloaded session's control turn. Earlier held-admission coverage was
updated to wait for prepared-turn completion rather than equating preparation
with model admission. All21 queue tests PASS at e1832b9895; receipts retained in
final-execution-red, final-execution-green1 (compile error),
final-execution-green2, final-gate-regression1 (old assertion),
final-gate-regression2, final-execution-replay (test harness compile error),
final-execution-replay2 and final-gate-regression3. No failures were discarded.

The complete candidate package is assembling through maintained package binary
selection and the supported prebuilt-artifact overrides. Its target is host GNU
rather than the working baseline's musl; qualification must cover this material
runtime dependency difference. No package is installed on the working account.

The pinned clock-reader wheel returns real qualified Stable Time under UID1000.
UID1017 has readable private clock config/CA/token but its old fixture endpoint
localhost36609 refuses connections; it correctly holds. No production credential
was copied. Installed Stable Time0.2.0 CLI exposes inspect/analyze/mcp, with no
consumer issuance command. Dedicated real test-user consumer provisioning remains
unresolved; current authority health is NTS-verified and finite. Read-only
Graphiti atlas discovery found no reviewed source cloud. This is not clock
qualification. The source reader-to-native elapsed interval also remains an open
qualification requirement. Production bounded Wake delivery stays disabled.

The bounded_wake_adapter worker owns only shared Wake runtime source/tests,
propagating original expiry and stable client identity without unbounded fallback.
Counter-only intents without a qualified absolute deadline must hold. Historical
already-submitted unbounded work retains its original reconciliation path and is
never resent as a bounded replacement. Formal review and its TDD findings pass
remain reserved; #695 remains OPEN.


### 2026-11-16 transport continuation

Explicit UID1017 read-only Stable Time enrollment was approved and executed;
authenticated UTC was observed without logging credential values. Native
`db4dcfc839` projects helper bounds through a fresh private host-counter read,
retaining the original finite authority lease. Red/green clock regression and
26 selected native queue/clock tests pass. The helper contract now requires
remaining validity and its host-owned counter source. Python13 focused checks
pass on both supported interpreters. Package3 and actual daemon boundary,
upgrade/rollback, full Python regression and shared cancellation acceptance
remain open. Production bounded delivery remains disabled and #695 remains OPEN.


### 2026-11-16 prepared expiry and stopped rollback qualification

Exact Native075639f50a package4, SHA44f25dea, passed two more installed
journeys under real UID1017, using the actual launcher and authenticated Stable
Time with the existing approved credential references. Prepared-expiry v2
passed39.919s: an explicitly trusted owned UserPromptSubmit hook entered while
eligible and returned after the original deadline; expired prompt and derived
context were absent from both captured model requests, including after reload.
Controls completed. This does not establish arbitrary suspension atomicity.

Stopped rollback v4 passed99.126s: three real TUI clients, two synthetic histories
and paused native goals/budgets; explicit stop, rollback to working0.169musl,
then explicit stop/re-upgrade to candidateGNU. History prefixes and goal fields
survived; old binary left the bounded entry untouched, and candidate expired
its original ID/deadline after re-upgrade. An owned mandatory log permission
failure prevented startup, then permission repair restored launchability.
Exactly two synthetic provider requests; no external model calls.

Earlier setup/readiness failures remain recorded. The v3 qualifier raced an
asynchronous paused-goal dialog: Enter selected Resume goal, causing the mock
request cap to fail. V4 explicitly waits, selects Leave paused and asserts status;
no product code or cap was changed. Final scoped processes0; working PID1879
and musl hash unchanged. Curated package4-partial-acceptance.json retains all
remaining gates. Default/shared layouts, private-owner locks, uninterrupted
reconnect, production cooperation, suspend boundary and full Python validation
remain unqualified. Production bounded adapter remains disabled; #695 OPEN.


## Implementation batch | 2026-11-16 | remaining #695 acceptance

Integration branch feat/native-expiry-695; frozen batch base f8e879c291c172add80211b83de2b3c581fa2295.
Owner ecochran76; coordinator root. WIP limit3 disjoint tickets; UID1017 native
runtime is serialized with root as sole owner. Existing broad review/TDD remain
recorded; new requested final review fixed point pending operator selection.
No missing blocker IDs or dependency cycles. Parent695 closure requires all
acceptance, including retained unresolved Python failure; passing subsets do
not close it. No deployment or production bounded activation in this batch.

| Local ticket | Owner | State | Dependencies | Scope and acceptance |
| --- | --- | --- | --- | --- |
| 695-QUAL | root | running | none | Actual UID1017 default/shared history and reconnect qualification using immutable package4; preserve budgets and working services. |
| 695-ADAPTER | pending_cancel_695 | running | none for source; activation depends 695-QUAL and 695-TIMING | Shared native pending cancellation and exact original identities, grants, no unbounded fallback; focused public-contract tests. |
| 695-TIMING | send_boundary_695 | running | none | Establish final execution timing guarantee or reproduce precise native blocker; source proposal only pending serialized ownership. |

Root owns plan/RUNBOOK/evidence/active-lanes and integration. Workers report
owned checkout/base/result SHA and validation; only root marks integrated or
validated. Worker report alone is not ticket closure. Unblocked tasks are
assigned one per worker; blocked activation stays pending. No renewed full
Python matrix, duplicate package build or prior broad review in execution.


### Remaining-ticket batch result | 2026-11-16

Root695-QUAL and worker695-ADAPTER are validated and DONE as repo-local tickets,
not parent closure. Ledger:0248-execution.json. Frozen batch basef8e879c2; adapter
worker97f6dca7 integrated as89c639f9. Worker branch has verified remote custody;
its clean checkout removed, Wake inventory125→124. Native inventory21 unchanged.
Root/default native home with CODEX_HOME unset passes120.172s. Legacy explicit
shared native home passes62.753s; this does not admit concurrent controller
shared mutable stores. Histories and paused native budgets survive supported
stopped rollback/re-upgrade; failed-start permission repair passes.

A new isolated helper wheel9f465233 from89c639f9, preserving the approved af1
helper and existing credential references, passes actual Native075 cancellation
and reconnect41.510s. Exact pending cancellation, actual lost-delete reply
followed by tombstone reconciliation without second delete, admitted refusal,
tombstone persistence through restart, visible reconnect notice and original
client's new prompt reaching owned provider all pass. Final owned processes0;
working PID1879/hash unchanged. Source31133/3129 checks plus rootintegration9
pass. No full-suite success or production activation is claimed.

Worker695-TIMING remains blocked with exact source anchors and minimal transport
remediation scope. No native code/build changed. User decision pending on strict
remote-start versus final native transport-send admission. The requested new
final review/remediation cycle is not consumed before this gate resolves.


### 2026-11-16 final native-send boundary accepted

Operator accepted the recommendation to use final native transport-send admission
for695, excluding remote model-start guarantees. Ticket695-TIMING reopened to
running; worker send_boundary_695 owns Native checkout/code exclusively, root
owns Wake integration and UID1017 runtime. Existing HTTP/WS outer guards stay;
HTTP must recheck after asynchronous auth/preparation, WS inside actual sender
after task/lock/command-queue delays. Bounded WS return must wait for send result
so rejected input cannot be published into retained history. Legacy unbounded
stream behavior must remain compatible. Existing provider/queue seams drive
red→green; no generic test framework or working daemon effects.

Final batch review compares Wakef8e879c2 and Native075639f50a to their completed
integration tips; prior earlier review cycle remains retained. One new final
two-axis review and one findings remediation pass are reserved after validation.
Package4 proof remains historical; changed native bytes require a new complete
immutable package and separate-UID acceptance before installed qualification.

Final-send causal scope refinement: initial outer guard currently consumes and
records Admitted before request transport. To preserve unknown-time hold before
first send, make outer checks non-consuming preflight and move first durable
consume to the final sender callback. Existing protocol/core guard and queue
service transition are included in this same ticket. After any actual first
request, Admitted remains historical truth and retry checks must not pretend to
undo it. Public queue checks must distinguish pre-first-send unknown/pending
from post-first-send authorization recovery, preserving original IDs/deadlines.
This implements the existing frozen contract; it does not add another mode.

Smallest seam selected: split the existing core admission context into
non-consuming pending preflight and final consume. Pending preflight verifies
the host guard exists; final existing QueueStore.admit_bounded owns the original
record/time/cancel transaction. Its current unknown→pending and expired→terminal
behavior is reused, without a new protocol/state API or duplicated UTC/DB reads.
Existing queue-selection gating and Authorized-stage retry rechecks remain.


### Package5 installed acceptance | 2026-11-16

Completion wake007c1957 actually reached this conversation with native receipt
90a3465c; registration alone was not treated as delivery. Reconciled exact
complete-package5/job-20261117T024538Z-0b8376c8c1a7: PASS1176.072s. All six
source and transferred hashes match; codex6bc59c44, Native9af. Nine serial
installed gates now pass: active updater cross/same, account/default/shared
history rollback, privateowner, preparation expiry/reload, queue expiry/cancel/
unknown/restart, and admitted/lostreply/reconnect. First8 passed initially.

Final adapter stage initially failed safely: real persisted RPC duplicate upper
bounds1794885200.049925 and1794885200.0499253 differ exactlyone f64 step; strict
equality refused admitted evidence. Exact public-response replay isolates that
one field. Public adapter regression RED, then focused10PASS311/10PASS312 after
Wakeff9b9c01 repair. At most adjacent representable bounds allowed; both finite,
ordered and qualified; larger upper rounded outward must be strictly before
original expiry. More disagreement and crossing expiry still refuse. Native
bytes unchanged; new isolated test helper preserves priorhelper/credentials.
The first repair replay had a too-long tmux socket before native start; short
case then PASS25.147s. No native rebuild or broad review repeated.

Additional public nativegoal check PASS42.807s: owned provider reports25tokens,
then goal explicitly paused and its exact owned follow-on turn interrupted.
Paused status, tokenBudget2000, exact tokensUsed25, original history and identity
survive stopped rollback/re-upgrade. Intentional owned interruption is separate
from active-stream updater preservation. Fresh owned-process census0 and working
PID1879/hash unchanged; no working native replacement. Original failed pipeline
and setup receipts retained. Curated package5-installed-acceptance.json owns
qualification summary; parent695 stays OPEN pending production adapter adoption,
original full Python assertion and applicable live/runtime gates.
