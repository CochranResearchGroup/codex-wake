# A2A mailbox operations foundation

State: CLOSED
Lane: P63
Parent: Plan 0101 / independent foundation of P63.7
Depends-On: Plans 0102-0104 integrated; delivery-dependent acceptance remains open
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/181
Branch: feat/p63-mailbox-operations
Target: origin/main
Owner: primary

## Scope

Explicit operator capability rotation, body-free diagnostics, retention preview
and bounded explicit body pruning. Preserve journal authority, receipt history,
identities and dedup tombstones. No envelope deletion, automatic retention,
service installation or production enrollment. Delivery/restart/multiroot live
qualification stays in Plan 0101; this packet does not claim full P63.7 done.

Retain uncertain attempts, open processing claims, active conversations and
unprojected receipt signals. Bodies become eligible only thirty days after
terminal resolution and with all pins discharged. Apply rechecks eligibility
inside one transaction and requires the exact preview fingerprint. A stale
preview refuses deletion. Compact metadata remains for at least the advertised
ninety-day dedup horizon; this packet conservatively retains it indefinitely.

Rotate only with explicit operator authority, increment generation, publish a
new private capability before commit, and invalidate old credentials. Rotation
never silently restarts accepted work; old generation claims require explicit
operator reconciliation before a new generation may report outcomes.

## Acceptance and bounds

Tests cover old credential denial/new credential validation, rollback during
capability publication, metadata preservation, stale retention previews, pinned
bodies, thirty-day eligibility and absence of bodies in diagnostics. Installed
CLI fixture must exercise new operator verbs without provider effects.
One primary owner; two implementation attempts and one bounded rework packet.
No independent lane needed for this small coupled operator slice. Campaign
checkpoint at or before 700,000 goal tokens, below the user's 750,000 stop.

## Current State

Implementation begins after PR #184 integration at canonical
6d4c399e11f3c08b5a048c61579675657cabcb08. Automatic delivery and receipt source
CLI/restore remain separate unfinished gates. This operations foundation can
progress independently without claiming those dependencies accepted.


## Local qualification

Six operations tests pass, including rollback on capability publication failure,
old token/cached actor refusal, thirty-day body eligibility, stale previews,
conversation/signal pins and preserved identity/digest/receipt/dedup metadata.
Comprehensive suite: 818 tests passed in 42.501 seconds without retries.
Installed fixture exercised doctor, empty retention preview/apply and rotation;
old capability was denied and new capability accepted. Twenty-two read-only
runtime connections closed, no residual children or runtime effect methods.

Signal acknowledgement clearing in the pruning unit fixture is explicitly
simulated. The current receipt library does not clear production retention pins;
those remain conservative until the source/restore integration qualifies exact
projection acknowledgements. Pruning is logical body-row removal; SQLite pages,
WAL files and backups are not secure-erased. Physical compaction, compact
ninety-day tombstones and restart/restore qualification remain wider gates.

Hosted Python 3.11/3.12 SUCCESS, run 37145185923. PR #185 merged at 2026-10-03T18:43:51Z; canonical f3050bde52301518f5ac061835b5ac502198ed1c. Bounded operations foundation accepted; parent campaign remains OPEN.
