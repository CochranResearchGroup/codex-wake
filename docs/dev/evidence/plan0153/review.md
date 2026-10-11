# Plan0153 — Primary serial review

Fixed point: origin/main da21f33855f769771b68f367245044b9cde51328.
Spec: issue243 and Plan0153. Review population: owned source/test/docs patch;
the root's unrelated private StableTime rollout is excluded. Primary serial
Standards and Spec passes; no delegated reviewer or independent-review claim.
One discovery/remediation pass plus closed-world verification; two-cycle bound
is not reset by the installed packet. Base...HEAD was empty before the first
checkpoint commit; the reviewed working diff and new files were explicitly used.

## Standards

S1 blocking, resolved: schema6 and its runtime compatibility were initially absent
from schema/worker inventory and status alerts. Existing records.schema_summary
and monitor health now advertise6; public schema/status regressions and live
installed worker capability pass. Schema contract, rollback and release note
document the boundary (policies0003/0005/0006).

S2 blocking, resolved: malformed identity/history could classify as dispatchable.
Exact wake ID/fingerprint, bounded counters, event containers and original native
effect identity are validated. Public classification rejects corrupted records.

S3 blocking, resolved: manual reconciliation and archival could read guest UTC.
Both schema6 paths use unknown timestamps; public CLI regressions pass. No guest
UTC authorizes scheduling, expiry or retention.

S4 blocking, resolved: an active old worker could satisfy generic monitor
readiness for an incompatible record. Native --require-monitor now verifies the
live schema6 capability; it retains the intent and reports incompatibility rather
than claiming automatic recovery. Installed compatible-worker admission passes.

Architecture judgement: the new modules own retained-request policy and the
authenticated clock variation. Existing poll, root lifecycle locks, native queue
and uncertain-effect reconciliation remain the dispatcher. No second mailbox,
message protocol, production clock mutation or service manager is introduced.
Private baseline overlay was removed before source publication.

## Spec

F1 blocking, resolved: consumer tolerance initially relaxed the service's below
100ms UTC qualification. Contract1.0 remains strict; malformed wider qualified
responses are rejected. Authenticated unavailable responses can supply elapsed
evidence only. Independent rate-bound samples prove conservative three-hour
not-before/precision/expiry, with no fabricated UTC.

F2 blocking, resolved: recovered UTC was ignored when continuous counter bounds
had become too wide. A captured UTC origin now qualifies the original deadline;
24h recovery regression passes. Epoch loss without that origin remains held.

F3 blocking, resolved: original request disappeared on acquisition failure. The
actual installed CLI failure is replaced by durable schema6 retention, stable
key conflict/dedup, visible alert and normal bounded monitor recovery. Concurrent
creators and fresh workers yield one successor; a separate crash after acceptance
reconciles without replay. Absolute at/stop and fresh pre-queue expiry remain
qualified-UTC gates.

Known limit, nonblocking for consumer admission: the native queue has no atomic
deadline contract. Fresh qualification and a35s handoff reservation prove
consumer admission eligibility, not completion before expiry or an OS-wide
atomic transaction across suspension. This limit is explicit in the schema doc.
Source acceptance does not prove production activation or completed model turns.
No source claim resolves companion StableTime availability issue7.

F4 blocking, resolved in bounded review cycle2: first qualification could rebase
an initially unanchored relative request and extend its original expiry. The
completion audit invalidated that part of the earlier acceptance. Its regression
failed with fired1 and now proves retained/held original origin/expiry after
current UTC recovers. The evaluator no longer manufactures a later anchor.
Counter/UTC-anchored automatic recovery remains; absolute requests retain their
known UTC deadlines. Verification is closed-world for this finding and affected
recovery/expiry paths; no new broad reviewer pass or reset of cycle bounds.

Accepted findings: Standards4 resolved; Spec4 resolved. No remaining accepted
source blocker. Separate setup confirmation and installed-rollout reconciliation
remain effect gates, not source-review findings.
