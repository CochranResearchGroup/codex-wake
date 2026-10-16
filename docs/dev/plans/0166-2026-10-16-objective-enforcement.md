# Plan0166 — Strict objective execution enforcement

State: OPEN. Owner: ecochran76 / primary. Spec#274; tickets#275–278.
Integration branch: feat/objective-enforcement. Base:0a5c8d1.
User ceiling: stop/checkpoint before1,000,000 tokens or3h from2026-10-16T19:41:41Z; hard checkpoint by22:31Z (10min reserve). Track native goal counters and UTC.

## Acceptance / non-goals
Implement full published#274 contract and each#275–278 acceptance criterion, using public lifecycle operations, native execution containment and independent OS readback. No deployment/fleet changes, shared-session termination, provider cancellation or exact token ceiling claims. Unsupported guarantees reject before task effects.

## Seam and execution graph
Public lifecycle launch/config/status/stop plus dedicated systemd execution adapter.
275→276;275+276→277;277→278. Only validated integration results unlock dependents.
TDD at public configuration/lifecycle seam; host adapter protocol fixtures plus disposable native acceptance. One whole-branch review, one remediation pass; no broad review restarts.

## Workers / owned paths
Primary owns lifecycle/configuration/monitor/CLI integration, ledger, plan and evidence.
Host worker owns new host_execution module and its tests only, independent branch/worktree.
Native probe owns temporary acceptance harness/evidence only; max2 native turns/20k tokens/120s each.
At most3 active agents total. No nested workers.

## Ledger
