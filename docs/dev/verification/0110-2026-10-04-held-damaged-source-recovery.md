# Held damaged-source recovery evidence

Verdict: ACCEPTED_BOUNDED_HELD_RECOVERY
Plan:0118
Campaign:0101 OPEN
Base:0ec069072bca81e95ad7156ffbc28578bf87ac2a

Red-capable command: PYTHONPATH=src python3 -m unittest discover -s tests
-p test_a2a_recovery.py. One case0.059s,ERROR,missing a2a_recovery module.
New feature boundary; no runtime-bug hypothesis required before implementation.
First implementation hit PRAGMA checkpoint table-locked in0.084s. Ranked
predictions: unconsumed journal-mode result, open preparation transaction, other
stage connection. Consuming mode result did not fix it (0.102s); tagged probe
reported prepared_transaction_open=False (0.097s). Reframed finalization to close
preparation handles and checkpoint a fresh connection before cold-file validation.
The same recovery fixture passed0.114s. No source had moved during failed probes;
private prepared artifacts were disposable. Tagged instrumentation removed.

First expanded9-case suite1.860s had one failure: interrupted activation gave
store_unavailable instead of recovery_incomplete pointer. Ranked prediction:
constructor file check preempts intent when canonical file absent; other causes
were missing marker or malformed receipt. Delegated the redundant constructor
check to the guarded connection, which validates intent before file existence.
No ownership check removed from actual connection. Corrected9 cases2.092s,PASS;
131 A2A cases18.968s,PASS. Backup17 cases3.825s,PASS. Failures retained, no
allowance reset or new drift-discovery review.

Installed package workload2.273s,PASS in isolated p63-recovery venv. Two owned
cases: actual installed CLI recovers a physically damaged canonical header;
installed production API is interrupted before publication, then fresh installed
CLI observes exact intent pointer and explicitly reconciles. Each case preserves
three raw source artifacts, two snapshot messages, receipt/outbox/body/state
rows and one unresolved dispatch intent. Inactive malformed sidecars are synthetic
artifact-preservation inputs, not claimed newer real business commits. Actual
pinned94e17a68 schema-one installation refuses recovered bus schema2. Old operator
cannot inspect or start another recovery; cached actors/scheduler/resume are held.
New operator inspection and a fresh schema2 held backup verify. FD5->5, children0,
transport0, roots removed. Frozen30s/child10s/FD+2/children0 budgets met.

Original source bytes/identities and prepared image are committed in a durable
intent; marker prevents normal access until exact explicit reconciliation.
External authority anchor rotates recovery permission independently of damaged
SQL; intent binds its original approval. Known snapshot history is retained, but
post-backup missing state remains unknown. This accepts only held recovery, not
gap reconciliation/release, actual services/actors, provider effects or full goal.
Two final format/corruption refusal cases, final full suite/wheel/hosted gates
remain pending. Do not claim final source acceptance from earlier installation.

Final focused recovery11 tests2.144s,PASS; comprehensive Python3.12
882 tests56.012s,PASS. Final rebuilt installed qualification2.011s,PASS,
FD5->5/children0/transport0 and both damaged-source/interrupted cases accepted
under held-recovery limits. Actual pinned legacy source94e17a68 installed in
a separate venv; recovered bus schema2 refused by that executable.
Wheel SHA256:5de016d492dc340690398da9f08984938fa3fc790c6c03d79a350b1384abf966.
No source change followed these checks; hosted exact-head gates pending.

## Final hosted and integration receipt

Exact source928effef29648d1c082e94ef6c482b073cab5ffd: hosted run37227096598
SUCCESS. Python3.11:882 tests42.206s, installed recovery2.237s; Python3.12:
882 tests40.957s, installed recovery2.438s. Both installed workloads: two cases,
each preserving3 source artifacts/2 messages/1 unknown intent; old reader refused,
new authority/hold confirmed, interruption reconciled; FD6->6/children0/transport0.
Complete installed and release gates passed. No retries or exclusions. PR204
SHA-fenced squashef59ca2b34397c24a192dc36ef57f6e165a47cfa. Plan0118 CLOSED.
Gap reconciliation/release and live/service/soak/release remain separateOPEN
requirements. Memory disposition unavailable: no authorized repository group,
zero Graphiti writes; emit one non-write receipt for this closeout.
