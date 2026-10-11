# Issue243 completion audit — correction F4

The first review accepted a later origin after a total initial clock outage.
The completion audit revoked that acceptance: a later origin could extend the
original expiry. The CLI/poll regression first fired one request when zero was
required. The earlier installed candidate likewise fails the new installed
unanchored-expiry scenario. Those failure logs remain private and attributable.
The final candidate retains the original request, never invents an anchor, and
reports requires_original_clock_evidence immediately in its registration receipt.

| Issue requirement | Verified evidence | Boundary |
| --- | --- | --- |
| Durable intent and visible outage | CLI status/schema tests; concurrent installed creators retain one ID | Active compatible schema6 monitor required |
| Conservative relative fallback | Same-epoch counter tests, rate bounds, outward rounding; installed three-hour successor | Original valid counter or UTC anchor required |
| Absolute stops and expiry | UTC-only absolute/stop gates; before/after-runtime rechecks; missing-origin expiry regression | Queue consumer admission checks; not an atomic queue deadline or completed-turn guarantee |
| Restart, suspend, root/thread, dedup | Epoch/frequency continuity holds, UTC original-deadline recovery, wrong-root/thread refusal, archive identity, crash reconciliation | Uncertain effects reconcile without resending |
| Precision and recovery | 99.999999 ms accepts; 100 and 100.000001 ms reject; wide counter bounds; eight fresh installed workers | Injected authenticated clock/native queue fixtures, no live model turn |

Standalone wheel/source parity and installed receipts are checked in beside this
artifact. The optional private composite separately preserves all three retained
StableTime files byte-for-byte. It is not published or activated. Source review
has Standards4 and Spec4 resolved after two bounded cycles. Historical checkpoints
remain history; the F4 later-origin acceptance is explicitly superseded here.

Matt setup confirmation, default-label preference, retained adapter publication,
main integration and production activation are unfinished. Issue243/Plan0153 stay
OPEN and PR244 stays draft. The installed global command and other sessions are
unchanged; no test tab was created. No CI wait, notification or production wake.
