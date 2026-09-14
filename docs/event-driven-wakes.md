---
last_updated: 2026-09-14
status: foundation-in-progress
applies_to: post-v0.5.2 product development
---

# Event-driven wakes

Event-driven wakes will let you resume an agent when a meaningful local or
external condition occurs. The design preserves Codex Wake's durable records,
inspectable evidence, bounded delivery, and narrow resume authority while
supporting filesystem, GitHub, runtime, data, monitoring, and human signals.

> **Implementation note:** The provider-neutral contract, in-memory engine,
> SQLite journal, capability-gated schema-v2 record projection, daemon seam,
> bounded inspection, and fresh-process recovery proof are implemented on the
> issue #4 delivery lane. Filesystem and GitHub adapters, webhook ingress, and
> product-facing recipes remain later work; no provider or live-dispatch proof
> is claimed here.

## Product outcome

You will be able to describe when work should resume without choosing a polling
loop, webhook server, provider cursor, or operating-system watcher.

Examples include:

- resume when a file appears or its observed state changes;
- resume when a GitHub workflow succeeds, fails, or completes;
- resume when a pull request merges or receives a requested review;
- resume when a local process, unit, socket, or mount changes state;
- resume when a governed job, queue, data record, or artifact becomes ready;
- resume when a monitoring alert opens or resolves; and
- resume when an authorized human approval or communication event arrives.

The event only authorizes Codex Wake to resume the recorded target. It does not
authorize the resumed agent to mutate a repository, provider, tenant, runtime,
or live system.

## Product principles

The signal substrate extends the existing wake state machine instead of
replacing it.

- Wake intent remains declarative data. Records contain no shell commands,
  callbacks, arbitrary code, credentials, or user-defined network queries.
- Every armed wake is durable before Codex Wake promises that it is monitored.
- Notifications improve latency. Reconciliation and authoritative state checks
  provide correctness whenever the source supports them.
- Ingestion is at least once. Deduplication, matching, and wake transitions are
  idempotent.
- Source outages, rate limits, stale observations, and verification gaps fail
  closed without creating a false match.
- Provider details remain inside adapters. The daemon does not learn GitHub,
  filesystem-watcher, Slack, queue, or monitoring payload formats.
- Evidence explains why a wake fired without retaining secrets or unnecessary
  private payloads.
- Compatibility is explicit. Writers do not create signal records until the
  installed reader advertises the required capability.

## Signal semantics

The contract distinguishes current state from an occurrence that may disappear
after delivery. This distinction controls restart and replay behavior.

| Semantics | Condition | Meaning | Recovery |
| --- | --- | --- | --- |
| `occurrence` | `occurs` | A qualifying receipt arrived after registration. | Replay a durable receipt from the local journal or provider history. |
| `state` | `holds` | A verified condition is currently true. | Recheck the authoritative source. |
| `state` | `becomes` | A condition changed from false or unknown to true after registration. | Compare the registration baseline with a later verified revision. |

Filesystem notifications cannot promise that every write occurrence survives a
host outage. A portable `file.changes` wake therefore means that the observed
file fingerprint differs from its registration baseline. The evidence must say
when several writes may have been coalesced.

GitHub webhooks are delivery hints. A GitHub wake that requires verification
fires only after the adapter confirms the relevant workflow, check, pull
request, or deployment state through the authoritative provider interface.

## Architecture

The architecture separates caller intent, signal correctness, source-specific
behavior, and the existing dispatch state machine.

```text
CLI or plugin caller
        |
        v
register safe wake intent
        |
        v
provider-neutral signal module <---- source adapters
        |                               | filesystem notifications
        |                               | GitHub polling and webhooks
        |                               | future governed sources
        v
durable match reservation and evidence
        |
        v
existing pending -> firing -> submitted workflow
        |
        v
tmux, Codex app-server, or OpenClaw Gateway dispatch
```

### Caller interface

Ordinary callers use one deep interface. They describe intent and receive a
durable registration result.

