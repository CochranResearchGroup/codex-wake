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
