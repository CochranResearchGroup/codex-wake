# Checkpoint02 — Conservative recovery and standalone source

Progress: outcome_progress. Goal readback at this packet: 246993 tokens,
2692 seconds; below the operator's 2M-token / six-hour stop. Primary only.

37 focused native-intent, clock-contract, native-network, migration and network
tests pass in 1.826s against the standalone feature, without the root's private
StableTime overlay. Thirteen intent scenarios include no-initial-clock recovery,
uncertain effect reconciliation during outage, counter epoch loss, known-UTC
continuity fallback, rate-bound not-before/precision/expiry, stop-at hold,
fresh pre-queue expiry, status alerts, cancellation and terminal-key archival.

Additional TDD defects observed and fixed: acceptance of >=100ms qualified UTC,
non-string counter wire fields and an estimate in an unavailable response,
missing status alerts/schema6 inventory, and guest UTC during intent archival.
One archive edit initially matched the classifier rather than archive_record;
the regression remained red and the misplaced hunk was corrected before green.

Primary service contract read: wsl-time src/client.rs validate_time and
src/authority.rs time. Qualified UTC remains strictly below 100ms; consumer
tolerance does not redefine service validity. Unavailable authenticated service
responses can supply elapsed-only QPC evidence with valid epoch/rate policy.
Microsoft QPC reference: https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps
QPC represents elapsed time, includes sleep, and does not represent UTC. A
service continuity epoch change holds a counter-only request rather than rebases
it. When absolutely no initial evidence exists, the visible conservative relative
origin starts at first qualified observation, so availability can mean lateness.

Read-only Plan0152 overlay removed from the owned worktree after exact hash
verification against preserved-baseline.json. Root and its installed release
remain unchanged. Configuration-aware native creation directly uses the new
adapter; it does not depend on publishing the separate rollout.

Next: isolated installed CLI/worker, concurrent/fresh-process/rollback proof,
bounded two-axis review, docs and integration. No global install/worker/session
effects. Setup default-label preference still awaits a reply; no setup writes
or label effects. CI waiting remains skipped.
