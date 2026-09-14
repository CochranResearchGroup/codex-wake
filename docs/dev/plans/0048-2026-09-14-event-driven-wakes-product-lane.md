# Event-Driven Wakes Product Lane

State: CLOSED
Lane: P48
Owner: ecochran76
Work Item: CochranResearchGroup/codex-wake#2
Branch: docs/p48-event-driven-wakes-vision
Target: main
Integration: pull-request

## Scope

Record the full product direction for safe provider-neutral event-driven wakes
and establish the collaboration prerequisites for later implementation lanes.

This slice adds:

- the evergreen event-driven wakes architecture and product vision;
- the roadmap entry and bounded delivery sequence;
- the GitHub issue target registry and initial active-lane catalog;
- a repo-local collaborative-development policy;
- concrete issue, branch, pull-request, subagent, and model-routing rules; and
- a reviewed child-issue decomposition for later publication.

## Non-goals

This slice records and governs the product direction. It does not implement or
release signal runtime behavior.

- Do not change the wake schema or runtime code.
- Do not create implementation child issues before the user reviews the
  proposed vertical slices.
- Do not start filesystem, GitHub, webhook, or migration implementation lanes.
- Do not expose a webhook listener or perform a live wake dispatch.
- Do not publish a release or alter the installed Codex Wake runtime.

## Current state

Codex Wake currently evaluates `not_before`, `file_exists`, `file_changed`, and
`process_done` predicates inside the polling daemon. The existing dispatch
state machine and JSON wake records are stable product seams.

The installed policy bundle is `v0.1.26`, and no newer published bundle was
available at lane start. The repo already carried issue, work-item, active-lane,
subagent, and model-calibration semantics, but `AGENTS.md` referenced missing
policy paths `0021` through `0048`. This slice removes those invalid pointers
and adopts a concrete collaborative-development policy.

GitHub issue `CochranResearchGroup/codex-wake#2` is the accountable work item
for this vision slice. No overlapping open issue or pull request existed at
creation time.

## Architecture decision

Use a caller-first registration interface over a provider-neutral signal
module. Ordinary callers register safe versioned recipes. The internal module
owns `arm`, `ingest`, and `evaluate`; provider adapters own authentication,
normalization, replay, and verification.

Preserve JSON wake records as the durable agent-facing contract. Use a
user-scoped SQLite signal journal for transactional receipts, deduplication,
source checkpoints, match reservations, and retention pins. Copy a bounded
sanitized match summary into the firing wake record.

Bridge SQLite arming authority and JSON publication with a recoverable outbox:
persist a `prepared` arm and stable identity, atomically publish the JSON record,
then finalize the arm as `published`. Only published arms can match. Startup
reconciliation completes JSON-backed prepared arms and fails closed on missing
or corrupt cross-store state.

Treat filesystem notifications and GitHub webhooks as latency hints. Use
restart reconciliation or provider polling as correctness authority whenever
the source can reconstruct current state or replay history.

The complete decision, invariants, failure model, adapter roadmap, and product
success criteria live in [Event-driven wakes](../../event-driven-wakes.md).

## Multi-agent execution contract

This product lane uses `balanced` execution. The primary owner retains the
shared contract, architecture, safety, dependency graph, integration, and final
acceptance claim.

Future plans may use up to three concurrent subagents for disjoint adapters,
fixtures, documentation, or verification. They must not fan out implementation
until the shared signal contract, storage authority, compatibility path, and
contract tests are accepted.

Each consequential delegated run records its handle, bounded scope, status,
evidence, requested and effective model when available, and the primary
reconciliation decision. Nested subagents are off by default.

## Design comparison receipt

Three read-only subagents produced independent interface designs under the
`Design It Twice` workflow.

| Handle | Constraint | Status | Reconciliation |
| --- | --- | --- | --- |
| `/root/minimal_interface` | Limit the signal module to one to three entry points. | Completed | Accepted `arm`, `ingest`, and `evaluate` as the internal seam. |
| `/root/extensible_interface` | Maximize future source and semantic extensibility. | Completed | Accepted explicit occurrence/state semantics, closed results, source contracts, and SQLite reservations. |
| `/root/caller_first_interface` | Make common CLI and plugin registration trivial. | Completed | Accepted a single public `register(intent, idempotency_key)` interface and safe recipe vocabulary. |

All three workers were read-only. They inherited the session model request;
the runtime did not report a separate effective model or token/cost receipt.
The primary owner reconciled the outputs without delegating the final decision.
This comparison is design evidence, not a formal model-calibration result.

## Independent review receipt

A fresh read-only review used `/root/vision_doc_review` with requested model
`gpt-5.6-luna` at medium reasoning. The runtime did not report a separate
effective-model receipt. The reviewer returned four actionable findings: add
workflow identity to the GitHub filter, define cross-store publication and
recovery, name the accountable owner, and record policy-adoption feedback. The
primary owner accepted and corrected all four findings, then retained final
validation and integration authority.

