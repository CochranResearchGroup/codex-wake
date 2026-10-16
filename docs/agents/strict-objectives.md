# Strict objective execution (development branch)

Implementation of spec#274 is under acceptance on feat/objective-enforcement.
This document does not announce an installed release or fleet rollout.

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
```

Existing MCP configuration and spawn operations use the same policy; execution
stop above is an operator CLI. Released root-scoped emergency interruption also
stops enrolled strict executors. Preserve ordinary capability/grant requirements.

The host needs Linux cgroupv2, a functioning user systemd manager, a supported
Codex executable and CLOCK_BOOTTIME. Initial deadline admission requires trusted
UTC; ongoing elapsed-time and observation leases use same-boot BOOTTIME, counting
suspend. A changed boot identity fences the guard. Restart does not grant a new
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

Guard shutdown fences new effects first, requests native termination for at most
checkpoint_grace_seconds, then exits so systemd terminates all cgroup descendants
with stop_grace_seconds before KILL. This retains existing persisted artifacts;
it does not generate a new model-authored semantic checkpoint. Failed persistence
cannot postpone forced termination. A final provider charge may remain unknown
when killed before publication; last sampled usage is not final-cost proof.

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
