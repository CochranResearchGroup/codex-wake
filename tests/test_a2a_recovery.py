from pathlib import Path
import hashlib
import json
import os
import sqlite3
from unittest.mock import patch
import tempfile
import unittest

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_backup import MailBackup
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_recovery import MailRecovery
from codex_wake.a2a_scheduler import MailScheduler


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bus, self.operator = BusStore.configure(self.root / 'bus')
        Mailbox.migrate(self.bus, self.operator)
        self.snapshot = self.root / 'snapshot'
        self.created = MailBackup(self.bus, self.operator).create(self.snapshot)

    def test_damaged_source_is_quarantined_and_recovers_under_fresh_held_authority(self):
        from codex_wake.a2a_recovery import MailRecovery
        with self.bus.path.open('r+b') as stream:
            stream.write(b'Damaged fixture!')
        original = hashlib.sha256(self.bus.path.read_bytes()).hexdigest()
        recovered = MailRecovery(self.bus.root, self.operator).recover(self.snapshot,
            expected_sha256=self.created['database_sha256'], acknowledge_gap=True)
        self.assertTrue(recovered['recovered'])
        self.assertTrue(recovered['recovery_hold'])
        self.assertEqual(hashlib.sha256((Path(recovered['quarantine']) / 'mailbox.sqlite').read_bytes()).hexdigest(), original)
        current = BusStore(self.bus.root)
        self.assertTrue(current.status()['paused'])
        self.assertTrue(current.status()['recovery_hold'])

    def recover(self):
        return MailRecovery(self.bus.root, self.operator).recover(self.snapshot,
            expected_sha256=self.created['database_sha256'], acknowledge_gap=True)

    def test_wrong_commitment_operator_and_gap_refuse_without_source_effect(self):
        original = self.bus.path.read_bytes()
        with self.assertRaises(BusError) as exc:
            MailRecovery(self.bus.root, self.operator).recover(self.snapshot, expected_sha256='0' * 64, acknowledge_gap=True)
        self.assertEqual(exc.exception.code, 'recovery_refused')
        with self.assertRaises(BusError):
            MailRecovery(self.bus.root, self.operator).recover(self.snapshot, expected_sha256=self.created['database_sha256'])
        _, wrong = BusStore.configure(self.root / 'other', bus_id='other')
        with self.assertRaises(BusError) as exc:
            MailRecovery(self.bus.root, wrong).recover(self.snapshot, expected_sha256=self.created['database_sha256'], acknowledge_gap=True)
        self.assertEqual(exc.exception.code, 'authorization_denied')
        self.assertEqual(self.bus.path.read_bytes(), original)
        self.assertFalse(list(self.bus.root.glob('recovery_*')))

    def test_fresh_authority_hold_and_old_actor_history(self):
        repo = self.root / 'repo'; repo.mkdir()
        self.bus.enroll(repo, self.operator)
        identities = [RuntimeIdentity('recovery-fixture', name, str(repo)) for name in ('sender', 'recipient')]
        actors, capabilities = [], []
        for identity in identities:
            cap, _ = self.bus.issue_actor(identity, repo, self.operator)
            capabilities.append(cap)
            actors.append(self.bus.authenticate(cap, identity, invoking_cwd=repo))
        mailbox = Mailbox(self.bus)
        identifier = mailbox.send(actors[0], identities[1], body='Private recovery fixture.', idempotency_key='recover', delivery='inbox')['message']['message_id']
        receipt = mailbox.ack(actors[1], identifier, outcome='declined')['receipt_id']
        self.snapshot = self.root / 'populated'
        self.created = MailBackup(self.bus, self.operator).create(self.snapshot)
        result = self.recover(); current = BusStore(self.bus.root)
        fresh = Path(result['operator_capability_file'])
        with current.connection() as database:
            current.operator(database, fresh)
            self.assertEqual(current.meta(database, 'schema_version'), 2)
            self.assertEqual(current.meta(database, 'recovery_epoch'), result['recovery_epoch'])
            self.assertIsNotNone(database.execute('SELECT receipt_id FROM mail_receipts WHERE receipt_id=?', (receipt,)).fetchone())
            self.assertEqual(database.execute('SELECT body FROM mail_bodies WHERE message_id=?', (identifier,)).fetchone()[0], 'Private recovery fixture.')
            self.assertEqual(database.execute('SELECT count(*) FROM actors WHERE revoked=0').fetchone()[0], 0)
            self.assertEqual(database.execute('SELECT count(*) FROM actors WHERE actor_id IN (?,?)', (actors[0].actor_id, actors[1].actor_id)).fetchone()[0], 0)
            with self.assertRaises(BusError):
                current.operator(database, self.operator)
        with self.assertRaises(BusError) as exc:
            current.set_paused(False, fresh)
        self.assertEqual(exc.exception.code, 'recovery_hold')
        with self.assertRaises(BusError):
            current.authenticate(capabilities[0], identities[0], invoking_cwd=repo)
        with self.assertRaises(BusError):
            Mailbox(current).show(actors[0], identifier)
        with self.assertRaises(BusError) as exc:
            MailScheduler(Mailbox(current), fresh).acquire()
        self.assertEqual(exc.exception.code, 'recovery_hold')
        with self.assertRaises(BusError) as exc:
            self.recover()
        self.assertEqual(exc.exception.code, 'authorization_denied')
        # A current schema-two held snapshot is independently verifiable.
        later = self.root / 'held-snapshot'
        MailBackup(current, fresh).create(later)
        self.assertTrue(MailBackup(current, fresh).verify(later)['verified'])

    def test_reader_fences_recovery(self):
        with self.bus.connection(read_only=True):
            with self.assertRaises(BusError) as exc:
                self.recover()
        self.assertEqual(exc.exception.code, 'bus_busy')
        self.assertFalse(list(self.bus.root.glob('recovery_*')))

    def fail_once(self, phase):
        replace = os.replace
        fired = []
        def fail(source, destination):
            source, destination = Path(source), Path(destination)
            selected = (phase == 'quarantine' and source == self.bus.path or
                phase == 'activation' and source.name == 'recovered.sqlite' or
                phase == 'anchor' and destination.name == '.recovery-authority.json')
            if selected and not fired:
                fired.append(True)
                raise OSError('fixture filesystem cut')
            return replace(source, destination)
        with patch('codex_wake.a2a_recovery.os.replace', side_effect=fail):
            with self.assertRaises(BusError) as exc:
                self.recover()
        self.assertEqual(exc.exception.code, 'recovery_incomplete')
        pointer = exc.exception.details['receipt_id']
        with self.assertRaises(BusError) as exc:
            BusStore(self.bus.root)
        self.assertEqual(exc.exception.code, 'recovery_incomplete')
        self.assertEqual(exc.exception.details['receipt_id'], pointer)
        result = MailRecovery(self.bus.root, self.operator).reconcile(expected_sha256=self.created['database_sha256'])
        self.assertEqual(result['receipt_id'], pointer)
        self.assertTrue(result['completed'])
        self.assertTrue(BusStore(self.bus.root).status()['recovery_hold'])
        with self.assertRaises(BusError) as exc:
            MailRecovery(self.bus.root, self.operator).reconcile(expected_sha256=self.created['database_sha256'])
        self.assertEqual(exc.exception.code, 'no_recovery_in_progress')

    def test_quarantine_cut_is_reconciled(self):
        self.fail_once('quarantine')

    def test_activation_cut_is_reconciled(self):
        self.fail_once('activation')

    def test_authority_publication_cut_is_reconciled(self):
        self.fail_once('anchor')

    def test_completion_receipt_cut_is_reconciled(self):
        from codex_wake.a2a_recovery import _manifest
        def fail(path, value):
            if Path(path).name == 'receipt.json':
                raise OSError('fixture receipt publication cut')
            return _manifest(path, value)
        with patch('codex_wake.a2a_recovery._manifest', side_effect=fail):
            with self.assertRaises(BusError) as exc:
                self.recover()
        self.assertEqual(exc.exception.code, 'recovery_incomplete')
        result = MailRecovery(self.bus.root, self.operator).reconcile(expected_sha256=self.created['database_sha256'])
        self.assertTrue(result['completed'])
        self.assertFalse((self.bus.root / '.recovery-in-progress.json').exists())

    def test_changed_quarantined_bytes_refuse_reconciliation(self):
        replace = os.replace
        def fail(source, destination):
            if Path(source).name == 'recovered.sqlite':
                raise OSError('fixture stopped before activation')
            return replace(source, destination)
        with patch('codex_wake.a2a_recovery.os.replace', side_effect=fail):
            with self.assertRaises(BusError):
                self.recover()
        intent = json.loads((self.bus.root / '.recovery-in-progress.json').read_text())
        preserved = self.bus.root / intent['recovery_epoch'] / 'mailbox.sqlite'
        with preserved.open('r+b') as stream:
            stream.write(b'Changed evidence')
        with self.assertRaises(BusError) as exc:
            MailRecovery(self.bus.root, self.operator).reconcile(expected_sha256=self.created['database_sha256'])
        self.assertEqual(exc.exception.code, 'recovery_incomplete')
        self.assertTrue(preserved.exists())
        self.assertTrue((self.bus.root / '.recovery-in-progress.json').exists())

    def test_malformed_intent_blocks_readers_and_is_not_discarded(self):
        marker = self.bus.root / '.recovery-in-progress.json'
        marker.write_text('{'); marker.chmod(0o600)
        original = self.bus.path.read_bytes()
        with self.assertRaises(BusError) as exc:
            BusStore(self.bus.root)
        self.assertEqual(exc.exception.code, 'recovery_incomplete')
        with self.assertRaises(BusError) as exc:
            MailRecovery(self.bus.root, self.operator).reconcile(expected_sha256=self.created['database_sha256'])
        self.assertEqual(exc.exception.code, 'recovery_incomplete')
        self.assertEqual(marker.read_text(), '{')
        self.assertEqual(self.bus.path.read_bytes(), original)

    def test_corrupt_snapshot_refuses_before_source_quarantine(self):
        original = self.bus.path.read_bytes()
        with (self.snapshot / 'mailbox.sqlite').open('r+b') as stream:
            stream.write(b'Corrupt snapshot')
        with self.assertRaises(BusError):
            self.recover()
        self.assertEqual(self.bus.path.read_bytes(), original)
        self.assertFalse(list(self.bus.root.glob('recovery_*')))
