# Native wake failure diagnosis — 2026-10-10

The LitScout wake `wake_20261010_140715_73d7` encountered two separate failures. Its original queue submission raised WakeError; later reconciliation raised ConnectionClosedError. The original wake remains cancelled and was not resubmitted.

## Confirmed reconciliation defect

The affected thread's history response was 14,620,973 bytes. websockets defaults to a 1,048,576-byte message limit, closing the connection with code 1009. Reads without turns and queue listing succeeded. Native reconciliation requests the full history, so it could not resolve uncertain delivery on this long-lived thread.

The native request client now permits responses up to a finite 32 MiB limit and disables compression, retaining socket ownership checks and the absolute request deadline. A real local Unix WebSocket regression with a 2 MiB history fails before the change and passes afterward. All 13 focused native tests pass. Source-scoped reconciliation of the affected live thread now completes with `no_exact_native_evidence`; this establishes successful transport, not successful wake delivery.

## Initial submission remains unexplained

A disposable local server exercised the installed Codex 0.162.1 queue command. It sends thread/queue/add directly and its successful stdout matches the existing acceptance expression. The live daemon recognizes that method (an empty request was rejected for missing threadId). These checks exclude a basic method or stdout-contract mismatch, but do not establish the original rejection cause. The original receipt retained only the exception class, losing subprocess stderr needed to diagnose it conclusively.

Temporary diagnosis receipts: `/tmp/codex-wake-litscout-diagnosis/`; focused test summary: `tests/green-v2.log` and `tests/green-v2.exit`. The cloned-root replay is superseded by the direct transport probe and regression: changing roots changes prompt identity and invalidates that replay as causal evidence.

## Remaining work

The installed 0.9.0-qualified release is unchanged. Promote the repair through the release procedure, preserve cancellation and uncertainty safeguards, and qualify a fresh disposable native wake before claiming automatic delivery works. Separately preserve bounded, redacted queue-command failure diagnostics so future submission failures have an attributable cause. Do not retry the cancelled incident wake.
