# Four independent time-provider candidates

Packet: Plan0122, 2026-10-08. Read-only research; no installed runtime changes.

| Operator | Endpoint probed | Reply | Raw diagnostic RTT |
|---|---|---|---|
| Cloudflare | time.cloudflare.com | accepted by prototype validator | 26 ms |
| NIST | time.nist.gov | accepted by prototype validator | 41 ms |
| Netnod | ntp.se | accepted by prototype validator | 131 ms |
| PTB | ptbtime1.ptb.de | accepted by prototype validator | 130 ms |

The machine-readable sibling `four-operators.json` preserves all four replies. One bounded parallel collection used `ntp(host)` from `prototypes/qualify_clock_sources.py`. This is transport reachability evidence at one observation, not an availability guarantee. These replies use unauthenticated UDP. Raw elapsed timing is diagnostic and is not established as a production time authority. Each interval refers to its own receipt instant; directly comparing those intervals would be incorrect.

## Primary-source qualification

- [Netnod distributed time service](https://www.netnod.se/swedish-distributed-time-service) documents Netnod operation, UTC(SP) synchronization and the public anycast service. Netnod is independent of Cloudflare and NIST. Its explicit leap-smearing profile still needs qualification before production admission.
- [PTB NTP service](https://www.ptb.de/cms/en/ptb/fachabteilungen/abt9/gruppe-95/ref-952/time-synchronization-of-computers-using-the-network-time-protocol-ntp.html) documents its public time service. PTB supplies a fourth operator. Its explicit leap-smearing profile still needs qualification before production admission.
- [Cloudflare NTP](https://developers.cloudflare.com/time-services/ntp/) explicitly does not smear leap seconds and warns against mixing smeared time.
- [NIST Internet Time Service](https://www.nist.gov/pml/time-and-frequency-division/time-distribution/internet-time-service-its) describes its leap-second behavior. [NIST server guidance](https://tf.nist.gov/tf-cgi/servers.cgi) limits polling frequency; the eventual adapter must honor provider policies.
- [Google Public NTP](https://developers.google.com/time) uses leap smearing; it is not admitted into this proposed step-UTC group.

## Decision and limits

Use four independently reviewed operators as the target configuration, requiring at least two agreeing observations and a unique largest agreeing group. A 2–2 split pauses time-dependent effects. Windows is a healthy, consistent fallback and cannot break network ties. Endpoint aliases do not provide independent votes.

The core has no provider defaults or acquisition loop. Netnod/PTB are reachable candidates, not enabled production defaults. Remaining gates are explicit time-scale compatibility, protocol/authentication policy, reliable age/alignment through suspend/restart, bounded polling, diagnostics, and mailbox migration validation. Internet access alone does not guarantee access to UDP time services or authenticated, correct time.
