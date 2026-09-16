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
- Apply absolute request and shutdown deadlines. Stop admission before draining
  the bounded active request set; leave no listener or worker thread after
  successful shutdown.
- Close every connection after one response. Extra/pipelined bytes never become
  another request. Return explicit content length, `Connection: close`, and
  `Cache-Control: no-store` with one bounded stable code and no exception text.
- Pass injected `WebhookResult` status/code through. Transport adds only stable
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

## Stop conditions

Stop and replan if the standard-library seam cannot preserve duplicate-header
evidence, request framing or absolute deadlines remain ambiguous, shutdown
cannot bound worker lifetime, non-loopback binding becomes implicit, the core
interface must change materially, or any test requires provider/runtime state.

## Definition of done

PR and CI accept the bounded transport on canonical main; issue #104 closes
from exact evidence; its branch/worktree are removed; #105 and #106 become
ready without inheriting an unresolved transport or authority decision.