```python
registration = event_wake.register(
    WakeIntent(
        when=GitHubCIFailed(
            repository="CochranResearchGroup/codex-wake",
            ref="refs/heads/main",
            workflow="CI",
        ),
        resume=Resume(
            prompt="Diagnose the failed release gate.",
            target=current_session(),
        ),
    ),
    idempotency_key="release-gate-watch",
)
```

`register` resolves shorthand, validates source policy, captures a baseline or
cursor, reserves the idempotency key, and durably publishes the wake. Its result
states what subject was armed and what recovery guarantee is available.

The CLI can expose safe recipes without exposing the internal receipt schema:

```bash
codex-wake when file changes ./build/result.json -- "Inspect the new result."

codex-wake when github-ci fails \
  --repo CochranResearchGroup/codex-wake \
  --ref refs/heads/main \
  --workflow CI \
  -- "Diagnose the failed release gate."
```

### Signal module interface

Wake creation, source runners, and the daemon meet at one internal seam with
three operations.

```python
class WakeSignalModule:
    def arm(self, wake_id, spec, context) -> ArmResult: ...
    def ingest(self, observations, source_commit) -> IngestResult: ...
    def evaluate(self, wake_id, armed_signal, now, limits) -> Evaluation: ...
```

This deep module hides normalization, local sequencing, deduplication, source
checkpoints, matching, authoritative verification, retention pins, match
reservations, and crash recovery. The interface is also the primary contract
test surface.

`evaluate` returns a closed result instead of provider exceptions:

- `Matched` carries a stable match token, sanitized receipt summary, and
  evidence reference.
- `NotReady` reports healthy progress and the next useful check.
- `Degraded` reports retryable source, authentication, freshness, rate-limit,
  or budget conditions while leaving the wake pending.
- `Invalid` identifies a permanent malformed or unsupported signal.
- `Expired` maps to the existing wake expiry transition.

The signal module owns an idempotent reservation for the winning observation.
The existing daemon owns the recoverable move to `firing`, and the existing
dispatch implementation continues to own delivery and acknowledgement.

### Source adapter interface

Source-specific behavior sits behind an internal adapter seam. Filesystem,
GitHub, and an in-memory test adapter justify this seam from the first delivery
slices.

```python
class SignalSourceAdapter:
    def contract(self) -> SourceContract: ...
    def establish_anchor(self, spec, now, budget) -> SourceAnchor: ...
    def observe(self, request, checkpoint, budget) -> ObservationBatch: ...
```

A source contract declares allowed event kinds, subjects, sanitized fields,
types, semantics, replay strength, verification capability, size limits, and
sensitivity. Authentication, webhook signatures, pagination, provider cursors,
rate limits, payload redaction, and provider retries stay in the adapter.

## Declarative signal contract

One versioned signal family supports future adapters without adding a daemon
branch for each provider.

```json
{
  "type": "signal",
  "contract_version": 1,
  "source": "github",
  "source_instance": "github-com-codex-wake",
  "semantics": "occurrence",
  "kind": "workflow_run.completed",
  "subject": "repo:CochranResearchGroup/codex-wake",
  "condition": "occurs",
  "where": {
    "all": [
      {"field": "workflow", "op": "eq", "value": "CI"},
      {"field": "branch", "op": "eq", "value": "main"},
      {
        "field": "conclusion",
        "op": "in",
        "value": ["failure", "cancelled", "timed_out"]
      }
    ]
  },
  "registration": {
    "registered_at": "2026-09-14T14:00:00Z",
    "local_after_sequence": 814,
    "source_anchor": "opaque-nonsecret-anchor"
  },
  "verification": "required"
}
```

The first contract supports exact source, instance, kind, and subject routing.
Filters support bounded `eq` and `in` operations over adapter-declared scalar
fields. The matcher enforces limits for clause count, list size, attribute
bytes, candidate receipts, and evaluation time.

The contract does not support regular expressions, JSONPath, arbitrary Boolean
programs, dynamic URLs, callbacks, shell commands, Python, or provider queries
written by wake callers.

## Durable observation contract

Adapters normalize authenticated source data before the signal module stores
it. The journal never becomes a raw provider-payload archive.

