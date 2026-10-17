# Strict objective execution (development branch)

Implementation of spec #274 is validated on feat/objective-enforcement.
Agent first-launch onboarding has a separate release-readiness gap below.
This document does not announce an installed release or fleet rollout.

For existing dev-session token/time supervision, use the separate
[agent guide](../../skills/codex-wake/references/existing-goal-limits.md). That
workflow does not require dedicated executor bootstrap and has native stop
semantics. The first-launch gap below applies to dedicated strict containment.

## Agent discovery and first-use readiness

Agents should load the shipped [resource-limit workflow](../../skills/codex-wake/references/resource-limits.md)
when the user supplies token/time or host limits. The skill description and MCP
configuration/spawn descriptions expose that trigger. Readback must distinguish
configured limits from a running, proven `objective_execution`.

**Release blocker for self-service MCP onboarding:** first launch from an ordinary
caller is not demonstrated or supported by the current path. MCP uses the caller
UUID as its objective reference; admission reads its native goal before the new
private executor is created. Proven native acceptance used operator CLI bootstrap
references. See `docs/dev/evidence/plan0167/bootstrap-order.json` for an injected,
zero-model-call reproduction of the ordering. Existing lifecycle acceptance does
not establish agent first-launch usability.

The strict private-home configuration also refuses unqualified `mcp_servers` and
hooks. Do not add Wake MCP there as an undocumented workaround or assume the
outer TUI's MCP tools are inherited by a strict worker. A supported agent bootstrap
and any in-executor control route need explicit host authority and acceptance.
Do not loosen caller identity, grants, owned endpoint checks or accounting to make
an onboarding example pass. This guide documents the operator path until then.

### Release verification checklist

- Resolve the first-launch gap with a caller-authorized public workflow. From a
  normal agent given only a resource-limited task and its approved profile, prove
  first launch, actual containment/readback, counted work, stop and unrelated
  process preservation. Missing controls must give an actionable refusal.
- Publish the **whole** `skills/codex-wake/` directory, including the new
  `references/resource-limits.md`, to each supported agent skill root using the
  existing deployment procedure. Compare installed file hashes. The wheel's
  package-data currently does not include this skill directory; wheel installation
  alone is insufficient. Do not update production skills during this audit.
- Reload/restart MCP clients and refresh the host's skill catalog. Verify the
  installed skill description contains resource-limit terms, every relative
  reference resolves, and `tools/list` exposes the new configuration/spawn guidance.
- Run a cold agent walkthrough for "2M tokens or four hours": inspect configured
  caps/remaining history, reject absent setup, enter the proven dedicated boundary
  before heavy work, and state sampled-token and outer-session exclusions.
- Retain explicit limits and setup authority. Time/token-only requests do not
  authorize inventing memory, swap, CPU, task, polling or grace settings. Updating
  prompts or skills cannot enforce an arbitrary already-running TUI in place.

## Controls and operator path

A launch profile opts in using `strict_execution`. Ordinary lifecycle profiles
retain their existing cooperative behavior. Strict launch requires an approved
objective, its cumulative ledger reservation and a live resident supervisor
before native task effects. Shared Codex servers are not adopted or terminated.

The operator must choose every control; there are no resource defaults:

| Control | Meaning |
| --- | --- |
| memory_max_bytes | Positive integer cgroup memory limit |
| memory_swap_max_bytes | Nonnegative integer swap limit; zero disables swap |
| cpu_quota_percent | Positive finite aggregate cgroup CPU quota |
| tasks_max | Positive integer task/process limit |
| stop_grace_seconds | Positive TERM-to-KILL service-manager allowance |
| checkpoint_grace_seconds | Positive bounded native shutdown/persistence allowance |
| poll_seconds | Positive independent guard interval, at most5seconds |
| accounting_max_age_seconds | Positive observation lease, at least twice poll_seconds |

Both graces together must be less than the session time allowance. Session
allowances cannot exceed objective allowances. Existing configuration readback
includes the effective controls, configuration revision, original deadline,
coverage/exclusions and current execution identity:

```sh
codex-wake --wake-root ROOT sessions configuration --profiles PROFILES --profile PROFILE --thread-id OBJECTIVE_REF --json
codex-wake --wake-root ROOT sessions execution --profiles PROFILES --profile PROFILE --thread-id OBJECTIVE_REF --json
codex-wake --wake-root ROOT sessions execution --profiles PROFILES --profile PROFILE --thread-id OBJECTIVE_REF --stop --json
codex-wake --wake-root ROOT sessions execution --profiles PROFILES --profile PROFILE --thread-id OBJECTIVE_REF --reconcile --json
```

Existing MCP configuration and spawn operations use the same policy; execution
stop above is an operator CLI. Released root-scoped emergency interruption also
stops enrolled strict executors. Preserve ordinary capability/grant requirements.

