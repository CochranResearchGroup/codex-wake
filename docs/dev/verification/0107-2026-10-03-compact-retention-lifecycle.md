# Compact retention lifecycle evidence

Verdict: INCOMPLETE
Plan: 0115
Campaign: 0101 OPEN

## Baseline and red loop

Resumed goal meter starts at zero with an additional 500k operator allowance.
Prior paused meter 412,020 remains historical. Source baseline main 94e17a6;
packet feat/p63-retention-lifecycle initially eefde260.

Command: PYTHONPATH=src python3 -m unittest discover -s tests
-p test_a2a_operations.py -k compaction

Observed: one test, 0.070 seconds, FAILED (one error). AttributeError:
MailOperations has no attribute compaction. This is an unimplemented feature
boundary, not a diagnosed runtime regression. No runtime change yet.
The fixture creates a terminal message in a disposable bus, advances a controlled
clock thirty-one days, and requires preview/apply to replace its full envelope
while preserving ID, digest, terminal receipt and exact duplicate admission.
It deliberately simulates published projections at the unit seam; it does not
qualify production projection acknowledgement or actual transport delivery.

## Next evidence

Coordinate migration, tombstone projection and admission lookup, participant
access, retained ancestry and all scheduler/signal consumers. Extend focused
coverage for pins, stale previews, migration atomicity, old-reader refusal and
ninety-day horizon. Then qualify the installed process and physical space recovery
using real projection acknowledgement. This draft records no accepted compaction,
service, restore, soak, release or live effects.

## Schema and logical compaction implementation, not final acceptance

Mailbox schema 2 adds a separate identity registry, compact tombstones and shared
metadata view. Explicit migration rebinds body/state/receipt/outbox foreign keys
transactionally, preserves original envelope sequencing and immutable triggers,
and checks foreign keys before committing. Frozen schema-1 SQL fixture is sourced
from main 94e17a68e655d9e54ead6001704dc0ef453eb933, not a guessed old schema.
Focused compaction loop now passes. Eleven operations cases passed on Python 3.12
in 0.978 seconds, covering preserved retry/read identity, ancestry pins, stale
preview, interrupted maintenance, explicit migration and rollback. The local
old-guard check is a schema-guard check only, not installed old-binary proof.

Current implementation deliberately remains unqualified: ninety-day tombstone
retirement, compact metadata cleanup, physical recovery and installed old/new
process acceptance still need implementation/evidence. Other campaign gates and
independent live authority boundaries are unchanged. No PR or merge-ready claim.

Final changed-surface source check at this checkpoint: 99 A2A tests, Python 3.12,
12.061 seconds, PASS. Python 3.11 eleven operations tests, 1.189 seconds, PASS.
No retry or exclusion; these are focused source checks, not the comprehensive or
installed acceptance lane.