```json
{
  "schema_version": 1,
  "receipt_id": "event_000000000815",
  "source": "github",
  "source_instance": "github-com-codex-wake",
  "kind": "workflow_run.completed",
  "subject": "repo:CochranResearchGroup/codex-wake",
  "provider_delivery_id": "github:delivery:abc123",
  "occurred_at": "2026-09-14T14:05:00Z",
  "observed_at": "2026-09-14T14:05:03Z",
  "local_sequence": 815,
  "attributes": {
    "workflow": "CI",
    "branch": "main",
    "conclusion": "failure",
    "run_id": 12345
  },
  "verification": {
    "state": "verified",
    "method": "github-api"
  },
  "evidence_ref": "events/evidence/event_000000000815.json"
}
```

The stable logical deduplication key is the source, source instance, and an
adapter-declared occurrence namespace plus occurrence value. Polling and push
adapters for one source must emit the same logical identity for the same
occurrence. A provider delivery ID may be retained as bounded transport
evidence, but it is not the cross-transport identity. Every adapter must
declare and test its deterministic identity and collision domain.

Provider timestamps are evidence. The local monotonic sequence determines
journal ordering.

## Runtime state and storage

Wake records remain JSON because they are the durable agent-facing and operator-
facing contract. A user-scoped SQLite signal journal owns transactional event
runtime state.

The journal stores:

- normalized receipts and deduplication keys;
- local sequences and provider checkpoints;
- registration anchors and state baselines;
- source health, leases, and bounded retry state;
- wake-to-receipt match reservations; and
- retention pins for active wakes and selected evidence.

SQLite lets receipt insertion, deduplication, checkpoint advancement, and match
reservation commit atomically. JSON exports may provide human-readable evidence,
but they do not become a second live authority.

### Cross-store publication protocol

Registration crosses the SQLite runtime authority and the JSON wake-record
contract, so `register` uses a recoverable outbox protocol rather than implying
an impossible transaction across both stores.

1. In one SQLite transaction, reserve the caller's idempotency key and stable
   wake ID, persist the source anchor, and create an arm row in `prepared` state.
2. Atomically write and rename the pending JSON wake record with the stable wake
   ID, arm ID, contract version, and source anchor.
3. In a second SQLite transaction, verify the published record identity and
   advance the arm row to `published`.
4. Return a successful registration only after the arm is `published`. Only
   published arms are eligible for observation matching.

Startup reconciliation completes interrupted registrations deterministically.
A `prepared` row with its matching JSON record is finalized to `published`. A
`prepared` row without JSON remains ineligible and retryable through the same
idempotency key until bounded expiry, after which it is tombstoned. A JSON wake
whose arm row is missing or corrupt remains pending with
`ARM_STATE_UNAVAILABLE` degradation evidence and cannot match. The runtime does
not reconstruct live authority from JSON unless a future version defines and
tests an explicit recovery contract for doing so.

This protocol makes the SQLite arm row authoritative for eligibility while the
JSON record remains authoritative for the agent-facing wake intent and state.
Neither store can independently cause a signal wake to fire.

When a signal matches, the daemon copies a bounded `trigger_match` summary,
receipt ID, verification state, and evidence reference into the wake record.
Archived wake records therefore remain explainable after journal compaction.

## Correctness and recovery

The implementation must preserve the following ordering rules across process
and host restarts.

1. `arm` validates the signal and establishes an unambiguous baseline or replay
   anchor before publishing the pending wake.
2. An adapter authenticates or verifies a delivery before normalization.
3. `ingest` commits sanitized receipts before acknowledging a webhook or
   advancing the provider checkpoint.
4. Redelivery returns the original receipt as a successful duplicate.
5. `evaluate` considers only committed observations after the wake's anchor.
6. `evaluate` reserves one winning observation for the wake before returning
   `Matched`; a retry returns the same reservation.
7. The daemon records the match before moving the wake to `firing`.
8. Existing firing recovery and bounded dispatch retry continue unchanged.
9. Retention never removes an active anchor or a receipt pinned by a match.

