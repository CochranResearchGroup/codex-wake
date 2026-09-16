# Signed webhook durable-ingest join

State: OPEN
Lane: P53-C2
Issue: #105
Branch: `feat/issue-105-signed-webhook-ingest`
Target: `main`
Integration: `squash`

## Current state

Canonical main `558ae15723a9dfcd4b79b31c7a66e53439328707`
contains the accepted provider-neutral HTTP transport and the existing signed
`GitHubWebhookIngress` core. They are not joined. The production
`GitHubRestClient` deliberately rejects callback threads because its
POSIX absolute deadline owns the main thread's real timer. Provider/store
deadline proof therefore requires a main-thread execution bridge, not weaker
socket inactivity timeouts or an unkillable background worker.

## Objective

Join one exact HTTP listener to one configured signed GitHub ingress so a real
socket request runs secret verification, an authoritative attempt read, and
one durable SQLite ingest under a single explicit absolute operation budget.
Preserve commit-before-ack, polling convergence, one-source ownership, and zero
wake evaluation or dispatch.

## Frozen execution seam

- Add one internal runtime/controller whose public lifecycle is a bound address
  readback, blocking main-thread `serve()`, and bounded `shutdown()`.
- The accepted `WebhookHTTPServer` owns sockets on a helper serving thread.
  Its injected callback transfers at most one admitted request to the
  controller; it has no unbounded queue.
- The controller executes the full secret/provider/checkpoint/store ingress
  operation on the POSIX main thread under one absolute deadline. Timeout
  returns a stable unavailable result, retains no queued work, and cannot
  acknowledge success.
- Construct a fresh production attempt client per delivery so request counters
  and deadlines never leak across requests. Permit that client to reuse the
  already-owned outer absolute deadline without silently disabling deadline
  ownership for polling callers.
- Retain one `GitHubWebhookIngress` instance per configured source so bounded
  rate and delivery caches remain coherent. Durable deduplication remains the
  journal's repository/run/attempt identity, not the transport cache.
- Accept dependencies through narrow factories/protocols. This slice may use
  provider-free fakes, but the executable/config/service and secret-reference
  product surfaces belong to #106.

## Observable acceptance

- A byte-exact signed real-socket request reaches the core, performs one
  authoritative attempt read, commits one normalized occurrence, and only then
  returns `200 COMMITTED`.
- Same delivery replay and a changed delivery ID for the same verified attempt
  return durable duplicate semantics without a second logical occurrence.
- Webhook-first, poll-first, restart-after-commit, disconnect-after-commit, and
  commit-failure cases converge without duplicate wakes or false success.
- Invalid signatures, disabled/reconfigured sources, second controller
  ownership, occupied ports, secret failure, provider failure, store failure,
  and absolute deadline exhaustion fail with stable bounded results.
- The provider operation is compatible with the listener callback thread only
  through the main-thread bridge; no signal timer is installed or modified by a
  worker thread.
- No code path evaluates predicates, publishes wake records, reserves attempts,
  or dispatches tmux, app-server, or OpenClaw targets.

## TDD sequence

1. Real socket to signed core to durable journal, with commit-before-ack.
2. Replay/delivery-ID variants and poll/webhook ordering convergence.
3. Main-thread provider deadline bridge and fresh-client-per-call proof.
4. Provider, secret, checkpoint, store, disconnect, and timeout failures.
5. Restart, second ownership, shutdown, and thread/process cleanup.

Each invariant starts with a focused failing test at the cheapest public seam.
Use deterministic fakes for provider traffic and real temporary SQLite journals
and loopback sockets. Do not invoke GitHub or any installed runtime.

## Write surface

- New integration/runtime module under `src/codex_wake/`.
- Minimal bounded change to `github_client.py` only if required to nest safely
  beneath the runtime-owned deadline; polling behavior must remain unchanged.
- One focused integration test module plus minimal existing-client regression
  tests.
- This plan's evidence.

Do not edit CLI parsing, service installation, packaging entry points, operator
docs, persisted source configuration, or readiness/support surfaces; #106 owns
those files.

## Validation

- Focused real-socket/durable-ingest tests on Python 3.11 and 3.12.
- Existing webhook core, HTTP transport, GitHub client, polling, and journal
  tests unchanged and green.
- Comprehensive Python, plugin, compilation, diff hygiene, planning audit, and
  required CI.
- No provider, installed service, non-loopback, ingress, release, or dispatch
  effect.

## Stop conditions

Stop and replan if the bridge requires an unbounded queue, background provider
thread/process without deterministic termination, nested signal ownership,
acknowledgement before commit, a change to durable occurrence identity, CLI or
service overlap with #106, or any real provider/runtime effect.

## Definition of done

PR and CI accept the signed durable-ingest join on canonical main; issue #105
closes from exact evidence; branch/worktree/active-lane custody is cleaned up;
and the #106 join can construct the accepted runtime without weakening its
deadlines or authority boundary.
