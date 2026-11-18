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