One observation may match several independently armed wakes within configured
fan-out limits. Each wake fires at most once. Consumption by one wake does not
silently hide the observation from another.

## Security, privacy, and authority

Every source must have an explicit instance configuration and allowlisted
scope. A source adapter cannot infer permission from an accessible credential.

The runtime must enforce these requirements:

- keep credentials, tokens, webhook secrets, signatures, and raw provider
  bodies out of wake records and normalized receipts;
- verify webhook signatures before acknowledging or storing an observation;
- use least-privilege provider credentials and explicit repository, channel,
  queue, tenant, or resource allowlists;
- bound payload size before parsing and bound normalized attribute size before
  storage;
- quarantine or reject unauthenticated, malformed, oversized, disallowed, or
  unsupported deliveries with sanitized diagnostics;
- keep private communication bodies in their governed source system and store
  only stable selectors plus evidence references;
- separate event observation authority from the resumed agent's mutation
  authority; and
- require idempotent wake prompts that recheck whether the requested outcome is
  already complete.

Webhook ingress must begin as localhost or an authenticated owned relay. Public
exposure requires a separate threat model, transport-authentication decision,
rate-limit design, and live deployment gate.

## Failure and degradation behavior

Transient source problems remain inspectable signal health, not new wake
statuses. The existing wake status vocabulary stays small.

| Condition | Required behavior |
| --- | --- |
| Duplicate delivery | Return the original receipt as a successful no-op. |
| Provider unavailable | Keep the wake pending and retry with bounded backoff. |
| Authentication unavailable | Mark the source degraded without exposing credential detail. |
| Rate limited | Preserve the checkpoint and honor the provider retry window. |
| Verification pending | Keep the observation ineligible until verified or expired. |
| Invalid signal specification | Reject registration or fail a corrupted pending record visibly. |
| Journal corruption | Fail closed for the affected source and require operator repair. |
| Watcher overflow or restart | Reconcile current state and label any coalesced recovery evidence. |
| Provider history gap | Keep affected wakes pending or expire them; never infer a match. |
| Evaluation budget exhausted | Yield with progress and resume from the durable checkpoint. |

## Operator experience

Operators need one inspection surface that separates wake state, source health,
and observation evidence.

The eventual command family should cover these outcomes:

- list available source instances and their capabilities;
- check whether a source can safely arm a proposed signal;
- inspect source health, last successful checkpoint, and replay lag;
- show which receipt and verification caused a wake to fire;
- list quarantined sanitized diagnostics without displaying raw payloads;
- export bounded event evidence for support or audit; and
- compact the journal only after active anchors and match pins are protected.

`doctor`, `monitor check`, and `product-readiness` must report signal-substrate
capability separately from target-dispatch readiness. A ready tmux or app-server
target does not prove that GitHub or filesystem observation is healthy.

## Source roadmap

The source sequence proves recovery and provider abstraction before expanding
the catalog.

| Order | Source slice | Product proof |
| --- | --- | --- |
| 1 | Provider-free signal module | Arm, ingest, deduplicate, match, reserve, restart, and inspect through deterministic tests. |
| 2 | Existing predicate compatibility | Route current time, file, and process behavior through the seam without semantic drift. |
| 3 | Filesystem state adapter | Use notifications for latency and reconciliation for restart or overflow correctness. |
| 4 | GitHub workflow polling | Verify workflow results with fixtures and a bounded optional live read. |
| 5 | Signed GitHub webhook ingress | Reduce latency while converging with polling through the same receipt identity. |
| 6 | Local runtime sources | Add process, systemd, socket, mount, and health transitions through declared contracts. |
| 7 | Governed data and human sources | Add queues, artifacts, approvals, monitoring, and communications only with source-specific privacy and authority rules. |

## Multi-agent delivery model

The shared signal contract remains on the critical path. Adapter work begins in
parallel only after that contract, storage authority, compatibility strategy,
and contract tests are accepted.

GitHub Issues provide the coordination ledger. Each implementation slice has
one accountable owner, one short-lived branch, one bounded plan when needed,
and one pull request. The default-branch active-lane catalog records concurrent
branch custody without copying issue bodies.

