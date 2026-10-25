# #346 active operator-reply renewal seam

Worker /root/ticket346, successor branch fix/346-active-operator-renewal.
Base e6ae58f. This is acceptance-driven implementation before the reserved broad
review. No production runtime, native source or installed prefix changed.

## Defect and public red/green

An actual native MCP invocation is itself an active native turn. The previous
renewal snapshot required an empty active-turn set, so a model handling the later
operator reply could not even propose renewal of a paused exhausted campaign.
The older injected acceptance fixture had active=[] and missed this condition.

Command (PYTHONPATH=src:tests, workspace .venv Python3.12):

```sh
python -m unittest test_goal_renewal.GoalRenewalTests.test_native_mcp_operator_reply_can_propose_and_apply_after_campaign_stops -v
```

RED: public CommandRunner.call(wake_goal_limits_extend) returned held with
renewal_native_not_paused, despite original stop proof and stop_turns=['work'],
paused native goal, actual native active=['operator-request'], and exact trusted
native caller metadata for operator-request. GREEN: same command passes after
threading native_context from the host adapter into proposal/application.

The focused module suite then passed11tests, including negative captured campaign,
mismatched/missing metadata, model argument turn claims, replacement native goal,
CLI without attestation and busy shared peer cases. The later operator reply is
still active and its native goal still paused after approved application; counters
remain40spent rather than resetting implicitly. Ruff undefined-name gates and
`git diff --check` passed.

## Exact exception and authority boundary

The sole active turn must equal the exact private-host attested caller turn and
session. Retained current or historical evidence must prove the original resource
campaign was stopped and paused. The active turn cannot equal any historical
captured campaign turn. The current native goal creation identity must match the
original budget's goal. Other sessions, arbitrary CLI claims, busy peers, unknown
accounting, changed boots/policy and old campaign turns stay held.

This exception excludes the caller's operator reply from campaign-work liveness;
it does not approve more resources. Model proposal cannot self-approve. Application
still consumes the exact current authenticated common attention response and
requalifies all resources/accounting/members. Native proposal/application caller
bindings are retained as private transaction provenance, outside model arguments.

Native worker345 separately found missing top-level sessionId/callId metadata in
the older development app-server and is restoring those from authentic host state.
These public-seam tests use an explicit native-protocol fixture and trusted metadata;
ordinary real-native model invocation remains a qualification gate until the new
pinned runtime emits that metadata and the combined installed journey passes.
Memory disposition: forbidden; no memory write requested.
