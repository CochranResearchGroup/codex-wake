# Connector permissions acceptance — #671

Source baseline: `882aae8007e71cc2641c66a742e340e6cf007310`.
Live installed connector: `0.22.0.dev28-1fb9180` (wheel SHA256
`1fb9180dd253f01e4073cd24f87b9119ef35e5cdf8958bb1acbc2fac841ed336`).
Public resource: `https://codex-wake.ecochran.dyndns.org/mcp`.

The opt-in acceptance script exercises the real deployed HTTPS OAuth token and
MCP endpoints. Local operator authorization creates three independent, bounded
permission grants for a disposable empty native conversation. Codes, verifier,
access and refresh tokens stay inside the test process. Existing operator grants
and deployment policy are read before/after and remain unchanged.

| Criterion | Live observation |
|---|---|
| Explicitly scoped read succeeds | Protected environment snapshot completed under an observe-only conversation-scoped grant |
| Read-only prompt denied | `insufficient_scope` |
| Out-of-scope prompt denied | A separate control grant for another conversation returned `insufficient_scope` |
| Stale generation fails closed | Changed socket generation returned `daemon_unavailable`; no input admitted |
| Denied input has no native queue effect | Queue empty and conversation idle before/after; initial thread start contained no turns |
| Own credentials cleaned up | Three grants revoked; public MCP rejected each old access token with HTTP401 |
| Own conversation cleaned up | Disposable conversation archived |

The stale-generation diagnostic is less specific than desired: a mismatching
pinned target falls through full registry discovery, where an unrelated daemon's
ownership cannot be verified. This establishes fail-closed refusal but **does not
prove a generation-specific `stale_target` error**. No product change is hidden
inside this acceptance ticket.

A first run stopped before credential issuance because an empty native
`thread/read(includeTurns=true)` returned JSON-RPC -32601, `list_turns is not
supported yet`. The same error reproduced while retaining the creator websocket;
retaining that connection is therefore not a remedy. This script instead uses
the applicable native empty-thread metadata and queue observations. It sends no
setup/model prompt and never addresses the operator's conversation. The initial
empty target and bounded raw-error probe were separately archived; a repeated
archive refusal for an already unavailable preliminary target was retained in
private diagnostic output rather than retried destructively.

## Reproduction

Use the exact installed connector Python, with its already configured private
policy and a private receipt destination:

```sh
"$CONNECTOR_PREFIX/bin/python" scripts/connector_permissions_acceptance.py \
  --config "$CONNECTOR_PRIVATE_CONFIG" --receipt "$PRIVATE_ACCEPTANCE_RECEIPT"
```

Actual run used the version above, the operator-owned external connector config,
and a receipt under the operator's private Codex Wake state. Output reported
`status: passed`; credential-free summary and full private receipt remain outside
Git. The script is opt-in; it does not join the hermetic unit suite.

Focused checks: `python3 -m compileall -q scripts/connector_permissions_acceptance.py`
and `git diff --check` passed. Hosted CI was not run under repository cost policy.
No connector restart, native daemon restart, plugin change or account alteration
occurred. Memory disposition: `forbidden` — no explicit memory write requested.
