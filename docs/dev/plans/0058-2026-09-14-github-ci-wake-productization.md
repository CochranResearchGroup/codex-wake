# GitHub CI wake productization goal campaign

State: OPEN
Lane: P50
Issues: #34, #35, #36, #37
Branch: `feat/issue-34-github-history-evidence`
Goal ID: P50-G1
Goal Version: P50-G1-v1
Checkpoint: P50-G1-C01

## Goal objective

> Deliver a production-safe GitHub Actions polling source, a supported
> `github-ci` operator recipe, continuous restart-correct daemon observation,
> sanitized readiness and support evidence, and one isolated installed canary
> that proves a post-anchor workflow completion can cause exactly one bounded
> visible Codex wake. Preserve the provider-neutral signal journal and existing
> dispatch transports. Do not claim history coverage or completion-time
> provenance beyond evidence the GitHub API actually supplies. Do not expose
> public webhook ingress, mutate provider configuration or credentials, refresh
> the global installation, deploy, tag, or release.

## Current state

Checkpoint `P50-G1-C00` starts from clean synchronized `origin/main`
`b38678da71a661038c5b29ba503ba0d3504af5d4`. P49 is closed and rolled back;
there were no open issues, pull requests, or implementation lanes before P50.
Issues #34 through #37 are now open, assigned, and dependency ordered.

The accepted GitHub adapter is fixture-only. It defines exact source,
repository, workflow, ref, conclusion, run-attempt identity, pagination,
checkpoint, and retry contracts, but the product has no production read
client, explicit enabled-source registry, GitHub daemon runner, or supported
GitHub registration CLI. The current fixture seam assumes complete coverage
through the poll clock and an immutable `completed_at`. GitHub REST list and
exact-attempt responses expose `updated_at`, not an explicit immutable
workflow-attempt completion timestamp, and list exhaustion does not prove
visibility through wall-clock now. P50 must resolve that evidence gap before
advancing a production checkpoint.

Graphiti was healthy but returned no P50-specific facts. Current repository,
GitHub, CodeGraph, official provider documentation, tests, and live readback
remain authoritative.

Checkpoint `P50-G1-C01` accepts the coordination merge through PR #38 at
`dadff6f570a255511feec782db9787ab22fbde85` and claims issue #34 for the
`feat/issue-34-github-history-evidence` worktree. The provider/security and
runtime consultations agree that list exhaustion and run `updated_at` cannot
be promoted into complete history or immutable completion-time evidence. The
first implementation packet must preserve that distinction and produce the
smallest safe production-read tracer before later runtime lanes open.

## Scope

- Resolve production history, watermark, and completion-time evidence without
  weakening fail-closed semantics or manufacturing coverage.
- Add an explicit nonsecret enabled-source registry. Registration selects an
  existing allowlisted source and cannot create provider authority.
- Add a bounded fixed-origin read-only GitHub client and exact-attempt
  verification with sanitized errors and durable retry behavior.
- Add supported `github-ci` registration and fresh-process daemon polling.
- Extend doctor, status, readiness, support export, documentation, and the
  installed-wheel smoke for GitHub source operation.
- Qualify one isolated installed candidate service against one exact
  post-anchor Actions completion and one live tmux dispatch.
- Use GitHub issues, short-lived branches, pull requests, CI, and canonical-main
  readback for every independently mergeable slice.

## Non-goals and effect boundaries

- No public listener, webhook configuration, webhook delivery, or ingress
  deployment.
- No workflow dispatch API, rerun, cancellation, branch/tag manipulation,
  release, deployment, or other GitHub mutation.
- No credential creation, refresh, scope change, logging, persistence in wake
  records, or exposure in diagnostics.
- No arbitrary URL, host, query, repository, workflow, ref, or credential input
  from a wake registration.
- No global `uv tool` refresh or mutation of the normal repo wake root,
  supervisor registry, or unrelated user services.
- No claim of exactly-once external delivery. The canary proves one bounded
  dispatch attempt for one wake.
- No additional event source such as pull-request review, merge, systemd,
  socket, queue, monitoring, or human approval in this goal.

## Architecture decisions to freeze in issue #34

