# Native delegated cached-inclusive accounting with injected local Responses

PASS_NATIVE_DELEGATE_INJECTED_ACCOUNTING on first packet; no second attempt.
Installed `/tmp/cw167-installed/bin/python` candidate6b4b233; native0.163 absolute
`/home/ecochran76/.local/bin/codex`. Script uses a private empty home, no auth,
localhost-only provider and real native legacy thread/goalblocked before turn.
No native auto-goal continuation is activated.

Advertised native tools include `multi_agent_v1`. First injected response makes
an actual `multi_agent_v1.spawn_agent` functioncall with `fork_context=true`.
Parent continuation and child response share originalrootturn
01a14c4b-042b-7a91-8f05-c1732fe5f7ad. Native metadata records exact child ID,
parent_thread_id and source.subagent.thread_spawn.parent_thread_id; shared
session_id equals rootthread. Child history_modelegacy, history_base null.

Actual native response records: root local-delegate-1 usage20/cache10;
root local-delegate-2 usage40/cache20; child local-delegate-3 usage30/cache15.
Installed observe_usage qualified90, exact identity set of all3responses,
including45cachedinput tokens; no goal display substitute, no host-authored
rollout records. Root cumulative60, child cumulative30. Three local Responses
POSTs, elapsed1.497seconds; zero externalprovider/model calls. Values are injected,
not billing. Native response/function SSE format follows version-matched
OpenAI rust-v0.163.0 core/tests/common/responses.rs; spawn namespace follows
core/tests/suite/step_settings/agent_spawn_tests.rs.

This actual child snapshot has NO copied parent token_usage_record and its first
counter is30, not inherited20+30. Therefore this packet qualifies actual descendant
coverage/attribution and exact-once response accounting for this snapshot, but
DOES NOT establish the live inherited-counter dedup path. Earlier sanitized
public fixtures cover copied parent response dedup; version source supports fork
baseline inheritance generally. No paginated/history_base support is claimed.

## Interrupt scope | source evidence, not a live cancellation assertion

Version-matched core/src/tasks/mod.rs312 creates a new cancellation token for
each session task. abort_turn_if_active580 and handle_task_abort930 cancel the
selected session task token, interrupt its code-mode cells, and clear its pending
input; the inspected path does not enumerate descendantthreads. Agent-specific
interrupt dispatch is separate in core/src/agent/control.rs327, sending Op::Interrupt
to selected agent_id. Thus root turn interruption alone is NOT qualified proof
that descendantwork stopped; do not expand childcontrolauthority silently.
This packet allowed child and parent to complete; no live childcancellation claim.
Sources fetched read-only from openai/codex rust-v0.163.0, local snapshots under
/tmp/cw-native-schema-0163/{tasks,agent-control,session}.rs.

Raw owned result `/tmp/cw167-native-delegate1/result.json`; freshcleanup receipt
cleanup-readback.json: exact native exited0, process identity absent, ownedhome
processes[], alias absent. Localserver closed. No unrelatedsessions/services
changed. Curated native-delegate-receipt.json contains native IDs/counters and
request hashes, no raw provider payload/credentials. Script compilecheck passes.
Memory disposition forbidden: bounded script/evidence lane, no externalmemorywrite.
