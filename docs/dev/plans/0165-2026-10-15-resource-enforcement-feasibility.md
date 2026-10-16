# Plan0165 — Issue270 resource enforcement feasibility

State: CLOSED. Research only; issue #270 owns intake. Isolated branch docs/270-resource-enforcement-feasibility, base 75c54a9053942f9d8ed16f4b04a392880f30dabf. Root emergency-controls lane is excluded.

Question: Can the existing lifecycle ledger plus a host supervisor stop already-running owned work at objective resource limits independently of model cooperation?

Primary sources: released lifecycle source/docs, installed systemd255 manuals and cgroup readbacks, upstream systemd/kernel documentation, installed Codex protocol/source where available.

Output: docs/dev/notes/2026-10-15-issue0270-resource-enforcement.md and docs/dev/evidence/issue0270/.

Bounds: 20 minutes, three disposable host experiments (deadline/active child, synthetic token exhaustion, controller/accounting loss); no model calls, production turns, shared service changes, or activation. This research session has no verified external token cap. Experiment services get 3-second runtime and 1-second termination grace, MemoryMax128M, MemorySwapMax0, CPUQuota20%, TasksMax16. No broad performance campaign.

Acceptance / done: map current controls; record experiment commands/results and cleanup; distinguish sampled token control from OS containment; identify missing guarantees; recommend smallest integration and go/no-go. Implementation and live termination excluded. No global ROADMAP or lane catalog edits while another lane owns them.

## Research closeout

Outcome: conditional GO for bounded executor-containment implementation design; NO-GO for exact token ceilings/live rollout. Three synthetic local host experiments removed their exact cgroups with sentinel preserved. Existing ledger11 and spawn27 fixture tests PASS; initial plain-python dependency failure retained. Actual native Codex containment, accounting-loss lease, suspend/resume and finite token overshoot remain unproven. Source baseline matches installed0.15.1 in four relevant modules. Report and raw evidence are under the locators above. No implementation, issue state mutation or activation.

Discovery bounds: two structural queries (second exposed absent worktree index), bounded known-source reads, one five-fact atlas routing query, primary systemd/kernel lookups. No delegation: coupled small source/host investigation remained local. Memory disposition unavailable: no appropriate reviewed Codex Wake group identified.

## Confirmed design follow-up |2026-10-16

Operator accepted all three proposed decisions: dedicated strict execution
boundaries with explicit shared-service exclusions; objective-wide sampled token
accounting including cached input and all actors/attempts; stop on stale/missing
accounting with explicit renewal after exhaustion. Captured in the2026-10-16
implementation brief and domain glossary. Research remains CLOSED; this records
design preparation, not an implementation/deployment claim.
