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
