# Bounded webhook HTTP transport contract

State: OPEN
Lane: P53-C1
Issue: #104
Branch: `feat/issue-104-webhook-http-transport`
Target: `main`
Integration: `squash`

## Current state

Canonical main at `dad2d80a4ce74e030ef604cc430449e76b636286`
contains the accepted `GitHubWebhookIngress` core and controlling P53 plan, but
no socket listener. The core accepts exact bytes or a bounded binary stream and
returns a sanitized `WebhookResult`; it must remain unaware of sockets, proxy
headers, bind policy, or HTTP parsing.

Implementation checkpoint: the isolated issue branch now contains the
provider-free transport and 18 focused public-interface socket tests. Independent
review findings have received one bounded correction pass; closed-world review
verification, published CI, and integration remain with the primary coordination
owner. This plan remains OPEN.

## Objective

Add one deep, provider-free HTTP transport module whose small interface accepts
a frozen listener configuration and an injected ingest callable. Prove over
real loopback sockets that exactly one bounded HTTP/1.1 POST can reach the
callable and that malformed, ambiguous, slow, concurrent, or shutdown-adjacent
traffic cannot escape the frozen admission contract.

## Public interface and seam

- Add one immutable listener configuration with explicit bind address, port,
  exact path, request/header/body/deadline/concurrency/shutdown limits, and a
  named non-loopback opt-in that defaults false.
- Add one listener module accepting that configuration plus an injected callable
  shaped like the existing ingress core: exact body bytes and a duplicate-free
  bounded header mapping in, `WebhookResult` out.
- Expose only the minimum lifecycle needed by the later executable/service:
  bound address readback, blocking serve, and bounded shutdown. Parsing,
  sockets, worker admission, response rendering, and cleanup remain hidden.
- Do not construct GitHub clients, journals, source configuration, wake
  evaluators, dispatchers, services, or CLI objects in this slice.

## Observable contract

- Accept HTTP/1.1 only, one request per connection, exact origin-form
  `POST /github/webhook`, no query, fragment, percent-encoded alias, trailing
  slash, absolute-form target, or redirect.
- Accept `application/json` and an optional exact UTF-8 charset parameter.
- Require exactly one decimal bounded `Content-Length`. Reject transfer
  encoding, TE/CL combinations, missing/duplicate/conflicting length,
  unsupported `Expect`, content encoding, folded headers, malformed names/
  values, excessive line/header counts/bytes, truncated bodies, and bodies over
  the configured limit before invoking the ingest callable.
- Treat `Host`, client address, and forwarding headers as data only. They never
  select a source, change admission, authenticate, build a redirect, or alter
  response content. Duplicate headers are rejected before conversion to a map.
- Bound accepted connections and active workers separately from the injected
  core. Reject excess work without an application queue.
- Apply absolute transport request/callback-response and shutdown deadlines.
  Provider/store execution budgets belong to #105 when those dependencies are
  introduced; a network response deadline is not proof that a callback stopped.
  Stop admission before draining
  the bounded active request set; leave no listener or worker thread after
  successful shutdown.
- Reject suffix/pipeline bytes already buffered or immediately observable at
  admission before invoking the callback. Never wait to predict future writes.
  Close every connection after one response; later bytes never become another
  request. Return explicit content length, `Connection: close`, and
  `Cache-Control: no-store` with one bounded stable code and no exception text.
- Pass only exact legitimate `WebhookResult` status/code pairs through; invalid
  pairs, including redirects, sanitize to `503 UNAVAILABLE`. Transport adds only stable
  codes for route, method, version, framing, size, media type, timeout,
  admission, and internal/unavailable failures.

## TDD tracer sequence

Use one public-interface real-socket test followed by the minimum implementation
for each behavior; never batch all REDs before implementation.

1. Valid exact request reaches the injected callable with byte-identical body
   and returns its committed result.
2. Exact route/method/version/media rules reject before invocation.
3. Content-length, transfer-encoding, duplicate-header, truncation, and
   pipelining cases remain single-request and bounded.
4. Request-line/header/body count, byte, read, and absolute-time budgets fail
   with stable sanitized results.
5. Connection/worker saturation rejects without queuing or invoking excess
   work.
6. Shutdown stops admission, drains within budget, and leaves no socket/thread.
7. Non-loopback bind fails unless explicitly opted in; proxy headers remain
   irrelevant to identity and behavior.

Each cycle records its exact failing and passing command. Tests exercise the
public listener interface and real sockets; internal parser helpers are not the
primary acceptance surface.

## Scope and write surface

