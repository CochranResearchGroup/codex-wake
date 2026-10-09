# Preserve app-server turn ownership after dispatch

Date: 2026-10-08
State: OPEN
Owner: delegated provider remediation lane; primary integration owner adjudicates
Lane: APP-PERSIST
Branch: fix/app-server-persistent-dispatch
Work item: docs/dev/plans/0120-2026-10-08-persistent-app-server-dispatch.md
Target: origin/main
Integration: squash_pr

## Current State

Source remediation and31 focused app-server/supervisor tests pass. Full Python
regression passes912tests in46.820seconds. The prior full run retained one outdated
supervisor routing fixture failure, then its scope was corrected explicitly.
Compileall and diff checks pass. Active planning audit retains the pre-existing
Plan0119 missing Current State finding; this plan adds no finding. Canonical integration,
provider installation and actual intended-thread completion remain unexecuted.

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
command has a five-second deadline. Require an absolute nonsymlink Unix socket,
current-actor ownership and a private actor-owned containing directory. Never
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
- [x] Missing/stopped/unsupported, nonprivate, wrong-actor and symlink socket
  paths refuse before proxy creation/turn-start; discovery never starts a daemon.
- [x] Silent RPC/discovery timeout is bounded and owned proxy cleanup reaps it.
- [ ] Canonical integration and installed intended-thread acceptance after primary
  review. No deployment, new wake or new turn belongs to this source packet.

One remediation packet and one primary closed-world adjudication; no broad
provider rewrite. Source qualification cannot close the installed acceptance gate.
Private red/green/full-suite receipts are retained by the parent campaign; tracked
regressions reproduce the relevant source behavior without provider access.
