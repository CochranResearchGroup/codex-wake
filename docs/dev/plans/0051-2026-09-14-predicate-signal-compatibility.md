# Plan 0051: Predicate Signal Compatibility

Status: OPEN

Issue: `CochranResearchGroup/codex-wake#5`

Branch: `feat/issue-5-predicate-compatibility`

## Outcome

Route the existing time, file-exists, file-changed, and process-done recipes
through the provider-neutral signal seam while preserving their schema-v1 CLI,
record, retry, expiry, cancellation, archive, evidence, and dispatch behavior.

## Scope

- Define built-in adapters and deterministic logical identities for the four
  existing predicates.
- Preserve existing commands and schema-v1 records as compatibility inputs.
- Add mixed-version, upgrade, downgrade, restart, and lifecycle fixtures.
- Keep provider logic and target transport behavior outside the adapter seam.

## Non-goals

- No GitHub, webhook, public ingress, installed-runtime mutation, live
  dispatch, deployment, or release work.
- No removal or incompatible rewrite of schema-v1 records.

## Acceptance

- Existing CLI and schema-v1 behavior remains byte- and outcome-compatible at
  its public boundaries.
- Each built-in predicate can be expressed and evaluated through the shared
  signal contract without a new daemon provider branch.
- Retry, expiry, cancellation, archive, evidence, and firing recovery retain
  deterministic coverage.
- Python 3.11/3.12, plugin, compile, and diff gates pass.

## Execution

Use one `gpt-5.6-sol` high-effort implementation agent in the issue worktree.
The primary owns compatibility decisions and integration. One mechanical
read-only review may use `gpt-5.6-luna` medium after the focused suite is green.

