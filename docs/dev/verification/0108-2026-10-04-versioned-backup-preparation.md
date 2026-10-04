# Versioned backup preparation evidence

Verdict: LOCAL_PASS_HOSTED_PENDING
Plan: 0116
Campaign: 0101 OPEN
Source base: fe425078a64c11ee690233081ec0bf7ab720cab9

Red-capable command: PYTHONPATH=src python3 -m unittest discover -s tests
-p test_a2a_backup.py. Before implementation: one test,0.032s,ERROR,
ModuleNotFoundError codex_wake.a2a_backup. This is a new feature, not a diagnosed
production regression; hypothesis phases are inapplicable.

After implementation: eight focused cases,1.922s,PASS. Changed-surface A2A source:
113 tests,20.700s,PASS. No retry/exclusion. Covered independent operator and
paused gates, consistent committed WAL, original message/digest/receipt and
uncertain notification, private paths and symlink refusal, no-overwrite,
partial copy, completion-audit failure, unknown versions, different identity,
corruption even with updated file hash, and read-only verification stability.

Installed Python3.12 package in isolated /tmp/codex-wake-p63-backup-venv:
workload0.864s,PASS. Two messages and one actual scheduler intent claim remain
unchanged, including dispatching uncertainty; no adapter or dispatch I/O. Actual
CLI copy then a fresh CLI verification preserved all rows across actors,
metadata/state/receipt/attempt/body/outbox tables while a WAL connection stayed
open. Backup184320bytes; FD5->6 within frozen+2 bound; no children. This is
within-budget evidence, not a claim of zero FD growth. Credential secret files
were not exported. Repeated creation preserved existing artifact and returned
committed request pointer; unsupported/corrupt snapshots refused; copied-root
writer refused. Disposable roots cleaned up. Snapshot verification always
reports activation_qualified=false. It requires the original readable bus;
no corrupt-source recovery, root activation, old-binary downgrade, service,
real agent delivery, provider effects or elapsed soak is qualified.

Final deadline tightening shares one ten-second copy/verification budget during
creation; read-only verification separately has ten seconds. Final comprehensive,
wheel and hosted checks remain pending. Earlier results remain valid observations,
not exact-final-head evidence. Full activation needs fencing against revived
revoked capabilities and loss of later receipts; do not equate backup creation
or a verified file commitment with that separate campaign gate.

Final focused backup suite: ten tests,1.260s,PASS. Added deterministic deadline
interruption with preserved partial/request, and older actor authority whose
verification does not revive current revocation. These fixtures demonstrate
activation limits rather than claiming readiness of older authority.

Comprehensive source Python3.12:862 tests,81.904s,PASS, before two final test-only
cases were added. Final ten-case focused suite covers those additions; hosted
checks will run the resulting864-case suite. No product-source change followed
that full run. Final rebuilt isolated wheel installed workload0.900s,PASS, with
the same184320byte snapshot and FD5->6/no-child/no-I/O observations.
Wheel SHA256:a2dd0308a44b0c52c9f1600e90de5667647cee529cdb3b2ab92ec65bb7be1bcd.
Compilation and diff whitespace checks passed. No extra drift-discovery review
was opened; verification remains confined to the frozen snapshot acceptance.
