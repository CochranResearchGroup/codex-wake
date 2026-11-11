# Post-TDD installed qualification #547

Exact source `f3e1e0d426f0012224439022c2dd48e8a7a0c4fe`, version
`0.22.0.dev3`, wheel SHA256
`8587274a52090af70e0ede950e4080cc25d1af1df13de8104155ddfc68dc24d8`.
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
| Idle CPU |0.831976% (0.50CPU/60.098s), pass|
| Active CPU |3.910094% (2.35CPU/60.101s), pass|
| Aggregate owned RSS |51,666,944bytes, pass|
| Event-send to public projection p95 |1.069560s, pass|
| Ordinary events projected |120/120, pass|
| Final owned controls / test-user OS processes |0/0|

CPU/RSS includes observer and all owned live readers/helpers plus reaped child
CPU, traversing children across all threads. Active owner2.04CPU/children0.31;
idleowner0.45/children0.05. Idle61ticks/+2inventory; active60ticks/+11inventory,
+1197resource serializations/+4803reuses. Excluded driver/native-fixture CPU
idle4.277s/active3.988s; private birth-qualified tmuxserver CPU0.30s/0.59s,
RSS4.94MB. Driver main/other-thread counters are retained, but native protocol
server and producer share that process and cannot be isolated further. Shared
tmux work cannot be attributed to individual clients. SharedWSLkernel/host and
metadata-only native fixture remain explicit limitations. This is no provider
turn or positive exact TUI responsiveness claim. All earlier failures remain
unchanged in this directory.

Exact installed CLI tier flags/readable status, actual stdio MCP schemas/reads,
authenticated HTTP and OAuth MCP start/status/stop passed; anonymous HTTP refused.
A separate stopped-cache fixture passed complete100-row329,178-byte reads through
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
no fullreal-broadcast claim. Live `/proc` aggregateRSS peak41,963,520bytes and
ownedCPU1.47s are phase observations. The separate `ru_maxrss` field reports a
3.30GB process-lifetime highwater and is not a valid20sphaseRSS measurement; it is
preserved with this distinction, not substituted for the valid `/proc` gate.

Commands used installed candidate Python with scripts from the exact archive:
`tab_observer_acceptance547.py --monitor --seconds 60 --tick-interval 1
--source-commit f3e1e0d426f0012224439022c2dd48e8a7a0c4fe --receipt UNIQUE`,
then `tab_observer_surfaces547.py --receipt UNIQUE` underUID1017, and
`tab_observer_live547.py --seconds 20 --receipt UNIQUE` as primaryUID1000.
Local source tests on Python3.11/3.12 are root-owned evidence, separate from these
installed Python3.12.3 results. No hostedCI, merge, deployment, productionmonitor
enablement or broadreview was performed by this lane.

This is one immutable requalification after the single broad review and single
TDD remediation pass. The source includes deadline propagation, skipped-evidence
invalidation and exact native endpoint/home/peer/epoch source binding. The
qualifier performed no additional review or TDD pass. Seventh-package success
and all earlier failed receipts remain unchanged.
