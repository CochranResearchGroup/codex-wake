"""Durable projection proof clears pins only with separate operator authority."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
from tests import test_a2a_receipt_authority as fixture
from codex_wake.a2a_operations import MailOperations
from codex_wake.a2a_receipt_authority import ConfiguredReceiptAuthority
from codex_wake.a2a_identity import BusError


class ProjectionAckTests(unittest.TestCase):
    setUp = fixture.ConfiguredReceiptTests.setUp
    write_config = fixture.ConfiguredReceiptTests.write_config
    arm = fixture.ConfiguredReceiptTests.arm
    mailbox_counts = fixture.ConfiguredReceiptTests.mailbox_counts

    def acknowledge(self, **kwargs):
        return MailOperations(self.mailbox, self.operator).acknowledge_projections(
            self.wake_root, self.config, self.adapter.source_instance, **kwargs)

    def pending(self):
        with self.bus.connection() as db:
            return db.execute("SELECT count(*) FROM mail_outbox WHERE kind='receipt_signal' AND status!='published'").fetchone()[0]

    def terminal(self):
        self.mailbox.ack(self.actors[1], self.identifier, outcome='declined')
        self.arm('declined')

    def test_real_projection_acknowledgement_unlocks_guarded_retention(self):
        self.terminal()
        self.assertEqual(self.acknowledge()['acknowledged'], 0)
        self.assertEqual(self.pending(), 2)
        self.adapter.mirror(self.module)
        self.assertEqual(self.acknowledge()['acknowledged'], 2)
        self.assertEqual(self.acknowledge()['acknowledged'], 0)
        self.assertEqual(self.pending(), 0)
        self.now += 31 * 86400
        operations = MailOperations(self.mailbox, self.operator)
        preview = operations.retention()
        self.assertEqual(preview['eligible'], [self.identifier])
        result = operations.retention(apply_fingerprint=preview['fingerprint'])
        self.assertEqual(result['pruned'], 1)
        self.assertFalse(self.mailbox.show(self.actors[0], self.identifier)['body_retained'])

    def test_fresh_cli_reports_body_free_exact_acknowledgement(self):
        self.terminal()
        self.adapter.mirror(self.module)
        executable = os.environ.get('CODEX_WAKE_RECEIPT_CLI')
        command = [executable] if executable else [sys.executable, '-m', 'codex_wake.cli']
        value = subprocess.run(command + ['a2a', 'ack-projections', '--bus-root', str(self.bus.root),
            '--operator-capability', str(self.operator), '--wake-root', str(self.wake_root),
            '--receipt-authority', str(self.config), '--source-instance', self.adapter.source_instance],
            text=True, capture_output=True, timeout=10)
        self.assertEqual(value.returncode, 0, value.stderr)
        self.assertEqual(json.loads(value.stdout)['projection']['acknowledged'], 2)
        self.assertNotIn('private fixture', value.stdout)
        self.assertNotIn(str(self.operator), value.stdout)
        self.assertEqual(self.pending(), 0)

    def test_wrong_operator_revocation_and_missing_journal_preserve_pins(self):
        self.terminal()
        self.adapter.mirror(self.module)
        with self.assertRaises(BusError):
            MailOperations(self.mailbox, self.root / 'absent').acknowledge_projections(
                self.wake_root, self.config, self.adapter.source_instance)
        self.write_config([])
        with self.assertRaises(BusError):
            self.acknowledge()
        self.write_config()
        journal = self.wake_root / 'signals' / 'journal.sqlite3'
        journal.unlink()
        with self.assertRaises(BusError):
            self.acknowledge()
        self.assertFalse(journal.exists())
        self.assertEqual(self.pending(), 2)

    def test_checkpoint_without_occurrences_and_corrupt_proof_do_not_clear_pins(self):
        self.terminal()
        self.adapter.mirror(self.module)
        with closing(self.module._connect()) as db:
            db.execute("UPDATE receipts SET content_fingerprint='corrupt'")
        with self.assertRaises(BusError):
            self.acknowledge()
        self.assertEqual(self.pending(), 2)
        with closing(self.module._connect()) as db:
            db.execute('DELETE FROM receipts')
        self.assertIsNotNone(self.module.source_checkpoint('a2a.receipt', self.adapter.source_instance))
        self.assertEqual(self.acknowledge()['acknowledged'], 0)
        self.assertEqual(self.pending(), 2)

    def test_semantic_mismatch_rolls_back_even_with_valid_content_fingerprint(self):
        import hashlib
        self.terminal()
        self.adapter.mirror(self.module)
        with closing(self.module._connect()) as db:
            row = db.execute('SELECT local_sequence,observation_json FROM receipts ORDER BY local_sequence DESC LIMIT 1').fetchone()
            value = json.loads(row[1])
            value['attributes']['receipt_kind'] = 'received'
            payload = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            db.execute('UPDATE receipts SET observation_json=?,content_fingerprint=? WHERE local_sequence=?',
                       (payload, hashlib.sha256(payload.encode()).hexdigest(), row[0]))
        with self.assertRaises(BusError) as error:
            self.acknowledge()
        self.assertEqual(error.exception.code, 'projection_proof_mismatch')
        self.assertEqual(self.pending(), 2)

    def test_row_bound_and_actor_rotation_hold_unacknowledged_rows(self):
        self.terminal()
        self.adapter.mirror(self.module)
        for limit in (0, 101, True):
            with self.subTest(limit=limit), self.assertRaises(BusError):
                self.acknowledge(limit=limit)
        self.assertEqual(self.acknowledge(limit=1)['acknowledged'], 1)
        self.assertEqual(self.pending(), 1)
        self.bus.rotate_actor(self.actors[0].actor_id, self.operator)
        with self.assertRaises(BusError):
            self.acknowledge()
        self.assertEqual(self.pending(), 1)

    def test_uncertain_cli_commit_returns_durable_operator_receipt_pointer(self):
        import io
        from contextlib import redirect_stdout
        from codex_wake.cli import main
        self.terminal()
        self.adapter.mirror(self.module)
        def fault(stage):
            if stage == 'after_commit':
                raise OSError('fixture interruption after accepted commit')
        self.mailbox.fault = fault
        output = io.StringIO()
        with patch('codex_wake.a2a_mailbox.Mailbox', return_value=self.mailbox), redirect_stdout(output):
            code = main(['a2a', 'ack-projections', '--bus-root', str(self.bus.root),
                '--operator-capability', str(self.operator), '--wake-root', str(self.wake_root),
                '--receipt-authority', str(self.config), '--source-instance', self.adapter.source_instance])
        self.assertEqual(code, 8)
        result = json.loads(output.getvalue())
        self.assertTrue(result['reconciliation_required'])
        receipt = result['reconciliation_pointer']['receipt_id']
        with self.bus.connection() as db:
            self.assertEqual(db.execute('SELECT action FROM events WHERE receipt_id=?', (receipt,)).fetchone()[0],
                             'acknowledge_receipt_projections')
        self.assertEqual(self.pending(), 0)
        self.mailbox.fault = None
        self.assertEqual(self.acknowledge()['acknowledged'], 0)

    def test_malformed_mailbox_projection_is_a_typed_refusal(self):
        self.terminal()
        self.adapter.mirror(self.module)
        for payload in ('[]', '{', '{}'):
            with self.bus.connection() as db:
                db.execute("UPDATE mail_outbox SET payload=? WHERE kind='receipt_signal'", (payload,))
            with self.subTest(payload=payload), self.assertRaises(BusError) as error:
                self.acknowledge()
            self.assertEqual(error.exception.code, 'receipt_corrupt')
            self.assertEqual(self.pending(), 2)

    def test_boolean_sequence_cannot_impersonate_integer_receipt_sequence(self):
        import hashlib
        self.terminal()
        self.adapter.mirror(self.module)
        with closing(self.module._connect()) as db:
            row = db.execute('SELECT local_sequence,observation_json FROM receipts ORDER BY local_sequence LIMIT 1').fetchone()
            value = json.loads(row[1])
            value['attributes']['sequence'] = True
            payload = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            db.execute('UPDATE receipts SET observation_json=?,content_fingerprint=? WHERE local_sequence=?',
                       (payload, hashlib.sha256(payload.encode()).hexdigest(), row[0]))
        with self.assertRaises(BusError) as error:
            self.acknowledge()
        self.assertEqual(error.exception.code, 'projection_proof_unavailable')
        self.assertEqual(self.pending(), 2)
