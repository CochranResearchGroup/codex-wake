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
