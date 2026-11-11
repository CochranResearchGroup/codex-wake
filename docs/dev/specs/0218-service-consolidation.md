## Problem Statement
Wake monitoring has accumulated independent services, overlapping owners and polling cost. Operators need fewer independently managed monitors and lower measured cost without losing responsiveness or durable intent.

## Solution
Use the shared supervisor for explicitly enrolled ordinary roots with per-root cadence, bounded concurrent process workers and inspectable ownership. Keep HTTP controller, webhook listener and refresh worker separate, with justified exceptions. Provide read-only audit evidence and reversible migration qualification.

## User Stories
1. As an operator, I want a concise inventory separating running services from definitions, so that I can assess actual cost.
2. As an operator, I want duplicate monitor ownership identified, so that I can remove overlap safely.
3. As an operator, I want one active polling owner per root, so that competing monitors cannot overlap effects.
4. As an operator, I want aliases of the same root covered by the same ownership boundary, so that registration aliases cannot bypass it.
5. As an operator, I want each root to retain its configured cadence, so that consolidation does not slow work or over-poll a slow root.
6. As an operator, I want a blocked root isolated, so that other roots continue progressing.
7. As an operator, I want concurrency bounded, so that work cannot create unbounded processes.
8. As an operator, I want failures and uncertain delivery visible, so that recovery does not blindly replay effects.
9. As an operator, I want enrollments and dispatch configuration preserved, so that consolidation grants no new authority.
10. As an operator, I want read-only resource samples with elapsed time and scope, so that performance claims are reproducible.
11. As an operator, I want obsolete unit candidates identified without deleting wake state, so that cleanup is safe.
12. As an operator, I want a reversible migration pilot, so that ownership can move without abandoning pending work.
13. As an operator, I want restart and rollback checks, so that consolidation survives interruption.
14. As an operator, I want resource and latency comparisons under synthetic representative backlogs, so that improvement is demonstrated without production dispatch.
15. As an operator, I want explicit rollout limits and retained exceptions, so that service count never overrides safety.

## Implementation Decisions
Preserve existing wake record formats, root enrollment, cadence, deadlines, dispatch commands and permissions. Use the existing supervisor/daemon public interfaces and user-scoped service boundary. Add nonblocking root-level polling ownership shared by both entrypoints; ownership contention is observable and never queues another overlapping poll. Concurrency uses process isolation rather than uncancellable threads. Timed-out or abandoned dispatch outcomes remain held for explicit reconciliation, not automatic uncertain replay. Scheduling uses monotonic time and per-root intervals; missed slots do not cause catch-up bursts. Keep limits finite. Audit operations are read-only. Migrate one root at a time with exact configuration and rollback evidence. Do not infer obsolete runtime state from a missing worktree.

## Testing Decisions
Test behavior through supervisor enrollment/run, daemon polling and the audit command. Existing supervisor/daemon tests are prior art. Use deterministic scheduling seams and real subprocess checks for ownership, isolation, shutdown and restart. Synthetic wake roots contain no credentials/private histories. Capture red/green receipts for consequential changes. Compare resource cost and latency on declared workloads; the earlier 12-second live sample is only a locator for investigation, not the baseline acceptance threshold. Run applicable local checks; skip hosted paid CI. Test release qualification in disposable state; working-host deployment is a separate boundary.

## Out of Scope
Native/account-daemon consolidation, arbitrary workspace discovery, pending-wake deletion, relaxed deadlines, new provider authority, universal exactly-once delivery, forced four-service quota, private history copying, paid CI or unrelated cleanup.

## Further Notes
Design and failure boundary confirmed by operator. Plan LOCAL-P218 governs execution. Deliver one validated integration branch, close accepted implementation tickets, then run exactly one broad two-axis review and one bounded TDD remediation pass. Parent spec remains open unless separately reconciled. Actual working-host rollout is not implied by source acceptance; migration ticket delivers executable disposable qualification and a rollback-ready operator procedure.


<!-- cw-p218-spec -->
