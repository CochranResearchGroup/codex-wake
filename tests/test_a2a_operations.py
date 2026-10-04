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
