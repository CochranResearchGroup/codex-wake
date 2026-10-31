# Reconciliation regression prevention

State: OPEN
Owner: primary for ecochran76
Spec: GitHub439; children440–443
Branch: feat/439-prevention
Base/comparator:5df7c811b4cd9b95a06d3ac4f6f92e84e3ec4f65

## Current State

Tickets440 cleanup (primary),441 validation adoption (worker),442 summaries (worker) are ready.443 integrated qualification is blocked by all three. Source-bound runner356 is reused. Three substantive lanes maximum; integration/shared documentation serialized by primary. No live cleanup/native/service/provider effects. All tests use disposable state. Review0/1 and final findings TDD0/1; freeze full diff only after ticket closure.

## Scope and acceptance

Spec439 is canonical outcome authority. Public seams: cleanup plan/apply on disposable Git trees; existing source-bound validation command; bounded read-only summary command. Deliver safe unknown retention, drift refusal, normal disposable removal and exact missing-registration cleanup; isolated fail-fast repository validation; <=8192-byte summaries with truthful omissions.443 proves integrated behavior and concise invocation guidance. Preserve first failures privately.

## Shared contract and ownership

Primary owns scripts/cleanup_worktrees.py, tests/test_cleanup_worktrees.py, this plan and lane catalog.441 owns existing candidate runner plus a repository local validation launcher/profile and source-bound validation guidance/tests.442 owns scripts/summarize_receipt.py and its public tests; no shared plan/catalog edits.443 adds integrated acceptance/evidence/navigation after dependencies validate.

Cleanup receipt contract: schema="codex-wake.cleanup.v1", kind="plan" or "result", status="PASS"/"HELD"/"FAIL", repository string, entries array. Each entry has id,path,head strings; action="retain"/"remove"/"prune"; disposition="eligible"/"retained_unknown"/"retained"/"removed"/"pruned"/"failed"/"unknown"; reasons array of strings. Additional fields are allowed. A result retains the plan entries with final dispositions. Physical eligibility never follows solely from this schema: exact live evidence and authority are required. Summary supports this schema and existing candidate receipt schema1 only; do not print raw command output/environment data.

## Execution ledger

|Ticket|Blockers|Owner|State|Evidence|
|---|---|---|---|---|
|440|none|primary|running|pending|
|441|none|worker|pending|pending|
|442|none|worker|pending|pending|
|443|440,441,442|worker after readiness|pending|pending|

Private detailed receipts: user-state implement439. Commits/merges, validations and tracker closure are distinct. Changes reach canonical main through reviewed PRs under existing integration policy; local checks satisfy CI. Parent439 remains unmodified.

## Completion

All four children validated and tracker-closed; one broad Standards/Spec review and one bounded TDD findings pass complete, exact final branch/ref/status and protected state read back. Existing retained inventory is never a deletion test target. No hosted CI spending, install, resource renewal, governor activation, privilege grants or global instruction changes.