The product lane uses a `balanced` execution bias:

- keep one primary owner for architecture, shared schemas, safety decisions,
  issue dependencies, integration, and completion claims;
- use no more than three concurrent subagents within a lane;
- prefer disjoint adapter, fixture, documentation, and validation write scopes;
- avoid nested subagents unless a plan names the orchestrator, child scopes,
  result flow, and cancellation behavior;
- record consequential run handles, status, evidence, and reconciliation in the
  plan or pull request; and
- stop parallel work when shared-contract uncertainty would make adapters invent
  competing semantics.

## Model selection and calibration

Model routing optimizes total allocation per accepted product slice while
preserving correctness and delivery time.

| Task tier | Default routing | Required evidence |
| --- | --- | --- |
| Deterministic or mechanical | Tools first, then an economical model only if judgment is needed. | Exact inputs, transformation output, and deterministic check. |
| Bounded implementation | Calibrated standard model and reasoning level. | Focused contract tests plus affected integration checks. |
| Architecture, security, or causality | Primary owner or a bounded specialist consultation. | Named decision, alternatives, constraints, and acceptance consequence. |
| Independent verification | Fresh context with a frozen review packet. | Candidate findings tied to criteria, evidence, and disposition. |

Calibration compares complete workflows, not isolated answers. A sample records
the task identity, requested and effective model when known, reasoning level,
context, topology, accepted outcome, defects, interventions, elapsed time, and
total allocation or a labeled proxy.

The lane promotes the least costly routing that meets frozen quality and time
requirements. Model changes, retries, worker replacement, and repair remain in
the same cumulative accounting window.

## Compatibility and release strategy

The signal writer must not outrun installed readers. The first implementation
slice will choose and test one explicit compatibility path.

The preferred path introduces multi-version read support before any signal
writer ships. Existing schema-version-1 wake records and predicates remain
valid. Signal-bearing wake records use the selected new wake schema or an
explicit capability marker only after older-runtime behavior, migration,
downgrade, mixed-version supervisor operation, and release notes are defined.

The signal journal has its own schema and migration sequence. Runtime upgrades
must back up or transactionally migrate the journal, preserve deduplication and
checkpoint identity, and expose repair guidance for interrupted migrations.

Each source release requires provider-free contract evidence. Live provider or
dispatch smokes are separate opt-in evidence and do not replace deterministic
tests.

## Non-goals

The product lane deliberately excludes several tempting extensions.

- arbitrary shell-command predicates;
- raw JSON event-bus access for ordinary callers;
- user-authored callbacks, regular expressions, JSONPath, or executable filters;
- webhook-only correctness without polling or reconciliation;
- public webhook exposure in the first implementation slice;
- automatic authorization of actions after an event wakes an agent;
- storage of raw private messages or provider payloads as wake evidence;
- exactly-once delivery claims across external providers; and
- a universal distributed event broker before local and GitHub adapters prove
  the module seam.

## Product success

The product lane succeeds when a clean installation can safely arm, observe,
fire, inspect, restart, and retire event-driven wakes across local filesystem
and GitHub CI sources.

Completion requires all of these outcomes:

- a stable provider-neutral signal contract and bounded matcher;
- crash-safe deduplication, checkpoints, match reservations, and retention;
- preserved behavior for existing wake predicates and dispatch transports;
- restart-correct filesystem observation with documented coalescing limits;
- GitHub polling plus signed-webhook convergence with current-state
  verification;
- source health and trigger evidence in operator inspection and readiness;
- schema compatibility, migration, release, and downgrade evidence;
- independently mergeable GitHub issues and pull requests with verified remote
  custody; and
- measured subagent and model-routing results for representative delivery
  slices.

## Next steps

Implementation starts only after the shared contract becomes an approved issue
slice. Track the current vision work in
[GitHub issue #2](https://github.com/CochranResearchGroup/codex-wake/issues/2)
and the [event-driven wakes product-lane plan](dev/plans/0048-2026-09-14-event-driven-wakes-product-lane.md).
