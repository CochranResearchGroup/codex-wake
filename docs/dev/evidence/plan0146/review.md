# Ticket0146 serial Standards and Spec review

Baseline dd52de9be7581cb86762ed458bb8cbb58f67b164; frozen candidate
c9c917d7b3058693e212a68cac70d8273306f19d. Primary serial review;
no independent evaluator claim. Frozen Plan0146 contract and original0101/0110
recovery obligations govern this review. Hosted CI wait remains waived.

Standards: zero accepted blocking findings. Existing lifecycle/SQLite transaction,
operator capability, public mailbox/scheduler and version-aware backup surfaces
are reused. Original immutable message/receipt rows are preserved. Public boundary
controls replace DB-oracle assertions; SQL mutation is only declared corruption
input. Installed fresh-process workload proves actual0.11.2 reader refusal,
quarantine retention, paused release and explicit fresh grants; FD5→5/children0.

Spec: three accepted blocking findings for one consolidated remediation cycle:

- P73-S1: schema3 legacy boundary checks field shape/epoch but does not bind its
  cutoff to the committed disposition audit receipt. Corrupt cutoff can expose
  snapshot-era processing. Require exact receipt/action/intent/cutoff commitment.
- P73-S2: recovered schema3 snapshot retains prior disposition/release metadata;
  a later recovery epoch would collide with the old current-disposition key.
  Preserve old audit history while making current disposition epoch-specific.
- P73-S3: retained unknown legacy messages still count as open processing work.
  A full legacy open quota can prevent new fresh-authority work indefinitely.
  Exclude fenced history from processing quota; retain total storage/retention caps.

Each finding needs a public red/green control, then only affected source/installed
checks repeated. Source225PASS79.484s and initial installed candidate pass are
retained as initial evidence, not final reviewed acceptance. No new finding pass
or repeated broad soak is authorized by this review packet.

## Consolidated remediation adjudication

P73-S1 reproduced cutoff corruption and unreceipted hold-clear acceptance;
core schema3 connections now require exact committed disposition/release events,
epoch/cutoff/intent and persistent unknown-state commitments. Both red controls
refuse after repair. P73-S2 reproduced stale current disposition after a second
recovery; preparation clears only epoch-current derived metadata, preserving
original audit rows, snapshot and quarantine; second epoch/release passes.
P73-S3 reproduced capacity refusal with a two-message legacy quota; current open
processing count excludes the fenced boundary while total storage limits remain.
The strengthened original public fresh-authority control passes.

All accepted findings resolved within one cycle; zero remaining accepted blocking
findings. Focused9PASS6.536s. Reviewed source/installed gates must now repeat only
the affected selection and installed fresh-process workload; no new discovery or
independent-review claim. Exact reviewed source is the following commit checkpoint.

Reviewed source9164e9c affected228PASS81.118s and installed86PASS36.363s.
Initial fresh-process workload on that candidate stopped in role-fixture setup
with the existing clock_continuity guard before recovery/disposition. The failed
receipt is retained. No production guard was changed: non-time role fixtures now
use the public Mailbox clock seam with fixed1000; operator history assertions use
its public inspection API on the same controlled clock. Recovery CLI commands
remain actual fresh processes, and no UTC qualification is claimed. Fixture-only
9PASS5.873s. Repeat those invalidated fixtures/workload; package code remains byte
identical to reviewed9164e9c, so unchanged86controls need no blanket repeat.
