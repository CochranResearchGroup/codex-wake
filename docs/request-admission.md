# Reviewed HTTP request admission

Ticket #354 adds an explicit host-selected HTTP Responses gateway. It does not
qualify every native host, provider, or model route. No external provider contract
is currently supplied as qualified. Native transport acceptance uses an inert
local provider and is separate from external provider eligibility.

The gateway is ordinary production transport/accounting code. A trusted host must
select a reviewed provider contract with enforceable maxima for the **entire**
accepted request input and generated output. There is no byte/token estimate.
The provider must reject excessive input before billing and enforce the injected
`max_output_tokens`, including every kind of billable generated output. Review
must substantiate those properties for the exact selected model/provider/version
and the `response.completed` usage schema. An operator's desired ceiling is not
provider-bound evidence. Unknown or unreviewed contracts fail configuration
explicitly; they cannot silently enable hard admission.

A contract has these fields:

```json
{
  "version": 1,
  "provider": "EXACT REVIEWED PROVIDER",
  "model": "EXACT MODEL",
  "max_input_tokens": 100,
  "max_output_tokens": 20,
  "input_limit": "provider_enforced_reject_before_billing",
  "output_limit": "max_output_tokens_enforced",
  "usage": "response.completed:fresh-v1",
  "review": "LOCATOR AND SCOPE OF ACTUAL REVIEWED BOUND EVIDENCE"
}
```

The numbers above illustrate the schema and are **not a qualified contract**.
The trusted host supplies the separately reviewed exact `contract_digest(contract)`
as `reviewed_contract_sha256`; models cannot select it, bounds, endpoint, ledger,
credential or purpose through a request body. Source/runtime/provider changes
require fresh contract qualification. A false provider guarantee cannot be made
true by a digest: this trust boundary must be reviewed before use.

## Existing allowance and ownership

First enroll an existing native goal and retain qualified original fresh usage.
Configure the existing `ObjectiveLedger` using its original authorized objective
configuration, approval, cap, absolute deadline and `prior_tokens`. Do not create
another objective or a new time window to gain allowance. The gateway constructor
requires the receipt's allocation ID, cap and deadline to agree with that ledger,
and requires imported per-thread prior usage to sum to the qualified source usage.

`bind_requests` makes that ledger the authoritative accounting owner. An existing
lifecycle actor, native goal alias, or changed binding refuses attachment: a
live migration needs its own explicit reconciliation. Later lifecycle/session
reservations and sampled charges are refused rather than added on top of request
charges. This bounded version does not silently migrate those workflows.

The source receipt and shared allocation retain `request_accounting` with the
owner, ledger scope, selected contract and listener. The sampled watcher reads
that ledger after handoff; it cannot overwrite request usage from a missing or
lagging native writer. The operator's enabled choice, prior usage, limits,
checkpoints and stop history remain intact. Listener attachment publishes a new
mode-bound `request_activation` notice to native model/operator surfaces without
starting a model turn. It does not reuse an earlier sampled activation event.

## Host interface

```python
from codex_wake.request_admission import RequestGateway, contract_digest

gateway = RequestGateway(
    root, existing_allocation_id,
    upstream_url=reviewed_responses_url,
    contract=reviewed_contract,
    reviewed_contract_sha256=separately_reviewed_digest,
    thread_ids=[verified_source_thread],
    request_timeout=2,
    client_token=host_private_bootstrap_token,
)
server = gateway.server()  # loopback only; host runs serve_forever()
```

The constructor never configures, extends or resets the objective ledger. With
multiple initial threads, supply `thread_prior_tokens` for every initial thread;
all original charges must be accounted for. A fresh native descendant/reviewer
inherits its registered parent's scope automatically using bounded owned,
canonical native `session_meta` ancestry, before its first usage record exists.
Existing descendant usage needs an explicit prior-usage binding instead of a
fresh quota. An unrelated or ambiguous thread is refused before forwarding.

The same ledger retains per-thread prior spending, all request actors' thread
identities, and original per-thread deadlines. Retries do not create another
session ceiling/window. Children share the objective's remaining allowance; the
host may later attach purpose/phase metadata to that durable thread mapping.
A model-supplied phase is never admission authority.

