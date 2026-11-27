# Issue 790 | Live spoke controller capabilities

Call `POST /network/v1/management/catalog` over the hub's OAuth API, or
`wake_network_management_catalog` on its MCP endpoint. Supply an exact
`peer_id` and `conversation_id`. Each operation includes its canonical
controller name, the JSON Schema for its caller-supplied arguments, required
scopes, and a contract ID. Call `POST /network/v1/management/execute` or
`wake_network_management_execute` with the same address, plus `operation`,
`contract` and an `arguments` object. Refresh the catalog after a
`contract_changed` error. The three pilot tools and routes remain available.

A grant must name the exact peer and conversation and carry the controller
operation's scopes. A delegated action list must admit the requested
network action and, for execution, the selected controller action. The
spoke's own OAuth grant is rechecked and narrowed to the selected operation,
owner pin, and intersection with the hub caller's scopes. Controller-specific
checks still apply. For example, `history.read` needs both `history.observe`
and `content.observe`. A control-only `operations.send` receives a
metadata receipt under the existing external-controller rule.

## Spoke configuration

Add an optional `capabilities` object to the private JSON file used by
`python -m codex_wake.wake_network_management --config PATH`. Its top-level
keys are the conversation IDs already published by that peer. Each value is
a map from canonical controller operation names to a binding with
`target` (the permitted local controller target) and `fixed` (the
owner-supplied controller arguments). Use the exact saved account, thread,
window, or other controller resource for each binding. The public contract
retains every unpinned controller argument and its validation rules. Fixed
arguments are kept on the spoke and cannot be supplied by callers. Required
controller identity arguments such as an expected target, native thread,
window, or pane must be pinned before an operation is advertised.

For example, a saved-history binding can pin `owner` and `thread_id` for
`environment.conversations.history.read`, with `target` set to the exact
account target returned by the local controller. Both the target and fixed
arguments contribute to the binding revision. A changed pin requires a fresh
catalog contract.

An active authenticated outbound poll advertises the selected bindings. The
hub resolves the entries against its own registered controller contracts and
returns only the operations allowed by the caller's grant. An unavailable
poll returns `offline`. A start acknowledged by the hub is one-use, and an
unconfirmed operation is `uncertain`. The hub does not queue or replay live
operations. A durable network message uses its separate custody route.

## Qualification

The focused journey uses OAuth and PKCE, public HTTP and Streamable HTTP MCP
routes via ASGI, disposable PostgreSQL, a separate real tmux socket, and the
actual spoke controller and worker protocol. It checks transport parity,
wrong scope and conversation, attempted window substitution, contract drift,
foreign peer start/completion, a visible rename, saved history, offline,
uncertainty and rejection of a late completion. The repository's fixed clock
fixture controls expiry. Production hosts and certificates are outside this
qualification.

```sh
# Set CODEX_WAKE_TEST_NETWORK_DSN to a disposable PostgreSQL connection.
PYTHONPATH=src:tests python -m unittest test_wake_network_management \
  test_wake_network test_external_oauth_connector
```
