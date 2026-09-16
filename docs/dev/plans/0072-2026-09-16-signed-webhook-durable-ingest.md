# Signed webhook durable-ingest join

State: CLOSED
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

## Local implementation evidence | 2026-09-16

Implementation branch base was refreshed by a non-rewriting merge of
`origin/main` at `b94ba448fdf2db7b4862ae17a511aa995c586393`. The new internal
join is `codex_wake.github_webhook_runtime.GitHubWebhookRuntime`. Its public
lifecycle is the actual `address` readback, blocking main-thread `serve()`,
and bounded `shutdown()`; the latter uses the existing immutable
`WebhookHTTPConfig.shutdown_timeout` budget.

`WebhookHTTPServer` serves sockets on `github-webhook-http`. Its injected
callback can admit only one bridge delivery and otherwise returns `503 BUSY`;
it has no application queue. The main-thread controller performs secret
resolution, a fresh attempt-client factory call, verified attempt read,
checkpoint lookup, and journal ingestion under one POSIX absolute deadline.
The persisted ingress object remains singular for its bounded rate and
delivery caches. `GitHubRestClient` defaults remain polling-owned; its optional
deadline lease is accepted only while the owning main-thread timer context is
active, so it cannot install a nested timer or be reused after the owner exits.

The first real-socket tracer was RED with the new runtime module absent and
GREEN after the minimal controller was added. Follow-on focused integration
tests cover commit-before-`200`, same and changed delivery replay, poll-first
and reopened-journal convergence, timeout recovery, disconnect after admission,
secret/provider/store failures, no-queue bridge saturation, and occupied-port
ownership. One additional real-socket regression constructs a fresh concrete
`GitHubRestClient` per delivery over fixture HTTPS responses; its positive-only
terminal proof is exposed to the ingress freshness guard without changing the
normalizer's stored proof provenance. Tests use temporary SQLite journals,
loopback only, and provider-free fakes; no wake evaluation, dispatch, provider
request, installed runtime, non-loopback bind, GitHub mutation, push, or merge
occurred.

Validation on local Python 3.12.13:

- `PYTHONPATH=src python -m unittest discover -s tests -p test_github_webhook_runtime.py`: 10 passed.
- `PYTHONPATH=src python -m unittest discover -s tests -p test_github_client.py`: 12 passed.
- Existing webhook core, HTTP transport, and polling focused suites: 12, 18,
  and 21 passed respectively.
- `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`:
  467 passed in 15.209 seconds.
- `npm --prefix plugins/openclaw-codex-wake test`: 12 passed.
- `python -m compileall -q src tests .codex/hooks`, `git diff --check`, and
  the active planning-contract audit: passed (the audit reports only its
  accepted legacy baseline findings).

## Integration receipt | 2026-09-16

PR #115 passed the required Python 3.11 and 3.12 release gates and squash-
merged at canonical `1d32bb1d12531ab41fb36c0180fc0510be8e1c88`. Issue
#105 closed, and its remote topic branch, local branch, and isolated worktree
were removed. Runtime construction remains owned by #106; no provider, service,
external ingress, release, deployment, or dispatch effect occurred.
