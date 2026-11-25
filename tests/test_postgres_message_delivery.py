"""Opt-in PostgreSQL integration against an isolated server."""
from datetime import UTC, datetime
from pathlib import Path
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from codex_wake.cli import run
from codex_wake.daemon import poll_once
from codex_wake.message_delivery import DeliveryReceipt, Message, PostgresMessages, deliver
from codex_wake.time_provider import TimeDecision


NOW = 1791504000
DSN = os.environ.get('CODEX_WAKE_TEST_MESSAGE_DB_DSN')
CLOCK = {'utc': {'status': 'network', 'sources': ['test-a', 'test-b'],
                 'lower': NOW, 'upper': NOW}, 'counter': None}


@unittest.skipUnless(DSN, 'requires a disposable PostgreSQL database')
class PostgresMessageDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.store = PostgresMessages(DSN)
        self.store.initialize()

    def test_direct_and_timed_commands_record_exactly_one_effect_after_worker_restart(self):
        from codex_wake.a2a_delivery import NotificationDispatcher
        from codex_wake.records import all_records
        from test_a2a_delivery import OwningClientDeliveryTests

        fixture = OwningClientDeliveryTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.wall_clock = NOW
        thread = '01a1227e-a041-7b72-9c36-18349e7dd22c'
        queue = '01a12280-80ef-7772-a00a-c68bd32ecbba'
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
                os.environ, {'CODEX_WAKE_MESSAGE_DB_DSN': DSN}), patch(
                'codex_wake.native_clock.snapshot', return_value=CLOCK):
            root = Path(tmp)
            executable = root/'codex'
            calls = root/'queue-calls'
            executable.write_text(f'''#!{sys.executable}
from pathlib import Path
with Path({str(calls)!r}).open("a") as stream:
    stream.write("queued\\n")
print("Queued message {queue} for thread {thread}.")
''')
            executable.chmod(0o700)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(run(['--wake-root', str(root/'wakes'), 'native', 'at', '--json',
                                      '--codex-path', str(executable), '--ttl', '10m', thread,
                                      '2026-10-09T00:00:00Z', '--', 'Timed follow-up']), 0)
            wake = json.loads(output.getvalue())
            self.assertEqual(wake['shared_admission'], 'recorded')

            body = root/'body.txt'
            body.write_text('Direct follow-up')
            output = io.StringIO()
            with patch('codex_wake.messages_cli.invoking_actor', return_value=fixture.actors[0]), patch(
                    'codex_wake.messages_cli.resolve_identity', return_value=fixture.identities[1]), patch(
                    'codex_wake.a2a_mailbox.Mailbox._now', return_value=NOW), contextlib.redirect_stdout(output):
                self.assertEqual(run(['messages', 'send', '--bus-root', str(fixture.bus.root),
                                      '--capability', str(root/'synthetic-capability'),
                                      '--to', 'thread:recipient', '--body-file', str(body),
                                      '--idempotency-key', 'direct-shared', '--json']), 0, output.getvalue())
            direct = json.loads(output.getvalue())
            self.assertEqual(direct['shared_admission'], 'recorded')
            self.assertEqual(fixture.dispatcher.tick()['submitted'], 1)
            self.assertEqual(NotificationDispatcher(fixture.scheduler, fixture.bindings).tick()['submitted'], 0)
            self.assertEqual(len(fixture.deliveries), 1)
            with patch('codex_wake.native_delivery.read_native_thread',
                       return_value={'id': thread, 'status': {'type': 'idle'}}):
                time_provider = lambda: TimeDecision('network', ('test-a','test-b'), NOW, NOW)
                now = datetime.fromtimestamp(NOW, UTC)
                for _ in range(2):
                    poll_once(root/'wakes', now, time_provider=time_provider)
            self.assertEqual(calls.read_text(), 'queued\n')
            record, = all_records(root/'wakes')
            self.assertEqual(record.record['status'], 'submitted')
            self.assertEqual(record.record['id'], wake['id'])

        import psycopg
        with psycopg.connect(DSN) as connection:
            results = connection.execute(
                """SELECT source,recipient,not_before_micros,expires_at_micros,state,receipt_id FROM wake_messages_v1
                   JOIN wake_message_attempts_v1 USING(scope,message_id)
                   WHERE message_id IN (%s,%s) ORDER BY source""",
                (direct['message']['message_id'], wake['id'])).fetchall()
        direct_expiry = direct['message']['expires_at']
        self.assertEqual(results, [
            ('direct', '["fixture","recipient"]', None, int(direct_expiry * 1_000_000), 'submitted',
             'actual-client-contract-turn'),
            ('wake', thread, NOW*1_000_000, (NOW + 600)*1_000_000, 'submitted', queue),
        ])

    def test_unfinalized_effect_cannot_be_replayed_by_a_new_worker(self):
        message = Message('wake_'+uuid4().hex, 'wake', 'fixture', 'recipient',
                          (NOW + 90)*1_000_000, 'Do once')
        self.assertIsNone(self.store.prepare(message, 'first-attempt'))

        def unexpected_effect():
            self.fail('uncertain delivery was replayed')

        result = deliver(PostgresMessages(DSN), message, 'second-attempt', unexpected_effect,
                         clock=lambda: CLOCK)
        self.assertEqual(result, DeliveryReceipt('uncertain',
                                                reason='original_message_effect_requires_reconciliation'))
