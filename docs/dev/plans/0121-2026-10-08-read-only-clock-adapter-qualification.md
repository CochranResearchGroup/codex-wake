# Plan 0121 — Read-only clock adapter qualification

State: CLOSED
Branch: prototype/wsl-time-consensus
Owner: primary agent
Outcome: bounded transport experiment complete; production qualification PARTIAL.

## Current State

Three bounded parallel collection rounds each received Windows UTC/QPC plus Cloudflare and NIST NTP replies. All nine reads succeeded. Four local failure controls were rejected. No production clock adapter is installed or integrated. Existing mailbox checkpoint is untouched.

## Scope and bounds

Question: can this workstation obtain real Windows and independent compatible network observations, with measured transport delays and bounded failures? Run three collection rounds, each under a 20-second outer process timeout, Windows read timeout 8 seconds and UDP reply timeout 3 seconds. No clock setting, service changes, real suspension/reboot, mailbox access or runtime deployment. Each NIST request was separated from the preceding round by more than four seconds.

## Source selection and primary references

Cloudflare and NIST are separate operators. Use time.cloudflare.com and time.nist.gov for this experiment. Cloudflare explicitly does not smear leap seconds; NIST describes conventional leap-second handling. Google Public NTP smears time and should not be casually mixed with these sources. This establishes administrative and documented time-scale distinctions, not independence from all common network or reference failures.

- [Cloudflare NTP](https://developers.cloudflare.com/time-services/ntp/)
- [NIST Internet Time Service and leap handling](https://www.nist.gov/pml/time-and-frequency-division/time-distribution/internet-time-service-its)
- [NIST endpoints and minimum request interval](https://tf.nist.gov/tf-cgi/servers.cgi)
- [Google Public NTP](https://developers.google.com/time)
- [NTP protocol specification](https://www.rfc-editor.org/rfc/rfc5905)

## Implementation under qualification

`prototypes/qualify_clock_sources.py` is a read-only experiment, invoked with `timeout 20s python3 prototypes/qualify_clock_sources.py`. It uses direct PowerShell interop to read DateTime.UtcNow and Stopwatch/QPC. These are UTC readings, not evidence that Windows UTC is synchronized. The Windows transport interval excludes unknown host UTC error.

NTP uses a connected UDP socket to pin the reply peer and a random transmit token verified against the returned origin timestamp; Linux wall time is not used as a trusted transmit timestamp. It validates packet size, server mode, version, leap alarm, stratum/Kiss-o'-Death, origin token, nonzero receive/transmit timestamps, timestamp order and rough root quality. It reports server time intervals using server root quality plus the full measured RTT, without claiming symmetric network delay. No system-clock adjustment API is used.

All duration measurements use Linux MONOTONIC_RAW diagnostically. UTC comparisons advance network observations to the latest receipt point using RAW elapsed duration. This is a conditional measurement, not a qualified production holdover clock. Real suspension can invalidate that alignment and was not exercised. NTP era 0 only is supported; protocol authentication, complete RFC client behavior, leap-second boundary handling and strict DNS cancellation remain unqualified.

## Measured results

| Round | Network interval union width | Windows ahead of network interval | Windows interop duration |
| --- | ---: | ---: | ---: |
| 1 | 50.1 ms | 1.715–2.421 s | 655.2 ms |
| 2 | 45.1 ms | 1.707–2.078 s | 325.2 ms |
| 3 | 46.8 ms | 1.725–2.030 s | 258.7 ms |

These ranges include measured transport bounds but assume the diagnostic RAW time scale. They are not certified accuracy bounds. Cloudflare and NIST intervals overlap in each round. Under the prototype's illustrative 1-second agreement policy, these observations favor network consensus over Windows. No live selection or effect was performed.

Direct `w32tm /query /status /verbose` returned “The service has not been started. (0x80070426)”. A separate Get-Service W32Time read returned Status 1 and StartType 3 (Stopped and Manual). Thus Windows synchronization cannot be assumed here. This does not establish why the service is stopped, whether another Windows mechanism adjusts UTC, or the cause of earlier Linux adjustment behavior.

Current Linux boot ID is 3cf33f0d-c332-452e-8b6d-396eccccd3db, different from the earlier investigation's fe9e3104-98d1-42bc-b1fa-495780e0f891. Do not treat this sample as continuous with that historical boot. No reboot was performed by this packet.

## Failure controls and validation

Four local UDP controls exercised the real adapter: truncated packet, unsynchronized reply, wrong origin, and no response. All returned failures; timeout surfaced without admitting an observation. These controls do not substitute for full fault coverage. Normal collection subprocesses exited zero; the diagnostic w32tm command exited nonzero as recorded. Raw observations, failure controls and derived comparison are preserved in `/home/ecochran76/.local/state/codex-wake/clock-research/20261008-adapters/`. A compact durable readback is committed as `prototypes/clock-adapter-qualification-results.json`.

## Acceptance disposition and next packet

Transport reachability PASS; compatible separate network operators PASS; observed sample agreement PASS; four refusal controls PASS. Production timing/authentication bounds NOT QUALIFIED; real sleep/reboot behavior NOT RUN; mailbox migration NOT RUN. This closes the bounded experiment, not the product feature.

Next build the production time-provider boundary with injected observations, source selection, bounded collection and restart-safe deadline handling. Qualify freshness using an elapsed source whose suspension semantics are explicit. Keep Windows-first preference conditional on its quality and the network consensus. Preserve read/cancel operations during time uncertainty. Only then design and verify migration of the live checkpoint and deadlines; do not merely bypass the existing guard.

Memory disposition: unavailable — no reviewed Codex Wake Graphiti target group in established context; record a non-write receipt against this artifact.
