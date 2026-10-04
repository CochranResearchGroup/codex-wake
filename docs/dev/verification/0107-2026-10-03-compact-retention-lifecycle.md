# Compact retention lifecycle evidence

Verdict: LOCAL_ACCEPTED_HOSTED_PENDING
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

## Ninety-day retirement and physical recovery, still incomplete

Red retirement probe: one test, 0.078s, expected aged tombstone eligibility but
observed no candidates. Implemented bounded retirement removes body/outbox/receipt/
state/tombstone/identity rows after the ninety-day creation horizon and keeps only
a SHA-256 sender/key refusal marker. Exact identity is no longer retained beyond
the horizon; old keys still visibly refuse as idempotency_horizon. Markers count
against the existing message capacity, so refusal metadata cannot grow without
bounds. Immutable attributable bus events remain. Bounded old submitted/unsent
orphan-attempt cleanup excludes dispatching/uncertain attempts and retained IDs.

Red physical-reclaim probe: missing reclaim_space API, one error, 0.081s. After
implementation the initial unpaused-refusal assertion failed because configure
starts paused. Corrected the fixture to explicitly resume first; no runtime pause
bug was found. The production operation requires pause, commits a request receipt,
checkpoints WAL, VACUUMs with a ten-second progress deadline and records before/after
file bytes. Reader contention or interruption gives maintenance_incomplete and
a preserved request receipt; the CLI marks reconciliation required. Logical rows
are not deleted by space recovery. A large disposable body fixture proves physical
file reduction and retained logical identity; reader contention preserves data.

Changed-surface source Python 3.12: 103 A2A tests, 12.740s, PASS. Python 3.11:
15 operations tests, 2.644s, PASS. Isolated installed wheel API tests outside
repository with PYTHONPATH unset: 15 operations tests, 2.072s, PASS. Installed
reclaim-space help requires explicit --apply and independent operator capability.
Wheel SHA256: 3d7d871d132b2dde3fb2fb3457bdf878bca7c2367070e93420282d5614e7775d.
No retry, exclusion or live effects. These installed API tests are not yet a
fresh-process populated old/new CLI migration proof. Full suite, hosted gates,
production projection acknowledgement and installed compatibility remain pending.

## Populated installed old/new qualification and final local source checks

New script a2a_retention_qualification.py constructs two populated schema-one
fixtures using the actual prior installed wheel, then invokes unmodified installed
old/new CLIs. Thirty-one/ninety-one-day age is a controlled fixture offset of both
wall and monotonic coordinates, not elapsed soak or a real reboot. New readers
refuse before migration; explicit migration preserves data; old installed readers
refuse afterward. Independently configured production receipt mirror/acknowledgement
clears pins; actual installed compact/reclaim-space commands preserve identity,
reduce files and retire old tombstones. Separate new processes prove listing and
exact retry identity. The managed signal reader is an explicit synthetic fixture
capability, not an installed service acceptance claim. Both cases have zero
dispatch attempts and no runtime/provider operations. Temporary roots are removed.

First installed workload: 3.511s, FD5->5, no children, each case recovered 36,864
bytes. A completion-audit fault probe then showed RuntimeError escaping after
VACUUM. Added a typed maintenance_incomplete boundary preserving the committed
request receipt; after-commit uncertainty still preserves its exact completion
receipt. Final installed workload: 3.833s, same recovery/census/effect result.
Final wheel SHA256 cd4e179544884ccf1e9df452f31b5e5a956b6cecac2a947a2a108e395822338f.
Final local comprehensive source Python 3.12: 853 tests, 50.167s, PASS. Python 3.11
focused operations: 16 tests, 2.714s, PASS. No retry or exclusion. Hosted workflow
installs schema-one package from pinned main 94e17a68e655d9e54ead6001704dc0ef453eb933
and runs old/new installed qualification with a 40s outer / 35s internal budget.
Hosted checks and integration remain required before closing Plan 0115. Full
campaign live, service, restore, soak and release gates remain OPEN.
