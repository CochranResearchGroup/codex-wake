# HF-14: Durable bounded background jobs

State: APPROVED_SPEC / implementation in progress
Work item: #336 / CW-HARNESS-173/HF-14
Owner: primary coordinator; implementation lane hf14
Authority: approved product form d9b59f368e984dff925597304f90e901,
all recommended answers; explicit implementation instruction 2026-10-24.
Base: 457030622d59d2ec47f5190b2025fbb7ea50ca79

## Frozen outcome and boundaries

Launch one approved local argv command outside the submitting turn, retain its
original process generation, bounded output and exact terminal result, and await
it through the existing filesystem-exists wake. No shell command strings,
provider calls, remote execution, host service installation or generic dispatcher.
The first command class is cooperative non-daemonizing process groups; escaping
with setsid or hostile same-UID activity is outside the containment contract.
A task brief and exact cwd bind command scope. Mutation commands additionally
require an exact active resource claim; custody alone grants no command authority.

## Lifecycle and durability

A private versioned job journal retains immutable intent/idempotency identity,
owner/task/brief, command and bounds. Commit a single launch attempt before
starting an independent supervisor. A release-gated child cannot exec until its
boot/PID/start-ticks/UID identity is persisted. Any uncertain launch is retained
without automatic retry. Controller or submitting shell exit does not kill the
supervisor. Supervisor loss or host reboot without a terminal receipt is unknown;
this is not reboot execution survival. Unknown versions/corruption fail closed.

The supervisor owns pipes and a process group, bounds stored stdout/stderr bytes,
drains excess output and enforces a monotonic wall deadline with bounded TERM/KILL
cleanup. It retains the leader generation through group cleanup. Terminal receipt
is atomically published only after exit collection and log finalization and binds
original job/generation, command hash, process identity, exit/signal and outcome.
Cancellation is attributable and generation-fenced; uncertain cancellation never
relaunches or guesses another process. No automatic record/log cleanup.

## Public seams and integration

BackgroundJobs owns launch, inspect, cancel and await_result. Host adapters provide
verified Principal inputs, never deserialize a model-supplied role. Common
job.launch/job.cancel permissions are checked before effects; wake delivery checks
its independent existing route permissions. Parent owns shared CLI/MCP action
registration and glossary; worker owns dedicated command adapter and docs.
Await accepts a host register_wake(result_path, idempotency_key, job) callback.
It must register FilesystemSignalAdapter.request('exists') through EventWake,
including frozen HF13 owner/startup/expiry/routes. The existing daemon reconstructs
that source; job completion does not itself dispatch a model turn.

## Acceptance and tests

Public module/command seams with temporary roots and real Python child processes
prove submitting-process exit, controller reconstruction, attributable exit/logs,
one-launch idempotency, bounded cancellation/resources, uncertain launch/reboot
retention and no replay. Real existing filesystem signal reconciliation proves
await readiness. Tests are source acceptance, not installed/service acceptance.
One vertical red/green cycle at a time; no independent broad review in this lane.

## Non-goals and closeout

No arbitrary descendant confinement, live reboot, provider input, production
changes, workflow engine, permission bypass or resource renewal. Preserve unknown
outcomes and existing unrelated resources. Primary integrates shared surfaces and
owns issue/plan closure. This worker may commit its bounded source slice only.
Memory disposition: forbidden, explicit task boundary prohibits memory writes.

## Resolved command authority

Primary resolved profile shape under the approved form: operator-only command
profiles store exact argv/cwd, owner, task/assignment pin and bounds. Profiles do
not grant permission. Launch independently requires the common action and exact
verified owner/task. Model caller chooses a profile ID, not arbitrary argv/role.
Public profile lookup supports existing host task-verification adapters. Declared
mutation profiles require genuine ResourceClaims.guard custody at release;
read-only classification remains a cooperative operator declaration.

## Caller-path correction

Mutation configure is supported through the dedicated CLI parser: mutation flag,
claim ID/generation and managed-agent locator. Existing verified caller and runtime
observation seams construct the trusted Claimant. Profiles retain custody identity
only; each new launch requires fresh host observation of the same exact owner and
live process generation. A stored legacy observation is identity provenance, never
fresh execution proof. The supervisor retains the just-observed launch binding and
rechecks its real age and live generation before releasing exec. No timestamp is
renewed synthetically. Read-only profiles remain unchanged.
