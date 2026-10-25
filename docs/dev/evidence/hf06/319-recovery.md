# Issue319 observation recovery — source and installed acceptance

User authorized diagnosing-bugs/TDD for318/319 within01:16:37–02:16:37UTC on
2026-10-25. This packet addresses319;318 remains open and is not renamed into a
permission/refusal-only completion. Source branchfix/318-319-lifecycle, PR332,
basePR327. Final runtime commit ef339e03e1d116823132e9ddd12b80dc518f2778.

## Reproduction and diagnosis

The public CLI regression injects a native thread/read timeout into an enrolled
campaign, then healthy exact reads. Before the fix, authorized recover returned
unsupported and healthy polls retained the stop. This proves the missing explicit
recovery transition, rather than assuming accounting or heartbeat clears a latch.
An operator turn, episode history, crash reconciliation and shared-member order
were added through observed failing regressions before their corresponding fixes.

Exact evidence root: `/home/ecochran76/.local/state/codex-wake/318-319/`.
RED/GREEN receipts:319-red.log/319-green1.log;
319-operator-turn-red.log/319-operator-turn-green.log;
319-episodes-red.log/319-episodes-green.log;
319-crash-red.log/319-crash-green.log;
319-shared-order-red.log/319-shared-order-green.log;
319-crash-status-red.log/319-crash-status-green.log;
319-direct-reconcile-red.log/319-direct-reconcile-green.log;
319-stop-scope-red.log/319-stop-scope-green.log.
Commands use the named test_goal_recovery tests, public CLI/CommandRunner and an
independent real watcher, isolated writable roots, and injected Unix native I/O.

## Result and retained authority

CLI/MCP recovery now requires explicit matching approval or a verified operator
capability. It checks agreeing native observations around aggregate nondecreasing
accounting, exact goal identity, same boot, fresh unchanged controller generation,
current host/common policies and original remaining resources. All checks repeat
at commit. The goal stays paused; this is not resource renewal or automatic resume.
An active original campaign turn cannot be reclassified as an operator reply
when its stop scope was never observed.

Shared recovery requires an operator's explicit allocation scope and every member's
qualified stopped state and current permissions. A pending allocation journal
fences admission through interrupted writes; status remains held and directs the
same operation to reconciliation. Root faults survive either member polling order.
First-stop evidence and old effect outcomes remain intact. Distinct stop/recovery
episodes retain later faults without overwriting the original diagnostic.

## Validation

Hosted CI40152284377 at ef339e0 passes both3.11/3.12 release gates: full1558-test
unit lanes, one opt-in skip each, undefined-name checks, compile, policy wiring,
package build and installed49-tool smoke. No hosted retries were needed.
Focused46 recovery/permission/controller tests pass at the final behavior.
The installed0.21.1 native active-turn/operator-reply qualification also passes
with4 localhost HTTP responses and zero external provider calls. Twelve original
resource/clock/identity fields match the native recovery before/after records.

Installed prefix `/home/ecochran76/.local/share/codex-wake/releases/0.21.1-ef339e0`;
wheel SHA256 `45e8fccebc8a473e634351efa54af67b88af8c17df6681f76f80a10382d4e0eb`.
`goal_recovery_native_qualification.py` passes at that installed interpreter:
actual native0.164.0, private Unix proxy delays one read until a real timeout,
independent controller stop, healthy reads alone retain the latch, and explicitly
authorized recovery preserves original charges/deadline/generation/limits. Zero
model turns/provider calls, native goal not resumed, no owned processes remain.
This native timeout probe uses an idle disposable goal; active/operator-turn and
shared/crash variants are proved at the injected public/controller seam, not
represented as paid/live-provider acceptance.

Local broad runs performed while implementation files were changing are retained
and not claimed as final passes. The early runs also hit timing-sensitive handoff
fixture failures under host I/O contention; the five affected handoff scenarios
pass a bounded serial rerun (preflight-serial.log). Later mutable-tree runs mixed
old stop code with the new scope requirement and correctly failed the recovery
fixture; immutable hosted ef339e0 contains both changes. A final source-frozen
local3.12 run is separately logged in frozen-full312.log; its terminal result must
be inspected before claiming it passed. Raw failed logs are not overwritten.

## Production activation

Commands, full skills and both relevant controllers use0.21.1-ef339e0. Before
handover, the former production goal controller was discovered cleanly stopped
with its unit still enabled; no fresh maintenance permit could be prepared.
After confirming seven campaigns already latched, activation used a cold start,
not a fabricated graceful permit. The replacement is active with fresh heartbeat.
All seven campaigns retain limits, charges, deadline, generation, allocation,
accounting basis, stop latches and first-stop evidence. No production recovery was
attempted and no old campaign renewed. Other native clients/daemon stayed running.
Rollback and preservation receipts:
`/home/ecochran76/.local/state/codex-wake/deployment-backups/0.21.1-ef339e0/`.
Old skill rollback directories were moved outside active skill roots to avoid
advertising duplicate obsolete skills. Prior prefixes remain intact.

## Remaining318 boundary

Current native0.164.0 rejects a scoped reload selector. Two settings-update probes
do not reload resources; stopping one owned toy MCP does not reconnect it. All
were isolated two-thread probes with cleanup. Local Codex source worktree
`/home/ecochran76/workspace.local/codex-318` prepares a separate
thread/mcpServer/reload method while preserving the legacy global method. Protocol,
schema and executable/peer-isolation acceptance are separate; no new native daemon
was installed or shared production reload attempted.318 cannot close from these
source/parser checks. The active user goal remains incomplete until318 is proved.

Memory disposition forbidden: no explicit user memory-write request.
