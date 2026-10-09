# Preserve app-server turn ownership after dispatch

Date: 2026-10-08
State: OPEN
Owner: delegated provider remediation lane; primary integration owner adjudicates
Lane: APP-PERSIST
Branch: fix/app-server-unix-websocket
Work item: docs/dev/plans/0120-2026-10-08-persistent-app-server-dispatch.md
Target: origin/main
Integration: squash_pr

## Current State

PR221 and alias correction PR222 integrated and were installed normally, with
unchanged four roots and the same Codex daemon. Fresh distinct native events
remain immutable and archived. The alias-qualified scenario admitted one wake,
but initialize timed out before any turn started: Codex's raw stdio proxy copies
bytes while its Unix control socket requires WebSocket upgrade and framing.

Actual installed0.162.0 read-only initialize succeeded over the supported Unix
WebSocket transport using already-declared websockets17.2. This successor
replaces the mismatched proxy bridge with that maintained client. Source
qualification and required CI precede primary review and any integration/adoption.
Actual intended-thread completion remains unproven.

## Problem and scope

Installed0.7.1 accepted a real app-server wake, then closed its owned standalone
server immediately after `turn/start`. The intended turn was interrupted after
52ms with only the canonical user pointer. Admission and dispatch receipts remain
valid; intended-thread completion failed. Preserve that original attempt without
retry. This bounded dependency repair owns app-server client lifetime, focused
provider-free regressions and operator documentation. No OpenClaw, mailbox,
watch evaluation, new ingress, provider installation or shared-daemon restart.

## Decision

Dispatch connects to the existing daemon's Unix WebSocket control transport with
the already-declared maintained `websockets.sync.client.unix_connect` library.
Read-only `app-server daemon version` discovers its exact socket with a five-second
deadline. Require a canonical actor-owned Unix socket under a private actor-owned
directory; a private owned leaf alias may resolve once to that canonical target.
Reject ancestor aliases, chains, unsafe directories and foreign/dangling targets.
Never start, replace, stop or take ownership of the daemon. There is no standalone
fallback for dispatch. Readiness includes a bounded actual WebSocket handshake.

Initialize sends the initialized notification. Every RPC filters notifications
and matches the exact request ID under one absolute30-second deadline, including
blocked writes; deadline expiry shuts down only the owned connection. The library
caps incoming messages at32MiB and close at one second. Only the owned connection
closes after turn/start acceptance; long agent work remains daemon-owned.
Submitted/acknowledged receipts do not prove completion; independently read the
exact intended turn transcript.
Read-only thread inspection retains its existing standalone client behavior.
Custom per-record process commands cannot establish persistent dispatch ownership
and are refused in real dispatch; injected provider-free clients remain supported.

## Acceptance and bounded validation

- [x] Reproduce the lifecycle regression before repair using a real local
  provider-free framed Unix WebSocket daemon.
- [x] Accepted turn remains able to complete after connection teardown; no completion
  claim is manufactured from `turn/start` acceptance.
- [x] Missing/stopped/unsupported, nonprivate, wrong-actor and unsafe/ambiguous alias
  paths refuse before connection/turn-start; discovery never starts a daemon.
- [x] Silent RPC/discovery timeout is bounded and owned connection cleanup closes it.
- [x] Exact supported owned leaf alias reaches a real provider-free daemon;
  canonical target is used and daemon-owned turn survives connection teardown.
- [ ] Followup canonical integration and installed intended-thread acceptance after primary
  review. No deployment, new wake or new turn belongs to this source packet.

One remediation packet and one primary closed-world adjudication; no broad
provider rewrite. Source qualification cannot close the installed acceptance gate.
Private red/green/full-suite receipts are retained by the parent campaign; tracked
regressions reproduce the relevant source behavior without provider access.
