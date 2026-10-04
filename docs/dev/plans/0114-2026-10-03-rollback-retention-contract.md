# Installed rollback and retention compatibility contract

State: CLOSED
Lane: P63
Owner: primary
Parent: Plan 0101 / issue #181
Branch: feat/p63-rollback-qualification
Target: origin/main
Integration: squash_pr

## Current State

Main ed973ba includes explicit receipt projection acknowledgement. Full campaign
OPEN. Audit requires pause rollback to preserve accepted/uncertain records and
visible finite dedup retention semantics. Live disposable scope remains pending.

## Scope and authority

One serialized packet qualifies installed CLI pause/status and scheduler refusal,
reopen/read/retry durability, and copied-root restore refusal on synthetic buses.
Correct a verified dedup horizon violation only after a red-capable public test.
Write surface: one mailbox invariant if needed, focused operations regression,
installed qualification harness/CI, verification/full requirement ledger,
README, parent and runbook. No real enrollment, supervisor, release publication,
provider effect, notification I/O, downgrade or destructive store recovery.

## Acceptance and bounds

At most three synthetic messages, one metadata-only dispatch claim (zero I/O),
one CLI pause, one simulated lease timeout and fresh recovery, two canonical
reopens. Unknown notification remains held; retry identity retained within the
90-day window; older keys visibly refused rather than implying infinite dedup.
Thresholds: 20 seconds total, child calls ten seconds each, FD growth at most two,
no residual children. Two implementation attempts, one targeted repair; inherit
review ledger. Current meter 305k; working checkpoint 450k, stop before 500k.

## Non-goals and definition of done

Accept only pause rollback and finite horizon compatibility axes with installed
and hosted evidence. Compact tombstone lifecycle, physical compaction, complete
backup/restore, live agents, service/soak and release remain open. Keep a full
requirement ledger that preserves every original acceptance gate and its evidence.

## Closeout

The existing idempotency_horizon guard already enforces ninety days; first test
expected the wrong code, corrected without runtime change. Seven operations tests
pass on Python 3.11/3.12. Installed rollback workload passes with stable descriptor
and child census, preserving unknown attempts and accepted data while paused.
Current-state requirement ledger in verification 0106 makes full completion
unproven and enumerates remaining gates. No runtime code, broad review allowance
or live authority changed. Hosted integration remains separate.
