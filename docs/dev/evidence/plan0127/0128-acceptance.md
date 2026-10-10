# Ticket0128 acceptance

Public command: `codex-wake native after|at|file`, exact thread UUID, explicit native transport, bounded expiry. Existing installed scheduler performs queue submission without tmux injection. Isolated editable candidate installed under the private plan127-runtime venv; global installation untouched. Codex0.162.1.

| Criterion | Outcome | Evidence |
| --- | --- | --- |
| Installed scheduler submits due wake unattended | PASS | 0128-scheduler-journal.txt, 0128-native-records.json |
| Queue acceptance differs from execution/ack | PASS | Native queue ID retained, execution/ack not_observed; 0128-native-live.json separately proves completed recipient token |
| Busy recipient held, then submitted after idle | PASS | 0128-busy-records.json holds then accepts; 0128-busy-live.json proves busy control and later recipient completion |
| Unavailable recipient held until expiry | PASS | 0128-unavailable-held.json and 0128-unavailable-expired.json; no native submission occurred |
| Native uncertainty does not automatically retry/fallback | PASS | public scheduler regression, uncertain output followed by second poll invokes queue only once; no tmux runner construction |
| Ordinary direct-send failure creates no mailbox | PASS by interface scope | Ordinary communication remains native Codex; this addition only registers explicit durable wakes and creates no mailbox database or message |

Regression receipt: `PYTHONPATH=src python -m unittest tests.test_native_delivery -v` initially failed because native command absent, then passed. File-never-created expiry regression initially failed (pending forever), fixed before acceptance. Native+daemon+records+shared-server suite:61 passed. Acceptance evidence contains only disposable actor/test state.

Standards review: existing scheduler/record seam reused; exact selection, explicit transport, persisted ambiguity before effect, per-wake locking, no blind retry and no global runtime mutation. Fixed missing expiry for unfulfilled file predicates. No remaining blocking standards finding for this slice.

Spec review: all0128 criteria mapped above. This slice does not establish native execution acknowledgment, unattended same-thread resume or ambiguous-effect reconciliation; those remain explicit later-ticket work. No exactly-once guarantee or full Plan0127 completion claim.
