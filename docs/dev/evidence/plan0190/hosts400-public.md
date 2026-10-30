# Ticket400 — integrated installed public acceptance

Worker: `feat/controller-400-acceptance`, frozen integrated source `07c396827e0824ff974aadd39d3ac7d2a02bde43`. This followup changes tests, the acceptance script and retained evidence only. Product modules are unchanged. The primary owns issue400 closure, integration ledger and production boundaries. Core worker API and initial TDD evidence are retained at `0d895443f00eba70adc5793f055d2e2073388211`; supplemental source-bound tests are copied from `92f05ff4779552a328b92e6c96c3606533ec091a` without importing its stale source base.

## Verified outcome

The installed combined package successfully runs actual `bin/codex-wake hosts` registration/list/resolve/route and the fixed SSH receiver. The read operation crosses a bounded subprocess transport with OpenSSH-shaped flags into a separate disposable destination root. The fixture is explicitly synthetic: it is not an SSH server, a real Windows/WSL environment, or a provider runtime. Distinct Windows/WSL host/environment/authority metadata is exercised without claiming real platform compatibility.

Actual installed `bin/codex-wake-mcp` stdio transport is exercised with the MCP2.2.0 client SDK: initialize, tools/list, wake_hosts_list and wake_hosts_resolve. Its current public catalog exposes these two host read tools and intentionally no route tool, because native MCP has no mapped routed-caller authority in this increment. OAuth MCP exposes the capable route interface instead; the script checks this distinction.

The installed OAuth listener is started by actual `bin/codex-wake controller serve`. The fixture registers a public client, locally approves a named service grant through actual CLI, then exchanges the S256 code through HTTP `/token`. One exact host/environment/authority/generation grant filters fleet inventory to the permitted WSL environment and resolves the same pinned target. HTTP `/operations`, OAuth MCP initialize/list/call and installed `controller remote` all successfully route the same inventory read. Their identical idempotency key returns the same durable receipt, and the fixture invocation count proves that these three adapters submit exactly one destination operation.

The receiver's fixed SSH principal permits only synthetic Alice inventory. The successful read returns Alice and never Bob. A caller grant narrowed to Bob intersects the fixed Alice mapping to no authority, producing a typed insufficient_scope result with failed execution. A host/environment grant missing authority/generation cannot route and produces unauthorized_target before any transport invocation. Revoking the OAuth grant causes both API and OAuth MCP requests to return401. The retained fixture also covers source offline refusal without queueing, stale generation and unsupported mutation rejection before transport, destination principal revocation, and response loss after a destination read. Reopening new CLI processes returns the original uncertain receipt without replay.

The supplemental focused test proves the final authorization callback blocks submission after revocation, records not_started/not_submitted, and does not later retry that admission when authorization returns. Missing exact grants, mismatched authority and expired fleet observations cannot reach the transport.

## Commands and package provenance

Focused source selection: `PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p 'test_controller*.py'`: **34 tests passed in10.391s**. This is a focused changed-area selection, not the whole repository suite. Existing shared-app-server fixture code emitted its existing websocket context-manager deprecation warning; the selection still passed.

Installed candidate:

```
python -m venv --system-site-packages /tmp/wake400-public
/tmp/wake400-public/bin/python -m pip install --no-deps .
/tmp/wake400-public/bin/python scripts/controller_hosts_acceptance.py
```

The wheel was `codex_wake-0.22.0.dev2-py3-none-any.whl`, SHA256 `77d2ebe6aa5e053da10f22c6c575205ffe21e84bf657455f7c5feb115ee57bf4`. Optional MCP dependencies were imported read-only through a disposable `.pth` pointing to `/home/ecochran76/workspace.local/codex-wake/.venv/lib/python3.12/site-packages`; no shared environment was installed into or modified. PYTHONPATH is cleared for installed subprocesses. Package provenance in `hosts400-installed-public.json` identifies the installed candidate, MCP dependency version, exact CLI command and hashes for six installed product modules. Every recorded source hash was independently compared against the frozen integrated worker source and matched.

First public-harness attempt used the MCP SDK wire alias `isError` as a Python model property; MCP2.2.0 requires `is_error`. The harness was corrected. A second attempt exposed an option-leading random generation value; the harness now passes opaque CLI values with `--generation=VALUE` and `--client-id=VALUE`, and positional grant IDs after `--`. Subsequent full disposable acceptance passed. These were fixture defects, not product retries or concealed product failures. Every attempt used its own disposable roots and synthetic credentials; no prior uncertain provider operation was replayed.

No live SSH/Windows/WSL/provider/shared service, production TLS ingress, credential copying, governor or resource renewal was used. Real host/platform matrix qualification remains ticket405. Mutation routing remains explicitly unsupported. Fixture processes are reaped, temporary state is removed, and fresh manual resource readback was taken after acceptance. No background listener or provider experiment remains active from this fixture.

Memory disposition: **forbidden** — this delegated tests/evidence followup does not authorize external memory effects; primary owns integrated closeout.
