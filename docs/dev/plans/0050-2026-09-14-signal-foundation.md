# Signal foundation

State: OPEN
Lane: P48-G1-I4
Owner: ecochran76
Work Item: CochranResearchGroup/codex-wake#4
Branch: feat/issue-4-signal-foundation
Target: origin/main
Integration: squash pull request
Base: 5b5d52943e7ba154eb4c1e0516cc7a0274403715

## Current state

Checkpoint `P48-G1-C00` opens issue #4 from the accepted Plan 0049 baseline.
The branch contains no runtime implementation yet. Existing schema-version-1
JSON records remain the only implemented wake format, and no live provider or
dispatch effect is authorized.

CodeGraph is healthy at 71 indexed files, 1,544 nodes, and 4,503 edges. The
current creation path enters through `cli.create_record`, while
`records.build_record` has 23 callers. `daemon.poll_once` owns the transition
to firing and calls `records.move_record`; the new signal module must preserve
those caller and dispatch contracts.

Graphiti is healthy but returned no P48-specific implementation evidence. The
current repository, issue, tests, Git refs, and CodeGraph readback are the
authoritative inputs.

## Packet 4A objective

Establish the smallest provider-neutral signal interface and one test-first,
in-memory registration-to-match trace. The interface must support versioned
registration, arm publication, normalized observation ingestion, bounded
evaluation, stable match reservation, sanitized evidence, and schema-v1
compatibility without provider or live-dispatch behavior.

## Interface constraints

The module exposes caller registration plus the internal `arm`, `ingest`, and
`evaluate` seam described by Plan 0049 and the product vision. Its observable
results distinguish matched, not ready, degraded, invalid, and expired states.
The implementation owns normalization, deduplication, anchoring, matching,
reservation, and evidence shaping; source-specific payloads stay behind source
adapters.

## Interface decision

Three read-only `gpt-5.6-sol` high-effort challenges compared a minimal
interface, an extensible kernel, and an ordinary-caller-first facade. The
primary accepts a hybrid with two layers:

- `EventWake.register(intent, idempotency_key)` is the only ordinary caller
  entry point. It selects a configured source adapter and does not expose
  anchors, receipts, checkpoints, or publication internals.
- `WakeSignalModule.arm`, `ingest`, and `evaluate` remain the explicit internal
  seam for registration orchestration, source runners, and the future daemon
  bridge.

Both layers return immutable closed outcomes. Registration distinguishes a
published registration, retryable degradation, and permanent invalidity.
Evaluation distinguishes `Matched`, `NotReady`, `Degraded`, `Invalid`, and
`Expired`. Provider exceptions and payloads never cross the adapter seam.

Packet 4A uses a single `signals.py` module until a second production adapter
justifies a package split. It injects an in-memory store and scripted source
adapter, uses synchronous methods that match the existing daemon, and leaves
SQLite, JSON publication, and provider runners for later packets.

Logical observation identity is
`(source, source_instance, occurrence_namespace, occurrence_value)`. A provider
delivery ID is optional transport evidence, not the cross-transport identity.
This lets later GitHub polling and webhook adapters converge on one workflow
run-attempt occurrence. Identical redelivery returns the original receipt;
conflicting immutable content under the same identity is invalid and does not
advance a checkpoint.

Packet 4A does not write signal-bearing wake JSON. The accepted compatibility
direction for Packet 4C is a capability-gated schema-version-2 signal record,
with multi-version readers retaining schema-version-1 behavior. A writer must
refuse signal registration when the installed reader lacks that capability.

The in-memory trace enforces these ordering rules:

1. Validate and canonicalize intent before mutation.
2. Establish an unambiguous source anchor before an arm becomes published.
3. Commit a complete sanitized observation batch before reporting checkpoint
   advancement.
4. Order eligibility by local sequence strictly after the anchor, never by
   provider time.
5. Reserve the lowest eligible winner before returning `Matched`; evaluation
   replay returns the same reservation.
6. Preserve one winner per wake while allowing bounded fan-out from one receipt
   to independent wakes.

The minimal design's removal of callable `arm` is rejected because the
accepted vision needs that internal seam for recoverable publication. The
extensible design's early `WakePublisher` and delivery-adapter ports are
deferred because Packet 4A cannot yet prove two implementations. Source-store
serialization and lease ownership remain a Packet 4B decision at the SQLite
transaction seam.

## Test-first sequence

Each step is one red-green vertical slice through a public interface:

1. Register one valid occurrence signal idempotently and return the same stable
   registration on replay.
2. Publish an armed signal only after its baseline or anchor exists.
3. Ingest a normalized observation, deduplicate its stable occurrence identity,
   and keep stored evidence bounded and sanitized.
4. Evaluate the armed signal to one stable match reservation; replaying the
   observation or evaluation cannot create a second winner.
5. Return explicit not-ready, degraded, invalid, and expired outcomes without
   raising provider-specific exceptions.
6. Demonstrate that existing schema-version-1 record readers and predicates
   remain valid when signal support is absent or unused.

## Packet boundaries

Packet 4A may add the provider-neutral signal module, types, in-memory adapter,
and focused contract tests. It must not add SQLite persistence, JSON outbox
publication, daemon integration, provider adapters, filesystem watchers,
GitHub access, public ingress, live dispatch, installed-runtime mutation,
deployment, or release behavior.

Packet 4B will add SQLite authority, source anchors, deduplication,
checkpoints, reservations, retention pins, and bounded evaluation progress.
Packet 4C will add the recoverable JSON outbox, daemon seam, inspection,
corruption handling, and fresh-process crash tests.

## Acceptance and stop conditions

Packet 4A is accepted when focused public-interface tests prove one complete
provider-free registration-to-match trace, the existing suite remains green,
and review finds no unresolved shared-interface or schema-v1 blocker.

Stop and return the interface decision to the primary when provider-specific
logic reaches the signal module, a proposed interface requires callers to know
journal internals, schema-v1 behavior changes, or the first two bounded
implementation attempts cannot pass the same acceptance check.

## Next action

Packet 4A is complete. It was split after two bounded implementation work
units into Packet 4A.2 for primary-owned acceptance hardening rather than
resetting the attempt count.

Three read-only interface challenges completed under
`/root/p48_i4_minimal`, `/root/p48_i4_extensible`, and
`/root/p48_i4_caller_first`. One implementation worker then completed ten
registration, ingestion, and evaluation contract tests. The primary accepted
its core behavior and added six tests for immutable evidence, storage and
projection bounds, observation-contract enforcement, bounded `in`, source
isolation, and fan-out.

Validation on Python 3.12.13 passed:

```text
PYTHONPATH=src python -m unittest tests.test_signals
Ran 16 tests in 0.002s - OK

PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
Ran 198 tests in 1.391s - OK

npm --prefix plugins/openclaw-codex-wake test
12 passed, 0 failed

python -m compileall -q src tests
PASS
```

Packet 4A changed only the signal module, caller facade, contract tests, this
plan, and the logical-identity wording in the product vision. Existing wake
records, daemon behavior, CLI commands, plugins, and dispatch transports are
unchanged.

The next action is Packet 4B: design and implement the SQLite journal at the
accepted signal seam, including transactional arm preparation, observation
deduplication, monotonic checkpoints, match reservations, retention pins, and
bounded evaluation progress. Packet 4C and every source adapter remain
blocked.