1. Production source configuration binds hostname, source instance, repository
   slug and numeric ID, workflow ID, full refs, conclusions, credential
   reference, consistency/history limits, and request/byte/time budgets.
2. The client constructs fixed GitHub GET endpoints internally. Redirects,
   pagination links, response text, and provider URLs never become caller
   authority or persisted evidence.
3. Exact attempt identity and positive occurrence evidence are distinct from a
   source-wide completeness watermark. A verified positive observation may be
   ingested only through an explicit contract that does not falsely advance
   unproven coverage.
4. A production checkpoint advances only to a conservative evidence watermark
   supported by the selected API mapping. If no provider guarantee supports a
   complete interval, the source retains bounded replay and reports the exact
   degraded coverage strength rather than claiming `[since, now]`.
5. Workflow-attempt occurrence time must have explicit provenance. Blind use of
   mutable run `updated_at` remains forbidden. Any conservative job-derived or
   first-observed terminal timestamp contract must state what it proves, what
   it excludes, and how restart/replay preserves registration ordering.
6. Credentials are selected by an explicit operator-owned reference. Tokens
   never appear in command arguments, records, logs, support exports, fixtures,
   or exception messages. Application transport permits only bounded GETs even
   if the external credential has broader provider capability.

## Dependency and execution graph

```text
#34 production history evidence and read client
              |
              +------------------+
              v                  v
#35 daemon and CLI runtime   #36 readiness and guidance
              +------------------+
                         |
                         v
              #37 isolated installed canary
                         |
                         v
              P50 integrated acceptance
```

Issue #34 is serialized because it freezes the provider-evidence contract used
by every later slice. After #34 merges, #35 and #36 may run in parallel in
separate worktrees. Issue #37 begins only after both are accepted on
`origin/main`. At most two implementation lanes plus one read-only reviewer are
active at once.

## Issue packets

### Issue #34: production history evidence

One vertical tracer selects an explicit source, performs bounded read-only
observation, verifies exact attempts, and commits only evidence justified by
the production mapping. Provider-free adversarial fixtures precede one bounded
read-only live qualification. This issue owns the source registry, credential
resolver interface, transport, evidence watermark, attempt-time provenance,
and direct tests.

### Issue #35: daemon and CLI runtime

One supported `github-ci` recipe registers only against enabled source
instances and the daemon recovers observation across a fresh process. This
issue owns CLI parsing and output, runner construction, lifecycle integration,
source health persistence, service configuration inputs, and compatibility
tests. Production provider calls remain disabled in tests.

### Issue #36: readiness and support

Operator surfaces distinguish configuration, credential capability, health,
watermark, lag, rate limit, history gap, and disabled state without exposing
provider payloads. This issue owns status/doctor/readiness/support projections,
installed product smoke coverage, README, and the canonical vision status.

### Issue #37: installed canary

Build a wheel from exact accepted source, install only into
`~/.local/state/codex-wake/p50-github-canary-20260914/venv`, and operate only
`codex-wake-p50-github-canary.service` with an isolated wake root and
`XDG_STATE_HOME`. Arm one exact source before a benign CI completion, restart
the service before completion, then accept only one verified occurrence, one
match, one dispatch attempt, hook acknowledgement, and
`visible_prompt_observed`. Extract a sanitized receipt, archive, uninstall, and
remove only exact P50 artifacts recoverably.

## Subagent and model routing

- Primary orchestrator: authority, architecture adjudication, shared contract,
  issue/plan state, integration, provider/live-effect gates, and final claim.
- Provider/security specialist: requested `gpt-6-astra`, high, for history
  evidence, credential isolation, endpoint, and causality decisions.
- Runtime implementation: requested `gpt-5.6-sol`, high, for CLI, daemon,
  restart, and shared-runtime behavior.
- Mechanical fixtures/docs/evidence: requested `gpt-5.6-luna`, medium, only
  with deterministic acceptance and bounded output.
- Deterministic tools own API readback, hashing, schema checks, test execution,
  CI polling, process/unit inspection, and counter reconciliation.

