# Objective enforcement — proposed ticket graph

Status: APPROVED and PUBLISHED; operator confirmed the breakdown on2026-10-16. Specification:[#274](https://github.com/CochranResearchGroup/codex-wake/issues/274). Research source:#270. These are proposed implementation tickets, not mutations of the research issue.

1. **Launch and inspect one contained objective executor** — blocked by:none. Public lifecycle launch validates explicit controls, reserves through the existing ledger, creates a dedicated executor with durable binding, and reports its coverage. Prove actual isolated Codex/tool/child membership, host limit readback and unrelated sentinel preservation; refuse unsupported or shared-only execution before tasks. Normal cleanup must leave no owned work. No automatic strict-mode production activation.
2. **Enforce the fixed objective deadline independently** — blocked by:1. The same public operation independently stops a blocked tool and resistant child at its original deadline, with bounded grace and verified process/cgroup emptiness. Restart and suspend/resume cannot replenish time; unsupported guarantees refuse admission. Stop ambiguity reconciles exact invocation identity.
3. **Stop on token exhaustion or lost accounting** — blocked by:1 and2. Existing cumulative accounting drives sampled token stops; an independent freshness lease stops work on stale/missing usage, transport loss or real observer death. Readback reports measurement delay and unknown overshoot. Cached input, failed work and preflight remain charged. Native and injected evidence are distinguished.
4. **Carry containment through concurrent work and lifecycle renewal** — blocked by:3. Multiple owned actors, reviewers, successors, refresh and restart share one objective boundary and ledger without replenishment or duplicate charging. Checkpoint reserve cannot extend the stop; exhausted work remains fenced until explicit renewal preserves historical consumption. Demonstrate through public lifecycle operations and a bounded disposable native acceptance packet.

All four retain the specification's exclusions and current released emergency-control integration. Proposed sequence is deliberately linear after ownership: failure stops depend on the deadline adapter, and cross-lifecycle composition depends on its stop/accounting contracts. No horizontal schema-only ticket.

## Published graph

- #275: contained executor; no blockers.
- #276: independent deadline; blocked by#275.
- #277: token/accounting-loss stops; blocked by#275 and#276.
- #278: lifecycle/concurrency/renewal; blocked by#277.

All four are enhancement/ready-for-agent sub-issues of#274. Native blocking edges and parent membership were read back. #275 is the first executable frontier; the other ready-for-agent labels describe specification completeness, not absence of blockers. Parent#274 and research#270 remain open, with bodies and labels unchanged.
