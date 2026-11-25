"""Exercise the one-scope cutover using real legacy records and PostgreSQL."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from codex_wake.cli import run
from codex_wake.message_delivery import DeliveryReceipt, configured_store, deliver, wake_message
from codex_wake.records import all_records, replace_record
from codex_wake.recurring_schedules import poll_schedules
from codex_wake.runtime_delivery import original_submission_expiry
import test_a2a_mailbox
import test_recurring_schedules


DSN = os.environ.get('CODEX_WAKE_TEST_MESSAGE_DB_DSN')
NOW = 2_000_000_000
CLOCK = {'utc': {'status': 'network', 'sources': ['test-a', 'test-b'],
                 'lower': NOW, 'upper': NOW}, 'counter': None}


@unittest.skipUnless(DSN, 'requires a disposable PostgreSQL database')
class MessageCutoverTests(unittest.TestCase):
    def test_verified_scope_preserves_schedule_reply_deadlines_and_original_uncertainty(self):
        fixture = test_a2a_mailbox.MailboxTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.now = NOW
        original = fixture.send(ttl=600)['message']
        reply = fixture.mailbox.reply(fixture.recipient, original['message_id'], body='Fixture reply',
                                      idempotency_key='reply', outcome='accepted')['message']
        isolated = Path(fixture.temporary.name)
        wake = isolated / 'wakes'
        wake.mkdir(mode=0o700)
        spec = isolated / 'schedule.json'
        spec.write_text(json.dumps(test_recurring_schedules.request()))
        registered = test_recurring_schedules.RecurringSchedules().cli(wake, 'register', '--request', str(spec),
                                               '--codex-path', sys.executable)
        poll_schedules(wake, CLOCK)
        pending, = all_records(wake)
        uncertain = dict(pending.record, status='firing',
                         native_delivery={'state': 'uncertain', 'submission_id': 'original-wake-attempt'})
        replace_record(wake, pending, uncertain)
        args = ['--wake-root', str(wake), 'migration', 'message-cutover', '--json',
                '--bus-root', str(fixture.bus.root), '--isolated-root', str(isolated),
                '--operator-capability', str(fixture.operator)]

        def command(*extra, expected_code=0):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(run([*args, *extra]), expected_code, output.getvalue())
            return json.loads(output.getvalue())

        with patch.dict(os.environ, {'CODEX_WAKE_CUTOVER_DB_DSN': DSN}):
            preview = command()
            self.assertEqual(preview['status'], 'previewed')
            self.assertIsNone(configured_store(wake))
            refused = command('--expected-source', 'wrong', expected_code=2)
            self.assertIn('changed since preview', refused['error'])
            self.assertIsNone(configured_store(wake))

            activated = command('--expected-source', preview['source_digest'])
            self.assertEqual(activated['status'], 'activated')
            self.assertEqual(activated['imported_messages'], 3)
            self.assertGreaterEqual(activated['uncertain_effects'], 1)
            self.assertEqual(command('--expected-source', preview['source_digest']), activated)
            self.assertIsNone(configured_store(fixture.repo))
            store = configured_store(wake)
            self.assertIsNotNone(configured_store(fixture.bus.root))
            from codex_wake.daemon import poll_once
            from codex_wake.message_cutover import DATABASE_UNAVAILABLE, database_unready

            with patch.dict(os.environ, {'CODEX_WAKE_CUTOVER_DB_DSN': ''}), \
                    patch('codex_wake.wake_cancellation.reconcile_cancellations') as reconcile:
                self.assertEqual(poll_once(wake).skip_reason, DATABASE_UNAVAILABLE)
                reconcile.assert_not_called()
                self.assertEqual(database_unready(fixture.bus.root), DATABASE_UNAVAILABLE)
                self.assertIsNone(database_unready(fixture.repo))
            self.assertIsNone(database_unready(wake))
            message = wake_message(wake, uncertain, original_submission_expiry(uncertain))
            result = deliver(store, message, 'retry-that-must-not-run',
                             lambda: self.fail('original uncertain Wake was replayed'), clock=lambda: CLOCK)
            self.assertEqual(result, DeliveryReceipt(
                'uncertain', reason='original_message_effect_requires_reconciliation'))

            with store._connect() as conn:
                (snapshot,) = conn.execute(
                    'SELECT snapshot FROM wake_message_cutovers_v1 WHERE cutover_id = %s',
                    (activated['cutover_id'],)).fetchone()
                self.assertEqual(snapshot['schedules'][0]['id'], registered['id'])
                self.assertEqual(snapshot['schedules'][0]['occurrences'][0]['due_at'],
                                 '2033-05-18T03:33:20Z')
                self.assertEqual(snapshot['wakes'][0]['id'], message.identifier)
                self.assertEqual(snapshot['wakes'][0]['native_delivery']['submission_id'],
                                 'original-wake-attempt')
                self.assertEqual(conn.execute(
                    'SELECT in_reply_to,expires_at_micros FROM wake_messages_v1 WHERE message_id=%s',
                    (reply['message_id'],)).fetchone(),
                    (original['message_id'], int(reply['expires_at'] * 1_000_000)))
                self.assertEqual(conn.execute(
                    'SELECT attempt_id,state FROM wake_message_attempts_v1 WHERE message_id=%s',
                    (message.identifier,)).fetchall(), [('original-wake-attempt', 'uncertain')])
            self.assertEqual(fixture.mailbox.show(fixture.sender, original['message_id'])['expires_at'],
                             original['expires_at'])
            # The public read-only native reconciliation recovers the original
            # transport receipt before making the local effect terminal.
            evidence = {'source': 'native_queue', 'queue_id': 'recovered-original-queue',
                        'client_message_id': 'original-client', 'execution': 'not_observed'}
            output = io.StringIO()
            with patch('codex_wake.native_delivery.native_evidence', return_value=(evidence, None)), \
                    patch('codex_wake.runtime_delivery.submit_bounded',
                          side_effect=AssertionError('reconciliation attempted a new send')), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(run(['--wake-root', str(wake), 'native', 'reconcile', message.identifier]), 0)
            self.assertEqual(json.loads(output.getvalue())['status'], 'submitted')
            saved = store.prepare(message, 'original-wake-attempt')
            self.assertEqual((saved.state, saved.receipt_id), ('submitted', 'recovered-original-queue'))
            self.assertEqual(store.prepare(message, 'different-attempt').state, 'uncertain')

            # An ordinary sender uses PostgreSQL only after its scope is active.
            followup = fixture.send('new-after-cutover', ttl=600)
            self.assertEqual(followup['shared_admission'], 'recorded')
            with store._connect() as conn:
                self.assertIsNotNone(conn.execute('SELECT 1 FROM wake_messages_v1 WHERE message_id=%s',
                    (followup['message']['message_id'],)).fetchone())
