# Plan 0119 candidate checkpoint

Execution worktree: `/home/ecochran76/workspace.local/codex-wake-p63-feature-successor`,
branch `feat/p63-live-delivery`, starting HEAD `f445033`. Issue 181 remains open.
M1–M4 remain unproven. This is candidate implementation, not live acceptance.

The retained `runtime/codex` patch adds an opt-in owning TUI endpoint and atomic
`turn/startIfIdle` server operation. Wake's native bind-client, dispatch and
bounded worker commands connect the existing mailbox scheduler to that endpoint.
The endpoint checks actual composer, modal, pending-input, thread and root state;
the server submits only to an already loaded idle thread without steering.
No mailbox schema change or fallback to the ordinary steering operation.

Validation at this checkpoint:

- Rust check passed against official revision
  `a956835d020762cb2b570053af06f643a11c0ecc` using toolchain 1.95.0.
- Candidate `codex-cli` executable built successfully in 7m28s and reports 0.160.0.
- 139 focused Wake A2A tests passed. Six additional Unix socket delivery tests
  passed, covering draft/busy deferral, lost-response uncertainty, retargeting,
  client generation and explicit idle-race rejection. Fixtures are not live proof.
- Reproduction helper applied the retained patch to the pinned archive and
  verified all patched file hashes. Initial missing new-file patch metadata was
  corrected; the failed prepare remains in local evidence.
- Archive lockfile normalization changes only source-less workspace package
  versions; external dependencies remain unchanged. The helper verifies both
  archive and normalized hashes and uses a locked build.
- Installed shared daemon rejects `turn/startIfIdle` as an unknown method before
  submission. Exact wakeB remained idle before and after this capability probe.
  Live round-trip attempts remain 0/3; one non-submitting capability probe.
- The built candidate recognizes the method in an isolated stdio server with an
  empty owned CODEX_HOME. Both empty and nonempty input against an unloaded exact
  thread return `WAKE_NOT_SENT:offline`. No thread is loaded and no provider
  submission occurs. Evidence: `candidate-capability.json` in the owned log root.
- Focused Rust composer eligibility test passed: private draft unchanged,
  pending user turn and external editor deferred; 1 passed, 5586 filtered out.
  Log: `/tmp/codex-wake-plan119-runtime/test-tui-guard.log`.
- The retained helper completed its locked build in 2m02s. Executable SHA256:
  `ecc8bc279390e63e3d2d7d16fa04d167a88c0f0327971ba269e765ff244073d5`.
  Exact build receipt: `/tmp/codex-wake-plan119-runtime/build-receipt.json`.

Owned candidate executable:
`/tmp/codex-wake-plan119-runtime/codex-a956835d020762cb2b570053af06f643a11c0ecc/codex-rs/target/debug/codex`.
Build/check/test logs and baseline capability response remain under
`/tmp/codex-wake-plan119-runtime`. No global install, shared daemon restart,
client reconnect, notification or message was performed.

Next: finish the Rust guard test, qualify the candidate server endpoint without
provider effects, and prepare the exact reversible activation gate for existing
wakeA/wakeB. Durable sender receipt-arm delivery is still unwired; automatic
message submission alone cannot close M1. Shared-runtime activation and actual
round-trip evidence remain required.

Budget checkpoint: inherited 996214 plus current meter 171065 = 1167279 before
this checkpoint writing; user ceiling is 1800000. Goal remains active.
Progress classification: blocker_reduction, with candidate executable and tests;
no accepted live behavior advancement.

Memory disposition: `not_durable`, because implementation is in progress with no
accepted live outcome or settled design closeout. Non-write receipt:
`/home/ecochran76/.graphiti-openclaw/state/closeout-memory/20261004T205024Z-remember.json`.
