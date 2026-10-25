# Issue318 scoped refresh repair

State: INCOMPLETE. PR332 carries the Wake adapter; the native dependency is local
in codex-318 and is not installed in the current shared daemon. Source, native
execution, installed resource proof and current-session refresh are separate gates.

## Red-capable public seams

`tests/test_scoped_refresh.py` drives public CLI admission and an independent
refresh controller over an owned Unix fixture. Initial admission failed with
refresh_capability_unsupported. Six cases pass: active-peer isolation, unsupported
native scope, missing workspace ownership, lost-response reconciliation without
replay, stale resource expiry and counter-regression refusal. Existing shared
refresh14 and common-permission12 cases pass. Undefined-name and policy-wiring
checks pass. Logs remain in the user-scoped318-319 evidence directory.

`scripts/scoped_refresh_native_qualification.py` drives two real loaded native
threads with versioned toy MCPs and real Wake processes, with zero model turns.
Installed native0.164.0 rejects the exact scoped method. The first patched-native
probe correctly failed: status inspection spawned temporary latest-config MCP
connections and showedv2 while actual tools still returnedv1. A separate pending
refresh probe accepted queue admission but still returnedv1 with zero model turns.
Both failures and cleanup receipts are retained; neither is a successful refresh.

## Required native dependency

- thread/mcpServer/reload requires an exact loaded thread selector and never
  invokes legacy global reload. dryRun:true validates it without queueing;
  response echoes threadId and queued:false. Actual admission returns queued:true.
- mcpServerStatus/list runtimeOnly:true requires a loaded thread and observes
  its existing MCP manager. Default config-inspection semantics remain unchanged.
- Out-of-band MCP access applies an already-admitted pending refresh without a
  model turn. In-flight steps retain their prior runtime snapshots.
- New native public two-thread regression covers inspection, selected refresh,
  a missing selector target, runtime catalog/behavior agreement and unchanged peer.

Wake mode thread_mcp_idle uses the read-only scope probe before advertising
support or admission and runtimeOnly:true for catalog proof. Only MCP resources
are eligible; skill cache reload is outside connection-only scope. The watcher
waits only for its source to be idle, journals once, verifies goal continuity and
actual resources, and never resumes/reset goals or falls back to shared reload.

## Current-session dependency readback

Read-only probe at2026-10-25 confirmed daemon2692768 still executes installed
Codex0.164.0 and rejects thread/mcpServer/reload. Its goal was unchanged and no
refresh effect was attempted. Current source cwd is codegraph, while the legacy
self-refresh host profile points at codex-wake. Neither wrong-workspace authority
nor a shared reload establishes current-session refresh. The scoped native fix
must be loaded by the actual daemon before that acceptance gate can be satisfied.

## Validation checkpoints

Protocol/schema revision with dryRun:254/254 PASS. Wake revision44eae6b hosted
CI40155428900 passes both Python release gates. That earlier revision predates
runtimeOnly catalog selection; the successor must be separately validated.
Native full app-server, core selected refresh tests, final build and installed
end-to-end qualification are still pending at this checkpoint. One initial full
app-server run is retained with legacy-status semantic regression, a missing
codex test binary and timing failures; it is not a clean final verdict.


## Installed proof and compatibility correction

Wake runtime311da84, version0.21.2, is installed at the immutable release prefix.
Hosted CI40156033409 passes both full1564-test suites: Python3.11 in148.857s and
Python3.12 in179.661s, with the existing optional skip. Installed49-tool MCP smoke
passes. A seventh public fixture case separately verifies that an active goal
stays active with the same nonzero counters and no goal/set or reset/resume call.

Native raw-source revisiona50f43518c corrects the earlier broad-getter prototype:
legacy runtime reads do not apply pending refreshes. Only the new scoped API and
explicit runtime inspection use the idle-application helper. All seven affected
native cases PASS, including selected_executor_plugin_exposes_its_mcps_only_to_that_thread
and the new two-thread reload regression. Native protocol254/254 PASS; the existing
core previous-runtime-retention regression PASS. Schema generation and application/
CLI builds PASS. The local native binaries report development version0.0.0; their
manifest, source revision and executable SHA256 identify them, not a release claim.

The final installed-native/Wake workflow in scoped-corrected-installed/receipt.json
PASSES: selected Wake0.21.2, peer0.21.1, same two thread IDs, identical paused goals,
zero model turns, exactly three toy startups (two originalv1 plus selectedv2), and
no owned native/watcher/toy survivors. The goal resource allowance is not renewed.
The public controller receipt reaches completed only after actual toy behavior
and runtimeOnly Wake catalog proof; queue acknowledgement is a separate boundary.
Goal recovery also PASSES again on installed0.21.2 against native0.164.0, with zero
model/external-provider calls and unchanged original resources.

A corrected, reviewable native dependency is included as
[the patch](../../../../patches/codex/318-thread-scoped-mcp.patch). It is not an
upstream PR or a live replacement of the current native daemon.

## Production readback and remaining gates

Five command links, both full skill directories and the independent refresh
watcher now use0.21.2-311da84. The already-qualified0.21.1 goal-limit controller is
unchanged: its implementation did not change in this slice. All seven production
campaign snapshots retain generation, allocation, limits, deadline, charges,
accounting basis, first stop and latch; no resources or caller grants were renewed.
Rollback custody is under deployment-backups/0.21.2-311da84 outside Git.

A new exact-workspace host route issue318-codegraph-thread uses the existing common
self permission, without adding a caller UUID grant. Installed inspection returns
permission:allow, requested_scope:current_connection, native_scope:thread_mcp_connections,
and capability:unsupported with explicit native_dependency:thread/mcpServer/reload.
The running daemon2692768 remains native0.164.0. This session has not refreshed.

The broad native prototype run reports931 executed cases:928 pass,3 fail, plus1 skipped. One failure
was the legacy-read regression corrected above. Hook warmup and safety-check typed
notification still fail in a bounded serial run; no baseline classification or
whole-native green claim exists. Native release qualification and activation in
the actual shared daemon remain open, as do318 and current-session acceptance310.
The overall318/319 goal is incomplete even though319 remains closed and installed.
Memory disposition:forbidden; no memory write was authorized.


Final native checks: scoped Clippy fix/check PASS and just fmt PASS. Final native
source6115475dd95f6ffd525992bd5f98051d543a4c68 differs from behavioral qualification
revisiona50f43518c by formatting/documentation only. Tests were not rerun after the
formatter, following native repository instructions. Corrected side-by-side native
binaries are pinned to a50f43518c; their installed-native/Wake probe also PASSES.
The earlier ab5ec6430c binary manifest is explicitly marked as requiring the
legacy-read correction and must not be promoted. A fresh process census finds no
owned fixture command-line survivors; all seven production snapshots still match.


## Opt-in experiment2026-10-25T03:43:24Z

After explicit user approval to experiment, a fresh isolated run using the pinned
installed nativea50f43518c and Wake0.21.2 PASSES in10.719s. Selected Wake upgrades
to0.21.2 while the peer remains0.21.1; both native thread IDs and paused goals are
unchanged. Zero model turns occur, exactly three toy startups are observed, and
native/watcher/toy cleanup is terminal with no detected owned survivors. Receipt:
user-scoped318-319/opt-in-experiment-20261025T034324Z/receipt.json.
Stock Codex, the shared daemon and production campaigns were not changed. The
experiment does not resolve the two broader native failures or refresh this
requesting session. Upgrade/rollback discipline is recorded in patches/codex/README.md.