- One new transport module under `src/codex_wake/`.
- One focused real-socket test module under `tests/`.
- Minimal package exports only if needed by the public interface.
- This branch-local plan and acceptance receipt updates.

## Non-goals and effect boundary

No GitHub/provider read, webhook signature verification change, journal write,
source configuration, CLI, service unit, installed executable, real listener
outside an ephemeral loopback test port, Cooper inventory, Traefik/bastion
route, secret material, wake evaluation, dispatch, release, deployment, or
global installation.

## Acceptance

- Focused real-socket tests prove the observable contract and no-callback paths.
- The existing GitHub webhook core tests remain unchanged and green.
- Comprehensive Python tests, plugin tests, compilation, diff hygiene, planning
  audits, and Python 3.11/3.12 CI pass.
- Independent review finds no unbounded read, ambiguous framing, proxy trust,
  response leak, worker/socket leak, or shutdown defect.
- Provider/network effects are limited to ephemeral loopback sockets owned by
  the focused tests.
- Clean shutdown permits immediate fixed-port rebind; simultaneous ownership
  of that same address/port remains rejected.

## Stop conditions

Stop and replan if the standard-library seam cannot preserve duplicate-header
evidence, request framing or absolute deadlines remain ambiguous, shutdown
cannot bound worker lifetime, non-loopback binding becomes implicit, the core
interface must change materially, or any test requires provider/runtime state.

## Definition of done

PR and CI accept the bounded transport on canonical main; issue #104 closes
from exact evidence; its branch/worktree are removed; #105 and #106 become
ready without inheriting an unresolved transport or authority decision.

## Implementation evidence | 2026-09-16

Owner: delegated implementation lane `/root/p53_c1_transport_impl`; primary
coordination owner retains reconciliation, publication, review, and integration.
Implementation base: `72e0965b2545f670cb3fc553c97a0bdd1b3cf7d2`.
Graphiti discovery: skipped because the frozen plan and supplied interface were
sufficient. Structural discovery used `codegraph explore 'WebhookResult
GitHubWebhookIngress'` against the canonical checkout's existing index; the
isolated worktree had no index. The existing core was not edited.

Public interface: `WebhookHTTPConfig` and `WebhookHTTPServer(config, ingest)` in
`codex_wake.webhook_http`; actual `(host, port)` readback through `address`,
blocking `serve()`, and bounded `shutdown()`. IP literals only; IPv6 is v6-only.
The named `allow_non_loopback` defaults false. Literal JSON media values are
`application/json` and `application/json; charset=utf-8`. Header names passed to
the callback are lowercase ASCII and unique. Response codes use the fixed
existing ingress vocabulary plus the bounded transport categories.

Connections bound parsing/request threads separately from simultaneous ingest
calls. A timed-out callback retains its slot until it exits. Absolute request
expiry closes the network response even while a callback remains active.
Deadline observation uses a 10 ms accept tick; fixed-size response writes have
a 10 ms cap. Shutdown stops admission and closes sockets, then joins every
tracked worker and serving owner until one absolute deadline. Successful return
proves worker cleanup. A callback that outlives the deadline causes the fixed
`TimeoutError("webhook shutdown deadline exceeded")`; callers may retry shutdown
after that callback exits. Arbitrary Python callables cannot be forcibly killed.

### RED/GREEN ledger

Every row used the exact same focused command for both RED and GREEN:

```sh
PYTHONPATH=src python -m unittest discover -s tests -p test_webhook_http.py
```

| Cycle | RED evidence | GREEN evidence |
| --- | --- | --- |
| Byte-identical request/result tracer | Missing module import, 1 error | 1 test passed |
| Exact route/method/version/media | Wrongly admitted variants, 11 failures | 2 tests passed |
| Framing and single-request pipeline | 13 failures, 3 errors | 4 tests passed |
| Size and absolute read budgets | Missing limit configuration, 7 errors | 6 tests passed |
| Separate connection/ingest admission | Missing limits, 2 errors | 7 tests passed |
| Truthful shutdown deadline/retry | Missing shutdown budget, 1 error | 8 tests passed |
| Bind/limit validation and proxy irrelevance | 13 failures, 2 errors | 10 tests passed |
| Fixed sanitized callback responses | 1 failure, 3 errors | 11 tests passed |
| Deadline while callback remains occupied | Client timed out, 1 error | 12 tests passed |
| HTTP/1.1 Host and TE/trailer framing | 4 failures | 13 tests passed |

Two final verification tests exercised partial-request shutdown and byte
trickling against the now-existing behavior: 15 tests passed in 1.311 seconds.
No test retries or quarantines were used to erase failures; the RED failures
above preceded their corresponding implementation changes.

