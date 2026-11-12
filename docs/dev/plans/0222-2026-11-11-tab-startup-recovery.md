# Automatic tab formatting startup recovery

State: CLOSED
Owner: primary / ecochran76
Work item: LOCAL-P222
Priority: bug follow-up
Branch: feat/tab-format-startup
Target: origin/main
Base: a337f510c27bef600fc95a375682c2fadbf5f59d

## Current State

Operational hold: incident [LOCAL-P223](0223-2026-11-11-tmux-subscription-crash.md)
confirmed a monitor-triggered tmux3.4 server crash. Startup and formatting were
stopped/disabled and originals restored. The activation facts below describe the
earlier qualification, which missed stalled-client session teardown. P223 owns
the corrective source/runtime acceptance; do not infer current activation here.


DONE. PR584 merged6dbeeeef; exact0.22.0.dev9 installed after package and real-unit
qualification. Startup is enabled/active for the private user controller and
recover_namespace is enabled for its selected workspace. All43 current tabs
match native options; monitor settings are preserved and observations fresh.
All320 package members and9 launchers match the merged source. Supervisor remained
running; no native lifecycle call or host reboot. See the
[deployment receipt](../evidence/plan0222/deployment.json).

## Scope and acceptance

Add local-only tabs startup enable/disable/status for one private controller root,
with an owned systemd user unit starting the existing foreground monitor at login.
Do not restart native Codex services or reboot this host. Preserve monitor settings,
manual formatting holds, rollback and opt-out. An explicit recover_namespace display
preference (default false) authorizes automatic namespace baseline rollover using
the same retained-originals mechanism as explicit enable. Exact workspace identity
is required; do not infer correspondence from labels or create terminals/agents.
Service can start before terminal availability and discover the server later.

## Execution

Primary serial lane, no delegated workers. TDD skill, real public controller/tmux
regression first; minimal shared baseline rollover; local service CLI with service
ownership/conflict tests; focused formatting/service tests and exact package
qualification. Startup unit lifecycle uses disposable terminal state under a real
user manager. Test UID1017 qualifies package behavior independently; report its
missing manager and shared-kernel limitation. No provider or prompt dispatch.
Use one bounded review/remediation pass; at most three setup probes per missing
runtime capability before reporting that exact unqualified boundary.

## Validation seams and done

Controller refresh proves opt-in replacement recovery, original custody, old-intent
fences and disabled/paused holds. Local service API/CLI proves unit content,
root-scoped ownership, idempotence and safe disable. Real service restart before
terminal readiness plus terminal replacement proves the startup sequence; a host
reboot is outside scope and cannot be claimed. Retain failures and exact commands,
source/package identity and rollback. Passing tests alone do not activate startup.

## Custody and memory

One task-owned checkout,117 registered after creation versus116 before. Retain
until publication/integration or a concrete runtime validation blocker; review
cleanup at closeout. Canonical source and current supplied receipts suffice for
planning; Graphiti discovery skipped to avoid repeating prior empty routing reads.
Memory write forbidden without an explicit memory-update request.

## Source and runtime evidence so far

Red: opted-in controller refresh initially rejected unknown recover_namespace.
Red: monitor started before configured socket failed to discover it in6.310s.
Both now pass. Shared retained-baseline helper preserves returning rollback holds;
unavailable observations remain fenced. Automatic discovery checks existing
bounded same-user discovery every5seconds and rebuilds feeds only on changed
workspace identities; configured socket generations invalidate immediately.

Broad focused run:258 tab tests,257PASS and1command-catalog integration failure
in113.217s. Registered the3startup commands as local-only operations and regenerated
reference/coverage. Corrected11contract/startup checks PASS5.930s; newly added
controller hold test passes in the9-test formatting selection. No assertions
weakened. Final two-axis review found a systemd dollar-expansion path issue;
red quoting test proved it and literal-dollar escaping fixes it. No other accepted
blocking finding; no further broad review loop.

Real user-manager candidate fixture PASS: service enabled before terminal exists;
late socket discovery and opted-in recovery preserve prior originals/settings;
repeated enable preserves monitor generation; service restart preserves rollback
and pane identity; disable stops only the owned fixture service. No host reboot.
Test UID1017 lacked /run/user/1017/bus; one temporary systemd user-manager probe
exited1 without starting a manager. Qualification therefore separates UID1017
package/CLI/rollback acceptance from disposable working-user unit lifecycle.

Final source16-case installed UID1017 regression selection and transport/rollback
qualification PASS; final reviewed package also passes the real user-manager
fixture. See [validation](../evidence/plan0222/validation.md). Proceed instruction
covers this proposed startup follow-up; source publication and account activation
follow qualification without another confirmation round. Existing native services
and supervisor are preserved; previous prefix and startup-disable rollback remain.

## Installation and final custody

Source6dbeeeef1ff239ed7f0ee2b9d40519c0d8f0d8d6, wheel
0477bb482c44109cce782d0a34d46cdfa5ece0b9f866451c447abd8f510b7c9e.
Real UID1017 package code, working immutable prefix and merged source all match320
members. Source review and qualified wheel precede selection. Supported startup
enable handed the detached monitor to the new user service without changing saved
settings; unit is enabled/active with zero restarts. Current43tabs have no native
option mismatches.10protected files retained.29of30 sampled native generations
remain; one prior native process is absent at final census, exit reason not
observed. No native lifecycle operation was performed and no causal continuity
claim is made for that process. Supervisor PID/state stayed unchanged across
activation. No model/provider call or actual host reboot.

Private qualification/plan0222 retains exact original launcher links, source/wheel
hashes, unit/formatting snapshots and rollback.py. Rollback disables only this
root's service, restores its prior recovery preference and previous complete CLI,
and starts the prior monitor with saved settings. It does not overwrite evolving
baseline/wake records. Old prefix remains intact. Synthetic QA receipts are
retained before task fixtures are removed. Task checkout cleanup follows remote
closeout readback;117registered before removal,116expected after. No unrelated
worktree or dirty main file is changed. Memory disposition forbidden by the
explicit memory-update boundary, no write attempted.
