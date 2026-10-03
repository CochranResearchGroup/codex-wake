"""Provider-free transaction and concurrency fault qualification."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
from threading import Barrier
import unittest

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox


class MailboxFaultTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.repo = root / 'repo'
        self.repo.mkdir()
        self.bus, self.operator = BusStore.configure(root / 'bus')
        self.bus.enroll(self.repo, self.operator)
        identities = [RuntimeIdentity('fixture-runtime', name, str(self.repo))
                      for name in ('sender', 'recipient')]
        actors = []
        for identity in identities:
            capability, _ = self.bus.issue_actor(identity, self.repo, self.operator)
            actors.append(self.bus.authenticate(capability, identity, invoking_cwd=self.repo))
        self.sender, self.recipient = actors
        self.target = identities[1]
        Mailbox.migrate(self.bus, self.operator)
        self.mailbox = Mailbox(self.bus, clock=lambda: 1000.0, monotonic=lambda: 1000.0)

    def send(self, key='fixture'):
        return self.mailbox.send(self.sender, self.target, body='fault fixture',
                                 idempotency_key=key, delivery='inbox')

    def counts(self):
        with self.bus.connection() as database:
            return tuple(database.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                         for table in ('mail_envelopes', 'mail_state', 'mail_receipts', 'mail_outbox', 'events'))

    def test_sqlite_busy_refuses_admission_then_original_intent_can_retry(self):
        before = self.counts()
        blocker = sqlite3.connect(self.bus.path, isolation_level=None)
        try:
            blocker.execute('BEGIN IMMEDIATE')
            with self.assertRaises(BusError) as caught:
                self.send()
            self.assertEqual(caught.exception.code, 'store_unavailable')
        finally:
            blocker.close()
        self.assertEqual(self.counts(), before)
        self.assertFalse(self.send()['deduplicated'])

    def test_disk_full_before_commit_rolls_back_all_admission_effects(self):
        before = self.counts()
        stages = []

        def disk_full(stage):
            stages.append(stage)
            if stage == 'before_commit':
                raise sqlite3.OperationalError('database or disk is full')

        self.mailbox.fault = disk_full
        with self.assertRaises(BusError) as caught:
            self.send()
        self.assertEqual(caught.exception.code, 'store_unavailable')
        self.assertEqual(stages, ['before_commit'])
        self.assertEqual(self.counts(), before)
        self.mailbox.fault = None
        admitted = self.send()
        self.assertFalse(admitted['deduplicated'])
        self.assertEqual(admitted['message']['recipient_sequence'], 1)

    def test_corrupt_store_refused_without_recreating_or_resetting_bytes(self):
        corrupt = b'not a SQLite journal\x00' * 100
        self.bus.path.write_bytes(corrupt)
        with self.assertRaises(BusError) as caught:
            BusStore(self.bus.root)
        self.assertEqual(caught.exception.code, 'store_unavailable')
        self.assertEqual(self.bus.path.read_bytes(), corrupt)
        with self.assertRaises(BusError):
            Mailbox(self.bus)
        self.assertEqual(self.bus.path.read_bytes(), corrupt)

    def test_revoked_authenticated_actor_has_no_mailbox_effects(self):
        identifier = self.send()['message']['message_id']
        self.bus.revoke_actor(self.recipient.actor_id, self.operator)
        before = self.counts()
        operations = [lambda: self.mailbox.read(self.recipient, identifier),
                      lambda: self.mailbox.ack(self.recipient, identifier, outcome='accepted'),
                      lambda: self.mailbox.list(self.recipient)]
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(BusError) as caught:
                    operation()
                self.assertEqual(caught.exception.code, 'authorization_denied')
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.mailbox.show(self.sender, identifier)['state']['recipient'], 'unread')
        self.bus.revoke_actor(self.sender.actor_id, self.operator)
        before = self.counts()
        with self.assertRaises(BusError) as caught:
            self.send('revoked-sender')
        self.assertEqual(caught.exception.code, 'authorization_denied')
        self.assertEqual(self.counts(), before)

    def test_concurrent_distinct_sends_have_unique_contiguous_fifo_slots(self):
        gate = Barrier(4)

        def send(index):
            gate.wait(timeout=5)
            return self.send('distinct-' + str(index))['message']

        with ThreadPoolExecutor(max_workers=4) as workers:
            values = list(workers.map(send, range(4)))
        ordered = sorted(values, key=lambda value: value['recipient_sequence'])
        self.assertEqual([value['recipient_sequence'] for value in ordered], [1, 2, 3, 4])
        self.assertEqual(len({value['message_id'] for value in values}), 4)
        inbox = self.mailbox.list(self.recipient)['messages']
        self.assertEqual([value['message_id'] for value in inbox],
                         [value['message_id'] for value in ordered])

    def test_cancellation_and_first_claim_race_have_one_serialized_winner(self):
        identifier = self.send()['message']['message_id']
        gate = Barrier(2)

        def attempt(claim):
            gate.wait(timeout=5)
            try:
                value = (self.mailbox.ack(self.recipient, identifier, outcome='accepted')
                         if claim else self.mailbox.cancel(self.sender, identifier))
                return claim, value, None
            except BusError as error:
                return claim, None, error.code

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = list(workers.map(attempt, (False, True)))
        winners = [entry for entry in outcomes if entry[2] is None]
        self.assertEqual(len(winners), 1, outcomes)
        winner_claim = winners[0][0]
        loser = next(entry for entry in outcomes if entry[2] is not None)
        self.assertEqual(loser[2], 'too_late' if winner_claim else 'not_processable')
        state = self.mailbox.show(self.sender, identifier)['state']
        self.assertEqual(state['admission'], 'accepted' if winner_claim else 'cancelled')
        self.assertEqual(state['recipient'], 'accepted' if winner_claim else 'unread')
        with self.bus.connection() as database:
            kinds = [row[0] for row in database.execute(
                "SELECT kind FROM mail_receipts WHERE message_id=? AND kind IN ('accepted','cancelled')",
                (identifier,))]
        self.assertEqual(kinds, ['accepted' if winner_claim else 'cancelled'])

    def test_simultaneous_identical_terminal_ack_has_one_durable_receipt(self):
        identifier = self.send()['message']['message_id']
        self.mailbox.ack(self.recipient, identifier, outcome='accepted')
        gate = Barrier(4)

        def complete(_):
            gate.wait(timeout=5)
            return self.mailbox.ack(self.recipient, identifier, outcome='completed',
                                    evidence='/fixture/result')

        with ThreadPoolExecutor(max_workers=4) as workers:
            values = list(workers.map(complete, range(4)))
        self.assertEqual(len({value['receipt_id'] for value in values}), 1)
        self.assertEqual(sum(not value['deduplicated'] for value in values), 1)
        self.assertTrue(all(value['message']['state']['recipient'] == 'completed' for value in values))
        with self.bus.connection() as database:
            count = database.execute("SELECT count(*) FROM mail_receipts WHERE message_id=? AND kind='completed'",
                                     (identifier,)).fetchone()[0]
        self.assertEqual(count, 1)
