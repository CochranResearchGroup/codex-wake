# Stop monitor-triggered tmux server crashes

State: CLOSED
Owner: primary / ecochran76
Work item: LOCAL-P223
Priority: incident
Branch: fix/tmux-subscription-crash
Target: origin/main
Base: 92c00a0d8495f2d7d386cd7d85cd4f610e8f6ded

## Current State

CLOSED for containment, source repair and safe installation. PR587 merged e16bc4d2;
exact0.22.0.dev10 installed with320matching package members and9launchers.
Formatting remains globally disabled, startup stopped/disabled, original styles
restored. Disabled unit now pins the fixed package without being started. The
same live Byobu server and all43initial pane process identities are retained.
Production reactivation is deliberately outside this closeout; require explicit
operator direction. See [deployment](../evidence/plan0223/deployment.json).

## Reproduction and ranked causes

An isolated2-session tmux with one %* pane subscription, paused fixture control
client and removal of its attached session crashes the server and loses the
unrelated survivor. Repro PC4d521 maps to the same control.c:924 (another inlined
copy). No-subscription control survives; subscription/no-stall control survives.
This is a red-capable1.5second native reproduction, not a synthetic assertion.
No formatting options or systemd are required. Exact debug buildid recorded in
private incident receipt; source and debug offsets agree.

1. Native wildcard-subscription timer dereferences the client's missing session:
   removing subscriptions must preserve the survivor under the same stalled-client
   removal sequence. Actual feed regression is the retained protection seam.
2. Rendered format strings: the minimised crash requires no format writes.
3. OOM or cgroup shutdown: live and fixture faults are native SIGSEGV at the same
   source line; no associated OOM kill, no systemd in the reproducer.

## Scope and acceptance

Remove native refresh-client -B wildcard subscriptions from the retained metadata
feed. Keep read-only event notifications and bounded metadata snapshots on the
same owned control connection; updates must still arrive without spawning a
process per tab/poll. Preserve metadata redaction, ownership/generation, no pane
input and timeout/output bounds. Actual feed lifecycle regression must keep an
unrelated session and pane process alive when a stalled source session disappears.

## Execution and done

Primary serial TDD/diagnosis lane. One focused review/remediation pass. No native
Byobu restart, host reboot, tmux package upgrade or agent relaunch. Do not reactivate
live formatting/startup during this incident; keep containment until explicit
operator direction. Source fix, focused tests, exact packaged UID1017 qualification,
publication/integration and safe CLI installation may proceed without restoring
production automation. Preserve failed reproductions and prove final monitor off,
current Byobu server generation retained, global opt-out and rollback retained.

## Custody and memory

One isolated checkout protects dirty main.117other registered entries before
creation;118after. Cleanup after durable custody/integration. Runtime incident
artifacts, private core-related material and native process evidence stay outside
Git. No personal memory write is authorized; disposition forbidden. Canonical
repo and current crash evidence suffice; no repeated Graphiti discovery.

## Review and validation

Actual-feed regression RED1.648s then GREEN;6feed checks PASS4.590s. Broader264
tests retained3timing-sensitive failures, resolved with fixture readiness barriers;
corrected21case selection PASS13.722s. Real UID1017 corrected22case installed
regressions and transport/rollback qualification PASS. Product patch unchanged
through fixture corrections. Standards/Spec primary review has no remaining
blocking finding. [Full evidence](../evidence/plan0223/validation.md).

No native wildcard subscriptions remain in source. Ordinary events plus bounded
1second metadata snapshots preserve retained connection, updates and resource
bounds. Prepare source publication and fixed CLI installation; retain global
formatting opt-out and startup disabled. Pin the disabled managed unit to the
fixed prefix without starting it; preserve original unit/manifest before change.

## Installation and custody

Source e16bc4d2a9c17ea42ad99d8e59daac8265ff2558; exact wheel
3133816f537ff43cbfb7b6d9babc9c733e0e7adb3b6ba41241fb0a1222e6ff92.
All320members match merged source, UID1017 install and selected immutable prefix.
Initial installed late-socket fixture failure retained; corrected22tests PASS
19.647s plus actual installed CLI/stdio/OAuth API controls and package rollback.
The raw native reproduction still demonstrates the tmux bug; product removes its
trigger instead of upgrading/restarting the native server.

Fresh OS readback: same live Byobu server PID,43of43initial pane IDs/PIDs retained,
no Byobu restart.10protected files unchanged;26of28sampled native generations
remain,2absent with exit reason unobserved; no native lifecycle call occurred.
No claim that every unrelated transient native process stayed alive. Monitor
stopped, startup disabled/inactive and pinned to fixed code, global opt-out true.

Private incident and qualification/plan0223 retain original state, kernel/symbol
proofs, failed reproductions, old unit/manifest, immutable wheel, exact launcher
rollback links and audit receipts. Keep containment if selecting an older package;
old versions still contain unsafe subscription code. No runtime transcript/core
content enters Git. QA fixtures and this checkout removed only after receipt
publication/remote readback.118registered before task checkout removal;117expected
after, other lanes untouched. Memory disposition forbidden under explicit memory
update boundary; no Graphiti write.