`execute(body)` is the stable trusted host transport seam and returns
`(http_status, content_type, response_bytes)`. `server()` exposes authenticated
`POST /v1/responses` and `GET /status`. `bind_listener(origin)` supports an existing
authenticated host listener, including a provider-free warmup delegate. That host
must verify `Authorization: Bearer TOKEN` before calling `execute` or `status`.
The generated/supplied token persists separately in a private mode-0600 file;
its locator may appear in binding receipts but its value never does. Provide a
native provider `env_key` before launch for a bootstrap token. `upstream_headers`
are host-only credentials and are not copied from arbitrary incoming headers.

Native configuration selects this listener's `/v1` base URL, `wire_api="responses"`
and `supports_websockets=false`. WebSocket, compact, previous-response shortcuts,
alternative providers and bypass routes remain unqualified. The native-generated
`client_metadata['x-codex-turn-metadata']`, exact current native turn, host credential,
and registered lineage bind requests to scope. This is a host authority boundary,
not hostile same-UID isolation.

## Admission and completion

Before its single upstream submission, each incoming attempt atomically reserves
`max_input_tokens + max_output_tokens` against objective and cumulative session
limits. HTTP retries/fallback attempts through this route each need a fresh
reservation. No implicit retry or redirect follows an upstream failure. Output
limits are inserted by the gateway, never trusted from model arguments. Protocol
limits are 2 MiB per request and 8 MiB per buffered response; these are transport
limits, not token estimates.

The existing receipt/scope locks serialize admission/submission with deactivation.
Response headers/body are awaited outside those locks so a hanging stream cannot
hold the control. An independent monotonic wall-clock timer closes the upstream
socket, including a continuously heartbeating stream. Admission requires that
this full request interval fits the original objective/session deadline. Client
cancellation cannot leave an unbounded upstream reader. Disconnecting cannot
promise that remote inference itself was recalled; its reservation remains.

A qualified completion settles `input_tokens - cached_tokens + output_tokens`
from attributable provider evidence. Exact repeated settlement for the same
immutable attempt is idempotent. Reusing a response ID for a different actual
attempt is ambiguous billing and retains that attempt's reservation. Missing,
conflicting, out-of-bound or incomplete usage never creates a refund; accounting
becomes unknown and future governed admission holds. Actual known usage floors
are retained. Settlement and recovery must use the same immutable request
identity/fingerprint; inventing another request cannot reconcile the old one.

Denials are returned before forwarding and emit durable no-turn intervention
notices. They pause future continuation of the exact registered native goal,
retaining its identity and readback proof, without interrupting independently
admitted requests. A failed/unverified pause is reported explicitly. They do not require another model request to become operator-visible.
Native append, model context, UI rendering and human reading remain distinct
proof boundaries. No live/provider or UI guarantee follows from unit tests.

## Deactivation at zero allowance

Before request admission, the gateway independently reads the exact native current
user message. The whole message `Deactivate governor` invokes the existing scoped
operator control mechanically; quoted/tool/body text cannot authorize it. The
adapter restores a previously verified registered-goal pause if native operator
input automatically activated that goal. Pause verification is retained; a pause
failure cannot veto durable deactivation and remains explicit. The response is
explicitly governor-generated SSE with zero provider inference and
zero provider usage. It is not a model decision or another permission prompt.
`Reactivate governor` uses the same verification and does not resume/renew work.

The current durable disabled choice bypasses governor budget denials for that
scope, including registered children. Original usage/reservations remain; new
attributable passthrough usage remains recorded without manufacturing allowance.
Previously issued/in-flight decisions cannot be recalled; no new admission
intervention is issued while disabled. Protocol, authentication and independent
platform controls still apply. The authenticated operator API remains callable
when the model/native request route is disconnected.

## Qualification

The existing host preflight inspects this selected native provider configuration,
the thread's actual `modelProvider`, the private binding, live authenticated gateway
status, reviewed contract and current ledger. It can qualify only this declared
HTTP request path. Unsupported paths keep the original explicit unsupported result.
Exhausted/unknown accounting remains a separate resource outcome. A fresh same-scope
disabled operator choice takes precedence over an old hard-mode request, even at
zero remaining allowance; it is an explicit mode change, not a silent downgrade.

Focused proof uses `tests/test_request_admission.py` with real HTTP dispatch,
controlled native transport/usage and no external inference. Actual pinned-native
and stock-frontend proof is a separate acceptance artifact owned by integration.