Effective runtime model, effort, allocation, and timing are recorded when
exposed; otherwise the receipt says unavailable. No worker may change scope,
weaken coverage semantics, perform provider mutation, dispatch live, merge,
close issues, or release. Nested delegation is disabled.

## Goal controls and bounds

```text
goal_id: P50-G1
goal_version: P50-G1-v1
max_work_unit_attempts: 2
max_review_rework_cycles: 1
max_hardening_checkpoints: 2
max_review_discovery_passes: 1
checkpoint_interval: 1 accepted issue or material gate
concurrency_limit: 2 implementation lanes plus 1 read-only reviewer
live_provider_mutations: 0
live_dispatch_attempts: 1
canary_retries_after_registration: 0
authorization_gate: material_departure_or_explicit_action_gate_only
review_verification_mode: closed_world_if_reviewed
checkpoint_fields: state_transition, acceptance_state, progress_classification, evidence, material_blockers, next_action_or_stop_reason
```

The approved goal authorizes ordinary issue/branch/PR work, bounded read-only
GitHub qualification, one isolated candidate service, one benign CI completion
caused by the ordinary issue #37 pull-request workflow, and one live tmux
dispatch. It does not authorize any excluded effect above. Ambiguous provider
or dispatch effect ends the live attempt; inspect the original identities and
do not create a replacement wake or retry the effect.

## Acceptance topology

### Provider correctness

- Exact source configuration and least-authority registration fail closed.
- Positive attempt verification and history completeness are independently
  represented and tested.
- Late visibility, old-created/newly-completed runs, reruns, pagination churn,
  missing attempts, retention gaps, rate limits, auth loss, malformed payloads,
  response limits, and timeouts cannot skip or falsely match work.
- Credential and raw provider material are absent from every durable and
  operator-facing surface.

### Runtime correctness

- CLI registration is durable, idempotent, and capability gated.
- Daemon restart recovers the same source, arm, checkpoint, retry state, wake,
  and dispatch bound.
- Filesystem and legacy predicate paths retain their accepted behavior.
- Source failure is inspectable and remains separate from target readiness.

### Product and installed proof

- Doctor, readiness, status, support export, and docs state the true source
  capability and recovery strength.
- A built wheel exercises the provider-free GitHub lifecycle through installed
  entrypoints.
- The isolated canary binds source commit, wheel and executable hashes,
  configuration fingerprint, unit and PID, wake and target, anchor and
  checkpoint, run and attempt, receipt, dispatch, acknowledgement, visibility,
  archive, and rollback.
- Final comprehensive Python 3.11 and 3.12 tests, plugin tests, entrypoint
  syntax, planning audits, and GitHub CI pass from canonical integration state.

## Stop and replan conditions

Stop before production integration if official provider evidence cannot support
the chosen timestamp or watermark contract, if the client would need arbitrary
network authority, or if credentials could leak. Stop before provider access
if the exact source is not configured, the authenticated identity is unknown,
or only a provider mutation can generate the needed evidence. Stop before the
canary if source/wheel/service identities disagree, the isolated root already
exists or is nonempty, the target or hook is not ready, the persisted attempt
bound is not one, restart recovery fails, or normal/global state drifts.

After registration, any ambiguous provider observation, coverage gap affecting
the selected occurrence, duplicate match, dispatch uncertainty, missing
visibility, or unrelated runtime drift ends the attempt. Preserve the original
record, extract evidence, and roll back without retry.

## Definition of done

Issues #34 through #37 are closed from accepted evidence; their plans and
branches are reconciled; one production-configured GitHub source works through
supported installed entrypoints; the isolated canary proves one post-anchor
workflow occurrence and one visible bounded wake; rollback is complete;
ROADMAP, RUNBOOK, vision, active-lane, verification, GitHub, Git, tests, and CI
agree on the result; and `origin/main` is clean with no P50 lane left active.

## Issue #34 implementation receipt | 2026-09-14

State transition: active -> provider-free implementation awaiting primary review.
Progress classification: outcome_progress. Issue #34 remains open; production
qualification, integration, and later P50 acceptance are not claimed here.

