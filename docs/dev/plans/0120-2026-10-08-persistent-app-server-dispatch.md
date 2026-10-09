# Preserve app-server turn ownership after dispatch

Date: 2026-10-08
State: OPEN
Owner: delegated provider remediation lane; primary integration owner adjudicates
Lane: APP-PERSIST
Branch: fix/app-server-owned-socket-alias
Work item: docs/dev/plans/0120-2026-10-08-persistent-app-server-dispatch.md
Target: origin/main
Integration: squash_pr

## Current State

Initial repair PR221 integrated as a691d356 and was installed normally with a
fresh Wake supervisor, unchanged four roots and unchanged Codex daemon. A fresh
distinct native acceptance event proved scheduling/parity/privacy but failed
before `turn/start`: actual Codex0.162.0 reports an owned leaf alias, which the
initial blanket nonsymlink check rejected. That failed event remains archived;
neither it nor the original interrupted event was retried.

The bounded followup qualifies that exact private alias layout and preserves
precise WakeError diagnostics.31 focused tests and912 full Python tests pass
(full46.245seconds); compileall and diff checks pass.
No further provider adoption or live event belongs to this source followup before
primary review. Actual intended-thread completion remains unproven.

## Problem and scope

Installed0.7.1 accepted a real app-server wake, then closed its owned standalone
server immediately after `turn/start`. The intended turn was interrupted after
52ms with only the canonical user pointer. Admission and dispatch receipts remain
valid; intended-thread completion failed. Preserve that original attempt without
retry. This bounded dependency repair owns app-server client lifetime, focused
provider-free regressions and operator documentation. No OpenClaw, mailbox,
watch evaluation, new ingress, provider installation or shared-daemon restart.

## Decision

Dispatch connects stdio through the installed Codex CLI's existing
`app-server proxy --sock SOCKET` to a running actor-owned daemon. Read-only
`app-server daemon version` discovers its exact socket; `proxy --help` qualifies
capability rather than guessing support from a version string. Each discovery
command has a five-second deadline. Require an absolute canonical Unix socket,
current-actor ownership and a private actor-owned containing directory. A reported
current-actor-owned leaf alias is allowed only under a private owned directory,
with an absolute canonical target socket under its own private owned directory.
Reject ancestor aliases, chains, unsafe directories and foreign/dangling targets;
pass the canonical resolved target to the proxy. Preserve specific WakeError
messages rather than masking them through its ValueError base class. Never
start, replace, stop or take ownership of that daemon. Missing/unsupported daemon
fails before `turn/start`; no fallback to the known-interrupting standalone owner.

Only the owned proxy is terminated/reaped after request completion. The existing
30-second RPC bound is enforced against silent peers and notification streams;
it is not a turn deadline. Typical long-running turns remain owned by the daemon
and do not block the supervisor. `submitted` and `ack_observed` remain admission
receipts; completion is unknown until independently observed in the exact thread.
Read-only thread inspection retains its existing standalone client behavior.
Custom per-record process commands cannot establish persistent dispatch ownership
and are refused in real dispatch; injected provider-free clients remain supported.

## Acceptance and bounded validation

- [x] Reproduce the lifecycle regression before repair using a real local
  provider-free Unix-socket daemon and owned proxy subprocess.
- [x] Accepted turn remains able to complete after proxy teardown; no completion
  claim is manufactured from `turn/start` acceptance.
- [x] Missing/stopped/unsupported, nonprivate, wrong-actor and unsafe/ambiguous alias
  paths refuse before proxy creation/turn-start; discovery never starts a daemon.
- [x] Silent RPC/discovery timeout is bounded and owned proxy cleanup reaps it.
- [x] Exact supported owned leaf alias reaches a real provider-free daemon;
  canonical target is used and daemon-owned turn survives proxy teardown.
- [ ] Followup canonical integration and installed intended-thread acceptance after primary
  review. No deployment, new wake or new turn belongs to this source packet.

One remediation packet and one primary closed-world adjudication; no broad
provider rewrite. Source qualification cannot close the installed acceptance gate.
Private red/green/full-suite receipts are retained by the parent campaign; tracked
regressions reproduce the relevant source behavior without provider access.
