# Ticket401 — durable correlated operation results

Spec [393](https://github.com/CochranResearchGroup/codex-wake/issues/393), ticket [401](https://github.com/CochranResearchGroup/codex-wake/issues/401). Product implementation checkpoints: `b4a28b4b7e294ab30b728687061de96a1e8fe45b` (durable mutation intent), `407ba3b6b577b76dd3d3add8be329da9cadbe2f3` (Mailbox/BackgroundJobs responses), `d8046ef74aca4b9dbdc5cf46a0d8e49971fcba52` (native sender verification and reachable explicit queues), `02ad659052a924aa89656262891b83d996f27d6c` (narrow grant revocation). This acceptance lane starts from exact combined `be127d46e4c43eecb6a081091c9f6da107d9ac81` and changes only the owned revocation iterator plus scripts/evidence. Primary owns shared integration, issue disposition and production gates.

**Current acceptance:** the original installed combined script passes the matrix below. A subsequent expanded all-capable-adapter attempt encountered the existing Mailbox clock-anomaly hold. That required matrix remains incomplete pending primary diagnosis; the successful receipt must not be read as closure of the expanded gate. Preserve the expanded failure and its earlier unaffected successful assertions separately.

## Contract

`ControllerRuntime(root, adapter=..., now=...)` owns durable admission/correlation/result custody, not a replacement execution framework. `execute(actor, operation, arguments, authorize=callback, dispatch=owner.execute)` requires reserved `_request={operation_id,idempotency_key,correlation_id,binding,target}`. It persists authenticated issuer/resource/subject/client/grant, target, immutable payload digest and correlation before dispatch. `_request` is stripped before calling existing effect owners; changed inputs conflict with an existing intent, and operation IDs cannot be rebound to different intents. Stage/select/rollback require admin; launch and send require control. Later result/wait/stream explicitly require observe. Token rotation with the same grant retains ownership. Every new privileged step reauthenticates; target owners retain final preflight.

Request `binding` is opaque caller correlation, never native identity. Host-approved `sender_binding` mappings authenticate native credentials in their owning environment. Credentials are never stored in client envelopes or operation journals. `operation_commands.mcp_call` additionally compares the selected host sender's native thread/session with the existing verified private native-MCP context. Model `_request.binding` values cannot impersonate native identity. CLI and OAuth service clients use explicitly permitted service bindings, without claiming to be a particular invoking native TUI.

`operations.send/result/wait/stream/cancel/rebind` use the same owner across adapters. Response-requested send defaults to waiting up to thirty seconds for an actual answer. A wait timeout ends waiting, not work. The default Mailbox backend uses native authenticated `Mailbox.send`, actual `replies` and body `read`; queue admission, notification and accepted/completed acknowledgements alone are never final answers. Result replies must match the original message and correlation. Native `Mailbox.reply` already routes the answer to the original native sending identity. Bounded event streaming uses explicit cursors/limits and separate progress/result messages; it is not provider-token streaming. Native receipts/history remain authoritative.

Inbox queueing requires explicit `queue=true, delivery=inbox` and TTL. It may retain an exact formerly verified conversation whose observation aged stale, but cannot adopt a replaced process generation or re-enable suppressed enrollment. Queuing creates no automatic resume, model input or notification; native Mailbox policy/permissions remain authoritative. The queued target and expiry are preserved. Unknown send admission reconciles the original native outbox message/digest/correlation without resending. Missing reconciliation remains uncertain.

The approved-command backend reuses `BackgroundJobs` profiles, task pins, native permissions and detached supervisor/result files. Caller argv/body/credential overrides are rejected. Command results survive the submitting process, and actual retained stdout supplies the final answer. Cancellation uses only the original job ID/generation/native principal. Generic plugin dispatch retains an unknown outcome if its owner or controller dies; it never relaunches an uncertain effect. It does not claim every arbitrary synchronous plugin is independently supervised.

Cancellation distinguishes confirmed, requested and uncertain owner outcomes. It does not imply rollback. Explicit successor rebind is restricted to the same authenticated subject/client/issuer/resource and independently authorized new grant. It changes controller response custody/correlation only, preserving original native identity/history. Another grant does not adopt old results without that explicit reference. Transactional merging preserves concurrent successor/cancellation custody when the effect owner finishes.

Private `revoke_grant(grant_id, issuer=..., resource=...)` is not a remotely selectable operation. It records revocation, enumerates only original exact grant-owned operations, reconciles existing native handles without resending, and requests existing Mailbox/BackgroundJobs cancellation through original host/native ownership references. It creates no new OAuth actor or work authority and leaves peer grants untouched. Generic effects without a cancellation owner remain explicitly uncertain. Each invocation retains at most one hundred pending operation records in memory; any remaining count is explicit. Primary-owned OAuth revocation outbox/callback wiring persists the revocation before cancellation and covers explicit revocation and refresh replay.

## Public-seam evidence

Exact source command: `PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p 'test_controller*.py'` on combined be127 plus the iterator fix: **51 passed in8.279s**. This is a focused selection, not the repository comprehensive suite. The existing websocket context-manager deprecation warning was emitted by shared-app-server fixture code.

TDD receipts retained in worker tool history:

- `... -m unittest discover -s tests -p test_controller_runtime.py` initially failed with missing controller_runtime; the first green proves the durable record is publicly visible before a real fixture file effect, with crash uncertainty, restart deduplication, changed-input conflict and foreign-owner refusal.
- The concurrent-owner test failed `AuthError(insufficient_scope)` when effect completion overwrote explicit successor custody; transactional merge made it green.
- The real stale-queue test failed stale_target before queue admission; the fix distinguishes stale retained identity from suppression/replacement. It proves an unread suppressed-notification native inbox message with the exact original target and no automatic reenrollment.
- Real native Mailbox tests prove completed acknowledgement is not an answer, late result bodies/correlation/native return identity, cursor deduplication, cancellation uncertainty after consumption, explicit successor binding and same-grant rotation.
- A native after-commit fault is reconciled to one original Mailbox message without replay. Real supervised-command tests retain actual stdout and prove revocation cancels only the owned process while the peer completes.

## Installed passing matrix

The successful combined run used:

```
python -m venv --system-site-packages /tmp/wake401-public
/tmp/wake401-public/bin/python -m pip install --no-deps .
/tmp/wake401-public/bin/python scripts/controller_runtime_acceptance.py --shared-cli
```

Optional MCP2.2.0 dependencies were imported read-only through a disposable `.pth` referring to the existing root virtual environment site-packages; the shared environment was not modified. PYTHONPATH is cleared for installed subprocesses. Wheel SHA256: `7f2a27f0db0aef0c4b0c4bf9c12e60982206a7794b094e2dfa62a47b0d805c9a`. The successful run is tool session55903, completed exit0 (output chunk8a62ae). `runtime401-installed-public.json` preserves its successful stdout metadata; all eight installed module hashes were independently compared with the exact worker source and matched. Passing script SHA256: `38f977c2011dec2c8c851de32247bbbdcd6a1bb281df275641b4ed2dd3fae183`.

| Installed surface | Proven by the original successful run |
| --- | --- |
| Shared bin/codex-wake operations | Send, zero-time wait, stream progress/cursor, caller wait process termination, late answer retrieval, plain final stdout versus JSON status stderr, native-send dedup; real supervised command after submitter exits |
| Actual stdio bin/codex-wake-mcp | Initialize/catalog, missing native context refusal, verified mapped native send, wait timeout, actual native reply result |
| OAuth direct API | Real registration/PKCE exchange, native send/wait/result, same-grant refresh retrieval; active original/peer queues and jobs, original-only revocation cancellation |
| OAuth MCP | Initialize and actual correlated result retrieval |
| Installed controller remote CLI | Actual correlated result retrieval |

The expanded harness adds explicit OAuth-MCP and remote-CLI send/wait calls and default response-requested command send. Its clock hold must be diagnosed before declaring the all-capable send/wait matrix accepted; it is not optional or erased by the earlier run. See `runtime401-expanded-failure.md`.

Every response in this fixture comes from actual native Mailbox reply bodies or actual supervised-process stdout, not a fake dispatch/result adapter. The recipient fixture reads the submitted question and constructs its answer from that body. Native private-MCP metadata is a synthetic fixture for the existing host transport contract, not proof of a real TUI loop or live provider. No live model/provider, credential copying, shared service, resource reset/renewal or governor was used. Real platform/provider qualification remains a distinct gate.

Memory disposition: **forbidden** — delegated source/acceptance work does not authorize external memory effects; primary owns integration closeout.
