from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox


class MailboxTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.repo = root / 'repo'; self.repo.mkdir()
        self.bus, self.operator = BusStore.configure(root / 'bus')
        self.bus.enroll(self.repo, self.operator)
        self.identities = [RuntimeIdentity('runtime', identifier, str(self.repo)) for identifier in ['sender','recipient','foreign']]
        self.actors = []
        for identity in self.identities:
            capability, _ = self.bus.issue_actor(identity, self.repo, self.operator)
            self.actors.append(self.bus.authenticate(capability, identity, invoking_cwd=self.repo))
        self.sender, self.recipient, self.foreign = self.actors
        Mailbox.migrate(self.bus, self.operator)
        self.now = 1000.0
        self.mailbox = Mailbox(self.bus, clock=lambda: self.now, monotonic=lambda: self.now)

    def send(self, key='request', **kwargs):
        return self.mailbox.send(self.sender, self.identities[1], body='Fixture request', idempotency_key=key, **kwargs)

    def test_disposition_lookup_survives_display_truncation_and_checks_authority(self):
        identifier = self.send()['message']['message_id']
        with self.mailbox.transaction() as database:
            for _ in range(100):
                self.mailbox._record(database, identifier, 'deferred', 'scheduler', self.now)
            database.execute('COMMIT')
        accepted = self.mailbox.ack(self.recipient, identifier, outcome='accepted')
        self.mailbox.ack(self.recipient, identifier, outcome='completed')
        displayed = self.mailbox.show(self.sender, identifier)
        self.assertTrue(displayed['receipts_truncated'])
        self.assertFalse(any(r['kind'] == 'accepted' for r in displayed['receipts']))
        receipt = self.mailbox.disposition_receipt(self.sender, identifier, 'accepted')
        self.assertEqual(receipt['receipt_id'], accepted['receipt_id'])
        with self.assertRaises(BusError):
            self.mailbox.disposition_receipt(self.foreign, identifier, 'accepted')
        self.bus.revoke_actor(self.sender.actor_id, self.operator)
        with self.assertRaises(BusError):
            self.mailbox.disposition_receipt(self.sender, identifier, 'accepted')

    def test_durable_envelope_separate_notification_and_received_receipts(self):
        admitted = self.send()
        identifier = admitted['message']['message_id']
        self.assertEqual(admitted['message']['state'], dict(admission='accepted',notification='pending',recipient='unread'))
        self.assertNotIn('body', self.mailbox.show(self.sender, identifier))
        reopened = Mailbox(BusStore(self.bus.root), clock=lambda: self.now, monotonic=lambda: self.now)
        received = reopened.read(self.recipient, identifier)
        self.assertEqual(received['body'], 'Fixture request')
        self.assertEqual(received['message']['state']['recipient'], 'received')
        self.assertEqual(received['message']['state']['notification'], 'pending')
        self.assertEqual(received['peer_content_trust'], 'untrusted')
        self.assertEqual(reopened.read(self.recipient, identifier)['receipt_id'], received['receipt_id'])
        with self.bus.connection() as database:
            payloads = [row['payload'] for row in database.execute('SELECT payload FROM mail_outbox')]
        self.assertTrue(all('Fixture request' not in payload for payload in payloads))

    def test_concurrent_identical_acceptance_has_one_envelope_and_fifo_slot(self):
        with ThreadPoolExecutor(max_workers=4) as workers:
            values = list(workers.map(lambda _: self.send(), range(4)))
        self.assertEqual(len({v['message']['message_id'] for v in values}), 1)
        self.assertEqual(sum(not v['deduplicated'] for v in values), 1)
        next_message = self.send('second')
        self.assertEqual(next_message['message']['recipient_sequence'], 2)

    def test_retry_preserves_original_expiry_and_changed_ttl_conflicts(self):
        first = self.send(ttl=60)
        self.now += 10
        retry = self.send(ttl=60)
        self.assertEqual(retry['message']['expires_at'], first['message']['expires_at'])
        with self.assertRaises(BusError) as error:
            self.send(ttl=61)
        self.assertEqual(error.exception.code, 'idempotency_conflict')

    def test_explicit_reopening_survives_restart_and_retry_cannot_change_it(self):
        original = self.send(resume_missing=True)['message']
        restarted = Mailbox(BusStore(self.bus.root), clock=lambda: self.now, monotonic=lambda: self.now)
        stored = restarted.show(self.sender, original['message_id'])
        self.assertEqual(stored['resume_policy'], 'same_thread')
        self.assertEqual(stored['notification_authority']['recipient']['generation'], 1)
        self.assertTrue(self.send(resume_missing=True)['deduplicated'])
        with self.assertRaises(BusError) as error:
            self.send(resume_missing=False)
        self.assertEqual(error.exception.code, 'idempotency_conflict')
        default = self.send('default')['message']
        self.assertEqual(default.get('resume_policy', 'hold'), 'hold')

    def test_interruption_before_commit_leaves_no_message(self):
        def interrupt(stage):
            if stage == 'before_commit': raise RuntimeError('fixture crash')
        self.mailbox.fault = interrupt
        with self.assertRaises(RuntimeError): self.send()
        with self.bus.connection() as database:
            self.assertEqual(database.execute('SELECT count(*) FROM mail_envelopes').fetchone()[0], 0)
            self.assertEqual(database.execute('SELECT count(*) FROM mail_outbox').fetchone()[0], 0)

    def test_interruption_after_commit_returns_original_reconciliation_pointer(self):
        def interrupt(stage):
            if stage == 'after_commit': raise RuntimeError('fixture disconnect')
        self.mailbox.fault = interrupt
        with self.assertRaises(BusError) as error: self.send()
        self.assertEqual(error.exception.code, 'effect_uncertain')
        identifier = error.exception.details['message_id']
        self.mailbox.fault = None
        self.assertEqual(self.send()['message']['message_id'], identifier)
        self.assertTrue(self.send()['deduplicated'])

    def test_read_is_not_claim_duplicate_claim_cannot_restart_processing(self):
        identifier = self.send()['message']['message_id']
        self.mailbox.read(self.recipient, identifier)
        self.assertIsNone(self.mailbox.show(self.recipient, identifier)['claim_receipt_id'])
        first = self.mailbox.ack(self.recipient, identifier, outcome='accepted')
        duplicate = self.mailbox.ack(self.recipient, identifier, outcome='accepted')
        self.assertTrue(first['claimed']); self.assertFalse(duplicate['claimed'])
        self.assertEqual(first['receipt_id'], duplicate['receipt_id'])
        self.mailbox.ack(self.recipient, identifier, outcome='completed', evidence='/fixture/result')
        self.assertFalse(self.mailbox.ack(self.recipient, identifier, outcome='accepted')['claimed'])
        with self.assertRaises(BusError):
            self.mailbox.ack(self.recipient, identifier, outcome='failed')

    def test_expiry_prevents_first_claim_but_allows_preexpiry_claim_to_complete(self):
        pending = self.send('pending', ttl=1)['message']['message_id']
        claimed = self.send('claimed', ttl=1)['message']['message_id']
        self.mailbox.ack(self.recipient, claimed, outcome='accepted')
        self.now += 2
        with self.assertRaises(BusError) as error:
            self.mailbox.ack(self.recipient, pending, outcome='accepted')
        self.assertEqual(error.exception.code, 'not_processable')
        finished = self.mailbox.ack(self.recipient, claimed, outcome='completed')
        self.assertEqual(finished['message']['state']['admission'], 'expired')
        self.assertEqual(finished['message']['state']['recipient'], 'completed')

    def test_cancel_suppresses_intent_and_cannot_retract_received_or_dispatching(self):
        identifier = self.send()['message']['message_id']
        cancelled = self.mailbox.cancel(self.sender, identifier)
        self.assertEqual(cancelled['message']['state']['admission'], 'cancelled')
        with self.bus.connection() as database:
            self.assertEqual(database.execute("SELECT status FROM mail_outbox WHERE kind='notification'").fetchone()[0], 'suppressed')
        with self.assertRaises(BusError): self.mailbox.ack(self.recipient, identifier, outcome='accepted')
        consumed = self.send('consumed')['message']['message_id']
        self.mailbox.read(self.recipient, consumed)
        with self.assertRaises(BusError) as error: self.mailbox.cancel(self.sender, consumed)
        self.assertEqual(error.exception.code, 'too_late')
        dispatching = self.send('dispatching')['message']['message_id']
        with self.bus.connection() as database:
            database.execute("UPDATE mail_state SET notification='dispatching' WHERE message_id=?", (dispatching,))
        with self.assertRaises(BusError): self.mailbox.cancel(self.sender, dispatching)

    def test_reply_lineage_permission_and_optional_ack_are_atomic(self):
        identifier = self.send()['message']['message_id']
        with self.assertRaises(BusError):
            self.mailbox.reply(self.foreign, identifier, body='Fixture reply', idempotency_key='reply')
        with self.assertRaises(BusError):
            self.mailbox.reply(self.recipient, identifier, body='Fixture reply', idempotency_key='reply', outcome='completed')
        with self.bus.connection() as database:
            self.assertEqual(database.execute('SELECT count(*) FROM mail_envelopes').fetchone()[0], 1)
        reply = self.mailbox.reply(self.recipient, identifier, body='Fixture reply', idempotency_key='reply', outcome='accepted')
        self.assertEqual(reply['message']['in_reply_to'], identifier)
        self.assertEqual(reply['message']['hop_count'], 1)
        self.assertEqual(reply['message']['conversation_id'], self.mailbox.show(self.sender, identifier)['conversation_id'])
        self.assertEqual(self.mailbox.show(self.recipient, identifier)['state']['recipient'], 'accepted')
        self.assertEqual(self.mailbox.read(self.sender, reply['message']['message_id'])['body'], 'Fixture reply')
        self.assertEqual(len(self.mailbox.replies(self.sender, identifier)), 1)
        with self.assertRaises(BusError) as error:
            self.mailbox.reply(self.recipient, identifier, body='Fixture reply', idempotency_key='reply', outcome=None)
        self.assertEqual(error.exception.code, 'idempotency_conflict')

    def test_foreign_access_sender_read_and_operator_inspection_do_not_fake_receipt(self):
        identifier = self.send()['message']['message_id']
        for action in [self.mailbox.show,self.mailbox.read]:
            with self.assertRaises(BusError): action(self.foreign, identifier)
        self.assertEqual(self.mailbox.read(self.sender, identifier)['message']['state']['recipient'], 'unread')
        inspected = self.mailbox.operator_inspect(self.operator, identifier, body=True)
        self.assertEqual(inspected['body'], 'Fixture request')
        self.assertIsNone(inspected['message']['received_receipt_id'])

    def test_capacity_rate_body_and_inbox_only_are_enforced_before_admission(self):
        self.mailbox.max_open = 1
        identifier = self.send(delivery='inbox')['message']['message_id']
        self.assertEqual(self.mailbox.show(self.sender, identifier)['state']['notification'], 'suppressed')
        with self.assertRaises(BusError) as error: self.send('over-capacity')
        self.assertEqual(error.exception.code, 'capacity')
        self.mailbox.ack(self.recipient, identifier, outcome='declined')
        self.mailbox.rate_limit = 1
        with self.assertRaises(BusError) as error: self.send('over-rate')
        self.assertEqual(error.exception.code, 'rate_limit')
        with self.assertRaises(BusError) as error:
            self.mailbox.send(self.sender, self.identities[1], body='x'*32769, idempotency_key='oversized')
        self.assertEqual(error.exception.code, 'body_limit')

    def test_unknown_domain_migration_and_clock_regression_fail_closed(self):
        self.assertEqual(Mailbox.migrate(self.bus, self.operator), 'already_current')
        self.send()
        self.now -= 5
        with self.assertRaises(BusError) as error: self.send('clock-regression')
        self.assertEqual(error.exception.code, 'clock_anomaly')
        with self.bus.connection() as database:
            database.execute("UPDATE meta SET value='999' WHERE key='mailbox_schema'")
        with self.assertRaises(BusError) as error: Mailbox(self.bus)
        self.assertEqual(error.exception.code, 'unsupported_mailbox_schema')

    def test_envelopes_are_immutable_and_body_digest_is_checked(self):
        identifier = self.send()['message']['message_id']
        with self.bus.connection() as database:
            with self.assertRaises(sqlite3.IntegrityError):
                database.execute("UPDATE mail_envelopes SET envelope='{}' WHERE message_id=?", (identifier,))
            database.execute('DROP TRIGGER mail_body_immutable')
            database.execute("UPDATE mail_bodies SET body='altered' WHERE message_id=?", (identifier,))
        with self.assertRaises(BusError): self.mailbox.read(self.recipient, identifier)
        self.assertIsNone(self.mailbox.show(self.sender, identifier)['received_receipt_id'])

    def test_rejection_has_bounded_body_free_durable_receipt(self):
        self.mailbox.max_open=1
        self.send()
        with self.assertRaises(BusError) as error: self.send('capacity-rejected')
        self.assertTrue(error.exception.details['rejection_receipt_id'])
        with self.bus.connection() as database:
            rejected=database.execute("SELECT subject FROM events WHERE action='message_rejected'").fetchone()[0]
        self.assertNotIn('Fixture request',rejected)
        self.assertEqual(json.loads(rejected)['code'],'capacity')

    def test_lineage_bound_and_recipient_filter_do_not_create_wrong_work(self):
        current=self.send(delivery='inbox')['message']['message_id']
        actor=self.recipient
        for hop in range(1,9):
            response=self.mailbox.reply(actor,current,body='Fixture reply',idempotency_key='hop-'+str(hop),delivery='inbox')
            self.assertEqual(response['message']['hop_count'],hop)
            current=response['message']['message_id']
            actor=self.sender if actor == self.recipient else self.recipient
        with self.assertRaises(BusError) as error:
            self.mailbox.reply(actor,current,body='Fixture reply',idempotency_key='hop-9',delivery='inbox')
        self.assertEqual(error.exception.code,'lineage_limit')
        self.assertEqual(self.mailbox.list(self.recipient,state='accepted')['messages'],[])

    def test_pending_thread_work_exposes_identifiers_without_message_bodies(self):
        identifier = self.send()['message']['message_id']
        work = self.mailbox.pending_thread_work('recipient')
        self.assertTrue(any(item['message_id'] == identifier for item in work))
        self.assertNotIn('Fixture request', json.dumps(work))
        self.assertEqual(self.mailbox.pending_thread_work('foreign'), [])
