# Plan 0054: Signed GitHub Webhook Convergence

Status: OPEN

Issue: `CochranResearchGroup/codex-wake#8`

Branch: `feat/issue-8-github-webhooks`

## Outcome

Add a provider-free authenticated webhook ingestion component that normalizes
GitHub workflow completions to the polling adapter's exact logical identity,
commits before acknowledgement, and remains bounded under invalid traffic and
event storms.

## Scope and acceptance

- Verify signatures over exact bounded bytes before JSON parsing or storage.
- Reject stale, oversized, unsupported, malformed, and disallowed events with
  sanitized diagnostics and no raw-payload persistence.
- Commit a verified normalized receipt or durable duplicate before success.
- Prove polling/webhook convergence, missed/delayed/out-of-order reconciliation,
  and size/rate/queue/fan-out/evaluation budgets with deterministic fixtures.
- Keep the ingress core transport-neutral and public-listener-free.
- Pass Python 3.11/3.12, plugin, compilation, and diff gates.

## Non-goals

No public listener, secret provisioning, live GitHub delivery, live dispatch,
installed-runtime mutation, deploy, tag, or release.

## Execution

Use `gpt-6-astra` high because authentication, commit-before-ack, and abuse
boundaries dominate. The primary owns shared identity and integration; one
`gpt-5.6-luna` medium read-only review follows green tests.

