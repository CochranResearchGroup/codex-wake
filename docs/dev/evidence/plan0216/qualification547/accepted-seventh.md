# Installed qualification #547

Exact source `8f5f04296f83ceecbd4f98c22bfa01e627081800`, version
`0.22.0.dev3`, wheel SHA256
`f072c599347fbf3d977d888235afcb35c4d89104190e1529bc449d0773800813`.
All314package members equal source, wheel and installed files before and after
acceptance. Declared dependencies resolved under real separate UID1017 using
Python3.12.3; msgspec0.22.0. Installed direct dependency and MCP file-manifest
hashes are retained separately. Build/install logs remain private; their hashes
and deterministic SOURCE_DATE_EPOCH=1794355200 are retained. No primary-account
installation or production symlink change occurred.

One canonical unprofiled installed TabMonitor+Slate100-tab fixture run used
60s idle/60s active, default1s ticks and activity/health/errors ON. No source
override. Startup and10-conversation activation were separate deterministic
barriers; all120ordinary events alternated actual thread states. Thresholds
were unchanged: idle<=1%, active<=5% of one core, aggregateownedRSS<=256MiB,
p95<=2s.

| Gate | Result |
|---|---|
| Idle CPU |0.732393% (0.44CPU/60.077s), pass|
| Active CPU |3.711613% (2.23CPU/60.082s), pass|
| Aggregate owned RSS |48,422,912bytes, pass|
| Event-send to public projection p95 |1.022886s, pass|
| Ordinary events projected |120/120, pass|
| Final owned controls / test-user OS processes |0/0|

CPU/RSS includes observer and all owned live readers/helpers plus reaped child
CPU, traversing children across all threads. Active owner1.93CPU/children0.30;
idleowner0.39/children0.05. Idle61ticks/+2inventory; active60ticks/+11inventory,
+1198resource serializations/+4802reuses. Excluded driver/native-fixture CPU
idle3.516s/active3.484s; private birth-qualified tmuxserver CPU0.30s/0.57s,
RSS4.54MB. Driver main/other-thread counters are retained, but native protocol
server and producer share that process and cannot be isolated further. Shared
tmux work cannot be attributed to individual clients. SharedWSLkernel/host and
metadata-only native fixture remain explicit limitations. This is no provider
turn or positive exact TUI responsiveness claim. All earlier failures remain
unchanged in this directory.

Exact installed CLI tier flags/readable status, actual stdio MCP schemas/reads,
authenticated HTTP and OAuth MCP start/status/stop passed; anonymous HTTP refused.
A separate stopped-cache fixture passed complete100-row329,179-byte reads through
all four transports with every marker/padding checked and originalstate restored.
That stale synthetic cache is explicitly not100live tabs on those transports.

Bounded20s existing-host acceptance ran the installed candidate as primaryUID1000
using a separate private observation root, with health/errors disabled.46existing
tabs/19bound conversations, one connected native source and availabletmux source;
68observed processbirths unchanged,0gone, pane layouts unchanged. The retained
read-only formatting channel read two windows in one enrolledworkspace, requests2,
failures0, connected/read_only; all recorded owned controls were gone after close.
No optionwrite/refresh/capture/input/providerrequest/productionmonitor activation
occurred. Productionmonitor remained stopped; fresh final test-user census0.

No natural live status transition occurred in that20swindow (0updates,1baseline).
Real native broadcast transition behavior therefore remains unverified by this
read-only live run. Root explicitly adjudicated this limit as compatible with
ticketclosure based on fixture broadcast qualification plus installedhost proof;
no fullreal-broadcast claim. Live `/proc` aggregateRSS peak42,348,544bytes and
ownedCPU2.49s are phase observations. The separate `ru_maxrss` field reports a
3.17GB process-lifetime highwater and is not a valid20sphaseRSS measurement; it is
preserved with this distinction, not substituted for the valid `/proc` gate.

Commands used installed candidate Python with scripts from the exact archive:
`tab_observer_acceptance547.py --monitor --seconds 60 --tick-interval 1
--source-commit 8f5f04296f83ceecbd4f98c22bfa01e627081800 --receipt UNIQUE`,
then `tab_observer_surfaces547.py --receipt UNIQUE` underUID1017, and
`tab_observer_live547.py --seconds 20 --receipt UNIQUE` as primaryUID1000.
Local source tests on Python3.11/3.12 are root-owned evidence, separate from these
installed Python3.12.3 results. No hostedCI, merge, deployment, productionmonitor
enablement or broadreview was performed by this lane.
