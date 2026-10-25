# Bounded background jobs

A background job executes one operator-configured local command independently of
its submitting turn. Command profiles contain exact argv, cwd, owner, task/assignment
pin and wall/log limits. A profile is command data: the common `job.launch` rule
must separately allow execution. New actions require approval by default.

The dedicated `jobs` command group supports `configure`, `profile`, `launch`,
`show`, `cancel` and `await`. Shared CLI/MCP integration is owned by the coordinator.
Configure requires a verified operator; launch selects a profile, never an arbitrary
model-supplied argv. Host callers may use `BackgroundJobs` directly with a verified
`Principal`. The public profile lookup supplies the exact task/assignment pin so a
caller adapter can recover task authority using the existing verifier.

```text
jobs configure --profile check --owner <exact-session> --task-id <task>
  --assignment-id <admission> --cwd /approved/workspace
  --argv-json '["/absolute/python", "check.py"]'
  --max-seconds 300 --max-log-bytes 1048576 <operator capability options>
jobs launch --profile check --idempotency-key check-1 <caller capability options>
jobs show --job-id job_<id> <caller capability options>
jobs cancel --job-id job_<id> --generation 1 <caller capability options>
jobs await --job-id job_<id> <caller capability options>
```

For mutation profiles, operator configuration additionally supplies `--mutation`,
`--claim-id`, `--claim-generation` and `--managed-agent-id`. The adapter obtains
current enrolled binding evidence through the existing `RuntimeObserver`; CLI
arguments cannot serialize a claimant or choose an operator role. Launch observes
the same managed owner afresh. Non-operator claimants must belong to the verified
caller's exact conversation. Runtime endpoint, socket, bounded timeout and existing
Grok binding/capability options select observation sources, not identity authority.

The host API accepts `mutation=True` with a genuine
`(claim_id, generation, Claimant)` tuple for configuration, then a fresh
`claimant=Claimant(...)` for launch. Profiles retain only claim ID/generation and
managed owner/process identity, not a reusable observation timestamp. Old profiles
with an expired stored observation still work when the same exact owner/process
is freshly verified; stale observations, suppressed owners and changed generations
refuse. `ResourceClaims.guard` fences admission and actual release, with live
process generation and the original fresh observation age checked immediately
before exec. Mutation classification is an operator declaration, not an OS
interceptor of arbitrary same-user commands.

Profiles are revisioned. Each job freezes its original profile revision/digest.
An identical idempotency key returns its original job, including unknown outcomes;
changed command data conflicts. Completion retains nonzero exit codes as command
completion, distinct from timeout/cancellation and uncertain execution.

The detached Python supervisor owns one non-daemonizing process group. It drains
stdout/stderr while retaining at most the configured **combined** byte cap, applies
a monotonic wall deadline, sends TERM and then KILL after a bounded grace, and
cleans up group descendants when the leader exits. It publishes `result.json`
atomically after collecting exit status and flushing logs. The receipt binds the
original intent and boot/PID/start-ticks/UID generation. Cancellation is separately
authorised immediately before signalling; revocation retains a refused receipt.
There are at most 256 retained jobs per root, a 3600-second wall maximum and a
10-MiB combined log maximum. Cleanup is explicit; old evidence is never removed
automatically. Arbitrary output artifacts outside captured logs are not bounded
by this facility; profiles must select approved commands and resource scope.

`await_result` accepts a host callback:
`register_wake(result_path, idempotency_key, job_snapshot)`. The callback must
register an existing file-exists wake with its original HF13 owner, startup,
expiry and permitted routes. Completion before await is supported by the exists
condition. The existing generic filesystem signal reconstructs watched paths
relative to the wake's cwd, so its adapter root must equal its Resume.cwd; an
existing absolute-path native file wake avoids changing the command workspace.
The callback alone does not establish monitor readiness or successful delivery.
Unknown jobs have no fabricated completion marker and cannot automatically resume
as completed. Inspect and reconcile them explicitly.

Submitting-shell exit and controller reconstruction are qualified by hermetic
real-process tests. Host reboot or supervisor loss without a result is retained
as `unknown`, without rerun or guessed cancellation. This does not promise reboot
execution survival, containment against descendants escaping with `setsid`,
hostile same-UID isolation, remote execution, provider calls or installed service
acceptance. A killed supervisor can leave its original group running; preserve
identity and reconcile it rather than signalling an unrelated reused PID.
