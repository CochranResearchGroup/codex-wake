from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_receipt_signals import ReceiptSignalAdapter
from codex_wake.event_wake import EventWake
from codex_wake.signals import Degraded, EvaluationLimits, Ingested, Matched, NotReady, Registration
from tests.test_signal_store import make_module
from tests.test_signals import make_intent


class ReceiptBridgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'repo'; self.repo.mkdir()
        self.bus, self.operator = BusStore.configure(self.root / 'bus')
        self.bus.enroll(self.repo, self.operator)
        self.identities = [RuntimeIdentity('fixture', name, str(self.repo)) for name in ('sender','recipient','foreign')]
        self.actors = []
        for identity in self.identities:
            cap, _ = self.bus.issue_actor(identity, self.repo, self.operator)
            self.actors.append(self.bus.authenticate(cap, identity, invoking_cwd=self.repo))
        Mailbox.migrate(self.bus, self.operator)
        self.now = 1000.
        self.mailbox = Mailbox(self.bus, clock=lambda: self.now, monotonic=lambda: self.now)
        self.identifier = self.mailbox.send(self.actors[0], self.identities[1], body='private fixture request',
                    idempotency_key='request', delivery='inbox')['message']['message_id']
        self.module = make_module(self.root / 'signals.sqlite')
        self.adapter = ReceiptSignalAdapter(self.mailbox, self.actors[0], self.identifier)

    def arm(self, condition='reply'):
        now = datetime.fromtimestamp(self.now, timezone.utc)
        wake = EventWake(self.module, adapters=[self.adapter], clock=lambda: now, id_factory=lambda: 'wake_receipt_fixture')
        result = wake.register(replace(make_intent(), when=self.adapter.request(condition)), idempotency_key='fixture-arm')
        self.assertIsInstance(result, Registration)
        # The engine exposes its durable arms for restored runner operation.
        return self.module.load_armed_signal(result.wake_id)

    def test_exact_reply_can_replay_and_match_without_body_or_notification(self):
        armed = self.arm()
        mirrored = self.adapter.mirror(self.module)
        self.assertIsInstance(mirrored, Ingested)
        now = datetime.fromtimestamp(self.now, timezone.utc)
        self.assertIsInstance(self.module.evaluate(armed.wake_id, armed, now, EvaluationLimits(max_candidates=100)), NotReady)
        self.mailbox.reply(self.actors[1], self.identifier, body='private fixture reply', idempotency_key='reply', delivery='inbox')
        self.assertIsInstance(self.adapter.mirror(self.module), Ingested)
        self.assertIsInstance(self.module.evaluate(armed.wake_id, armed, now, EvaluationLimits(max_candidates=100)), Matched)
        self.assertEqual(self.adapter.mirror(self.module)['status'], 'caught_up')
        with self.bus.connection() as database:
            self.assertEqual(database.execute('SELECT count(*) FROM mail_receipts').fetchone()[0], 2)
        self.assertNotIn(b'private fixture', (self.root / 'signals.sqlite').read_bytes())

    def test_receipt_before_arm_is_replayed_and_foreign_actor_refused(self):
        self.mailbox.read(self.actors[1], self.identifier)
        armed = self.arm('received')
        self.adapter.mirror(self.module)
        now = datetime.fromtimestamp(self.now, timezone.utc)
        self.assertIsInstance(self.module.evaluate(armed.wake_id, armed, now, EvaluationLimits(max_candidates=100)), Matched)
        with self.assertRaises(BusError): ReceiptSignalAdapter(self.mailbox, self.actors[2], self.identifier)

    def test_revocation_does_not_create_signal_evidence(self):
        self.arm()
        self.bus.revoke_actor(self.actors[0].actor_id, self.operator)
        self.assertIsInstance(self.adapter.mirror(self.module), Degraded)
        self.assertIsInstance(self.module.source_checkpoint('a2a.receipt', self.adapter.source_instance), type(None))

    def test_corrupt_signal_intent_is_refused_without_receipt_effect(self):
        self.arm()
        with self.bus.connection() as database:
            database.execute("UPDATE mail_outbox SET payload='{}' WHERE kind='receipt_signal'")
        self.assertIsInstance(self.adapter.mirror(self.module), Degraded)
        self.assertIsNone(self.module.source_checkpoint('a2a.receipt', self.adapter.source_instance))
        with self.bus.connection() as database:
            self.assertEqual(database.execute('SELECT count(*) FROM mail_receipts').fetchone()[0], 1)

    def test_interrupted_signal_commit_is_reconciled_by_original_checkpoint(self):
        self.arm()
        def crash(stage):
            if stage == 'after_ingest_commit':
                raise RuntimeError('fixture interrupted acknowledgement')
        interrupted = make_module(self.root / 'signals.sqlite', checkpoint=crash)
        self.assertIsInstance(self.adapter.mirror(interrupted), Degraded)
        self.assertEqual(self.adapter.mirror(self.module)['status'], 'caught_up')
