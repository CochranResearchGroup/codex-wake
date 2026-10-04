from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_operations import MailOperations


class OperationsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.repo=self.root/'repo';self.repo.mkdir()
        self.bus,self.operator=BusStore.configure(self.root/'bus')
        self.bus.enroll(self.repo,self.operator)
        self.identities=[RuntimeIdentity('fixture',name,str(self.repo)) for name in ('sender','recipient')]
        self.capabilities=[];self.actors=[]
        for identity in self.identities:
            capability,_=self.bus.issue_actor(identity,self.repo,self.operator)
            self.capabilities.append(capability)
            self.actors.append(self.bus.authenticate(capability,identity,invoking_cwd=self.repo))
        Mailbox.migrate(self.bus,self.operator)
        self.now=1000.
        self.mailbox=Mailbox(self.bus,clock=lambda:self.now,monotonic=lambda:self.now)
        self.ops=MailOperations(self.mailbox,self.operator)
        self.identifier=self.mailbox.send(self.actors[0],self.identities[1],body='private operation fixture',
                     idempotency_key='request',delivery='inbox')['message']['message_id']

    def test_explicit_rotation_invalidates_old_capability_and_cached_actor(self):
        capability,receipt=self.bus.rotate_actor(self.actors[0].actor_id,self.operator)
        self.assertTrue(receipt)
        self.assertEqual(capability.stat().st_mode & 0o777,0o600)
        with self.assertRaises(BusError):self.bus.authenticate(self.capabilities[0],self.identities[0],invoking_cwd=self.repo)
        with self.assertRaises(BusError):self.mailbox.show(self.actors[0],self.identifier)
        current=self.bus.authenticate(capability,self.identities[0],invoking_cwd=self.repo)
        self.assertEqual(current.generation,self.actors[0].generation+1)
        self.assertEqual(self.mailbox.show(current,self.identifier)['message_id'],self.identifier)

    def test_failed_capability_publication_preserves_original_generation(self):
        with patch('codex_wake.a2a_bus.write_capability',side_effect=OSError('fixture disk full')):
            with self.assertRaises(OSError):self.bus.rotate_actor(self.actors[0].actor_id,self.operator)
        self.assertEqual(self.bus.authenticate(self.capabilities[0],self.identities[0],invoking_cwd=self.repo).generation,1)
        self.assertEqual(self.mailbox.show(self.actors[0],self.identifier)['message_id'],self.identifier)

    def test_unprojected_receipts_pin_terminal_body(self):
        self.mailbox.ack(self.actors[1],self.identifier,outcome='declined')
        self.now+=31*86400
        preview=self.ops.retention()
        self.assertEqual(preview['eligible'],[])
        self.assertIn('unprojected_receipt_signal',preview['candidates'][0]['pins'])
        result=self.ops.retention(apply_fingerprint=preview['fingerprint'])
        self.assertEqual(result['pruned'],0)
        self.assertTrue(self.mailbox.show(self.actors[0],self.identifier)['body_retained'])

    def terminal_with_fixture_published_signals(self):
        self.mailbox.ack(self.actors[1],self.identifier,outcome='declined')
        # Simulate an independently qualified signal publisher acknowledgement.
        # No production API can fabricate this acknowledgement.
        with self.bus.connection() as database:
            database.execute("UPDATE mail_outbox SET status='published' WHERE kind='receipt_signal'")

    def test_explicit_pruning_preserves_identity_digest_receipts_and_dedup(self):
        self.terminal_with_fixture_published_signals()
        self.now+=29*86400
        self.assertEqual(self.ops.retention()['eligible'],[])
        self.now+=2*86400
        before=self.mailbox.show(self.actors[0],self.identifier)
        with self.bus.connection() as database:
            database.execute("UPDATE mail_outbox SET status='published' WHERE kind='receipt_signal'")
        preview=self.ops.retention()
        self.assertEqual(preview['eligible'],[self.identifier])
        applied=self.ops.retention(apply_fingerprint=preview['fingerprint'])
        self.assertEqual(applied['pruned'],1)
        after=self.mailbox.show(self.actors[0],self.identifier)
        self.assertFalse(after['body_retained'])
        self.assertEqual(after['body_digest'],before['body_digest'])
        self.assertEqual(after['receipts'],before['receipts'])
        with self.assertRaises(BusError) as error:self.mailbox.read(self.actors[1],self.identifier)
        self.assertEqual(error.exception.code,'body_unavailable')
        retry=self.mailbox.send(self.actors[0],self.identities[1],body='private operation fixture',idempotency_key='request',delivery='inbox')
        self.assertEqual(retry['message']['message_id'],self.identifier)
        self.assertTrue(retry['deduplicated'])

    def test_new_reply_pins_conversation_and_invalidates_old_preview(self):
        self.terminal_with_fixture_published_signals();self.now+=31*86400
        preview=self.ops.retention()
        self.mailbox.reply(self.actors[1],self.identifier,body='late fixture reply',idempotency_key='reply',delivery='inbox')
        with self.assertRaises(BusError) as error:self.ops.retention(apply_fingerprint=preview['fingerprint'])
        self.assertEqual(error.exception.code,'retention_preview_stale')
        current=self.ops.retention()
        self.assertIn('active_conversation',current['candidates'][0]['pins'])
        self.assertTrue(self.mailbox.show(self.actors[0],self.identifier)['body_retained'])

    def test_diagnostics_do_not_read_claim_or_expose_peer_content(self):
        value=self.ops.diagnostics()
        self.assertTrue(value['metadata_only'])
        self.assertNotIn('private operation fixture',str(value))
        self.assertEqual(value['states']['recipient'],{'unread':1})
        self.assertIsNone(self.mailbox.show(self.actors[0],self.identifier)['received_receipt_id'])

    def test_dedup_outside_advertised_ninety_day_horizon_is_visibly_refused(self):
        self.now += 90 * 86400
        retry = self.mailbox.send(self.actors[0], self.identities[1], body='private operation fixture',
            idempotency_key='request', delivery='inbox')
        self.assertEqual(retry['message']['message_id'], self.identifier)
        self.now += 1
        with self.assertRaises(BusError) as error:
            self.mailbox.send(self.actors[0], self.identities[1], body='private operation fixture',
                idempotency_key='request', delivery='inbox')
        self.assertEqual(error.exception.code, 'idempotency_horizon')
        with self.bus.connection() as database:
            self.assertEqual(database.execute('SELECT count(*) FROM mail_envelopes').fetchone()[0], 1)

    def expire_and_publish_fixture_signals(self):
        # Unit fixture only: installed qualification uses independent exact
        # committed projection acknowledgement, including expiry receipts.
        self.mailbox.list(self.actors[0], outbox=True)
        with self.bus.connection() as database:
            database.execute("UPDATE mail_outbox SET status='published' WHERE kind='receipt_signal'")

    def test_compaction_retains_terminal_identity_without_full_envelope(self):
        # This fixture qualifies the maintenance boundary only. Installed proof
        # must acknowledge projections through the production authority seam.
        self.terminal_with_fixture_published_signals()
        self.now += 31 * 86400
        before = self.mailbox.show(self.actors[0], self.identifier)
        with self.bus.connection() as database:
            database.execute("UPDATE mail_outbox SET status='published' WHERE kind='receipt_signal'")
        self.expire_and_publish_fixture_signals()
        preview = self.ops.compaction()
        self.assertEqual(preview['eligible'], [self.identifier])
        result = self.ops.compaction(apply_fingerprint=preview['fingerprint'])
        self.assertEqual(result['compacted'], 1)
        after = self.mailbox.show(self.actors[0], self.identifier)
        self.assertEqual(after['message_id'], before['message_id'])
        self.assertEqual(after['body_digest'], before['body_digest'])
        self.assertEqual(after['terminal_receipt_id'], before['terminal_receipt_id'])
        self.assertFalse(after['body_retained'])
        self.assertTrue(after['compacted'])
        with self.bus.connection() as database:
            self.assertEqual(database.execute(
                'SELECT count(*) FROM mail_envelopes WHERE message_id=?',
                (self.identifier,)).fetchone()[0], 0)
        retry = self.mailbox.send(self.actors[0], self.identities[1],
            body='private operation fixture', idempotency_key='request', delivery='inbox')
        self.assertTrue(retry['deduplicated'])
        self.assertEqual(retry['message']['message_id'], self.identifier)

    def test_compaction_pins_reply_and_stale_preview_preserves_full_envelope(self):
        self.terminal_with_fixture_published_signals()
        self.now += 31 * 86400
        self.expire_and_publish_fixture_signals()
        preview = self.ops.compaction()
        self.mailbox.reply(self.actors[1], self.identifier, body='reply keeps ancestor',
            idempotency_key='late-reply', delivery='inbox')
        with self.assertRaises(BusError) as error:
            self.ops.compaction(apply_fingerprint=preview['fingerprint'])
        self.assertEqual(error.exception.code, 'retention_preview_stale')
        current = self.ops.compaction()
        self.assertIn('retained_reply', current['candidates'][0]['pins'])
        self.assertTrue(self.mailbox.show(self.actors[0], self.identifier)['body_retained'])

    def test_compaction_rollback_and_repeat_preserve_identity(self):
        self.terminal_with_fixture_published_signals()
        self.now += 31 * 86400
        self.expire_and_publish_fixture_signals()
        preview = self.ops.compaction()
        def fault(stage):
            if stage == 'before_commit':
                raise RuntimeError('fixture interrupted compaction')
        self.mailbox.fault = fault
        with self.assertRaises(RuntimeError):
            self.ops.compaction(apply_fingerprint=preview['fingerprint'])
        self.mailbox.fault = None
        with self.bus.connection() as database:
            self.assertEqual(database.execute('SELECT count(*) FROM mail_tombstones').fetchone()[0], 0)
        self.assertTrue(self.mailbox.show(self.actors[0], self.identifier)['body_retained'])
        with self.bus.connection() as database:
            database.execute("UPDATE mail_outbox SET status='published' WHERE kind='receipt_signal'")
        self.expire_and_publish_fixture_signals()
        preview = self.ops.compaction()
        self.ops.compaction(apply_fingerprint=preview['fingerprint'])
        self.assertEqual(self.ops.compaction()['eligible'], [])
        self.assertEqual(self.mailbox.list(self.actors[0], outbox=True)['messages'][0]['message_id'], self.identifier)
        with self.assertRaises(BusError) as error:
            self.mailbox.reply(self.actors[1], self.identifier, body='new intent',
                idempotency_key='after-compaction', delivery='inbox')
        self.assertEqual(error.exception.code, 'message_compacted')

    def test_legacy_schema_requires_explicit_atomic_migration(self):
        legacy, operator = BusStore.configure(self.root / 'legacy-bus')
        with legacy.connection() as database:
            database.executescript((Path(__file__).parent / 'fixtures' / 'a2a_mailbox_v1.sql').read_text())
        with self.assertRaises(BusError) as error:
            Mailbox(legacy)
        self.assertEqual(error.exception.code, 'unsupported_mailbox_schema')
        actual = Mailbox._migrate_identity
        def interrupted(database):
            actual(database)
            raise RuntimeError('fixture interrupted migration')
        with patch.object(Mailbox, '_migrate_identity', side_effect=interrupted):
            with self.assertRaises(RuntimeError):
                Mailbox.migrate(legacy, operator)
        with legacy.connection() as database:
            self.assertEqual(database.execute("SELECT value FROM meta WHERE key='mailbox_schema'").fetchone()[0], '1')
            self.assertIsNone(database.execute("SELECT name FROM sqlite_master WHERE name='mail_identities'").fetchone())
        self.assertTrue(Mailbox.migrate(legacy, operator).startswith('receipt_'))
        Mailbox(legacy)
        self.assertEqual(Mailbox.migrate(legacy, operator), 'already_current')
        # This enforces the old schema guard; installed old-binary proof is separate.
        with patch('codex_wake.a2a_mailbox.MAILBOX_SCHEMA', 1):
            with self.assertRaises(BusError) as error:
                Mailbox(legacy)
        self.assertEqual(error.exception.code, 'unsupported_mailbox_schema')

    def test_tombstone_retirement_preserves_horizon_refusal_and_audit(self):
        self.terminal_with_fixture_published_signals()
        self.now += 31 * 86400
        self.expire_and_publish_fixture_signals()
        preview = self.ops.compaction()
        self.ops.compaction(apply_fingerprint=preview['fingerprint'])
        self.now = 1000. + 90 * 86400
        self.assertEqual(self.ops.compaction()['eligible'], [])
        retry = self.mailbox.send(self.actors[0], self.identities[1],
            body='private operation fixture', idempotency_key='request', delivery='inbox')
        self.assertEqual(retry['message']['message_id'], self.identifier)
        self.now += 1
        self.expire_and_publish_fixture_signals()
        preview = self.ops.compaction()
        self.assertEqual(preview['eligible'], [self.identifier])
        self.assertEqual(preview['candidates'][0]['action'], 'retire')
        result = self.ops.compaction(apply_fingerprint=preview['fingerprint'])
        self.assertEqual(result['retired'], 1)
        with self.assertRaises(BusError) as error:
            self.mailbox.send(self.actors[0], self.identities[1],
                body='private operation fixture', idempotency_key='request', delivery='inbox')
        self.assertEqual(error.exception.code, 'idempotency_horizon')
        with self.bus.connection() as database:
            for table in ('mail_tombstones','mail_state','mail_receipts','mail_outbox','mail_identities'):
                self.assertEqual(database.execute('SELECT count(*) FROM ' + table + ' WHERE message_id=?', (self.identifier,)).fetchone()[0], 0)
            self.assertEqual(database.execute('SELECT count(*) FROM mail_retired_keys').fetchone()[0], 1)
            self.assertIsNotNone(database.execute('SELECT 1 FROM events WHERE receipt_id=?', (result['receipt_id'],)).fetchone())
            self.assertEqual(database.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(self.ops.compaction()['eligible'], [])

    def test_physical_reclaim_requires_pause_and_preserves_logical_identity(self):
        large = self.mailbox.send(self.actors[0], self.identities[1],
            body='x' * 32768, idempotency_key='large', delivery='inbox')['message']['message_id']
        self.mailbox.ack(self.actors[1], large, outcome='declined')
        self.now += 31 * 86400
        with self.bus.connection() as database:
            database.execute("UPDATE mail_outbox SET status='published' WHERE kind='receipt_signal'")
        self.expire_and_publish_fixture_signals()
        preview = self.ops.compaction()
        self.ops.compaction(apply_fingerprint=preview['fingerprint'])
        self.bus.set_paused(False, self.operator)
        with self.assertRaises(BusError) as error:
            self.ops.reclaim_space()
        self.assertEqual(error.exception.code, 'maintenance_requires_pause')
        self.bus.set_paused(True, self.operator)
        result = self.ops.reclaim_space()
        self.assertLess(result['after_bytes'], result['before_bytes'])
        self.assertTrue(self.mailbox.show(self.actors[0], large)['compacted'])
        with self.bus.connection() as database:
            self.assertEqual(database.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(database.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_busy_physical_maintenance_preserves_reconciliation_receipt(self):
        self.bus.set_paused(True, self.operator)
        with self.bus.connection(read_only=True) as reader:
            reader.execute('BEGIN')
            reader.execute('SELECT count(*) FROM events').fetchone()
            with self.assertRaises(BusError) as error:
                self.ops.reclaim_space()
            self.assertEqual(error.exception.code, 'maintenance_incomplete')
            requested = error.exception.details['receipt_id']
        with self.bus.connection() as database:
            row = database.execute('SELECT action FROM events WHERE receipt_id=?', (requested,)).fetchone()
            self.assertEqual(row['action'], 'space_reclaim_requested')
        self.assertTrue(self.mailbox.show(self.actors[0], self.identifier)['body_retained'])

    def test_retirement_interruption_rolls_back_key_and_message_deletion(self):
        self.terminal_with_fixture_published_signals()
        self.now += 31 * 86400
        self.expire_and_publish_fixture_signals()
        preview = self.ops.compaction()
        self.ops.compaction(apply_fingerprint=preview['fingerprint'])
        self.now += 60 * 86400
        self.expire_and_publish_fixture_signals()
        preview = self.ops.compaction()
        def fault(stage):
            if stage == 'before_commit':
                raise RuntimeError('fixture interrupted retirement')
        self.mailbox.fault = fault
        with self.assertRaises(RuntimeError):
            self.ops.compaction(apply_fingerprint=preview['fingerprint'])
        self.mailbox.fault = None
        with self.bus.connection() as database:
            self.assertEqual(database.execute('SELECT count(*) FROM mail_retired_keys').fetchone()[0], 0)
            self.assertEqual(database.execute('SELECT count(*) FROM mail_tombstones').fetchone()[0], 1)
        self.ops.compaction(apply_fingerprint=preview['fingerprint'])
        self.mailbox.max_messages = 1
        with self.assertRaises(BusError) as error:
            self.mailbox.send(self.actors[0], self.identities[1], body='new explicit intent',
                idempotency_key='new-key', delivery='inbox')
        self.assertEqual(error.exception.code, 'capacity')

    def test_reclaim_completion_fault_preserves_requested_receipt(self):
        count = 0
        def fault(stage):
            nonlocal count
            if stage == 'before_commit':
                count += 1
                if count == 2:
                    raise RuntimeError('fixture interrupted maintenance completion')
        self.mailbox.fault = fault
        with self.assertRaises(BusError) as error:
            self.ops.reclaim_space()
        self.mailbox.fault = None
        self.assertEqual(error.exception.code, 'maintenance_incomplete')
        with self.bus.connection() as database:
            row = database.execute('SELECT action FROM events WHERE receipt_id=?',
                (error.exception.details['receipt_id'],)).fetchone()
            self.assertEqual(row['action'], 'space_reclaim_requested')
        self.assertTrue(self.mailbox.show(self.actors[0], self.identifier)['body_retained'])

    def test_compaction_projects_expiry_before_clearing_pending_notification(self):
        identifier = self.mailbox.send(self.actors[0], self.identities[1], body='expired notification fixture',
            idempotency_key='notify-expiry', delivery='notify')['message']['message_id']
        self.mailbox.ack(self.actors[1], identifier, outcome='declined')
        self.now += 31 * 86400
        with self.bus.connection() as database:
            database.execute("UPDATE mail_outbox SET status='published' WHERE kind='receipt_signal'")
        preview = self.ops.compaction()
        self.assertNotIn(identifier, preview['eligible'])
        candidate = next(item for item in preview['candidates'] if item['message_id']==identifier)
        self.assertIn('unprojected_receipt_signal', candidate['pins'])
        with self.bus.connection() as database:
            state = database.execute('SELECT admission,notification FROM mail_state WHERE message_id=?', (identifier,)).fetchone()
            self.assertEqual(tuple(state), ('expired','suppressed'))
