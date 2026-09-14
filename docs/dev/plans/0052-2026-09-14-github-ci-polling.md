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

## Adapter packet outcome

The delegated implementation packet is provider-free and locally green in
`src/codex_wake/github_polling.py` and `tests/test_github_polling.py`. The issue
remains open for primary acceptance and integration.

`GitHubPollingAdapter.request()` exposes exact ref and terminal-conclusion
intent. Configuration pins repository name and numeric identity, numeric
workflow identity, full refs, allowed conclusions, an opaque credential name,
and exactly `actions:read` plus `metadata:read` permission declarations. It does
not load or inspect a credential. Raw `SignalRequest` registration must equal
the permitted declarative shape; it cannot turn off verification or add a
provider query. Normalized attributes are bounded typed selectors, never raw
API payloads, log bodies, URLs, headers, or credentials.

Observation uses an injected `GitHubReadClient` with only `list_runs()` and
`get_run_attempt()`. A list candidate cannot become eligible until the exact
repository/run/attempt read agrees with its immutable terminal evidence.
Logical identity is `(github, source_instance,
github.workflow_run.attempt.completed, repository_id:run_id:run_attempt)`.
Repeated polling and future webhook hints must use that identity. Separate
attempts remain separate occurrences. Provider completion time is stored as
both the stable source observation timestamp and `completed_at_us`; actual
poll coverage time is carried in `SourceCommit.observed_through`. This keeps
overlapping replay byte-stable for the journal's immutable receipt contract.

The opaque versioned cursor binds the configured source/allowlist and a UTC
coverage instant. Every poll covers a fixed bounded time window, with overlap
after a prior committed cursor. It bounds pages and page size, rejects broken
page order, and advances no checkpoint until all pages and authoritative
attempt verification succeed. Source coverage that cannot span the requested
window yields `GITHUB_HISTORY_GAP`. Auth loss, rate limits, and verification
failure produce sanitized closed outcomes. Retry deadlines suppress premature
reads; a runner can restore its durable source-health failure through
`previous_failure`. This adapter does not create a second checkpoint or
source-health store.

`RunPage.covered_from/covered_through` is an explicit trusted transport
obligation, not a claim that GitHub page exhaustion proves history coverage.
A future real client must establish complete terminal-attempt coverage despite
retention, pagination churn, and provider indexing delay, or return unavailable
coverage. Likewise, `WorkflowRun.completed_at` must be authoritative immutable
attempt-completion evidence; blindly interpreting a mutable workflow
`updated_at` as completion time does not satisfy this contract. No HTTP client
or live provider validation was added in this packet.

## Shared seam outcome

After the other write lane stopped, the primary delegated these exact additive
shared seams to the same issue7 worker. Both are implemented:

- Added optional `SourceContract.occurrence_order_attribute` and set this
  adapter's contract to `completed_at_us`. The anchor baseline already carries
  the registration instant under that key. Before ordinary matching, shared
  evaluation requires an integer observation value strictly greater than
  the durable arm baseline. This prevents a delayed pre-B observation ingested
  for arm A after arm B registers from waking B.
- Bound the adapter-local read-only `CheckpointReader.source_checkpoint(source,
  source_instance)` to journal readback returning `SourceCommit`, `None`, or
  `Degraded`. `poll_into()` reads that cursor and delegates observation plus
  cursor commit to the existing atomic journal ingestion method.

The passing shared tracer is A registered at t0, B registered at t2, run 101
completed at t1 but ingested at t3: A may match and B must not. Run 100 completing
at t4 is eligible for B despite its lower creation-order ID. Both the in-memory
and SQLite engines prove this delayed-ingest case. Invalid ordering fields,
state-mode misuse, missing/non-integer baselines, missing observation evidence,
and damaged durable baselines fail closed. Stale SQLite receipts advance safe
evaluation progress. The optional field is omitted from serialized contracts
when unset, preserving old fingerprints, and decoded with `.get` for old rows.

The SQLite checkpoint reader opens with `mode=ro`, never creates a missing
journal, and returns the committed cursor after restart. The runner fixture
now uses real SQLite registration/ingestion and proves a failed atomic ingest
does not advance that cursor.

## Validation receipt

The following comprehensive receipt covers the initial isolated adapter
packet, before the shared-seam follow-up:

The `/root/p48_i7_github_polling` delegated packet used the requested
`gpt-6-astra`, high-effort routing from this plan, with no nested delegation.
Separate effective-model/allocation counters were not exposed. TDD first
showed the missing module, then reproduced config bypasses, malformed evidence,
checkpoint-validation gaps, and missing retry restoration before each fix.

- Focused: `PYTHONPATH=src python -m unittest tests.test_github_polling -v`:
  13 passed, including fresh-process durable receipt and match replay.
- Comprehensive Python 3.12.13: 252 passed in 6.151 seconds.
- Comprehensive Python 3.11.15: 252 passed in 6.254 seconds.
- OpenClaw plugin: 12 passed.
- `python -m compileall -q src tests` and `git diff --check`: passed.

The shared-seam follow-up ran the affected selection on Python 3.12.13:
`tests.test_github_polling`, `tests.test_signals`, `tests.test_signal_store`,
`tests.test_signal_records`, `tests.test_signal_crash`, `tests.test_daemon`,
`tests.test_injector`, `tests.test_records`, and `tests.test_cli`: 157 passed in
4.376 seconds. Compile and whitespace checks passed. The primary owns the new
aggregate validation after this follow-up; the earlier 252-test receipt is not
an aggregate claim for the shared edits.

All checks were local, deterministic fixtures with no test retries. No provider
reads, credential operations, webhook ingress, dispatch, installed-runtime
changes, Git commits/pushes, deployment, or release were performed by the
delegated packet. Final acceptance and the merged issue receipt belong to the
primary after reconciliation.
