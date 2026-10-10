"""Original processing claims survive authority generation changes without takeover."""
from pathlib import Path
import json
import tempfile
import unittest

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox


class ClaimReconciliationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.bus, self.operator = BusStore.configure(self.root / 'bus')
        self.bus.enroll(self.repo, self.operator)
        Mailbox.migrate(self.bus, self.operator)
        self.identities = [RuntimeIdentity('claim-fixture', name, str(self.repo)) for name in ['sender', 'recipient']]
        self.actors = []
        for identity in self.identities:
            cap, _ = self.bus.issue_actor(identity, self.repo, self.operator)
            self.actors.append(self.bus.authenticate(cap, identity, invoking_cwd=self.repo))
        self.mailbox = Mailbox(self.bus, clock=lambda: 1000.0, monotonic=lambda: 1000.0)
        self.message = self.mailbox.send(self.actors[0], self.identities[1], body='Owned fixture task',
            idempotency_key='one-original-claim', delivery='inbox')['message']['message_id']
        self.claim = self.mailbox.ack(self.actors[1], self.message, outcome='accepted')
        self.assertTrue(self.claim['claimed'])

    def rotate(self):
        cap, _ = self.bus.rotate_actor(self.actors[1].actor_id, self.operator)
        return self.bus.authenticate(cap, self.identities[1], invoking_cwd=self.repo)

    def test_terminal_evidence_survives_rotation_without_granting_a_second_start(self):
        terminal = self.mailbox.ack(self.actors[1], self.message, outcome='completed', evidence='fixture:result')
        current = self.rotate()
        value = self.mailbox.reconcile(current, self.message)
        processing = value['processing_reconciliation']
        self.assertEqual(processing['state'], 'known_terminal')
        self.assertEqual(processing['terminal_receipt_id'], terminal['receipt_id'])
        self.assertEqual(processing['terminal_outcome'], 'completed')
        self.assertEqual(processing['claim_receipt_id'], self.claim['receipt_id'])
        self.assertFalse(value['grants_new_processing'])

    def test_metadata_reconciliation_needs_no_clock_and_operator_is_audited(self):
        def unavailable():
            raise AssertionError('metadata inspection must not acquire time')
        mailbox = Mailbox(self.bus, clock=unavailable, monotonic=unavailable)
        value = mailbox.reconcile(self.actors[1], self.message)
        self.assertEqual(value['processing_reconciliation']['state'], 'already_claimed')
        inspected = mailbox.operator_reconcile(self.operator, self.message)
        self.assertEqual(inspected['time_status'], 'not_observed')
        self.assertTrue(inspected['receipt_id'])
        self.assertNotEqual(inspected['receipt_id'], mailbox.operator_reconcile(self.operator, self.message)['receipt_id'])
        self.assertEqual(value['message']['receipts'],
                         mailbox.reconcile(self.actors[0], self.message)['message']['receipts'])

    def test_repeated_acceptance_and_reconciliation_do_not_grant_another_start(self):
        before = self.mailbox.reconcile(self.actors[1], self.message)
        repeated = self.mailbox.ack(self.actors[1], self.message, outcome='accepted')
        self.assertFalse(repeated['claimed'])
        self.assertTrue(repeated['deduplicated'])
        self.assertEqual(repeated['receipt_id'], self.claim['receipt_id'])
        after = self.mailbox.reconcile(self.actors[1], self.message)
        self.assertEqual(before, after)
        self.assertFalse(after['grants_new_processing'])

    def test_unclaimed_metadata_does_not_itself_authorize_processing(self):
        identifier = self.mailbox.send(self.actors[0], self.identities[1], body='Separate fixture',
            idempotency_key='unclaimed-fixture', delivery='inbox')['message']['message_id']
        value = self.mailbox.reconcile(self.actors[1], identifier)
        self.assertEqual(value['processing_reconciliation']['state'], 'unclaimed')
        self.assertIsNone(value['processing_reconciliation']['claim_receipt_id'])
        self.assertFalse(value['grants_new_processing'])

    def test_new_generation_reconciles_original_unknown_claim_without_permission_to_repeat(self):
        current = self.rotate()
        value = self.mailbox.reconcile(current, self.message)
        self.assertEqual(value['processing_reconciliation']['state'], 'held_for_original_claim')
        self.assertEqual(value['processing_reconciliation']['claim_receipt_id'], self.claim['receipt_id'])
        self.assertEqual(value['processing_reconciliation']['owner_generation'], 1)
        self.assertEqual(value['processing_reconciliation']['current_generation'], 2)
        self.assertFalse(value['grants_new_processing'])
        self.assertEqual(value['message']['state']['recipient'], 'accepted')
        self.assertIsNone(value['processing_reconciliation']['terminal_receipt_id'])
        self.assertNotIn('Owned fixture task', json.dumps(value))
        for outcome in ['accepted', 'completed', 'failed', 'declined']:
            with self.subTest(outcome=outcome):
                with self.assertRaises(BusError) as denied:
                    self.mailbox.ack(current, self.message, outcome=outcome)
                self.assertEqual(denied.exception.code, 'claim_fenced')
        with self.assertRaises(BusError) as stale:
            self.mailbox.ack(self.actors[1], self.message, outcome='completed')
        self.assertEqual(stale.exception.code, 'authorization_denied')
