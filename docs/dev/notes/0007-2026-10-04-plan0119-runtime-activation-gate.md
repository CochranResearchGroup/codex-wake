# Plan 0119 runtime activation gate

Status: prepared, not authorized or executed. Candidate source checkpoint:
`10fce9d` on `feat/p63-live-delivery`. Verification 0112 records focused tests,
actual executable build, reproduction, and isolated unloaded-thread rejection.
This gate is necessary for M1; it does not close any milestone.

Candidate executable:
`/tmp/codex-wake-plan119-runtime/codex-a956835d020762cb2b570053af06f643a11c0ecc/codex-rs/target/debug/codex`
Current SHA256 `8c1315463e35083aa33e47e4f05137ed6d607f5c55d2bc1b4a536c046aa6390b`.
Current patch SHA256 `bbcf349398054e371003ce04aa894e8a6ee1c9445359ba88bb5efcdfd8b37212`.
Namespace and durable sender-arm follow-up is retained in the same execution
branch; verification0113 supersedes the initial build locator for activation.
The installed 0.160.0 server rejects the added method; normal turn/start cannot
substitute because it may steer a concurrent turn.

Activation scope requiring explicit approval under Plan0119 execution controls:

Policy0021 also requires an exact integrated origin/main commit for deployment.
Hosted source checks and integration must pass before this gate can execute.

1. Fresh-read all loaded shared-daemon threads and the exact demo clients. Wait
   until the restart can occur without interrupting active turns. Reconfirm demo
   threads and empty composers; never delete/archive/create replacement threads.
2. Preserve the current package selection and daemon settings, including absence.
   Current selection is `/home/ecochran76/.codex/packages/standalone/current` →
   `/home/ecochran76/.codex/packages/standalone/releases/0.160.0-x86_64-unknown-linux-musl`.
   Settings path `/home/ecochran76/.codex/app-server-daemon/settings.json` currently
   does not exist. Re-read both immediately before any mutation.
3. Stage the exact hash-verified binary in an owned private candidate package;
   atomically select it at the existing standalone current link. Temporarily
   disable daemon auto-update using the existing settings format
   `updater.autoUpdateEnabled=false`, preserving other settings.
4. Run the candidate's `app-server daemon restart` against existing CODEX_HOME.
   This affects every client connected to this user-scoped shared daemon,
   including unrelated sessions and possibly this execution session. It is a
   deployment gate, not the demo-owned worker restart required by M3.
5. Reconnect only the designated wakeA/wakeB clients to their same durable IDs
   using the candidate executable and opt-in endpoint environment. Preserve panes
   and thread history. A: `01a10876-c7cf-7ae1-ad99-e9d829994e45`, pane `%71`;
   B: `01a10876-e53a-7322-bf68-ff43e9b2f2dc`, pane `%72`. Fresh process-generation
   readback is required before terminating or reconnecting either client.
6. Verify exact identities, socket ownership, method capability and live guards;
   bind the two clients with native CLI commands. Activate only the demo bus and
   bounded worker for one request/reply attempt after sender receipt wiring is
   ready. No unrelated root enrollment or business-system effects.

Rollback: pause the demo bus and stop its owned worker; atomically restore the
original current link and exact settings (remove candidate-created settings if
originally absent), then use the original executable's `app-server daemon restart`.
Reconnect demo clients to the same IDs using the original executable. Verify
daemon selection and all owned process generations; preserve mailbox, signal
journal, notifications, attempts, receipts and uncertainty history. No mailbox
schema migration is required by this candidate.

Approval covers only the preceding reversible local activation and reconnect,
not release publication, unrelated client termination, additional roots, or an
unsupported transport fallback. If shared-runtime activation is declined, retain
this observed blocker and continue source work without claiming live acceptance.
