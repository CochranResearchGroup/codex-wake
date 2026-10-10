# Source review against ac6a575

Frozen objective: Plan0133 tickets0134/0135; public CLI/scheduler and persisted
reader compatibility. Installed activation belongs to0136 and is not claimed.
Review performed serially by primary under repo policies, using code-review's
Standards and Spec axes; repo-native plans are the configured tracker.

## Standards

Versioned compatibility is explicit; old schema4 semantics remain. Behavior
regressions use the existing unittest harness at public CLI/poll/dispatch seams,
with injected provider acquisition. No source/live service or root overlap.
Candidate R1: metadata sources string could masquerade as a list of operators.
Blocking; red reproduced expiry of malformed state; collection-type check fixes it.
No independent reviewer or runtime acceptance is claimed.

## Spec

Candidate R2: legacy timestamp parser truncates native5 fractional expiry at
transport dispatch. Blocking; red reproduced premature expiry, repaired using
precise deadline and preserving fractional retry times for new records.
Candidate R3: unavailable time must not prevent read-only resolution of an
already uncertain submission. Blocking; red retained firing despite exact native
proof, repaired with lock/re-read reconciliation and unknown timestamps. No resend.
Arming, interval holds, outage/restart persistence, cancellation, malformed state,
Windows decision admission, compatibility and legacy tests pass. Installed real
recipient, installed worker restart and live provider readback remain0136 gates.
One review discovery and one consolidated remediation pass; no scope expansion.
