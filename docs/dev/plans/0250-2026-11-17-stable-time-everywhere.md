# 0250 | Stable Time for all WSL measurements

State: OPEN
Owner: root
Parent: #695 remaining Python gate; operator correction applies across Codex Wake.
Integration: feat/native-expiry-695; base098f409a8de5d7010984189127bf4f10e12fb1d3.
WIP3. Reuse owned checkout; preserve workingdaemon, credentials and unrelatedlanes.

## Contract

Every application time measurement uses qualified Stable Time UTC or its
host-counter evidence: timestamps, elapsedtime, deadlines, timeouts andfreshness.
No WSLwall/monotonic fallback, midpoint fabricated as expiryproof, or global
monkeypatch. Missing/unqualified evidence, counterepoch/frequency change, expired
handoff or counterrollback holds timedependent effects. Strict guards stay strict.
Persisted old clockcoordinates never silently change domains or renew deadlines.
Existing explicit host-injected deterministic clockseams remain valid for tests.
Blocking transport primitives are not evidence of elapsedtime or UTC.

## Bounded execution graph

ST01 shared strict measurement interface (root, running, no blockers): reuse
native_clock/host_counter rather than duplicate credentials orservice protocol.
Prove WSLclock discontinuity cannot affect measurement and unavailable authority
refuses without rawclock fallback. Immutable hostcounterepoch continuity owns
elapsed evidence; qualified UTC bounds own calendar/expiry decisions.

ST02 runtime bypass audit (worker, running, no blockers): classify all existing
rawtime measurement calls by owner/purpose and migrationdependency; identify
bootstrap cycles and persisted clockdomains before adaptation. Read-only return;
not a claim of completed migration.

ST03 claimant/background adoption (pending, blocked ST01+ST02): replace real
freshness/observation/supervisor measurements and prove original publicmutation
case with strict sharedclock; legacy/future/stale/unqualified evidence refused.

ST04 remaining runtime/script adoption (pending, blocked ST01+ST02): migrate all
measurement paths without broad search-replace changing time domains. Static
inventory must have no undocumented production WSLmeasurement bypasses. Focused
checks by causally affected owner; no duplicated comprehensive suite/review.

GR01 Grok readiness diagnosis (worker, running, no blockers): reconcile current
installed profile, stale catalog and qualifiedtime logic with deployedP233
acceptance. Read-only; no login/refresh/inference, quota reset, servicechanges,
credentialcopies or new provider spend without existing exact effect authority.
Preparation of a concrete bounded repair/requalification may proceed locally.

## Acceptance and limits

Deliver one validated integration branch. Focused publicseam red/green first;
reuse native9af/package5 and previous review, do not rebuild/reviewagain.
GlobalAGENTS already updated; source migration remains incomplete until ST04.
No workinghost activation or premature closure695/628. Parent validation still
requires an explicitly authorized comprehensive pass after source convergence.
Memorywrite forbidden absent explicitrequest; retain canonical evidence instead.

## Bootstrap transport boundary

`host_counter` cannot request the shared measurement clock while acquiring its
QPC sample: that would recurse through `native_clock.snapshot`. Its Linux LP64
timerfd is an explicit, relative kernel blocking-I/O fuse, never a UTC sample,
elapsed measurement, freshness result or authorization deadline. No guest clock
value is read. One retained client fuse covers connect, send, retries and the
entire response frame; progress never rearms it. Request and producer frame
fuses likewise cover the whole frame, and a malformed or late producer is
retired without replay. Unsupported timerfd acquisition holds before bridge
startup; there is no clock or platform fallback. Fixed idle accept and owned
child cleanup waits remain blocking primitives. Actual counter qualification,
epoch/rate continuity and UTC handoff age remain with the existing authenticated
Stable Time and QPC validators. A kernel fuse firing proves only transport
refusal, never that an authority deadline elapsed.

## Current bounded continuation

ST04-COLLECTOR (owner collector_stable_deadlines, running; blockers validated
ST01/ST04-APP-TRANSPORT) owns local_session_events launch, RPC and stream deadlines.
Acceptance: original qualified deadline, refusal before new input on clock loss,
uncertain/no replay after possible input, exact protective ownership preserved.

