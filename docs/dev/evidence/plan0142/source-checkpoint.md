# Ticket0142 source checkpoint

Baseline843fabc; public dispatcher reproduction: u1-red-exact.log,
1FAIL0.385s notification_visibility_unproven with one paste and no visible marker.
First fixture failed against a bound import alias and is retained separately;
corrected only external fixture wiring before the exact red. Green1PASS0.459s.
Actual native queue receipt replaces screen receipt; binding identity and draft
checks retained. Scheduler context revalidates original attempt/leases/authority,
returns current issued recipient capability; immutable envelope unchanged.

Reply bookkeeping crash red1FAIL1.010s left arm firing despite committed native
submission. Allow exact native_live_recipient_v1 receipts; green with network
expiry control2PASS0.904s. No resend. Draft appearing during native preparation
red1FAIL0.365s; final fresh UI check green1PASS0.400s. Remaining pre-submit race is
observational, not an atomic idle guarantee. Existing scope retained.

Tests at public dispatcher and external runtime/queue peers replace three obsolete
paste-based tests. Retained risk mapping: pointer/body/claim behavior→live native
receipt and result-consumption cases; partial paste uncertainty→unconfirmed,
rejected, timeout and interrupted native queue cases; expiry→public cancelled/
expired no-effect cases and existing network-expiry test with real scheduler claim.
Legacy stock wake injector paste test remains because that transport still exists
for its separate wake path. Imported fixture class was corrected to module import
so unittest does not rediscover saved tests in the live module.

Affected71PASS23.611s before final draft/malformed control additions. Presubmit116PASS58.751s on the affected selection before the final malformed
receipt case; that final case is included in installed candidate verification.
Installed/native proof follows frozen-source verification.
No old Plan0139 state changed; source proof is not installed/live completion.
