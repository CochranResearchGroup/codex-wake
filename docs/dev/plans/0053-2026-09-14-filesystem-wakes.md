# Plan 0053: Restart-Correct Filesystem Wakes

Status: OPEN

Issue: `CochranResearchGroup/codex-wake#6`

Branch: `feat/issue-6-filesystem-wakes`

## Outcome

Deliver portable file-created, file-exists, and observed-file-changed signal
recipes whose durable fingerprints and reconciliation remain correct across
restart, watcher loss, overflow, rename, delete/recreate, and coalesced writes.

## Scope and acceptance

- Keep watcher notifications as optional latency hints; bounded fingerprint
  reconciliation is correctness authority.
- Normalize safe path subjects and bounded evidence without retaining file
  content or accepting arbitrary callbacks.
- Preserve pre-registration baselines for `becomes` and change semantics.
- Expose baseline, observed fingerprint, and coalescing evidence through the
  existing bounded inspection surface.
- Prove provider-free registration, persistence, restart, match, and
  no-dispatch firing, plus Python 3.11/3.12 and plugin regression gates.

## Non-goals

No live target dispatch, installed service mutation, deploy, release, GitHub
provider work, or guarantee that every physical write occurrence is retained.

## Execution

Use `gpt-5.6-sol` high for implementation. The primary owns shared signal and
CLI contracts; one `gpt-5.6-luna` medium read-only review follows green tests.