- Added `GitHubSourceRegistry` for explicitly configured enabled sources and
  `GitHubRestClient` for internally constructed GitHub.com GET endpoints.
  Registration selects an existing source; no URL or token comes from a wake.
  Credentials are obtained through an injected reference resolver and are not
  persisted. Request, response-byte, aggregate-byte, pagination, and time budgets
  bound each poll. Redirects and provider pagination URLs are never followed.
- Production mode is explicitly `positive_only`, restricted to branch refs.
  It maps the provider's `head_branch` into `refs/heads/` and checks the exact
  configured namespace plus repository slug/ID, workflow ID, attempt, and SHA.
  The coordination owner selected this initial branch-only mapping; tag refs
  and enterprise hosts are unsupported.
- A terminal exact-attempt read and its fully paginated jobs establish
  `terminal_proof_at`: the maximum of attempt `run_started_at` and valid job
  `completed_at` values. This is a lower bound on workflow completion, not its
  immutable completion time. Mutable workflow `updated_at` is never consumed.
  Empty job evidence permits the attempt-start lower bound only. An old lower
  bound does not prove post-arm completion and produces no observation.
- Positive batches expose `coverage=positive_only` and health
  `GITHUB_COVERAGE_UNPROVEN`. Their checkpoint remains the configuration-bound
  epoch/order zero. They re-enumerate within the arm's bounded history horizon;
  list exhaustion does not establish an interval of complete history. Newer
  attempts cannot hide earlier attempts because each exact attempt is read.
  Any request, malformed response, page, jobs, or verification failure aborts
  the batch before ingestion. Missing history cannot be inferred absent.
- Normalized evidence uses `terminal_proof_at_us` with explicit provenance.
  Both normalized time fields contain that stable proof bound, not poll time;
  fresh-process replay keeps the same receipt identity. If provider evidence
  changes, the existing journal identity-conflict guard fails closed. The
  previous fixture-only completion contract and receipt shape remain intact;
  source fingerprints distinguish the production ordering contract. No
  signal-store schema change is required.
- Ingress, daemon, CLI, readiness, and installation were not changed. The
  current webhook freshness gate requires the fixture completion timestamp and
  therefore cannot accept this production positive-only mode. No public
  production webhook capability is claimed. A production runner must consume
  `PollBatch.health` alongside ingestion; the older `poll_into` convenience
  return is an ingestion result, not a completeness or readiness result.

TDD evidence: source selection, positive-only journal ingestion, old-started
job proof, failure categories, earlier rerun visibility, aggregate byte limits,
duplicate JSON rejection, disabled/tag-source rejection, and fixture-shape
compatibility each had a failing test before the implementation passed. Final
tests additionally exercise late visibility, old proof with newer updated_at,
atomic provider failure, and a fresh Python process recovering the same receipt
and match with order zero.

Validation performed by implementation worker `/root/p50_i34_implementation`:

- Python 3.12.13 focused: `PYTHONPATH=src python -m unittest
  tests.test_github_client tests.test_github_polling
  tests.test_github_source_config tests.test_github_webhooks` — 41 passed.
- Python 3.12.13 comprehensive: `PYTHONPATH=src python -m unittest discover
  -s tests -p 'test_*.py'` — 323 passed in 8.723 seconds.
- `compileall` for the three changed production modules and `git diff --check`
  passed. Python 3.11, plugin tier, live provider qualification, and integration
  are reserved for the primary owner; this receipt does not claim them.

CodeGraph reported the branch worktree unindexed, so exact scoped native reads
were used. Graphiti discovery was skipped because the supplied issue and
current branch-local plan were sufficient for this packet. Effective model,
reasoning effort, and allocation were not exposed to the worker runtime;
configuration was inherited. No nested agents, credentials, provider calls,
commits, pushes, dispatch, installed-runtime changes, or memory writes occurred.

Next action: primary review and bounded read-only provider qualification of the
selected lower-bound and branch mapping, then issue #34 integration if accepted.

### Accepted blocking findings: one bounded repair cycle

State transition: primary review -> repaired, awaiting closed-world verification.
Progress classification: blocker_reduction. This cycle addresses only the two
accepted findings and does not reopen broad review.

