"""Operator recovery disposition through the public CLI, on disposable stores."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.cli import main
from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_backup import MailBackup
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_recovery import MailRecovery
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_scheduler import MailScheduler


class RecoveryDispositionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bus, self.old_operator = BusStore.configure(self.root / 'bus')
        Mailbox.migrate(self.bus, self.old_operator)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.bus.enroll(self.repo, self.old_operator, notify=True)
        self.identities = [RuntimeIdentity('fixture-runtime', name, str(self.repo))
                           for name in ['sender', 'recipient']]
        self.old_actors = []
        for identity in self.identities:
            capability, _ = self.bus.issue_actor(identity, self.repo, self.old_operator)
            self.old_actors.append(self.bus.authenticate(capability, identity, invoking_cwd=self.repo))
        mailbox = Mailbox(self.bus)
        self.legacy = mailbox.send(self.old_actors[0], self.identities[1], body='Unknown prior work.',
                                   idempotency_key='legacy-intent', delivery='notify')['message']['message_id']
        self.legacy_unread = mailbox.send(self.old_actors[0], self.identities[1], body='Unknown unread prior work.',
                                          idempotency_key='legacy-unread', delivery='notify')['message']['message_id']
        mailbox.ack(self.old_actors[1], self.legacy, outcome='accepted')
        self.bus.set_paused(False, self.old_operator)
        scheduler = MailScheduler(mailbox, self.old_operator)
        dispatcher = scheduler.acquire()
        job = scheduler.jobs(dispatcher)[0]
        recipient = scheduler.acquire('recipient:' + job['recipient_key'])
        self.unknown_attempt = scheduler.claim(dispatcher, recipient, [job['job_id']])['attempt_id']
        self.bus.set_paused(True, self.old_operator)
        snapshot = self.root / 'snapshot' 
        backup = MailBackup(self.bus, self.old_operator).create(snapshot)
        with self.bus.path.open('r+b') as stream:
            stream.write(b'Damaged fixture!')
        self.original_digest = hashlib.sha256(self.bus.path.read_bytes()).hexdigest()
        self.recovered = MailRecovery(self.bus.root, self.old_operator).recover(
            snapshot, expected_sha256=backup['database_sha256'], acknowledge_gap=True)
        self.operator = self.recovered['operator_capability_file']
        self.commitment = ['--recovery-epoch', self.recovered['recovery_epoch'],
                           '--expected-database-sha256', backup['database_sha256']]

    def invoke(self, verb, *arguments, operator=None):
        with patch('sys.stdout', new_callable=io.StringIO) as output:
            code = main(['a2a', verb, '--bus-root', str(self.bus.root),
                         '--operator-capability', operator or self.operator, '--json', *arguments])
        return code, json.loads(output.getvalue())

    def dispose(self):
        return self.invoke('dispose-recovery', *self.commitment,
                           '--accept-missing-state-unknown', '--reason', 'Retain unknown history; begin fresh work only.',
                           '--idempotency-key', 'one-original-disposition')

    def test_deliberate_unknown_disposition_releases_only_into_paused_fresh_authority(self):
        code, held = self.invoke('recovery-status')
        self.assertEqual(code, 0)
        self.assertTrue(held['recovery']['hold'])
        self.assertTrue(held['recovery']['gap_unknown'])
        code, disposed = self.dispose()
        self.assertEqual(code, 0)
        self.assertEqual(disposed['recovery']['disposition'], 'retain-unknown')
        self.assertTrue(disposed['recovery']['hold'])
        self.assertEqual(self.dispose()[1]['receipt_id'], disposed['receipt_id'])
        code, released = self.invoke('release-recovery', *self.commitment,
                                     '--disposition-receipt', disposed['receipt_id'])
        self.assertEqual(code, 0)
        self.assertFalse(released['recovery']['hold'])
        self.assertTrue(released['recovery']['gap_unknown'])
        code, status = self.invoke('status')
        self.assertEqual(code, 0)
        self.assertEqual(status['bus']['store_schema'], 3)
        self.assertTrue(status['bus']['paused'])
        self.assertEqual(status['bus']['active_actors'], 0)
        self.assertEqual(self.invoke('status', operator=str(self.old_operator))[0], 7)
        quarantine = Path(self.recovered['quarantine']) / 'mailbox.sqlite'
        self.assertEqual(hashlib.sha256(quarantine.read_bytes()).hexdigest(), self.original_digest)

    def test_fresh_authority_cannot_process_or_dispatch_snapshot_history(self):
        code, disposed = self.dispose()
        self.assertEqual(code, 0)
        self.assertEqual(self.invoke('release-recovery', *self.commitment,
                                    '--disposition-receipt', disposed['receipt_id'])[0], 0)
        _, recovery = self.invoke('recovery-status')
        fresh = []
        for identity in self.identities:
            actor = next(a for a in recovery['recovery']['revoked_actors'] if a['thread_id'] == identity.thread_id)
            code, rotated = self.invoke('rotate', actor['actor_id'])
            self.assertEqual(code, 0)
            fresh.append(self.bus.authenticate(Path(rotated['actor_capability_file']), identity, invoking_cwd=self.repo))
        self.bus.enroll(self.repo, Path(self.operator), notify=True)
        mailbox = Mailbox(self.bus, max_open=2)
        with self.assertRaises(BusError) as denied:
            mailbox.ack(fresh[1], self.legacy_unread, outcome='accepted')
        self.assertEqual(denied.exception.code, 'recovery_legacy_held')
        _, original = self.operator_show(self.legacy)
        self.assertEqual(original['message']['state']['recipient'], 'accepted')
        self.assertEqual(original['message']['recovery']['disposition'], 'retain-unknown')
        self.assertTrue(original['message']['recovery']['legacy'])
        self.assertIsNone(original['message']['terminal_receipt_id'])
        self.invoke('resume')
        scheduler = MailScheduler(mailbox, Path(self.operator))
        lease = scheduler.acquire()
        self.assertEqual(scheduler.jobs(lease), [])
        admitted = mailbox.send(fresh[0], self.identities[1], body='Fresh new work.',
                                idempotency_key='fresh-intent', delivery='inbox')
        self.assertNotEqual(admitted['message']['message_id'], self.legacy)
        self.assertTrue(mailbox.ack(fresh[1], admitted['message']['message_id'], outcome='accepted')['claimed'])

    def operator_show(self, identifier):
        with patch('sys.stdout', new_callable=io.StringIO) as output:
            code = main(['messages', 'show', identifier, '--as-operator', '--bus-root', str(self.bus.root),
                         '--operator-capability', self.operator, '--json'])
        return code, json.loads(output.getvalue())

    def test_lost_disposition_response_reconciles_original_key_without_second_effect(self):
        class LostResponse(io.StringIO):
            failed = False
            def write(self, text):
                if not self.failed:
                    self.failed = True
                    raise OSError('controlled output interruption after commit')
                return super().write(text)
        with patch('sys.stdout', new_callable=LostResponse) as output:
            code = main(['a2a', 'dispose-recovery', '--bus-root', str(self.bus.root),
                         '--operator-capability', self.operator, '--json', *self.commitment,
                         '--accept-missing-state-unknown', '--reason', 'Retain unknown history; begin fresh work only.',
                         '--idempotency-key', 'one-original-disposition'])
        failure = json.loads(output.getvalue())
        self.assertEqual(code, 8)
        self.assertTrue(failure['reconciliation_required'])
        self.assertEqual(len(failure['partial_receipt_ids']), 1)
        code, original = self.dispose()
        self.assertEqual(code, 0)
        self.assertTrue(original['deduplicated'])
        self.assertEqual(original['receipt_id'], failure['partial_receipt_ids'][0])
        self.assertTrue(original['recovery']['hold'])

    def test_release_refuses_a_reintroduced_legacy_notification(self):
        code, disposed = self.dispose()
        self.assertEqual(code, 0)
        # External storage corruption is the fault input; observations stay public.
        with self.bus.connection() as database:
            database.execute("UPDATE mail_outbox SET status='pending' WHERE kind='notification' AND message_id=?",
                             (self.legacy_unread,))
        code, refused = self.invoke('release-recovery', *self.commitment,
                                    '--disposition-receipt', disposed['receipt_id'])
        self.assertEqual(code, 8)
        self.assertEqual(refused['error']['code'], 'recovery_refused')
        self.assertTrue(self.invoke('recovery-status')[1]['recovery']['hold'])

    def test_release_reconciliation_returns_the_original_release_receipt(self):
        _, disposed = self.dispose()
        args = [*self.commitment, '--disposition-receipt', disposed['receipt_id']]
        code, released = self.invoke('release-recovery', *args)
        self.assertEqual(code, 0)
        code, repeated = self.invoke('release-recovery', *args)
        self.assertEqual(code, 0)
        self.assertTrue(repeated['deduplicated'])
        self.assertEqual(repeated['receipt_id'], released['receipt_id'])

    def test_storage_failure_before_disposition_commit_keeps_the_original_hold(self):
        with self.bus.connection() as database:
            database.execute("CREATE TRIGGER fixture_disposition_failure BEFORE INSERT ON meta "
                             "WHEN NEW.key='recovery_disposition' BEGIN SELECT RAISE(ABORT,'controlled storage failure'); END")
        code, refused = self.dispose()
        self.assertEqual(code, 8)
        self.assertFalse(refused['success'])
        _, status = self.invoke('recovery-status')
        self.assertTrue(status['recovery']['hold'])
        self.assertIsNone(status['recovery']['disposition'])
        _, original = self.operator_show(self.legacy)
        self.assertEqual(original['message']['state']['recipient'], 'accepted')
        with self.bus.connection() as database:
            database.execute('DROP TRIGGER fixture_disposition_failure')
        code, disposed = self.dispose()
        self.assertEqual(code, 0)
        self.assertFalse(disposed['deduplicated'])

    def test_corrupted_legacy_boundary_cannot_enable_snapshot_processing(self):
        self.assertEqual(self.dispose()[0], 0)
        with self.bus.connection() as database:
            # Corruption input, not an outcome oracle.
            value = self.bus.meta(database, 'recovery_disposition')
            value['legacy_through_sequence'] = 0
            database.execute("UPDATE meta SET value=? WHERE key='recovery_disposition'", (json.dumps(value),))
        code, refused = self.invoke('recovery-status')
        self.assertEqual(code, 8)
        self.assertEqual(refused['error']['code'], 'store_unavailable')

    def test_later_recovery_epoch_has_its_own_disposition_and_release(self):
        _, first = self.dispose()
        self.assertEqual(self.invoke('release-recovery', *self.commitment,
                                    '--disposition-receipt', first['receipt_id'])[0], 0)
        snapshot = self.root / 'second-snapshot'
        code, backup = self.invoke('backup', '--snapshot', str(snapshot))
        self.assertEqual(code, 0)
        sha256 = backup['backup']['database_sha256']
        with self.bus.path.open('r+b') as stream:
            stream.write(b'Damaged again!!')
        code, recovered = self.invoke('recover-backup', '--snapshot', str(snapshot),
                                      '--expected-database-sha256', sha256,
                                      '--accept-unbacked-state-hold', '--apply')
        self.assertEqual(code, 0)
        self.operator = recovered['recovery']['operator_capability_file']
        epoch = recovered['recovery']['recovery_epoch']
        self.commitment = ['--recovery-epoch', epoch, '--expected-database-sha256', sha256]
        self.assertIsNone(self.invoke('recovery-status')[1]['recovery']['disposition'])
        code, second = self.dispose()
        self.assertEqual(code, 0)
        self.assertNotEqual(first['receipt_id'], second['receipt_id'])
        code, released = self.invoke('release-recovery', *self.commitment,
                                     '--disposition-receipt', second['receipt_id'])
        self.assertEqual(code, 0)
        self.assertEqual(released['recovery']['epoch'], epoch)
        self.assertTrue(released['recovery']['gap_unknown'])

    def test_unreceipted_hold_clear_is_not_a_release(self):
        self.assertEqual(self.dispose()[0], 0)
        with self.bus.connection() as database:
            database.execute("UPDATE meta SET value='false' WHERE key='recovery_hold'")
        code, refused = self.invoke('status')
        self.assertEqual(code, 8)
        self.assertEqual(refused['error']['code'], 'store_unavailable')
