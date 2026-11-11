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
