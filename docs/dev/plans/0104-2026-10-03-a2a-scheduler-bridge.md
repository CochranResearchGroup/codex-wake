# A2A scheduler journal and projection bridge

State: OPEN
Lane: P63
Parent: Plan 0101 / P63.4
Depends-On: Plan 0103 mailbox integration
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/181
Branch: feat/p63-scheduler-bridge
Target: origin/main
Owner: primary

## Frozen packet

Add a journal-authorized scheduler service, deterministic body-free job
projections, global/per-recipient generation leases, bounded scanning/batching,
atomic dispatch attempts and typed outcomes. Keep runtime effects behind an
injected qualified adapter; no automatic use of legacy turn/start or TUI paste.
Explicit operator authority selects bus and projection root. Lease generations
fence stale commits. A dispatch claim persisted before external I/O expires into
uncertain and is held; it is never silently retried. Provably unsent outcomes
have at most three actual attempts, bounded backoff, and recipient rate limits.
Pause, cancellation, expiry and capability revocation are rechecked at claim.

Body-free projections are derived jobs, distinct from legacy wake JSON schemas.
An exact bus/intention/recipient and journal authority must match before dispatch;
a file alone confers no rights. Atomic private publication reconciles identical
files after interruption and refuses conflicts. Duplicate service owners cannot
claim one recipient simultaneously. Receipt signal publication uses immutable
receipt IDs and ordered checkpoints; no signal can fabricate mailbox receipts.

## Acceptance and boundaries

Provider-free tests cover interrupted publication and claim/I/O/outcome cuts,
concurrent owners, lease expiry, stale writers, cancellation and expiry races,
revocation, pause, busy/offline deferral, exact pinned targets, bounded scans,
FIFO batching, notification limits and uncertain holds. Installed fixture smoke
must exercise real executable scheduler entrypoints with no provider effect.
Actual live delivery and production service installation remain separate gates
in Plan 0101. No full-system acceptance from this bounded packet.

## Bounds

One primary owner; one optional disjoint test worker after API freeze. Two
implementation attempts and one closed-world rework packet. Default scan 100,
batch 20, tick 5 seconds; 10 notification attempts per recipient/hour. Preserve
all unaffected accepted samples if a later packet fails. Campaign checkpoint
at or before 700,000 goal tokens, below the user's 750,000 stop.
