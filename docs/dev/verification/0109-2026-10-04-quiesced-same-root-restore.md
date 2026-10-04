# Quiesced same-root restore evidence

Verdict: IMPLEMENTED_QUALIFICATION_PENDING
Plan:0117
Campaign:0101 OPEN
Base:1108be728822683b279443c2d71a8ee642faea75

Red-capable command: PYTHONPATH=src python3 -m unittest discover -s tests
-p test_a2a_backup.py -k quiesced_restore. One test,0.058s,ERROR: MailBackup
has no restore method. New feature boundary, not a runtime bug; hypothesis
phases inapplicable. After implementation the same fixture passed0.083s.

First16-case backup/restore suite3.134s and121 A2A suite16.939s each had one
failure: interruption fixture expectedrestore_incomplete but sawstore_unavailable.
Its mock wrapper was not a sqlite3.Connection, so snapshot.backup rejected the
mock before reaching the intended stage-to-canonical fault. Corrected only the
fixture to a genuine SQLite Connection subclass. No production error-code
change to disguise the failure. Corrected16-case suite3.315s,PASS.

Connection fencing is cooperative for upgraded BusStore clients, not an OS
security boundary or an installed old-binary census. Normal connections hold a
shared lock; explicit restore takes exclusive ownership with1second bounded
wait. Exact non-audit state comparison prevents newer authority/outcomes from
being rewound. All later audit entries are copied into the private stage before
SQLite atomic backup into the existing canonical inode. Store remains paused.
Interruption/completion-audit fault keeps request receipt and stage. No root
rebinding, automatic notification replay or corrupt-source recovery claim.
Only disposable synthetic fixtures are used; final source/installed/hosted
qualification pending. Inherited discovery/review allowances were not reset.

Changed-surface A2A121 tests15.734s,PASS. First installed rebuilt workload
2.055s,PASS: actual state-equivalent restore preserved inode, two messages/one
unknown intent, participating reader blocked, later actor revocation refused.
FD5->6 within+2, no children or transport, private fixture removed.
Final schema comparison also covers indexes/views/triggers; focused17 cases
3.440s,PASS and rebuilt installed workload2.124s,PASS. Wheel SHA256:
1bfbee84785e4b29ac73caa15e386ccf809df636fc67808fc7e019ef58853d64.

First comprehensive source871 tests49.080s,FAILED with four StopIteration errors
in message wait fixtures. Tight reproduction: test_messages_cli -k bounded_wait,
one case1.652s, same error. Ranked predictions shown before correction: shared
time.monotonic mock consumed by new lifecycle deadline; extra wait-loop calls
would survive isolation; test-order leak unlikely after standalone reproduction.
Bound lifecycle monotonic independently; unchanged wait assertions and semantics.
This is the second implementation attempt, not a fresh discovery allowance.
Final qualification after that correction is pending. Preserve first failures.

Final comprehensive Python3.12:871 tests52.343s,PASS after lifecycle clock
isolation. Final rebuilt installed workload2.069s,PASS, same184320bytes,
FD5->6 within+2/no children/no transport; state-equivalent restore, original
inode, retained rows/unknown intent and newer authority refusal proven.
Wheel SHA256:40bbffa105a66ea2a07358cbd967e0fb10b3f284addb180127ba8bd56ae1dfbb.
The existing interrupted-copy fixture now interrupts actual SQLite page copying
using a genuine Connection subclass rather than merely throwing before copying.
Final focused check and hosted exact-head gates still required.
