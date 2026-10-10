# Native wake failure diagnosis — 2026-10-10

The LitScout wake `wake_20261010_140715_73d7` encountered two separate failures. Its original queue submission raised WakeError; later reconciliation raised ConnectionClosedError. The original wake remains cancelled and was not resubmitted.

## Confirmed reconciliation defect

The affected thread's history response was 14,620,973 bytes. websockets defaults to a 1,048,576-byte message limit, closing the connection with code 1009. Reads without turns and queue listing succeeded. Native reconciliation requests the full history, so it could not resolve uncertain delivery on this long-lived thread.

The native request client now permits responses up to a finite 32 MiB limit and disables compression, retaining socket ownership checks and the absolute request deadline. A real local Unix WebSocket regression with a 2 MiB history fails before the change and passes afterward. All 13 focused native tests pass. Source-scoped reconciliation of the affected live thread now completes with `no_exact_native_evidence`; this establishes successful transport, not successful wake delivery.

## Initial submission remains unexplained

A disposable local server exercised the installed Codex 0.162.1 queue command. It sends thread/queue/add directly and its successful stdout matches the existing acceptance expression. The live daemon recognizes that method (an empty request was rejected for missing threadId). These checks exclude a basic method or stdout-contract mismatch, but do not establish the original rejection cause. The original receipt retained only the exception class, losing subprocess stderr needed to diagnose it conclusively.

Temporary diagnosis receipts: `/tmp/codex-wake-litscout-diagnosis/`; focused test summary: `tests/green-v2.log` and `tests/green-v2.exit`. The cloned-root replay is superseded by the direct transport probe and regression: changing roots changes prompt identity and invalidates that replay as causal evidence.

## Remaining work

The repaired source was installed into the separate immutable `0.9.0-f4afd98` environment with module byte parity verified. Disposable wake `wake_20261010_143402_114f` was accepted, wrote its expected execution marker, and completed native turn `01a1263c-3cd4-7251-a201-d68efc766fff`. User entrypoints were promoted and only the LitScout integration scheduler was restarted; fresh process argv confirms the repaired Python environment, and exact-root monitor health is ready. The old `0.9.0-qualified` environment remains intact for rollback. Receipts are under `~/.local/state/codex-wake/native-repair-f4afd98/`: `deployment.json` records link rollback targets and `acceptance.json` records execution evidence. The disposable wake was archived and its tab closed.

The original cancelled wake remains cancelled. Its initial submission failure remains unexplained; separately preserve bounded, redacted queue-command failure diagnostics so future submission failures have an attributable cause. This qualification covers the tested idle attached thread and large-history reconciliation, not every delivery mode.
