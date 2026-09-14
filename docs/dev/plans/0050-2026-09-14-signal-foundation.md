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

Publish this checkpoint, register the branch in the active-lane catalog, and
run three bounded read-only interface challenges before writing the first
failing test. The primary will reconcile those alternatives and retain the
final shared interface decision.