### Local validation

- Python 3.12.13 comprehensive command:
  `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`:
  453 passed in 15.874 seconds.
- Python 3.11 focused command:
  `PYTHONPATH=src python3.11 -m unittest discover -s tests -p test_webhook_http.py`:
  15 passed in 1.319 seconds.
- Unchanged ingress core:
  `PYTHONPATH=src python -m unittest discover -s tests -p test_github_webhooks.py`:
  12 passed in 1.081 seconds.
- `npm --prefix plugins/openclaw-codex-wake test`: 12 passed.
- `python -m compileall -q src tests .codex/hooks`: passed.
- `git diff --check`: passed.
- `python .codex/skills/repo-policy-selector/scripts/audit_planning_contract.py
  --repo-root . --active-only --json`: passed with the existing explicit legacy
  baseline, no new planning finding.

### Handoff constraints

No provider calls, installed runtime effects, non-loopback test bind, CLI/service
changes, GitHub mutation, push, or merge occurred in this implementation lane.
Published Python 3.11/3.12 CI and closed-world review verification are not yet
evidenced. The initial independent review and correction are recorded below.
The next integration slice must account for the existing
`GitHubRestClient._absolute_deadline` main-thread restriction: directly calling
that client from the transport's callback threads fails closed. Supply a bounded
compatible adapter or execution seam in #105; do not weaken provider deadlines.

## Independent review correction | 2026-09-16

Reviewer: `/root/p53_c1_security_review`, reviewing `68068cd`. Requested model:
`gpt-5.6-sol` with high reasoning; effective model and effort were unreported.
The primary owner accepted the following findings for one bounded correction
pass. This is remediation evidence, not a new independent acceptance verdict.

| Accepted finding | Correction and evidence |
| --- | --- |
| Observable suffix admission | Replaced the initial permissive pipeline test. Prequeued small and large bodies with a one-byte suffix or second request now fail before the callback. The large case exercises immediate socket peeking beyond the read buffer. A separate callback-signaled late-write test proves later traffic never creates a second invocation. No grace wait or future-byte absence claim is made. |
| Nonsensical status/code pairs | Exact allowlist covers every real ingress pair and transport pair. `302 COMMITTED`, `599 COMMITTED`, and `200 SIGNATURE_INVALID` become `503 UNAVAILABLE`; every legitimate core pair retains its result. |
| Fixed-port restart failure | `SO_REUSEADDR` is set before bind, without `SO_REUSEPORT`. A real request followed by server-first close, clean shutdown, and immediate same-address rebind succeeds. Concurrent ownership remains rejected. |
| Provider/store budget ownership | #104 and this plan now explicitly qualify transport/callback-response budgets only. #105 must prove absolute provider/store execution bounds; parent P53 retains that acceptance criterion. Plan 0070 is reconciled accordingly. |

All remediation RED/GREEN runs used the exact command:

```sh
PYTHONPATH=src python -m unittest discover -s tests -p test_webhook_http.py
```

- Suffix correction: RED 16 methods / 4 failures; GREEN 16 passed (1.322 s).
- Exact result pairs: RED 17 methods / 3 failures; GREEN 17 passed (1.766 s).
- Immediate restart: RED 18 methods / 1 bind error; GREEN 18 passed (1.606 s).

The earlier RED/GREEN ledger remains historical evidence; its permissive
pipeline behavior is superseded by the accepted finding and correction above.

### Post-correction validation

- `PYTHONPATH=src python -m unittest discover -s tests -p test_webhook_http.py`:
  18 passed in 1.606 seconds (Python 3.12).
- `PYTHONPATH=src python3.11 -m unittest discover -s tests -p test_webhook_http.py`:
  18 passed in 17.402 seconds while the comprehensive lane ran concurrently.
- `PYTHONPATH=src python -m unittest discover -s tests -p test_github_webhooks.py`:
  12 passed in 2.287 seconds; the core remains unchanged.
- `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`:
  456 passed in 38.950 seconds.
- `npm --prefix plugins/openclaw-codex-wake test`: 12 passed.
- `python -m compileall -q src tests .codex/hooks` and `git diff --check`: passed.
- `python .codex/skills/repo-policy-selector/scripts/audit_planning_contract.py
  --repo-root . --active-only --json`: `ok: true`, `problems: []`, no unused
  baseline findings.

No provider calls, runtime installation, non-loopback socket bind, push, PR,
or other external mutation occurred during remediation. The unpublished local
implementation commit is amended for the primary owner's closed-world review.
