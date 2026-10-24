# HF-06-E / #324 source acceptance

Owner: worker /root/hf06_e; integration/closure remains primary-owned.
Branch: feat/324-wake-route-permissions; base faebbd6.

## Implemented behavior

Public native/Grok operator CLI registration accepts ordered --wake-route values
(background, existing_tab, new_tab, fresh_task). Verified private MCP identity
uses the same admission logic through the primary's private CLI keyword hook.
All listed routes must be allowed at admission. The task owner supplies task
scope only when the verified principal has that scope; owner_id alone is no grant.

Nested wake policy version2 freezes routes, verified permission context and
admission revision in the existing schema8 intent fingerprint. Policy version1
and legacy schema5/6/7 behavior are unchanged. An authentic frozen policy-v1
reader from faebbd6 rejects version2 rather than ignoring its route restrictions.
No outer record-schema bump is required; incompatible workers hold the record.

Native dispatch revalidates each route before observations and immediately
before submission. Route-specific observation never implicitly resumes/loads a
saved conversation. Existing-tab/background native queue use qualified existing
capabilities. New-tab/fresh-task remain unsupported unless an adapter explicitly
qualifies them. Exact recipient, original intent, deadline and original counter
anchor remain unchanged. Another due conversation is untouched.

Only RuntimeSubmission(not_sent, pre_io=True) permits advancing the frozen
route cursor. Durable uncertainty precedes attempted submission. Unknown results
and unproven not_sent outcomes remain reconciliation-only. Reconciliation keeps
the original route, submission identity and prompt; it can run read-only after
revocation. Definite pre-I/O failures remain in bounded route history. Corrupt
route progress or changed frozen route metadata holds rather than dispatches.

Current qualified Grok effects remain limited to its exact existing terminal;
policy checks fence input, unsupported broader routes do not become execution
capabilities, and uncertain terminal input is never replayed.

## Evidence

- RED: PYTHONPATH=src <integration-venv-python> -m unittest discover -s tests
  -p test_wake_route_permissions.py -v failed on missing public route/capability
  registration options before implementation. Retained /tmp/hf06-e-red.log.
- GREEN: same command, 11 tests pass, including actual public native MCP
  admission/spoof refusal, real CLI capability admission, independent OS-process
  revocation with zero I/O, two-conversation isolation, pre-I/O fallback,
  uncertainty/no fallback, unproven non-submission, task-owner retirement,
  unsupported new-tab hold, immutable/default-frozen intent and actual Grok
  operator CLI plus uncertain terminal fixture.
- Existing wake policy8, native intent recovery18, native delivery15, Grok
  runtime10 and runtime-policy8 tests pass.
- Final isolated XDG selected runs: new routes11, wake policy8, native intent18,
  runtime-policy8 pass. No provider, external time source or real tab input.
- Pinned undefined-name checker, policy wiring and whitespace checks pass.

Public MCP proof used temporary primary-owned cli.py/harness_mcp.py/mcp_server.py
hooks from76bb2c9. Those three files were restored before this worker commit;
the integration already owns the hooks and must re-run the new public suite on
the combined tip. No primary-owned evaluator/central CLI/MCP changes are included.

## Limits

This is source/fixture acceptance, not installed runtime qualification. No new
lifecycle implementation or native Grok caller attestation is claimed. #318/#319
remain separate scoped-refresh/recovery work. No push, tracker closure, broad
review or final TDD remediation pass was performed by this worker.

Memory disposition: forbidden; developer requires explicit user memory-write
request, and this task authorizes implementation only.