The host needs Linux cgroupv2, a functioning user systemd manager, a supported
Codex executable and CLOCK_BOOTTIME. Initial deadline admission requires trusted
UTC; ongoing elapsed-time and observation leases use same-boot BOOTTIME, counting
suspend. This follows the [Python CLOCK_BOOTTIME contract](https://docs.python.org/3.12/library/time.html#time.CLOCK_BOOTTIME); the continuity tests inject elapsed-time jumps and do not claim an actual host suspend trial. A changed boot identity fences the guard. Restart does not grant a new
deadline. Host failure, scheduler delay and suspended execution prevent a
universal real-time termination guarantee; enforcement resumes when the host can
schedule it. Dedicated RuntimeMaxSec provides an independent service-manager
backstop; the guard subtracts both grace allowances before deadline shutdown.

The operator provisions a private owned objective directory under
ROOT/strict-execution/SHA256(OBJECTIVE_ID)[:24], its private home subdirectory and
private config.toml. Profile codex_home must name that home and app_server must
be unix://ABSOLUTE_OBJECTIVE_DIRECTORY/app-server.sock. The runtime binds its
private generation/configuration and exact systemd InvocationID/cgroup there.
An existing unowned endpoint, unowned conversation history, external MCP/hooks,
missing controls or shared endpoint is refused. Credential provisioning remains
operator-owned; runtime does not copy credentials. Do not expose config contents
or auth material in evidence.

Coverage is the dedicated local executor and its descendants, including local
tool/setup/build/test processes. Kernel readback reports memory.max,
memory.swap.max,cpu.max,pids.max and cgroup members. Shared services, external
provider execution and same-user IPC escape are explicitly excluded. Membership
is observed evidence, not an assurance against hostile same-user escape.

Token enforcement is sampled stop. Native cumulative total_tokens includes
cached input; immutable actor/goal attribution avoids charging preflight twice.
No numeric maximum overshoot is established. Native publication delay plus guard
polling, scheduling and shutdown affect actual overshoot. A heartbeat observation
is not fresh token evidence: unchanged native counters cannot renew a usage
lease. Initial null counters get only the bounded admission observation lease;
new admission remains held while accounting is unknown. Missing/decreasing or
malformed accounting, lost controller identity and expired leases fence work.
Brief ledger contention consumes the existing lease and cannot renew it.
Guard readback reports ledger-verification BOOTTIME separately from each actor's
first/latest native observation, native total, publication timestamp fingerprint
and lease age. The reported native wall timestamp is not an elapsed-time
source. Publication delay is explicitly unmeasured across independent clocks;
poll interval is configured detection cadence, not a universal latency bound.
The native observer-death acceptance measured22ms detection and1.351s to empty;
these are bounded observations, not guaranteed limits. Accounting scans refuse
more than512rollouts or32MiB aggregate per poll; bounded nonblocking regular-file
reads also reject concurrent growth beyond that capacity. This internal parsing
capacity is independent of the operator's host resource limits.

Guard shutdown fences new effects first, requests native termination for at most
checkpoint_grace_seconds, then exits so systemd terminates all cgroup descendants
with stop_grace_seconds before KILL. This retains existing persisted artifacts;
it does not generate a new model-authored semantic checkpoint. Failed persistence
cannot postpone forced termination. A final provider charge may remain unknown
when killed before publication; last sampled usage is not final-cost proof.

After exact local termination, `--reconcile` checks owned native rollout counters
and terminal markers without a model call. A completed proof settles cumulative
usage. Missing terminal evidence keeps accounting unknown and retains any later
sampled floor; termination alone cannot prove final cost or permit renewal.

A fresh paused native goal can reuse its unique owned settled actor only when
its initial counters are zero and its allowance exactly equals that actor's
remaining tokens. Progressed or ambiguous goals are refused rather than deriving
an offset from native display counters. Explicit renewal preserves settled
historical actors and original deadlines in the ledger; it does not reapply an
expired historical actor's session allowance to new work.

Stopped/exhausted generations remain fenced. A new configuration revision alone
cannot replenish the ledger: explicit operator renewal must retain historical
consumption/authorization and settle the previous execution. Ambiguous launch or
stop effects remain uncertain and require exact identity reconciliation. Operator
stop can recover a missing launch identity only when the private generation, live
guard process identity, current systemd InvocationID and cgroup membership agree.
An already empty original invocation settles without issuing another stop; a
replacement invocation is preserved. Never retry a unit name blindly.

Current evidence and unproven acceptance gates are in Plan0166 and
`docs/dev/evidence/plan0166/ledger.json`. Injected telemetry OS tests are labelled
separately from actual native evidence. No deadline, token or concurrency ticket
is validated by a helper unit test alone.
