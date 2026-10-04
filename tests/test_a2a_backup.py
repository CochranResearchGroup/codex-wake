from pathlib import Path
import hashlib
import json
import shutil
import sqlite3
import tempfile
from unittest.mock import patch
import unittest

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_backup import MailBackup
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox


class BackupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bus, self.operator = BusStore.configure(self.root / 'bus')
        Mailbox.migrate(self.bus, self.operator)

    def test_versioned_snapshot_preserves_identity_and_verifies_read_only(self):
        from codex_wake.a2a_backup import MailBackup
        backup = MailBackup(self.bus, self.operator)
        created = backup.create(self.root / 'snapshot')
        self.assertTrue(created['receipt_id'])
        checked = backup.verify(self.root / 'snapshot')
        self.assertTrue(checked['verified'])
        self.assertFalse(checked['activation_qualified'])
        self.assertEqual(checked['bus_id'], self.bus.bus_id)
        self.assertEqual(checked['mailbox_schema'], 2)

    def test_paused_and_independent_operator_authority_required(self):
        self.bus.set_paused(False, self.operator)
        with self.assertRaises(BusError) as exc:
            MailBackup(self.bus, self.operator).create(self.root / 'snapshot')
        self.assertEqual(exc.exception.code, 'pause_required')
        self.assertFalse((self.root / 'snapshot').exists())
        self.bus.set_paused(True, self.operator)
        _, wrong = BusStore.configure(self.root / 'other', bus_id='other')
        with self.assertRaises(BusError) as exc:
            MailBackup(self.bus, wrong).create(self.root / 'snapshot')
        self.assertEqual(exc.exception.code, 'authorization_denied')
        self.assertFalse((self.root / 'snapshot').exists())

    def test_wal_snapshot_preserves_message_receipt_and_uncertain_notification(self):
        repo = self.root / 'repo'; repo.mkdir()
        self.bus.enroll(repo, self.operator)
        identities = [RuntimeIdentity('backup-fixture', name, str(repo)) for name in ('sender', 'recipient')]
        actors = []
        for identity in identities:
            capability, _ = self.bus.issue_actor(identity, repo, self.operator)
            actors.append(self.bus.authenticate(capability, identity, invoking_cwd=repo))
        mailbox = Mailbox(self.bus)
        identifier = mailbox.send(actors[0], identities[1], body='Private WAL backup fixture.', idempotency_key='snapshot', delivery='inbox')['message']['message_id']
        acknowledgement = mailbox.ack(actors[1], identifier, outcome='declined')
        # Retain a live connection so committed WAL has not been checkpointed away.
        with self.bus.connection() as live:
            live.execute("UPDATE mail_state SET notification='uncertain' WHERE message_id=?", (identifier,))
            created = MailBackup(self.bus, self.operator).create(self.root / 'snapshot')
            self.assertTrue(created['verified'])
            with sqlite3.connect(self.root / 'snapshot/mailbox.sqlite') as copied:
                self.assertEqual(copied.execute('SELECT notification FROM mail_state WHERE message_id=?', (identifier,)).fetchone()[0], 'uncertain')
                self.assertEqual(copied.execute('SELECT body FROM mail_bodies WHERE message_id=?', (identifier,)).fetchone()[0], 'Private WAL backup fixture.')
                self.assertIsNotNone(copied.execute('SELECT receipt_id FROM mail_receipts WHERE receipt_id=?', (acknowledgement['receipt_id'],)).fetchone())
            self.assertEqual(mailbox.send(actors[0], identities[1], body='Private WAL backup fixture.', idempotency_key='snapshot', delivery='inbox')['message']['message_id'], identifier)
        copied_root = self.root / 'copy'; copied_root.mkdir(mode=0o700)
        shutil.copy2(self.root / 'snapshot/mailbox.sqlite', copied_root / 'mailbox.sqlite')
        with self.assertRaises(BusError) as exc:
            BusStore(copied_root)
        self.assertEqual(exc.exception.code, 'bus_identity_mismatch')

    def test_private_paths_symlinks_and_existing_snapshot_refused(self):
        backup = MailBackup(self.bus, self.operator)
        directory = self.root / 'snapshot'
        backup.create(directory)
        for name, mode in (('', 0o700), ('mailbox.sqlite', 0o600), ('manifest.json', 0o600)):
            self.assertEqual((directory / name).stat().st_mode & 0o777, mode)
        original = (directory / 'manifest.json').read_bytes()
        with self.assertRaises(BusError) as exc:
            backup.create(directory)
        self.assertEqual(exc.exception.code, 'backup_incomplete')
        self.assertEqual((directory / 'manifest.json').read_bytes(), original)
        (self.root / 'linked').symlink_to(directory, target_is_directory=True)
        with self.assertRaises(BusError) as exc:
            backup.verify(self.root / 'linked')
        self.assertEqual(exc.exception.code, 'ownership_mismatch')
        (directory / 'manifest.json').chmod(0o644)
        with self.assertRaises(BusError) as exc:
            backup.verify(directory)
        self.assertEqual(exc.exception.code, 'ownership_mismatch')

    def test_incomplete_copy_preserves_request_and_refuses_verification(self):
        backup = MailBackup(self.bus, self.operator)
        with patch('codex_wake.a2a_backup._manifest', side_effect=OSError('fixture disk full')):
            with self.assertRaises(BusError) as exc:
                backup.create(self.root / 'snapshot')
        self.assertEqual(exc.exception.code, 'backup_incomplete')
        with self.bus.connection() as live:
            self.assertEqual(live.execute('SELECT action FROM events WHERE receipt_id=?', (exc.exception.details['receipt_id'],)).fetchone()[0], 'backup_requested')
        self.assertTrue((self.root / 'snapshot/mailbox.sqlite').exists())
        with self.assertRaises(BusError):
            backup.verify(self.root / 'snapshot')

    def test_completion_audit_failure_preserves_verified_backup(self):
        backup = MailBackup(self.bus, self.operator)
        original = self.bus.event
        def fail(database, actor, action, subject):
            if action == 'backup_completed':
                raise sqlite3.OperationalError('fixture completion audit failure')
            return original(database, actor, action, subject)
        with patch.object(self.bus, 'event', side_effect=fail):
            with self.assertRaises(BusError) as exc:
                backup.create(self.root / 'snapshot')
        self.assertEqual(exc.exception.code, 'backup_incomplete')
        self.assertTrue(backup.verify(self.root / 'snapshot')['verified'])

    def test_readonly_verification_does_not_change_source_or_backup(self):
        backup = MailBackup(self.bus, self.operator); directory = self.root / 'snapshot'
        backup.create(directory)
        before = {p.name: p.read_bytes() for p in directory.iterdir()}
        with self.bus.connection() as live:
            events = live.execute('SELECT * FROM events ORDER BY receipt_id').fetchall()
        for _ in range(2):
            self.assertTrue(backup.verify(directory)['verified'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir()})
        with self.bus.connection() as live:
            self.assertEqual(events, live.execute('SELECT * FROM events ORDER BY receipt_id').fetchall())

    def test_corruption_unknown_version_and_different_bus_refused(self):
        backup = MailBackup(self.bus, self.operator); directory = self.root / 'snapshot'
        backup.create(directory)
        manifest_path = directory / 'manifest.json'
        original = manifest_path.read_text(); manifest = json.loads(original)
        manifest['format_version'] = 2; manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(BusError) as exc:
            backup.verify(directory)
        self.assertEqual(exc.exception.code, 'backup_invalid')
        manifest_path.write_text(original)
        other, operator = BusStore.configure(self.root / 'other', bus_id='other')
        with self.assertRaises(BusError) as exc:
            MailBackup(other, operator).verify(directory)
        self.assertEqual(exc.exception.code, 'bus_identity_mismatch')
        with (directory / 'mailbox.sqlite').open('r+b') as stream:
            stream.write(b'corrupt')
        with self.assertRaises(BusError) as exc:
            backup.verify(directory)
        self.assertEqual(exc.exception.code, 'backup_invalid')
        manifest = json.loads(original)
        manifest['database_sha256'] = hashlib.sha256((directory / 'mailbox.sqlite').read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(BusError) as exc:
            backup.verify(directory)
        self.assertEqual(exc.exception.code, 'backup_invalid')

    def test_copy_deadline_preserves_partial_evidence_and_request(self):
        with patch('codex_wake.a2a_backup.DEADLINE_SECONDS', 0):
            with self.assertRaises(BusError) as exc:
                MailBackup(self.bus, self.operator).create(self.root / 'snapshot')
        self.assertEqual(exc.exception.code, 'backup_incomplete')
        self.assertTrue(exc.exception.details['receipt_id'])
        self.assertFalse((self.root / 'snapshot/manifest.json').exists())
        self.assertTrue((self.root / 'snapshot/mailbox.sqlite').exists())

    def test_old_actor_authority_is_not_activated_by_verification(self):
        repo = self.root / 'repo'; repo.mkdir()
        self.bus.enroll(repo, self.operator)
        identity = RuntimeIdentity('backup-fixture', 'sender', str(repo))
        capability, _ = self.bus.issue_actor(identity, repo, self.operator)
        actor = self.bus.authenticate(capability, identity, invoking_cwd=repo)
        backup = MailBackup(self.bus, self.operator)
        backup.create(self.root / 'snapshot')
        self.bus.revoke_actor(actor.actor_id, self.operator)
        self.assertFalse(backup.verify(self.root / 'snapshot')['activation_qualified'])
        with self.assertRaises(BusError) as exc:
            self.bus.authenticate(capability, identity, invoking_cwd=repo)
        self.assertEqual(exc.exception.code, 'authorization_denied')
        with sqlite3.connect(self.root / 'snapshot/mailbox.sqlite') as copied:
            self.assertEqual(copied.execute('SELECT revoked FROM actors WHERE actor_id=?', (actor.actor_id,)).fetchone()[0], 0)

    def test_quiesced_restore_preserves_same_identity_and_later_audit(self):
        backup = MailBackup(self.bus, self.operator)
        directory = self.root / 'snapshot'; backup.create(directory)
        with self.bus.connection() as live:
            later = self.bus.event(live, 'operator', 'fixture_later_audit', {})
        restored = backup.restore(directory)
        self.assertTrue(restored['restored'])
        self.assertTrue(self.bus.status()['paused'])
        self.assertEqual(self.bus.bus_id, restored['bus_id'])
        with self.bus.connection() as live:
            self.assertIsNotNone(live.execute('SELECT receipt_id FROM events WHERE receipt_id=?', (later,)).fetchone())
            self.assertEqual(live.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_restore_refuses_new_actor_authority_without_reviving_snapshot(self):
        repo = self.root / 'repo'; repo.mkdir()
        self.bus.enroll(repo, self.operator)
        identity = RuntimeIdentity('backup-fixture', 'sender', str(repo))
        capability, _ = self.bus.issue_actor(identity, repo, self.operator)
        actor = self.bus.authenticate(capability, identity, invoking_cwd=repo)
        backup = MailBackup(self.bus, self.operator)
        backup.create(self.root / 'snapshot')
        self.bus.revoke_actor(actor.actor_id, self.operator)
        with self.assertRaises(BusError) as exc:
            backup.restore(self.root / 'snapshot')
        self.assertEqual(exc.exception.code, 'restore_refused')
        with self.assertRaises(BusError):
            self.bus.authenticate(capability, identity, invoking_cwd=repo)
        with self.bus.connection() as live:
            self.assertEqual(live.execute("SELECT count(*) FROM events WHERE action='restore_requested'").fetchone()[0], 0)

    def test_restore_refuses_concurrent_participating_connection(self):
        backup = MailBackup(self.bus, self.operator)
        backup.create(self.root / 'snapshot')
        with self.bus.connection(read_only=True):
            with self.assertRaises(BusError) as exc:
                backup.restore(self.root / 'snapshot')
        self.assertEqual(exc.exception.code, 'bus_busy')
        self.assertTrue(backup.restore(self.root / 'snapshot')['restored'])

    def test_new_connections_refuse_during_exclusive_lifecycle_window(self):
        with self.bus.maintenance_connection():
            with self.assertRaises(BusError) as exc:
                with self.bus.connection():
                    self.fail('writer entered exclusive window')
        self.assertEqual(exc.exception.code, 'bus_busy')
        self.assertTrue(self.bus.status()['paused'])

    def test_restore_completion_failure_preserves_request_stage_and_pause(self):
        backup = MailBackup(self.bus, self.operator); directory = self.root / 'snapshot'
        backup.create(directory)
        original = self.bus.event
        def fail(database, actor, action, subject):
            if action == 'restore_completed':
                raise sqlite3.OperationalError('fixture completion audit full')
            return original(database, actor, action, subject)
        with patch.object(self.bus, 'event', side_effect=fail):
            with self.assertRaises(BusError) as exc:
                backup.restore(directory)
        self.assertEqual(exc.exception.code, 'restore_incomplete')
        self.assertTrue(list(self.bus.root.glob('restore_*.sqlite')))
        self.assertTrue(self.bus.status()['paused'])
        self.assertTrue(backup.verify(directory)['verified'])
        with self.bus.connection() as live:
            self.assertEqual(live.execute('SELECT action FROM events WHERE receipt_id=?', (exc.exception.details['receipt_id'],)).fetchone()[0], 'restore_requested')
            self.assertEqual(live.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_restore_copy_interruption_preserves_canonical_and_snapshot(self):
        backup = MailBackup(self.bus, self.operator); directory = self.root / 'snapshot'
        backup.create(directory)
        original = sqlite3.connect
        calls = []
        class Stage(sqlite3.Connection):
            def backup(self, destination, **kwargs):
                def interrupted(status, remaining, total):
                    self.asserted_pages = total - remaining
                    if remaining > 0:
                        raise sqlite3.OperationalError('fixture interrupted after first copied page')
                return super().backup(destination, pages=1, progress=interrupted)
        def connect(path, *args, **kwargs):
            if Path(str(path)).name.startswith('restore_'):
                calls.append(path)
                kwargs['factory'] = Stage
            return original(path, *args, **kwargs)
        with self.bus.connection() as live:
            before = [tuple(row) for row in live.execute('SELECT * FROM meta ORDER BY key')]
        with patch('codex_wake.a2a_backup.sqlite3.connect', side_effect=connect):
            with self.assertRaises(BusError) as exc:
                backup.restore(directory)
        self.assertEqual(exc.exception.code, 'restore_incomplete')
        self.assertEqual(len(calls), 1)
        with self.bus.connection() as live:
            self.assertEqual(before, [tuple(row) for row in live.execute('SELECT * FROM meta ORDER BY key')])
            self.assertEqual(live.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertTrue(backup.verify(directory)['verified'])

    def test_restore_refuses_new_recipient_receipt_and_preserves_outcome(self):
        repo = self.root / 'repo'; repo.mkdir()
        self.bus.enroll(repo, self.operator)
        identities = [RuntimeIdentity('restore-fixture', name, str(repo)) for name in ('sender', 'recipient')]
        actors = []
        for identity in identities:
            capability, _ = self.bus.issue_actor(identity, repo, self.operator)
            actors.append(self.bus.authenticate(capability, identity, invoking_cwd=repo))
        mailbox = Mailbox(self.bus)
        identifier = mailbox.send(actors[0], identities[1], body='Restore receipt fixture.', idempotency_key='receipt', delivery='inbox')['message']['message_id']
        backup = MailBackup(self.bus, self.operator)
        backup.create(self.root / 'snapshot')
        receipt = mailbox.ack(actors[1], identifier, outcome='declined')['receipt_id']
        with self.assertRaises(BusError) as exc:
            backup.restore(self.root / 'snapshot')
        self.assertEqual(exc.exception.code, 'restore_refused')
        with self.bus.connection() as live:
            self.assertIsNotNone(live.execute('SELECT receipt_id FROM mail_receipts WHERE receipt_id=?', (receipt,)).fetchone())
            self.assertEqual(live.execute('SELECT recipient FROM mail_state WHERE message_id=?', (identifier,)).fetchone()[0], 'declined')
