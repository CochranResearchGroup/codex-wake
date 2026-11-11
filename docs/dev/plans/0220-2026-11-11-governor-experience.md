# LOCAL-P220 | Usable governor and native /wake

State: IN_PROGRESS. Owner: primary/ecochran76. Spec:#570. Tickets:#571–574.
Branch:feat/governor-experience. Frozen base/review point:3f8a18fa196037fa9efe00bf2ad36b05c61f2a3c.

## Authority and scope
Operator approved all interview decisions, public/native journey seams, immediate publication/implementation and delegation. Existing parents343–346/350 remain untouched; #570 owns this bounded successor. Three implementation lanes maximum; one ticket per worker; no nested delegation. Primary owns573, backend worker571, native worker572.574 starts after571–573validated. One broad review then one bounded TDD remediation pass. No working native restart, stock changes, paid CI or provider-heavy experiments.

## Frozen shared interface
Backend owns `codex_wake.governor.execute(root, verb, arguments, *, principal=None)`; verbs status,activate,extend,reset,disable,resume,advisory. `principal=None` is NOT operator authority: model/native MCP must use existing verified caller binding; trusted local CLI passes explicit authenticated local operator context via backend-approved helper (contract details synchronized before effects). Arguments include selector (defaultsCODEX_THREAD_ID), endpoint, token_limit,time_limit_seconds, add_tokens,add_seconds,resume, request_id,expected_revision as applicable. Normalized result has schema_version, state(enforced/advisory/disconnected/disabled/limit_reached), scope, usage, limits, deadline, watcher, revision, actions and reason. Retain underlying owner receipts. Status must not create allocation or start watcher. Mutations fail explicitly; no automatic advisory fallback.

Native UI invokes fixed argv `codex-wake governor VERB --json` with current thread context; never shell interpolation/model inference. Native forms submit explicit operator actions. Catalog-only actions reuse existing qualified CLI contracts. Changes may refine field spellings once, with coordinator recorded contract revision; no independent authorities.

## Validation
Primary seam:installed modded Codex and Wake public controls using existing native acceptance tools. Targeted public tests for lifecycle/authority/transport; native rendering/commands tests. Immutable UID1017 installed native journey/rollback/delegation required for574. Reuse existing fixture tooling; no standalone fixture framework or incidental implementation tests. CargoSignal native build with stable cache and job limits. Windows/SSH deferred.

## Done
All scoped tickets integrated and validated with exact source/runtime receipts; one review findings adjudicated and one bounded remediation pass verified. Tracker closure distinct from merge/deploy. Preserve dirty original checkout and unrelated lanes. Memory discovery skipped:full fresh accepted interview and current authoritative sources sufficient. Memory write forbidden absent explicit user request.

## Required native loss-containment extension

Implementation found that graceful watcher exit stops work, but SIGKILL leaves
no external process to act. The accepted failure behavior therefore requires
private native `thread/governorLease/set` (arm/renew, read-only query, release),
with exact thread/lease/controller-generation/enrollment-revision binding.
Native expiry uses Linux BOOTTIME, clamps to the earliest applicable deadline,
and persists scoped lease/goal recovery marks. Native cold resume holds automatic
work from an expired or unqualified lease while preserving operator inspection.

Core causal-root cancellation follows native root-turn provenance through task
startup and delegation. Cancel before admitting late children; do not use a global
admission gate or adopt an unrelated operator turn. Goal identity is captured
internally; goal-less active turns need no synthetic goal. Idle goal-less future
task isolation is explicitly unsupported until a causal scope exists. The guard
owns stopping only; Wake's existing allocation ledger remains the accounting owner.

New strict activation requires native guard acknowledgement and watcher
`governor_protocol=1` plus a fresh first-poll acknowledgement. Legacy watcher-only
records remain readable, without claiming this stronger failure guarantee. Failed
setup must not start a task budget window; existing shared ceilings are retained.
These seams implement the already-approved watcher-loss/isolated-task behavior;
they do not authorize a new provider, global daemon adoption or working deployment.

## Host binding and presentation

Default native controls/private controller follow the existing locally owned
Codex MCP goal-root/policy configuration. Verified model callers carry that host
policy through typed context, never JSON authority fields. Explicit isolated roots
remain exact. Private CLI/PowerShell bridging has local operator admission;
API/MCP session operations cannot obtain that role by naming a verb. Mutations
mint request identity before transmission and retain it for uncertain recovery.
Native UI status uses one private connection bootstrap then shared-controller
HTTP, bounded polling, invalidation on governor tool completions and truthful
unknown states. Human time output distinguishes UTC deadlines from authenticated
counter-relative bounds. Token enforcement is based on qualified sampled usage
and native interruption; universal request-level hard-token guarantees remain out
of scope on hosts without demonstrated admission coverage.

The native lease endpoint also supports explicit operator guarded-start: reserve
request identity and bind the new causal turn to its lease before inference.
This completes stopped goal-less task continuation without creating a hidden goal.
A query with guarded-start metadata is capability-only. Duplicate or uncertain
requests reconcile the reserved/started turn and never submit another turn.
Plain idle goal-less activation still cannot claim an unidentified future task.
