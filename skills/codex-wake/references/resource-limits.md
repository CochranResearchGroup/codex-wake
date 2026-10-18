# Dedicated executor resource limits

For token/time limits in the existing dev tab, start with
[existing-session goal supervision](existing-goal-limits.md). Use this separate
workflow for dedicated containment such as "keep builds under the approved
memory/CPU limits". Codex Wake strict execution
is opt-in containment of a dedicated objective executor on qualified Linux/WSL
systemd/cgroup hosts. It is not a reminder, a timer wake, or an exact token ceiling.

## Choose the supported path before starting work

| Situation | Action |
| --- | --- |
| No granted strict profile or missing required controls | Report the specific missing setup; obtain operator provisioning before contained work |
| Ordinary existing TUI, no owned strict source | Operator must bootstrap a dedicated executor; current MCP spawn cannot perform this first launch |
| Verified owned strict source, native goal, caller grant and separately qualified control route | Inspect configuration, then use only that approved lifecycle route and same-objective ledger |
| Need to limit the current TUI or all unrelated agents/services in place | Unsupported coverage; state it explicitly rather than claiming strict enforcement |
| Executor stopped/exhausted, accounting unknown, or controller unavailable | Hold new work; operator reconciles exact identity/final usage and explicitly authorizes any renewal |

**Current first-launch gap:** MCP spawn uses the real caller UUID as the objective
reference. Its admission path reads that source's native goal before creating a
strict executor. A caller outside the new private executor has no such source
there. The proven initial-launch path is operator CLI with an approved bootstrap
reference; it is not an agent fallback for missing MCP authority. An agent-facing
bootstrap path still needs implementation and first-launch acceptance before a
release can promise self-service enforcement from any ordinary TUI.

Strict private homes currently reject unqualified `mcp_servers` and hooks. Do not
add MCP there as a workaround, assume outer-session tools are inherited, or use
operator CLI to bypass caller checks. A host-provisioned control route must be
qualified separately. The MCP inspection template below is for clients that
already have the granted tool; it does not install that tool in an executor.

## Agent steps for an already provisioned strict source

1. Obtain your actual `CODEX_THREAD_ID` in a native shell. Use only the profile
   granted to that caller; never use a parent's ID or choose another objective.
2. Read `wake_sessions_configuration`:

   ```json
   {
     "caller_thread_id": "ACTUAL_CALLER_UUID",
     "thread_id": "ACTUAL_CALLER_UUID",
     "profile": "OPERATOR_GRANTED_STRICT_PROFILE"
   }
   ```

3. Verify these returned facts before heavy work:
   - `strict_execution` exists, with every required control and the declared
     coverage/exclusions. A legacy expiry-only profile is insufficient.
   - `objective_token_limit` and `objective_time_limit_seconds` match the user's
     authorization; session shares do not exceed it. Check `started_at`,
     `objective_deadline`, ledger `original_deadline`, historical usage,
     reservations and remaining allowance. Do not restart the clock at handoff.
   - `objective_execution` identifies the expected running owned invocation,
     cgroup and guard/controller evidence. `null` means not enrolled; a configured
     `execution_layout` or a visible tab alone does not prove enforcement.
   - Accounting is known and admission is available. Inspect explicit holds and
     exact receipt identity; initial missing usage does not permit more admission.
4. Choose spawn, refresh or handoff using the packaged `lifecycle.md` templates.
   Keep one stable intent and a fixed expiry within the remaining deadline.
   Preserve the host-selected writer/reviewer instructions and checkpoint hash.
   Reconcile the same intent after a timeout or uncertain effect.
5. Perform the limited work inside the proven dedicated executor. Setup, builds,
   tests and descendants there share its boundary. Your outer planner, unrelated
   sessions, shared services and external provider execution are excluded. Keep
   any outer planning/review allocation separate; do not advertise whole-session
   enforcement when only the worker is contained.
6. Report actual completion and usage. Native cumulative `total_tokens` includes
   cached input, preflight, review, retries, failed work and automatic goal turns;
   native goal display counters can differ. Do not promise an exact provider-turn
   count or exact token ceiling. Checkpoint/shutdown time consumes original caps.

If the user supplied only token/time limits, use an already approved complete
host policy or report the missing memory, swap, CPU, task and grace controls.
Do not invent those settings, larger caps, a new start time or a zero prior spend.
Unknown usage stays unknown. A new context, service restart or edited defaults
does not renew authority.

## Operator provisioning and recovery

The operator owns a private registry, exact caller grants, objective identity,
approval, original start, attributable prior spend and complete explicit limits.
Choose these before effects; example research caps are not defaults. Provision:

- A trusted workspace and private per-objective Codex home/Unix endpoint; operator
  credentials stay private. The runtime must not adopt a shared server.
- A host profile with `strict_execution`: `memory_max_bytes`,
  `memory_swap_max_bytes`, `cpu_quota_percent`, `tasks_max`, `poll_seconds`,
  `accounting_max_age_seconds`, `checkpoint_grace_seconds`, `stop_grace_seconds`.
- Lifecycle session/objective token and time limits, full selected checkpoint
  writer/reviewer instructions, correction bound and an approved continuation.
- A persistent resident monitor on that exact wake root, verified after its
  launching shell returns. Configuring an MCP client does not start this monitor.

The supported first launch uses the operator's approved bootstrap reference:

```sh
codex-wake --wake-root OWNED_ROOT sessions configuration --profiles PRIVATE_REGISTRY --profile STRICT_PROFILE --thread-id BOOTSTRAP_REF --json
codex-wake --wake-root OWNED_ROOT sessions spawn --profiles PRIVATE_REGISTRY --profile STRICT_PROFILE --objective-ref BOOTSTRAP_REF --intent STABLE_INTENT --name WORKER_NAME --task APPROVED_TASK --expires-at FIXED_ISO8601 --json
```

These are operator templates, not permission for an agent to omit caller identity.
A strict native source needs an exact host continuation/goal binding before later
MCP operations. Do not fabricate a native goal or directly mutate ledger aliases.

Operator-only inspection/stop/final accounting:

```sh
codex-wake --wake-root OWNED_ROOT sessions execution --profiles PRIVATE_REGISTRY --profile STRICT_PROFILE --thread-id OBJECTIVE_REF --json
codex-wake --wake-root OWNED_ROOT sessions execution --profiles PRIVATE_REGISTRY --profile STRICT_PROFILE --thread-id OBJECTIVE_REF --stop --json
codex-wake --wake-root OWNED_ROOT sessions execution --profiles PRIVATE_REGISTRY --profile STRICT_PROFILE --thread-id OBJECTIVE_REF --reconcile --json
```

Goal pause or RPC success is not process-stop proof. Final reconciliation requires
exact local termination and native terminal usage evidence; a sampled floor is
not final billing. Renewal must retain historical consumption and authorization,
with newly approved bounds recorded separately. Agent MCP cannot reset this.

## Say precisely what is enforced

A suitable readback is: "Work is in owned executor INVOCATION under objective ID,
with the approved caps and original deadline D. Token enforcement is sampled,
including cached input; maximum overshoot is unknown. Outer-session work and
shared/external services are excluded."

If not enrolled, say: "Resource enforcement is not active: MISSING_SETUP.
I have not started work under a claimed strict guarantee." Never describe a
cooperative native goal, reminder, expiry or scheduled wake as equivalent coverage.
