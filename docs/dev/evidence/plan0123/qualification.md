# Plan0123 acquisition qualification

Source baseline: 36de0b0. Inspection is explicitly opt-in and makes no mailbox or clock changes.

## Acquisition and policy

`codex-wake time inspect` invokes a packaged Windows PowerShell collector on WSL. The collector brackets DNS/UDP operations with host QPC, pins the reply peer with a connected UDP socket, uses unpredictable 64-bit origin tokens, and returns one common host-counter instant with guest/host boot identities and a collection generation. Python validates the envelope and packet before normalizing intervals. Printed bounds refer to collector completion; they are not a claim about the later display instant. No Linux wall clock supplies UTC, RTT, sample age or cache expiry.

The operator registry is visible with `time inspect --offline`. Cloudflare and NIST are admitted for **unauthenticated plain-NTP inspection** using their documented conventional UTC profiles. They are independently operated; this does not guarantee reference-clock/network-path diversity. Netnod and PTB stay visible and disabled (`time_scale_unqualified`). We have not inferred their leap policy from ordinary replies. Live production candidacy is not asserted by this command; the schema exposes `production_ready: false` and the explicit authentication policy for every source.

NTP intervals conservatively include the entire measured round trip, reported root delay/dispersion, server precision, counter quantization and 100 ppm elapsed-time uncertainty. The latter is a declared engineering envelope for short host-QPC intervals, not a claim that arbitrary hardware is calibrated. Maximum RTT 0.5 s and root error 0.1 s keep admitted observations useful under the 1 s consensus-union limit. Maximum age 120 s limits holdover drift to 12 ms and bounds stale reuse; uncertain rounds cannot authorize deadlines. Precision outside 2^-30 through 1 s is rejected. Era-zero timestamps are supported only for 2020–2036, with a hard upper bound before the rollover. Leap announcements/alarm replies are excluded rather than extrapolated across the event.

Each DNS lookup and UDP send/receive is bounded to 2 s on Windows. Round admission rejects more than 20 host seconds, with a 25 s parent-process termination safeguard. Two admitted providers keep this well below that bound. A per-user Windows file lease serializes collectors; a same-host-boot QPC attempt marker limits network rounds to one per 64 s, including failed attempts. Repeated calls reuse the same collection while recomputing age at a fresh QPC instant. No automatic burst/retry loop exists: retry/backoff is 64 s, longer than [NIST's four-second minimum](https://tf.nist.gov/tf-cgi/servers.cgi). Cache/lease files live solely under LOCALAPPDATA/codex-wake/time-inspection. Host reboot invalidates the counter/cache; guest reboot invalidates observations but preserves the host rate guard. Malformed cache fails closed.

## NTS packaging spike

Extracted Ubuntu chrony 4.5-1ubuntu4.2 into `/tmp/codex-wake-nts-spike`; did not install it or start a service. Official [chronyd documentation](https://chrony-project.org/doc/latest/chronyd.html) specifies `-Q` as offset-only and `-x` as disabling clock control. Executed:

```
chronyd -Q -x -t 10 'server time.cloudflare.com nts maxsamples 1' 'pidfile /tmp/codex-wake-nts-spike/client.pid' 'bindcmdaddress /tmp/codex-wake-nts-spike/client.sock'
chronyd -Q -x -u ecochran76 -t 10 'server time.cloudflare.com nts maxsamples 1' 'pidfile /tmp/codex-wake-nts-spike/client.pid' 'bindcmdaddress /tmp/codex-wake-nts-spike/client.sock'
```

First failed because the extracted package's `_chrony` account does not exist. Second ran with clock control disabled, emitted a command-socket permission warning and timed out without synchronization. Both outputs are preserved beside this note. No success or root cause is inferred from timeout. Packaging decision: established Chrony remains the candidate for a future optional authenticated adapter, with an explicit user and private writable paths; it cannot currently supply the required bounded host-counter observations. The functional inspection collector therefore declares plain NTP, never attempts NTS and never silently downgrades a failed NTS request. No new cryptography or certificate bypass was introduced.

## Evidence and review

`first-live-inspection.json` and `second-live-inspection.json` show real two-operator network consensus. `cached-live-inspection.json` retains the second generation with fresh host-counter age, proving repeated inspection avoids another network round. All four operators are represented in each report. Those receipts prove inspection behavior and admitted plain-NTP transport only, not authenticated UTC or live wake behavior.

TDD seam: public CLI plus `inspect_time(collector=...)`; injected collector replaces only the external host acquisition boundary. First command test failed for the missing `time` verb, then passed. Common-instant test failed for the missing collector interface, then passed. Additional deterministic fault controls cover malformed packets, wrong origins, excessive delay, stale evidence, duplicate replies, DNS errors, request replay, host/guest identity mismatch, invalid counters and missing interop. Existing decision-core tests cover duplicate operators, outages and tied groups.

Standards review: acquisition is isolated from mailbox authority; packaged host script has a narrow role and no system adjustment operations. Spec review: all four candidates remain visible, unknown profiles disabled, two independent qualified plain-NTP inspection sources demonstrated. No authenticated or live production admission is claimed. Production acquisition for deadline effects requires the subsequent integration contract to retain these trust and instant limits.
