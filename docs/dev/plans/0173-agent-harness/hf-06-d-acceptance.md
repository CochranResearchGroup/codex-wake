# HF-06-D / issue323 source acceptance

State: IMPLEMENTED; coordinator integration/closure pending
Owner: ecochran76; worker /root/hf06_d
Branch: feat/323-a2a-permissions; base0597a2a

## Behavior and authority

One operator-selected common policy root is pinned in existing bus metadata.
`BusStore.bind_permissions(wake_root, operator_capability)` establishes the
binding; `a2a permissions` exposes that operator path. A model cannot choose it
through a message parameter. Once bound, loss/invalidity of the policy refuses
new effects instead of returning to legacy. A different root is a migration
conflict, not an implicit permission increase. Unbound buses retain legacy rules.

`BusStore.bind_permission_tasks(actor_id, task_ids, operator_capability)` grants
references only to existing approved briefs within the enrolled actor workspace.
It pins actor generation and approved revision/digest in existing bus metadata.
The `a2a permission-tasks` operator command exposes this operation. An optional
message task_id must match both actors' verified task bindings; copying a task
identifier into arguments is insufficient. A reply retains the original task,
and a changed task under the same idempotency key conflicts.

The mailbox checks both sender action and recipient receive policy at new
admission. Reading a peer body and claiming work recheck current rights; claim
and reply are separately configurable. Metadata/reconciliation stay available
without granting processing. Existing claim generation fencing, terminal outcomes,
correlation, immutable intent and expiry remain unchanged. Permission evaluation
adds no task, tool, workspace or resource allowance.

The independent notification scheduler checks common policy at claim and again
through its existing notification-context seam immediately before transport.
Revocation after claim records a qualified unsent outcome with no client I/O.
Uncertain transport history retains its original no-replay behavior.

## Red / green

Red command: PYTHONPATH=src <integration-venv-python> -m unittest discover -s tests
-p test_a2a_permissions.py -v. Public CLI denied-receiver case failed because
BusStore.bind_permissions was absent (retained /tmp/hf06d-red.log).

Green at the same public seam: seven common-policy tests pass. They cover real
SQLite/actor capabilities, public messages send with a misleading wake-root,
operator-only root binding, denied receiver, distinct claim/reply rules, metadata
reconciliation after revocation, missing adopted policy and trusted task scope.
Native identity resolution is injected in the public CLI fixture; no live actor
or model input is used.

Eight owning-client Unix transport tests pass, including receiver revocation
across scheduler reconstruction and revocation between actual claim and client
I/O. Existing lost-response uncertainty and exact identity tests remain green.

Broader focused regression: test_a2a*.py ran173 tests in56.187s, all pass (this
includes the first six common-policy tests; seventh operator-bind test passed
separately afterward). Runtime A2A: five tests pass. Saved-recipient and tab-routing
suite outcomes are returned to the coordinator. Ruff undefined-name check and
whitespace checks pass. Logs retained under /tmp/hf06d-*.log for this run.

## Integration hook

Primary-owned MCP SEND schema must expose optional task_id; the coordinator
confirmed it landed1520816. Primary permissions configure should call
bus.bind_permissions(root, the already verified operator capability) after common
policy adoption; additional buses can use explicit operator binding. No shared
CLI entrypoint, MCP server or central evaluator was changed by this worker.

## Limits

Source/fixture acceptance only. No provider message, native turn, production
policy, service, installation or deployment was changed. Parent owns comprehensive
integration and tracker closure. No broad code-review or final TDD-remediation
pass was invoked here. Memory disposition forbidden: user did not request a
memory write and developer requires an explicit request.
