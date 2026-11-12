# Stop monitor-triggered tmux server crashes

State: OPEN
Owner: primary / ecochran76
Work item: LOCAL-P223
Priority: incident
Branch: fix/tmux-subscription-crash
Target: origin/main
Base: 92c00a0d8495f2d7d386cd7d85cd4f610e8f6ded

## Current State

IN_PROGRESS. Kernel confirms production tmux server SIGSEGV at21:43:27 and21:50:18
on Ubuntu tmux3.4-1ubuntu0.2. Both PC offsets4ce75 map through exact-build symbols
to control.c:924, control_check_subs_all_panes, inlined in subscription timer.
Saved kernel/service/formatting evidence privately before containment. Global
formatting disabled, startup unit disabled/stopped, original43-tab formatting
restored through supported rollback with no failures. Live Byobu server retained.

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
