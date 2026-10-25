# #346 renewal worker evidence

Worker branch: feat/346-goal-renewal. Base: e181d28.
Runtime handle: /root/ticket346, native thread 01a1714c-f544-7b21-af3b-6d20d7eba5bd.
User authorized manual resource monitoring; no production service/policy or native
shared daemon was changed. Work is new modules, dedicated docs and focused tests.

## Public seams and observed red/green

The seams are `propose/apply` and the CLI/native adapter `execute/command`, backed
by actual private files, original accounting records, the existing common queue,
an owned native-protocol websocket endpoint and an independent owned watcher.
They establish source behavior; they do not prove stock frontend rendering.

Commands use `PYTHONPATH=src:tests` and the workspace development Python at
`../codex-wake/.venv/bin/python` (Python3.12 with installed websockets17.2).
Initial system Python lacked websockets; no behavioral verdict was taken from it.

1. Red: `python -m unittest test_goal_renewal.GoalRenewalTests.test_operator_extension_retains_consumed_usage_and_does_not_resume -v`
   failed because goal_renewal did not exist. Green: same command passed after the
   first vertical extension implementation, retaining40spent of90total/50remaining.
2. Red: `python -m unittest test_goal_renewal.GoalRenewalTests.test_reset_opens_new_window_and_retains_lifetime_and_stop_history -v`
   failed with reset unsupported. Green: same command passed with zero current
   window/40lifetime, new generation, retained stop and later post-anchor charging.
3. Focused final `python -m unittest test_goal_renewal -v`:9tests PASS before
   final docs. Includes authenticated CLI exact deadline; native-identity common
   attention response; model self-approval refusal; stale/expired proposal and
   hard host ceiling refusal; dead watcher/unknown history/mandatory deny; shared
   all-member reset requiring explicit scope; interrupted filesystem publication
   reconciled with the same proposal; resume held pending the new revision poll.
4. `uv tool run --from ruff==0.14.2 ruff check --select F821,F822,F823` on the
   three changed Python files: PASS. `git diff --check`: PASS.

No broad review was run; the coordinator owns the goal's single review/remediation
pass. No installed CLI/MCP or real native resume claim is made by these fixtures.

## Required coordinator wiring

- `goal_renewal_commands.register_parser(commands)` accepts the existing
  goal-limits subparser. Dispatch extend/reset/apply-renewal to `command(args,root)`.
- Register `tool_specs()` under family goal-renewal and route its
  `mcp_call(runner,verb,arguments,native_context)` through the existing native host.
- Before enrollment mutation, show admission or poll accounting/effects, call
  `goal_renewal.renewal_hold(root,receipt)`. Pending receipt or shared allocation
  fences hold without introducing an unrelated accounting stop.
- Renewal increments enrollment_revision and drops poll_ack. Resume requires
  the exact fresh first-poll acknowledgement, all-member accounting and current
  native paused state. Keep generation on extend; reset changes it.
- Report lifetime usage as lifetime_tokens_before_window plus current used_tokens
  as later polls advance; the stored application snapshot is not a live total.

## Remaining gates

Top-level CLI/MCP registration, actual first-poll resume integration, installed
native/frontend journey and unrelated-session isolation remain coordinator gates.
Finalized departed shared members are explicitly unsupported, not silently edited.
Unknown filesystem/native outcomes hold for exact reconciliation without another
budget. Ticket346 must not be closed until its complete intended target is proved.
Memory disposition: forbidden; no memory write was requested for this work.