## Published child issue map

The user approved the tracer-bullet decomposition on 2026-09-14. The issues
were published in dependency order and read back from GitHub.

1. [**#4 Establish the signal contract and crash-safe journal.**](https://github.com/CochranResearchGroup/codex-wake/issues/4) Add multi-version
   reader groundwork, safe registration, bounded matching, SQLite receipts,
   deduplication, reservations, inspection, and provider-free restart tests.
   This is the critical-path blocker for every later slice.
2. [**#5 Preserve existing predicates behind the signal evaluation seam.**](https://github.com/CochranResearchGroup/codex-wake/issues/5) Route
   time, file-exists, file-changed, and process-done behavior through the new
   module without changing user-visible semantics.
3. [**#6 Deliver restart-correct filesystem wakes.**](https://github.com/CochranResearchGroup/codex-wake/issues/6) Add notification acceleration,
   registration fingerprints, startup and overflow reconciliation, evidence,
   CLI recipes, and end-to-end no-dispatch tests. This depends on slices 1 and 2.
4. [**#7 Deliver GitHub CI wakes through authoritative polling.**](https://github.com/CochranResearchGroup/codex-wake/issues/7) Add explicit repository and
   workflow allowlists, least-privilege credentials, provider checkpoints,
   fixtures, current-state verification, CLI recipes, and bounded optional live
   read evidence. This depends on slice 1.
5. [**#8 Converge signed GitHub webhooks with polling.**](https://github.com/CochranResearchGroup/codex-wake/issues/8) Add authenticated ingress,
   delivery deduplication, acknowledgement-after-commit, replay reconciliation,
   event-storm containment, and an opt-in live smoke. This depends on slice 4.
6. [**#9 Productize signal readiness and lifecycle.**](https://github.com/CochranResearchGroup/codex-wake/issues/9) Extend doctor, monitor,
   product-readiness, evidence export, retention, cleanup, migration, downgrade,
   packaging, and public-install smoke across filesystem and GitHub sources.
   This depends on slices 3 through 5.
7. [**#10 Calibrate multi-agent and model routing for signal work.**](https://github.com/CochranResearchGroup/codex-wake/issues/10) Run a bounded comparison across
   representative adapter, fixture, and verification work. Record accepted
   outcomes, defects, interventions, elapsed time, and allocation proxies before
   changing repo defaults. This depends on completed implementation samples.

## Dependency and ownership model

The shared contract and storage slice has one coordination owner. Filesystem and
GitHub polling may proceed in parallel only after that slice is accepted.
Webhook work follows GitHub polling. Productization joins the completed source
lanes. Calibration observes representative completed work and cannot block
correctness fixes.

Each child issue names one accountable owner, affected surface, future branch,
plan locator, dependencies, overlaps, acceptance evidence, and live effect.
Every substantive branch will appear in the default-branch active-lane catalog
before parallel implementation begins.

## Closeout receipt

Pull request [#3](https://github.com/CochranResearchGroup/codex-wake/pull/3)
merged the vision and governance foundation into `origin/main` as
`46dcb9a60c8af497009470cc76edbea40471ec05` after the Python 3.11 and 3.12
release gates passed. The user then approved the seven-slice decomposition.

Issues #4 through #10 were created with stable idempotency markers, assigned to
`ecochran76`, labeled `enhancement`, marked `READY` in their bodies, linked to
parent issue #2 and this plan, and read back with their concrete dependencies.
No implementation branch was opened and no provider, dispatch, install, or
release effect occurred.

## Validation plan

This documentation slice uses deterministic and review checks rather than
runtime tests.

- Run the active planning audit and goal-policy audit.
- Run the active-lane audit against the proposed branch state.
- Run the policy selector test suite affected by the adopted policy and wiring.
- Verify internal documentation links and `git diff --check`.
- Review the published pull-request diff, base, issue link, and GitHub CI result.
- Record remote branch and pull-request readback before handoff.

## Acceptance criteria

The vision slice is acceptable when all of these statements are true.

- The product vision distinguishes occurrences, held state, and state
  transitions.
- The architecture defines caller, signal-module, adapter, storage, matcher,
  evidence, recovery, privacy, authority, and compatibility contracts.
- The roadmap names independently verifiable vertical delivery slices.
- The repo has an explicit GitHub issue target and an accountable parent issue.
- The repo has a valid active-lane catalog ready for future concurrent work.
- Collaborative issue, branch, pull-request, CI, merge, subagent, and model
  optimization rules are wired from `AGENTS.md`.
- Three independent interface designs are reconciled with a durable receipt.
- The child issue map is presented to the user before publication.
- The branch, pull request, validation, and remaining integration state are
  read back exactly.

## Definition of done

This plan is closed: the documentation and governance change merged through
pull request #3, GitHub issue #2 records the merged outcome, and approved child
issues #4 through #10 are ready to govern implementation. Roadmap lane P48 is
`READY`; issue #4 is the next critical-path work item to claim.