GR01-SAMPLE (root, preparation running; blockers validated GR01/ST01) qualifies
the selected Grok build's existing thread/sample route before live use. It captures
one response on an ephemeral fork; model tool calls are not dispatched by Core.
This is a narrow candidate, not full coding or mixed-provider qualification.
The old packet adapter unconditionally refused and its schema inspection used
Native9af instead of the selected Grok sourcea5806e; that earlier categorical
capability inference is withdrawn. Preserve original receipts and append correction.
Require selected executable acceptance, eligible parent/turn pins, bounded startup
effects, qualified external deadline and consumed unknown attempts before spending
the approved fresh allowance. No new Native build or working-daemon adoption.

## Creation and wait batch closeout

The current batch in0250-execution.json closes ST04-CREATION,
ST04-CONTROLLER-WAITS, ST04-LOCAL-WAITS and ST04-LOCAL-ACTOR on the integration
branch. One review from5d291917 to frozenf0556ea0 accepted one Spec P1 boundary
finding; one bounded TDD pass adds final wait authorization before publication.
See docs/dev/evidence/issue0695/st04-current-batch-review.md. ST04-COLLECTOR was
validated in the preceding batch. GlobalST04 and #695 remain OPEN; this closeout
does not establish full Python, installed runtime, activation or live Grok proof.

## Daemon, event metadata and signal lease batch

ST04-DAEMON-UTC, ST04-RECORD-EVENTS and ST04-SIGNAL-LEASES are validated and
closed repo-local on the integration branch. Default legacy scheduling uses
qualified lower UTC; missing UTC holds legacy work with additive time_held
reporting while relative native counter intents continue. Signal expiry holds
new matching on uncertainty and preserves already reserved matches. Events and
legacy moves use qualified-or-unknown metadata; schema2 moves retain their
required timestamp and hold before publication rather than becoming unreadable.
Lease reclaim and continuation use lower/upper bounds without renewing ownership.
The journal schema and terminal-fence contract remain unchanged.

Combined92 focused checks pass on Python3.11/3.12; final27 causal checks pass on
both after integration guards. Earlier review/remediation are preserved without
a new broad review. See issue0695/st04-daemon-signal-validation.json under
docs/dev/evidence. GlobalST04/fullPython/runtime/activation remain open.
The stale Grok parent lookup is resolved by the retained takeover receipt; the
current live gate is the expired allowance and uncertain sample, not a missing
parent. No new live work is authorized by this source continuation.

## Acknowledgement wait and monitor batch

ST04-ACK-WAIT and ST04-MONITOR are validated/closed repo-local. A positive
acknowledgement wait uses one retained qualified counter deadline, acquired before
paste, and rechecks after receipt observation. Missing time before paste holds
without an attempt; loss after possible paste retains an unknown outcome and
prohibits replay while allowing later receipt reconciliation. Zero wait stays an
untimed inspection. Monitor metadata uses qualified lower UTC or null/not_observed;
freshness requires conservative qualified bounds. Integrated49 focused checks
PASS on Python3.11/3.12. See issue0695/st04-ack-monitor-validation.json.
Global ST04 and #695 remain open; legacy transport metadata/final-send admission
and signal-v2 terminal timestamps still need separate adoption. No broad review,
full suite, Native build, live provider effects or deployment occurred.

## Signal cancellation and input/output custody packet

ST04-SIGNAL-CANCEL preserves readable schema2 records and durable terminal fences
when stopping without UTC. ST04-INJECTOR-METADATA requires qualified default UTC
before legacy transport work and holds Native4 expiry uncertainty. ST04-HOST-STDIN
retains a qualified frame deadline through input acceptance. ST04-OUTPUT-FRAMES
retains a positive wait across generator suspension and preserves untimed
inspection/established terminal-page drainage. ST04-GROK-EVENT-WAIT retains its
original custody wait and refuses an unqualified final connection without replay.
No live Grok allowance is renewed. Actor acquisition remains its separate
pre-custody UTC gate; unvalidated targets are not mutated for diagnostics.

Fresh source inventory at ffa2ac25 found305 direct raw measurements in83
production files,29 callable bindings and16 legacy wrapper calls. This is a
static candidate inventory before the packet, not current reachability or proof
of a completed migration. Tabs/terminal contracts are the largest coupled debt;
OpenClaw remains parked. Prior broad review is preserved without repetition.
Final packet evidence owns exact checks, retained failures and closeout states.
