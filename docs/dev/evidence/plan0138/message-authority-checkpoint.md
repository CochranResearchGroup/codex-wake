# Plan0138 unit2 — Persist sender choice before transport integration

Unit1 is qualified in native-acceptance.md. Unit2 remains IN_PROGRESS.

Public message send/reply now accept --resume-missing. The original immutable
envelope stores same_thread policy only for explicit notification opt-in, plus
sender and recipient actor IDs, roots and capability generations at admission.
Default envelopes and fingerprints retain previous bytes/semantics. Reusing an
idempotency key with a different reopening choice conflicts. Inbox-only delivery
cannot authorize reopening. Replies require their own explicit choice.

TDD seam: public Mailbox.send/show across a fresh BusStore and Mailbox instance.
Red: PYTHONPATH=src python3 -m unittest discover -s tests -p test_a2a_mailbox.py
failed18tests with one TypeError for unsupported resume_missing.
Green: same command18PASS. Public messages CLI suite7PASS.

Second TDD seam: public MailScheduler.claim after explicit capability rotation.
Red: PYTHONPATH=src python3 -m unittest discover -s tests -p test_a2a_scheduler.py
failed8tests with one failure: replaced recipient capability was incorrectly
claimable. Green: same command8PASS after comparing both original actor IDs,
generations and roots for explicit reopening messages. Existing notification
rights are still rechecked. No lifecycle or transport effect was attempted.

This checkpoint does not implement notification reopening and is not acceptance
or release evidence. It must not be integrated/released as the complete feature.
Next: connect existing journal-fenced NotificationDispatcher to explicit saved
recipient delivery, with a public dispatch regression before implementation.
Recheck original actor generations and roots before lifecycle/queue effects.
Keep busy/draft live-client paths unchanged, hold default/offline/changed identity,
preserve cancellation/expiry/restart/uncertain no-replay safeguards. Then qualify
installed unattended request/reply, serial Standards/Spec, release and integration.

Private supervisor50807 remains owned and quiescent after its original scheduled
test; clean it up at runtime closeout. Its completed wake is never replayed.
Controller continuation wake wake_20261010_153022_b44e was already armed; do not
create a duplicate continuation wake. Goal origin1791645933; checkpoint18:15:33UTC,
stop before18:25:33UTC or3million tokens. Full Plan0138 remains active.
