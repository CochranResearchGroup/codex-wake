# Nested budget source checkpoint

2026-10-14; issues256–257 remain OPEN.

Primary integrated the objective ledger returned by worker/root/objective_ledger.
The worker owned only objective_ledger.py and its tests; no effects or commits.
Worker goal counter/model/effort unavailable. Primary conservatively retains its
100,000-token reservation rather than claiming measured external usage.

Worker red: module missing. Green:5 public ledger tests in0.257s. Primary review
found replay/session-expiry and path-authority gaps; one bounded corrective packet
added those checks. Final worker report:7 tests passed0.175s. Primary accepted
the returned implementation with direct inspection and combined verification;
added read-only inspection and aggregate overcommit replay fencing afterward.

Runtime adapter now charges source cumulative goal snapshots once, reserves
session resources atomically against the shared objective, charges preflight
including rejection/overspend, bounds the successor's actual native goal budget,
and records continuation/rollback without renewing the original deadline.
Monitor includes shared accounting and session deadline, with an owned pause/
interrupt path even when trusted time becomes unavailable. Unknown actor spend
holds admission; empty native turn history proves zero prior model work, allowing
existing same-tab readiness reconciliation without inventing accounting.

Public red/green: successor session cap100 initially yielded native budget920;
after integration preflight30 leaves70. Public configuration readback demonstrates
prior spend40 preserved through an explicit cap extension500→600, yielding560
remaining, while editing defaults alone leaves the active ledger at500.

Retained failures:

- /tmp/plan0156-budget-focused.log: two same-tab reconciliation failures from
  unknown usage on a native thread with no turns; explicit empty-history zero
  observation fixes this without resetting completed actor counters.
- /tmp/plan0156-budget-final.log:37 order-dependent failures from caching the
  trusted-clock function; dynamic lookup restores the actual injected boundary.
- /tmp/plan0156-budget-final2.log: one expired-preparation vocabulary regression;
  expired original/session deadline now remains `expired`, with original reason.

Final focused result is recorded in RUNBOOK before source commit. Full release
checks and installed native both-mode acceptance have not run. Explicit reset
semantics, refresh/spawn ledger coverage and bounded automatic correction remain
open; extension history and a durable cycle counter do not prove those outcomes.
