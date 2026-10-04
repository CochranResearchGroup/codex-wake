# Exact operator receipt projection acknowledgement

Parent: Plan 0113 / Plan 0101 / issue #181.
Baseline: b0684e31c1777d10d03789dbac7a38dde7f57e96.

## Initial red feedback and repair history

Command: PYTHONPATH=src python3 -m unittest tests.test_a2a_projection_ack -q.
Initial three cases failed: missing MailOperations.acknowledge_projections and
CLI invalid choice ack-projections. First implementation passed 53 focused and
841 comprehensive tests (52.772s). No effect authority was inferred from a
source checkpoint or observer grant alone.

One targeted malformed-proof repair episode: non-object outbox JSON escaped
as AttributeError at intent.get; malformed JSON decoder failures also needed
typed handling. Added shared normalization errors receipt_corrupt. Its focused
red probe failed before the proof lookup, then passed for list, invalid syntax
and missing fields. Intermediate 842 comprehensive tests passed (45.695s).

A type probe showed boolean sequence True compared equal to integer sequence 1,
acknowledging two rows when a checksum-consistent but malformed proof was injected.
Validate observations against the stored source contract before exact comparison.
The first repair query incorrectly selected contract_json from source_state rather
than source_instances; 55 focused and 843 comprehensive tests failed closed with
three failures and three errors (full 44.475s). Corrected the table from canonical
source ownership. No failed run was erased or treated as an infrastructure flake;
no broader review allowance renewed. A throwaway probe first omitted PYTHONPATH
and failed to import the package; the corrected source probe established the type
issue. Temporary probe was inline, with no debug instrumentation left in source.

## Acceptance

Independent private observer grant pins exact bus/root, actor generation, message
and source instance. Separate explicitly supplied operator capability is checked
before inspecting proof or changing the mailbox. Durable signal journal opens
SQLite mode=ro with no initialization/migration; owned canonical regular path,
non-public-write mode, supported application/schema, canonical observation checksum
and source-contract types required. At most 100 selected IDs/rows per call.

Every acknowledged row equals the immutable normalized mailbox receipt including
participants, message, kind, sequence, verification and times. Missing or compacted
occurrences remain pending even when the source checkpoint exists. Semantic mismatch
rolls the whole mailbox transaction back. Actor rotation/revoked grant/missing
journal/wrong operator and malformed metadata cannot clear pins. Grant authorization
is rechecked before commit. Observer remains read-only; it cannot acknowledge or prune.

Primary integration test: terminal message stays pinned before mirroring; real
committed observations acknowledge exactly two rows; repeat acknowledges zero;
thirty-day retention preview/apply then prunes the body using its existing guard.
No simulated published status in this acceptance. Post-commit interruption returns
effect_uncertain, reconciliation_required and a durable operator receipt pointer.
Fresh CLI outputs counts/provenance without bodies or capabilities.

## Final validation

Focused: PYTHONPATH=src python3 -m unittest tests.test_a2a_projection_ack
tests.test_a2a_receipt_signals tests.test_a2a_receipt_authority tests.test_a2a_operations
tests.test_a2a_cli tests.test_signal_store -q: 55 tests, Python 3.12 5.984s;
Python 3.11 8.381s. Comprehensive: 843 tests, 55.152s, no unchanged rerun/flaky retry;
/tmp/codex-wake-p63-ack-accepted-final-suite.log. Compile/diff and active planning audit
passed with the existing exact legacy baseline.

Isolated installed wheel, PYTHONPATH=tests only and explicit installed CLI:
nine projection tests, 1.769s; imported a2a_operations from venv site-packages.
FD five to five, children zero to zero. Wheel SHA256:
38a07cff87675ad088fab9eb390e372bc2c0a4425381e7e2a69d82d5b6a73024.
Installed hosted CI adds the same nine-case boundary check after wheel installation.

## Limits

Synthetic temporary mailboxes only; no real actor enrollment, provider effects,
service changes, automatic pruning or live dispatch. Full Plan 0101 remains OPEN,
including pending named disposable live scope, delivery/suspension, service/soak,
physical compaction/tombstones and release/rollback qualification. Read-only observer
and generic dispatch hold unchanged. Discovery skipped because current canonical
sources suffice; Graphiti writes unavailable without an authorized repository group.
