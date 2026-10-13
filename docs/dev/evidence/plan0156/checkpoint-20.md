# Plan0156 checkpoint20 — installed protocol mismatch retained and corrected

State transition: prepared host-observation fixture → failed native attempt → provider-free protocol qualification.
Acceptance state: full Plan0156 OPEN / IN_PROGRESS; selected native preflight and
continuation remain unaccepted. Progress classification: blocker_reduction;
failed native packet remains a failure. Parent window1791887366–1791908966 and
full acceptance unchanged. No further provider attempt in this packet.

Installed11 eight-module parity and exact remote a211a62 verified before new
live-handoff03. Source native checkpoint completes at48069. Successor is created
and original assignment admitted, but host observer calls invalid
thread/mcp/tool/call and tears down before any preflight receipt or activation.
This should have been qualified before the provider call; retained as actual
validation failure, not reclassified as readiness. Curated installed-handoff-03.json.

Current generated native ClientRequest schema includes mcpServer/tool/call, not
thread/mcp/tool/call. RED public host-observation regression: PYTHONWARNINGS=ignore
 .venv/bin/python -m unittest
 tests.test_handoff_acceptance_supervision.HostNativeObservationTests.test_host_readback_binds_resource_to_source_and_successor -q.
Expected mcpServer/tool/call, actual thread/mcp/tool/call. Corrected all three
runner sites including prepared/final public MCP acceptance calls. GREEN same
suite tests.test_handoff_acceptance_supervision: PASS5/0.001s.
Runner also qualifies actual host catalog/resource route on settled paused source
before admitting a successor; this prevents buying the second task on a bad route.

Provider-free actual installed readback: native_request mcpServer/tool/call for
wake_sessions_show on the exact existing paused source after explicit local load.
No queue/turn/goal mutation or new conversation; no model assignment. Tool returns
isError=false/exact source. complete=false because original fixture tmux already
closed; that is not full readiness or handoff acceptance. Goal unchanged before/
after, server exits0. Successor goalnull and retained native turns[]; do not infer
usage zero from this. Fresh readable private-home census empty, denied entries
explicit in receipt. No expired handoff intent replay, goal activation or renewal.

## Accounting and next unit

Source48069 adds known resumed external subtotal263464 (known lifetime590359).
Successor01a134e5-14a6-73b3-94c7-b9c14faea04b has no cumulative usage report.
External ledger explicitly labels unknown rather than inventing zero. Reserve
250000 against remaining planning allowance; this is conservative bookkeeping,
not measured spending or a verified hard upper bound. Native root counters remain
separate. Do provider-free ready source work before another combined installed
packet; no third repeat within the changed-fixture one-attempt bound.

Next: same-tab public CLI/native/PT Y behavior using explicit owned tab generation
and exact fresh-thread identity, followed by active-successor/missing-source
rollback. Full native selected preflight/goal continuation remains open, plus
nonnull refresh-goal installed proof, consolidated review/remediation, required
local CI, combined CLI/MCP/skills acceptance, integration/release/rollback/cleanup,
clean main and issues248–251 closure. No scope narrowed or gate waived.
Memory disposition: unavailable; no reviewed Graphiti target from discovery.
