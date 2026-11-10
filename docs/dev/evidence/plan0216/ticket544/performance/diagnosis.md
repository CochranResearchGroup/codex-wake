# Pre-review performance gate repair

Base9331614d, isolated fix/observer-copy-cost-544. This is the pre-review hard
resource gate repair; the requested single broad review/remediation remains later.
No production enablement, deployment, provider traffic or threshold change.

## Causal loop and changes

The frozen100tab workload failed idleCPU on the exact installed candidate. A
20second diagnostic profile at default1second cadence confirmed that repeated
full resource deepcopy dominated publictick cost. Per-tick copies consumed .966s
in the retained before profile. The observer now caches JSON contract data's
canonical encoding until actual inventory/activity/source availability changes,
then decodes fresh independent public containers in C each tick. Nested caller
mutations cannot enter the retained cache or other returned snapshots.

A second cause was concrete protocol cadence: the observer created a tmux feed
with .5second pending-response deadline, then did not poll until its default
one-second next tick. Initial subscription responses were incorrectly rejected as
metadata_timeout before ready frames were consumed, causing reconnect/inventory
churn. Both initial and replacement feeds now allow2seconds. A real100tab public
regression pauses to the actual next service cadence and verifies continued source
availability, no inventory subprocesses and independent returned nested data.

The cached transport also erased the concrete TmuxTransport ownership type. The
existing default-redacted visible-error guard therefore returned unknown without
classifying the owned screen. A validated concrete tmux proxy now preserves that
type and delegates commands to its already-qualified original adapter. Generic
or unavailable transports retain the generic proxy; no ownership guard was relaxed.
A real default-privacy public observer fixture verifies an error is present with
only its redacted message retained. This restores real tier work before resource
qualification, rather than counting unknown attempts as successful error checks.

## Observed evidence

The two new public regressions fail against the base implementation (retained
public-regressions-red.txt) and pass with the fix. All5observer tests pass both
Python3.11.15 and3.12.13; ruff undefined-name gate and diff whitespace pass.

The identical qualification-driver workload was used for10seconds idle plus
10seconds active,100real disposable tmux panes/copied sleep codex binaries,
metadata-only native fixture, tiers ON,1second ticks, UID1017. The before observer
module hash matches base9331614d exactly. The after diagnostic uses an explicit
UID1017 source copy with only this observer file changed; it is not installed
acceptance. Driver copy changed only its installed-only assertion to permit the
explicitly labeled diagnostic source override, plus the unprofiled switch below.

Profile before -> after:

- Idle12.713% ->2.283%; active15.493% ->5.295% one core (profiler overhead included).
- Publictick cumulative2.918s ->.739s; inventory12calls ->3calls in20seconds.
- Tick fullresource deepcopy cumulative.966s -> no fullresource deepcopy.
- After aggregateRSS42.6MiB, p95send-to-projection.223s, no remaining owned clients.

Short unprofiled after: idle1.762% still FAILS1% gate; active3.271% passes5%, RSS
40.9MiB and p95~1.015s. Two active notifications were pending at the measurement
boundary. This diagnostic is not a pass, and full60second installed acceptance
must still run on an exact complete package after remaining inventory/cache work.
Root owns the remaining cache hotspot: afterprofile inventory3calls .582s, cache
observe3calls .531s, process observation300calls .164s. No cache/traits files were
changed by this packet.

Commands used the driver `/tmp/wake216-qualification-547/acceptance.py` with
`--seconds 10 --tick-interval 1 --diagnostic-profile PATH --receipt PATH`, running
under sudo -n -u codex-daemon-test and `/tmp/wake216-uid1017/bin/python`3.12.3.
The source diagnostic override was `/tmp/wake547-copysource/src`; no working-host
prefix or symlink changed. `COPYCOST_UNPROFILED=1` suppressed cProfile for the
short unprofiled variant while preserving its diagnostic/not-acceptance label.
Machine receipts retain exact component CPU, RSS, request counts and cleanup.

Memory disposition: forbidden; no explicit memory-write request.