1. **Branch origin ambiguity.** Both list and exact-attempt responses now require
   `head_repository.id` and `head_repository.full_name` to equal the configured
   repository before mapping `head_branch` into `refs/heads/`. Missing, null,
   malformed, or fork origins reject the whole batch. The regression previously
   produced positive batches in ten missing/mismatched-origin cases and now
   rejects them all. The primary supplied a sanitized live readback for exact
   attempt `34920248569/1`: repository and head_repository both have ID
   `1242753508` and full_name `CochranResearchGroup/codex-wake`; branch `main`,
   event `push`, workflow `279450573`, SHA
   `9e9cd3caf5330394a4c8299ee72d1e22e1d3962f`, completed/success. This verifies
   availability of the required fields on the selected live attempt; the
   implementation worker performed no live read.
2. **Absolute deadline over response headers.** A scoped POSIX `ITIMER_REAL`
   guard now covers one complete synchronous transaction: credential resolution,
   connect/DNS/TLS, request, headers, body, and cleanup. It uses the smaller of
   the request limit and remaining poll time, raises a sanitized budget error,
   cancels its timer, restores the previous signal handler, and closes response
   and connection resources. It starts no worker thread or subprocess. It
   refuses existing timers, pending/blocked alarms, unsupported platforms, and
   non-main-thread callers before credential resolution or network activity.
   **Issue #35 must run this initial production transport on the Linux/POSIX
   main thread with an unowned real timer.** An unsupported runner receives
   `GITHUB_SOURCE_UNAVAILABLE` rather than weaker timeout behavior.

The deterministic header-trickle fixture uses a socket pair and the real HTTP
header parser. It supplies bytes faster than the inactivity timeout but needs
two seconds to finish the headers. Before repair, the one-second-budget check
returned after 2.036 seconds; after repair, it returned a budget failure in
1.002 seconds, with connection/socket closure, alarm restoration, and the
bounded fixture producer joined. Additional tests verify handler/timer
restoration after success and provider failure, preservation of an existing
periodic alarm, and off-main rejection with zero credential/network calls.

Repair validation: Python 3.12.13 focused GitHub suite — 45 tests passed in
2.557 seconds. Compile checks and `git diff --check` passed. Per the primary's
repair closeout instruction, comprehensive Python and plugin tiers are reserved
to the primary; the earlier 323-test result predates this repair and is not
presented as post-repair comprehensive evidence. No additional files, provider
calls, commits, pushes, or live effects were introduced by the repair.

### Primary acceptance and read-only qualification

Closed-world verification by `/root/p50_i34_review` reproduced and closed both
accepted findings. Exact `head_repository` binding rejects missing and fork
origins at list and attempt boundaries. The header-trickle deadline now stops,
closes resources, restores signal state, preserves an already-owned alarm by
failing closed, and rejects off-main use before credentials or network.

Post-repair primary validation passed:

- Python 3.12.13 comprehensive: 327 tests in 10.188 seconds;
- Python 3.11.15 comprehensive: 327 tests in 10.524 seconds;
- focused GitHub polling/client/config/webhook selection: 45 tests in 3.191
  seconds;
- OpenClaw plugin: 12 tests passed;
- both plugin JavaScript entrypoint syntax checks, `compileall`, and
  `git diff --check` passed.

The bounded live qualification used the production `GitHubRestClient` with an
in-memory resolver for the already-authenticated `gh` profile; no credential
value was printed, persisted, or passed in process arguments. It performed only
the fixed GitHub GET routes against repository ID `1242753508` and workflow ID
`279450573`. The client listed ten runs and exact-read run
`34920248569`, attempt 1, branch `refs/heads/main`, SHA
`9e9cd3caf5330394a4c8299ee72d1e22e1d3962f`, completed/success, with
`terminal_proof_at=2026-09-15T02:12:42Z` and provenance
`github_attempt_started_or_job_completed_lower_bound`. The receipt explicitly
records `coverage=positive_only` and `checkpoint_advanced=false`.

Issue #34 acceptance is ready for integration. This does not claim a daemon,
CLI, persistent on-disk source registry, webhook production convergence,
installed runtime, dispatch, or complete GitHub history; those remain owned by
issues #35 through #37.
