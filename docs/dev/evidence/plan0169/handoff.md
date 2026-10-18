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

Delivery gate: full suite not green. delegation-validation.json preserves1372tests
with64failures/1error/1skip. Prior64identifiers remain, plus one intermittent
mailbox disposition subtest (exact isolated candidate/main both pass). Full run
began before final renewal recovery guard; final focused test and exact review
cover that delta. Do not erase failures or claim release readiness.

Resource bound: original goal01a14f45-25a2-7ef1-bcce-1205f176cc73 created1792332310,
deadline1792353910 (2026-10-18T20:05:10Z),2Mfresh tokens. Current read-only qualified
usage745150fresh; native goal remains historical blocked with stale counters.
Use source observe_usage for actual cumulative spend; never count cache toward
the fresh ceiling or reset counters/time. Stop/checkpoint before original limits.

Next bounded packet: triage release-gate failures against unchanged baseline,
starting with the repeated pending_thread_work fixture family. Separate evidence
from implementation scope and preserve unrelated work. Max2hypothesis attempts,
focused reproduction first; do not repeat passed native acceptance or silently
waive CI. Plan0168 refresh remains separate/expired and supplies no runtime retry.
