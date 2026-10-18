# Issue289 restart-safe handoff

Authority: user-approved goal and explicit host-delegated self-enrollment decision;
ADR0002, Plan0169v4, RUNBOOK Turn353. The old operator-origin approval question
is resolved. Do not ask for it again or restore per-session UUID provisioning.

Custody: /home/ecochran76/workspace.local/codex-wake-allocation-control, branch
fix/289-allocation-campaign-control. Read current git HEAD/status; this checkpoint
extends a9881c6. Main checkout89e3eb8 and spec checkoutdbd37ca were preserved.
No remote push, PR, merge, release, production install/grant, shared MCP reload,
service restart, counter reset or allowance renewal occurred.

Implemented: v2 host allocation delegation; native MCP Context.meta caller binding;
shared cumulative response ledger/dedup; original deadline; inherited stop/grace;
explicit host renewal with finalized old charges and exact response anchors.
Legacy v1 remains. Fresh input+output excludes cache by default. Goal pause stops
owned campaign turns while later operator messages remain usable.

Evidence: native-public-final.json binds five final source/installed module hashes,
/tmp/cw289-v4-installed candidate, actual two-conversation public enrollment20->40
fresh with unchanged deadline, unrelated control unchanged, six localhost Responses
requests, no external calls. Final exact process groups70439/70590have no members.
33focused tests pass; policy wiring/compile/diff checks pass. Review findings were
reproduced/repaired; see review.md. No further broad discovery pass.

Validation checkpoint: final frozen02c7893full run PASS1372tests/183.474s,1skip,
exit0with isolated XDG_CONFIG_HOME/XDG_STATE_HOME and StableTime opt-out. The
prior64baseline identifiers were host registry/mailbox fixture contamination;
20selected tests prove isolation fixes the family without product edits. Earlier
failed logs and one intermittent disposition mismatch remain retained. Plugin12
PASS, compile/policy/diff/build PASS. README and CI now isolate unit process
state. See delegation-validation.json. This is local, not remote matrix CI.

Resource bound — renewed explicitly by operator after this checkpoint:
allocation issue289-renewal-de360e1d0be04564bb7c947f996807d3.
New allowance2Madditional fresh tokens/6hours, start2026-10-18T15:39:29.531693Z,
deadline2026-10-18T21:39:29.531693Z. Original history is preserved; fresh baseline
801245plus qualified reset_anchor in the private operator-allocations JSON under
/home/ecochran76/.local/state/codex-wake/goal-limits/. Use observe_usage with
that anchor, excluding cached input. Native goal01a14f45-25a2-7ef1-bcce-1205f176cc73
is active by user action; no native counter reset/replacement goal occurred.
Installed external enforcement remains held/armed:false. This is renewed operator
authority, not claimed armed enforcement. Preserve200k-token/900second checkpoint
reserve. Resource renewal does not reset review or discovery bounds.

Next bounded packet: integrate this qualified branch through the repository's
GitHub/CI workflow, then perform separately authorized exact-main release/install
qualification. No per-session grants or operator-origin approval question remains.
Preserve prior failed receipts and unrelated sessions/services. No repeated broad
review or native qualification needed unless the code changes or new evidence
warrants it. Plan0168 refresh remains separate/expired and supplies no runtime
retry. See canonical Plan0169v4d/RUNBOOK Turn354 for latest status.

Memory disposition: forbidden; no reviewed destination routing for a Graphiti
write, machine non-write receipt in /tmp/cw289-self-enrollment-memory-disposition-20261018.json.
