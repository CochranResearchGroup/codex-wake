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

## Implementation outcome

Implementation is complete in the issue branch; independent review, CI, and
merge acceptance remain with the primary owner. No gated effect was executed.

`GitHubWebhookIngress.ingest(body, headers, now=...)` accepts exact bytes or a
blocking binary stream. It returns a small sanitized status/code result. The
caller may acknowledge success only for `200 COMMITTED` or `200 DUPLICATE`,
returned after the real journal ingest has committed. No delivery-cache hit
can bypass that durable operation. Commit races return a retryable failure;
the next attempt reloads the current checkpoint and safely deduplicates.

The primary approved two additive polling interfaces:
`normalize_verified_attempt` validates a terminal allowed attempt and produces
the same occurrence and evidence for both inputs; `checkpoint_for_anchor`
validates the configured source binding and creates a canonical UTC epoch,
order-zero checkpoint only when no checkpoint exists. The epoch means no
polling coverage. An existing checkpoint is reused exactly. An individual
registration cutoff cannot establish source-wide coverage because older arms
may still need earlier history.

The ingress authenticates HMAC-SHA256 over the entire bounded raw body before
JSON parsing. It resolves at most two named secret references on every request
for rotation; keys are neither loaded from a provider nor persisted. Duplicate
case-insensitive headers, non-UTF-8 JSON, duplicate JSON keys, non-JSON numeric
constants, malformed identities, unsupported events/actions, and disallowed
repository/workflow/ref/conclusion claims fail closed.

Signed `workflow_run.updated_at` bounds the hint's age; it is not described as
a signed delivery timestamp. A separate injected `get_run_attempt` read must
confirm repository, run, attempt, workflow, ref, SHA, terminal status, and
conclusion. Its authoritative completion time must also be fresh. Receipt
verification remains exactly `verified / github-run-attempt-read`, including
polling's stable completion timestamp and occurrence identity. Signatures
alone never impersonate an authoritative attempt read. This slice maps
`head_branch` to `refs/heads/`; ambiguous/tag-only webhook refs fail closed and
remain recoverable through the accepted polling adapter.

Default resource limits are 256 KiB body, 1024 stream read calls, one request
in flight with no queue, 120 admitted requests per 60 seconds, two secret
resolutions, one attempt read, one normalized journal observation, and a
256-entry delivery-digest cache. Oversized streams stop at the configured
limit plus one byte. Legal short reads are consumed until EOF, so an unsigned
suffix cannot hide after a valid JSON prefix. Each ingress has zero evaluation
or dispatch budget and does not enumerate wakes; existing bounded evaluators
own fan-out. Configuration has hard upper bounds.

The unsigned delivery ID and bounded in-memory digest cache are transport
diagnostics, not durable replay authority. Cache eviction, process restart, or
a changed delivery ID cannot bypass logical occurrence deduplication. Rate
limits and cache scope are one ingress instance/process; any future scaled
listener must enforce shared admission and bounded stream/provider deadlines.
Public listener behavior, network latency, secret provisioning, provider
credentials, and live delivery are explicitly unverified.

## Test and routing receipt

- Worker: `/root/p48_i8_webhooks`, exclusive issue #8 writer, no subagents.
  Requested route: `gpt-6-astra`, high. Effective runtime configuration and
  measured allocation are unavailable; no savings claim is made.
- TDD REDs established the missing module/configuration, claim rejection,
  admission bounds, and delivery conflict behavior before implementation.
  Primary review found a short-read prefix acceptance defect, reproduced as
  `COMMITTED` with unread unsigned trailing bytes and repaired. Worker review
  found arbitrary-arm checkpoint seeding could omit an older needed run;
  primary approved the epoch seed, and its RED `[102]` became GREEN `[101, 102]`.
- Focused: 30 GitHub tests (12 webhook, 18 polling) pass on Python 3.11,
  including fresh subprocess `os._exit` before/after the journal commit,
  rollback/retry, checkpoint races, polling-first and webhook-first duplicate
  convergence, missed/stale/out-of-order delivery, rerun attempts, hostile
  payloads, raw-data/secret absence, no-queue admission, and bounded fan-out.
- Final comprehensive `PYTHONPATH=src python3.11 -m unittest discover -s tests
  -p 'test_*.py'`: 275 tests passed in 7.472 seconds. Python 3.12 with the same
  selection: 275 passed in 7.262 seconds. `npm --prefix
  plugins/openclaw-codex-wake test`: 12 passed. Both Python versions passed
  `-m compileall -q src tests`; `git diff --check` and explicit whitespace
  checks for the two new files passed. Tests are isolated, provider-free,
  without retries, flakes, quarantines, or live/soak execution.

Protocol references checked during implementation:
[GitHub signature validation](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)
and [workflow-run events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads#workflow_run).
