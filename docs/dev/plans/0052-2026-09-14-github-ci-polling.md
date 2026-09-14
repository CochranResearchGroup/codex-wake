# Plan 0052: GitHub CI Polling

Status: OPEN

Issue: `CochranResearchGroup/codex-wake#7`

Branch: `feat/issue-7-github-ci-polling`

## Outcome

Add a provider-neutral GitHub workflow-run polling adapter that can arm an
exact allowlisted repository, workflow, ref, and conclusion and can prove a
verified post-anchor match through deterministic provider-free fixtures.

## Scope

- Define least-privilege configuration, allowlists, stable run identity,
  pagination, checkpoints, retry windows, and history-gap behavior.
- Normalize only bounded sanitized workflow evidence into the signal journal.
- Add fixtures for success, failure, cancellation, timeout, duplicates, stale
  runs, auth loss, rate limits, restart, and verification failure.
- Expose only declarative caller intent; arbitrary URLs and provider queries
  remain invalid.

## Non-goals

- No live GitHub API call, credential mutation, webhook ingress, live dispatch,
  installed-runtime mutation, deployment, tag, or release.
- No shared dispatch or SQLite schema redesign without primary reconciliation.

## Acceptance

- Exact allowlisted registration fails closed with sanitized diagnostics.
- Only a verified qualifying run after the durable anchor can reserve a match.
- Pagination, gaps, retries, duplication, and restart are deterministic and
  bounded in provider-free tests.
- Python 3.11/3.12, plugin, compile, and diff gates pass.

## Execution

Use one `gpt-6-astra` high-effort implementation agent because credential,
verification, and provider-history boundaries dominate this slice. The primary
owns shared-contract changes and integration. One mechanical read-only review
may use `gpt-5.6-luna` medium after focused acceptance is green.

