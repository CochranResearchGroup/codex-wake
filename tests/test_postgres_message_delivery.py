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
        fixture.namespace = 'fixture-' + uuid4().hex
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
import sys
if sys.argv[1] != 'queue':
    sys.exit(2)
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
            result = fixture.dispatcher.tick()
            self.assertEqual(result['submitted'], 1, result)
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
            ('direct', fixture.actors[1].key, None, int(direct_expiry * 1_000_000), 'submitted',
             'actual-client-contract-turn'),
            ('wake', thread, NOW*1_000_000, (NOW + 600)*1_000_000, 'submitted', queue),
        ])

    def test_public_reply_inbox_and_bounce_redirect_keep_exact_shared_links(self):
        from codex_wake.a2a_identity import RuntimeIdentity
        from test_a2a_delivery import OwningClientDeliveryTests

        fixture = OwningClientDeliveryTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.wall_clock = NOW
        third = RuntimeIdentity('fixture', 'other-recipient', str(fixture.repo))
        capability, _ = fixture.bus.issue_actor(third, fixture.repo, fixture.operator)
        other = fixture.bus.authenticate(capability, third, invoking_cwd=fixture.repo)
        sender, recipient = fixture.actors
        body = fixture.root / 'body.txt'
        body.write_text('Retained private fixture text')

        def command(actor, verb, *args, expected=0):
            output = io.StringIO()
            with (patch('codex_wake.messages_cli.invoking_actor', return_value=actor),
                  patch('codex_wake.a2a_mailbox.Mailbox._now', return_value=NOW),
                  patch('codex_wake.messages_cli.resolve_identity',
                        side_effect=lambda selector, **kwargs: {
                            'thread:recipient': fixture.identities[1],
                            'thread:other-recipient': third,
                        }[selector]),
                  contextlib.redirect_stdout(output)):
                code = run(['messages', verb, '--bus-root', str(fixture.bus.root),
                            '--capability', 'test-enrollment', '--json', *args])
            value = json.loads(output.getvalue())
            self.assertEqual(code, expected, value)
            return value

        with (patch.dict(os.environ, {'CODEX_WAKE_MESSAGE_DB_DSN': DSN}),
              patch('codex_wake.native_clock.snapshot', return_value=CLOCK)):
            original = command(sender, 'send', '--to', 'thread:recipient', '--body-file',
                               str(body), '--idempotency-key', 'question', '--delivery', 'inbox')['message']
            reply = command(recipient, 'reply', original['message_id'], '--body-file',
                            str(body), '--idempotency-key', 'answer', '--delivery', 'inbox')
            self.assertEqual(reply['shared_admission'], 'recorded')
            reply_id = reply['message']['message_id']
            listed = command(sender, 'replies', original['message_id'])['replies']
            self.assertEqual([(r['message_id'], r['in_reply_to']) for r in listed],
                             [(reply_id, original['message_id'])])
            self.assertEqual(command(sender, 'read', reply_id)['body'], 'Retained private fixture text')
            command(other, 'replies', original['message_id'], expected=7)

            bounced = command(sender, 'send', '--to', 'thread:recipient', '--body-file',
                              str(body), '--idempotency-key', 'bounce', '--busy-policy', 'idle-only',
                              '--ttl', '12m')['message']
            args = (bounced['message_id'], '--to', 'thread:other-recipient',
                    '--idempotency-key', 'redirect-bounce')
            self.assertEqual(command(sender, 'redirect', *args, expected=8)['error']['code'], 'not_bounced')
            fixture.status = 'deferred'
            outcomes = fixture.dispatcher.tick()['results']
            self.assertTrue(any(row['message_id'] == bounced['message_id'] and row['status'] == 'bounced'
                                for row in outcomes), outcomes)

            redirect = command(sender, 'redirect', *args)
            self.assertEqual(redirect['shared_admission'], 'recorded')
            redirected = redirect['message']
            self.assertNotEqual(redirected['message_id'], bounced['message_id'])
            self.assertEqual(redirected['redirected_from'], bounced['message_id'])
            self.assertEqual(redirected['expires_at'], bounced['expires_at'])
            self.assertEqual(redirected['busy_policy'], 'idle-only')
            self.assertEqual(redirected['recipient']['thread_id'], third.thread_id)
            self.assertTrue(command(sender, 'redirect', *args)['deduplicated'])
            self.assertEqual(command(sender, 'show', bounced['message_id'])['message']['state']['admission'],
                             'bounced')
            command(recipient, 'redirect', *args, expected=7)
            cancelled = command(sender, 'cancel', redirected['message_id'])['message']
            self.assertEqual(cancelled['state']['admission'], 'cancelled')

        with self.store._connect() as db:
            result = db.execute(
                """SELECT in_reply_to,redirected_from,local_terminal FROM wake_messages_v1
                   WHERE message_id=%s""", (reply_id,)).fetchone()
            self.assertEqual(result, (original['message_id'], None, False))
            result = db.execute(
                """SELECT in_reply_to,redirected_from,local_terminal FROM wake_messages_v1
                   WHERE message_id=%s""", (redirected['message_id'],)).fetchone()
            self.assertEqual(result, (None, bounced['message_id'], True))

    def test_positive_queue_removal_retires_original_shared_attempt(self):
        message = Message('wake_' + uuid4().hex, 'wake', 'fixture', 'recipient',
                          (NOW + 90) * 1_000_000, 'Do once')
        attempt, queue = str(uuid4()), str(uuid4())
        self.assertIsNone(self.store.prepare(message, attempt))
        self.store.finish(message, attempt, DeliveryReceipt(
            'submitted', queue, evidence_kind='native_queue_acceptance'))
        with self.assertRaises(ValueError):
            self.store.reconcile_queue_removal(message, attempt, str(uuid4()), 'bounded_native_canceled')
        self.store.reconcile_queue_removal(message, attempt, queue, 'bounded_native_canceled')
        self.store.reconcile_queue_removal(message, attempt, queue, 'bounded_native_canceled')
        self.assertEqual(self.store.prepare(message, 'new-attempt'),
                         DeliveryReceipt('unsent', reason='message_retired'))
        with self.store._connect() as db:
            result = db.execute(
                """SELECT attempt_id,state,receipt_id,execution,reason FROM wake_message_attempts_v1
                   WHERE scope=%s AND message_id=%s""", (message.scope, message.identifier)).fetchall()
            self.assertEqual(result, [(attempt, 'submitted', queue, 'queue_cancelled',
                                       'bounded_native_canceled')])

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

    def test_public_dnd_hold_bounce_override_and_failed_interrupt(self):
        from codex_wake.a2a_identity import BusError
        from test_a2a_delivery import OwningClientDeliveryTests

        fixture = OwningClientDeliveryTests()
        fixture.namespace = 'fixture-' + uuid4().hex
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.wall_clock = NOW

        def stable():
            return {'utc': {**CLOCK['utc'], 'upper': fixture.wall_clock,
                            'lower': fixture.wall_clock}, 'counter': None}

        def cli(*arguments, code=0, actor=None):
            stdout = io.StringIO()
            capability = fixture.root / 'fixture-issued-capability'
            with patch('codex_wake.messages_cli.invoking_actor', return_value=actor or fixture.actors[1]), \
                    patch('codex_wake.a2a_mailbox.Mailbox._now', return_value=fixture.wall_clock), \
                    contextlib.redirect_stdout(stdout):
                self.assertEqual(run(['messages', arguments[0], '--bus-root', str(fixture.bus.root),
                                      '--capability', str(capability), *arguments[1:], '--json']), code,
                                 stdout.getvalue())
            return json.loads(stdout.getvalue())

        def send(key, *, busy_policy='wait'):
            return fixture.mailbox.send(fixture.actors[0], fixture.identities[1], body='test message',
                                        idempotency_key=key, busy_policy=busy_policy)['message']['message_id']

        def first():
            return fixture.dispatcher.tick()['results'][0]

        with patch.dict(os.environ, {'CODEX_WAKE_MESSAGE_DB_DSN': DSN}), \
                patch('codex_wake.native_clock.snapshot', side_effect=stable):
            self.addCleanup(self.store.set_dnd, fixture.actors[1].key, fixture.thread_id, 'clear')
            self.assertIsNotNone(cli('dnd', 'hold', '--for', '20s')['until_micros'])
            original = send('held')
            self.assertEqual(first()['reason'], 'recipient_dnd')
            fixture.wall_clock += 6
            denied = cli('intervene', original, '--operator-capability', str(fixture.operator),
                         '--interrupt-turn', 'turn-unavailable')
            self.assertEqual(denied['interruption'], 'requested')
            self.assertEqual(first()['reason'], 'recipient_dnd')
            cli('intervene', original, '--operator-capability', str(fixture.operator), '--override-dnd')
            fixture.wall_clock += 5
            fixture.status = 'deferred'
            self.assertEqual(first()['reason'], 'interrupt_unavailable')
            receipt = cli('intervene', original, '--operator-capability', str(fixture.operator), '--status')['policy']
            self.assertEqual(receipt['interruption'], 'unavailable')
            self.assertNotEqual(receipt['override_authorization'], receipt['interrupt_authorization'])
            self.assertEqual(fixture.deliveries, [])
            fixture.wall_clock += 5
            self.assertEqual(first()['reason'], 'recipient_dnd')
            fixture.wall_clock += 5
            self.assertEqual(first()['reason'], 'busy')
            fixture.status = 'ready'
            fixture.wall_clock += 5
            got = first()
            self.assertEqual(got['status'], 'submitted', got)
            self.assertEqual([row['message_id'] for row in fixture.deliveries], [original])

            cli('dnd', 'hold')
            older_held = send('older-dnd-held')
            override = send('override')
            self.assertEqual([item['reason'] for item in fixture.dispatcher.tick()['results']],
                             ['recipient_dnd', 'recipient_dnd'])
            cli('intervene', override, '--operator-capability', str(fixture.operator), '--override-dnd')
            fixture.status = 'deferred'
            fixture.wall_clock += 5
            self.assertEqual([item['reason'] for item in fixture.dispatcher.tick()['results']],
                             ['recipient_dnd', 'busy'])
            fixture.status = 'ready'
            fixture.wall_clock += 5
            got = fixture.dispatcher.tick()['results']
            self.assertEqual(got[0]['reason'], 'recipient_dnd')
            self.assertEqual(got[1]['status'], 'submitted', got)
            fixture.mailbox.cancel(fixture.actors[0], older_held)

            cli('dnd', 'bounce')
            bounced = send('dnd-bounce')
            self.assertEqual(first()['status'], 'bounced')
            self.assertEqual(fixture.mailbox.show(fixture.actors[0], bounced)['state']['admission'], 'bounced')
            with self.assertRaises(BusError):
                fixture.mailbox.read(fixture.actors[1], bounced)
            cli('dnd', 'clear')
            fixture.status = 'deferred'
            idle_only = send('idle-only', busy_policy='idle-only')
            self.assertEqual(first()['reason'], 'recipient_busy')
            self.assertEqual(fixture.mailbox.show(fixture.actors[0], idle_only)['state']['admission'], 'bounced')
            self.assertEqual([row['message_id'] for row in fixture.deliveries], [original, override])

    def test_public_direct_and_timed_messages_share_oldest_eligible_order(self):
        from codex_wake.a2a_delivery import bind_client
        from codex_wake.a2a_identity import RuntimeIdentity
        from test_a2a_delivery import OwningClientDeliveryTests

        fixture = OwningClientDeliveryTests()
        fixture.namespace = 'fixture-' + uuid4().hex
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.wall_clock = NOW
        thread = str(uuid4())
        fixture.thread_id = thread
        recipient = RuntimeIdentity(fixture.namespace, thread, str(fixture.repo))
        fixture.bindings.unlink()
        bind_client(fixture.bindings, fixture.socket_path, recipient)
        capability, _ = fixture.bus.issue_actor(recipient, fixture.repo, fixture.operator)
        receiver = fixture.bus.authenticate(capability, recipient, invoking_cwd=fixture.repo)
        root = fixture.root / 'wakes'
        executable = fixture.root / 'codex'
        calls = fixture.root / 'queue-calls'
        executable.write_text(f'''#!{sys.executable}
from pathlib import Path
import sys
if sys.argv[1] != 'queue':
    sys.exit(2)
with Path({str(calls)!r}).open("a") as stream:
    stream.write("queued\\n")
print("Queued message {uuid4()} for thread {thread}.")
''')
        executable.chmod(0o700)

        def stable():
            return {'utc': {**CLOCK['utc'], 'upper': fixture.wall_clock,
                            'lower': fixture.wall_clock}, 'counter': None}

        def arm(at, body):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(run(['--wake-root', str(root), 'native', 'at', '--json',
                                      '--codex-path', str(executable), '--ttl', '10m', thread,
                                      at, '--', body]), 0, output.getvalue())
            return json.loads(output.getvalue())

        def direct(key):
            return fixture.mailbox.send(fixture.actors[0], recipient, body=key,
                                        idempotency_key=key)['message']['message_id']

        def wake():
            now = datetime.fromtimestamp(fixture.wall_clock, UTC)
            poll_once(root, now, time_provider=lambda: TimeDecision('network', ('test-a', 'test-b'),
                                                                     fixture.wall_clock, fixture.wall_clock))

        with patch.dict(os.environ, {'CODEX_WAKE_MESSAGE_DB_DSN': DSN}), \
                patch('codex_wake.native_clock.snapshot', side_effect=stable), \
                patch('codex_wake.message_policy.native_identity', return_value=receiver.key), \
                patch('codex_wake.native_delivery.read_native_thread',
                      return_value={'id': thread, 'status': {'type': 'idle'}}):
            arm('2026-10-09T00:00:00Z', 'older wake')
            first = direct('newer direct')
            self.assertEqual(fixture.dispatcher.tick()['results'][0]['reason'], 'recipient_fifo_wait')
            self.assertEqual(fixture.deliveries, [])
            wake()
            self.assertEqual(calls.read_text(), 'queued\n')
            fixture.wall_clock += 5
            result = fixture.dispatcher.tick()
            self.assertEqual(result['submitted'], 1, result)
            self.assertEqual(fixture.deliveries[-1]['message_id'], first)

            second = direct('older direct')
            arm('2026-10-09T00:00:05Z', 'newer wake')
            wake()
            self.assertEqual(calls.read_text(), 'queued\n')
            result = fixture.dispatcher.tick()
            self.assertEqual(result['submitted'], 1, result)
            self.assertEqual(fixture.deliveries[-1]['message_id'], second)
            fixture.wall_clock += 31
            wake()
            self.assertEqual(calls.read_text(), 'queued\nqueued\n')

            future = datetime.fromtimestamp(fixture.wall_clock + 120, UTC).isoformat()
            arm(future, 'older but ineligible wake')
            eligible = direct('younger but eligible direct')
            self.assertEqual(fixture.dispatcher.tick()['submitted'], 1)
            self.assertEqual(fixture.deliveries[-1]['message_id'], eligible)

            self.store.set_dnd(receiver.key, thread, 'hold')
            self.addCleanup(self.store.set_dnd, receiver.key, thread, 'clear')
            now = datetime.fromtimestamp(fixture.wall_clock, UTC).isoformat()
            held = arm(now, 'held timed wake')
            wake()
            from codex_wake.records import find_record
            self.assertEqual(find_record(root, held['id']).record['policy_outcome'],
                             dict(state='held', reason='recipient_dnd'))
            self.store.set_dnd(receiver.key, thread, 'bounce')
            fixture.wall_clock += 31
            wake()
            self.assertEqual(find_record(root, held['id']).record['policy_outcome'],
                             dict(state='bounced', reason='recipient_dnd'))
            self.assertEqual(calls.read_text(), 'queued\nqueued\n')
            redirected_thread = str(uuid4())
            from codex_wake.records import WakeError
            from codex_wake.runtime_delivery import original_submission_expiry
            original = find_record(root, held['id']).record
            args = ['--wake-root', str(root), 'native', 'redirect', held['id'],
                    '--to', redirected_thread, '--idempotency-key', 'timed-bounce-redirect',
                    '--codex-path', sys.executable, '--json']
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(run(args), 0)
            redirected = json.loads(output.getvalue())
            self.assertEqual(redirected['redirected_from'], held['id'])
            self.assertNotEqual(redirected['id'], held['id'])
            new_wake = find_record(root, redirected['id']).record
            self.assertEqual(new_wake['target']['thread_id'], redirected_thread)
            self.assertEqual(original_submission_expiry(new_wake), original_submission_expiry(original))
            self.assertEqual(find_record(root, held['id']).record, original)
            fixture.wall_clock = original_submission_expiry(original) / 1_000_000 + 1
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(run(args), 0)
            self.assertEqual(json.loads(output.getvalue())['id'], redirected['id'])
            args[args.index('timed-bounce-redirect')] = 'expired-redirect'
            with self.assertRaisesRegex(WakeError, 'native_redirect_original_window_closed'):
                run(args)
            with self.store._connect() as db:
                self.assertEqual(db.execute(
                    'SELECT redirected_from,recipient FROM wake_messages_v1 WHERE message_id=%s',
                    (redirected['id'],)).fetchone(), (held['id'], redirected_thread))

    def test_operator_interrupts_only_the_exact_turn_then_delivers(self):
        from threading import Thread
        from websockets.sync.server import unix_serve

        from codex_wake.a2a_delivery import binding_dict
        from codex_wake.a2a_identity import RuntimeIdentity
        from codex_wake.a2a_tmux_delivery import TmuxBinding
        from codex_wake.process import boot_id_value, process_start_time_ticks
        from test_a2a_delivery import OwningClientDeliveryTests

        fixture = OwningClientDeliveryTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.wall_clock = NOW
        endpoint = fixture.private / 'native.sock'
        metadata = dict(codexHome=str(fixture.repo / 'account'))
        thread = dict(id=str(uuid4()), modelProvider='fixture', cwd=str(fixture.repo))
        recipient = RuntimeIdentity.from_metadata(thread, metadata)
        capability, _ = fixture.bus.issue_actor(recipient, fixture.repo, fixture.operator)
        actor = fixture.bus.authenticate(capability, recipient, invoking_cwd=fixture.repo)
        binding = TmuxBinding(recipient.namespace, recipient.thread_id, recipient.cwd,
                             '/fixture/tmux', os.getpid(), process_start_time_ticks(os.getpid()),
                             boot_id_value(), 'fixture-newest-generation')
        fixture.bindings.write_text(json.dumps(dict(schema_version=1, bindings=[binding_dict(binding)])))

        turn = str(uuid4())
        state = dict(active=True, interrupts=[])
        def peer(connection):
            for raw in connection:
                request = json.loads(raw)
                if 'id' not in request:
                    continue
                method = request['method']
                if method == 'initialize':
                    reply = metadata
                elif method == 'thread/read':
                    reply = {'thread': dict(thread, status=dict(type='active' if state['active'] else 'idle'),
                                            turns=[dict(id=turn, status='inProgress' if state['active'] else 'interrupted')])}
                elif method == 'turn/interrupt':
                    state['interrupts'].append(request['params'])
                    state['active'] = False
                    reply = {}
                else:
                    raise AssertionError(method)
                connection.send(json.dumps(dict(id=request['id'], result=reply)))

        def stable():
            return {'utc': {**CLOCK['utc'], 'upper': fixture.wall_clock,
                            'lower': fixture.wall_clock}, 'counter': None}

        def cli(verb, *args):
            stdout = io.StringIO()
            with patch('codex_wake.messages_cli.invoking_actor', return_value=actor), \
                    contextlib.redirect_stdout(stdout):
                self.assertEqual(run(['messages', verb, '--bus-root', str(fixture.bus.root),
                                      *args, '--json']), 0, stdout.getvalue())
            return json.loads(stdout.getvalue())

        with unix_serve(peer, str(endpoint)) as server:
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            self.addCleanup(worker.join, 2)
            self.addCleanup(server.shutdown)
            with patch.dict(os.environ, {'CODEX_WAKE_MESSAGE_DB_DSN': DSN}), \
                    patch('codex_wake.native_clock.snapshot', side_effect=stable), \
                    patch('codex_wake.shared_app_server.locate_shared_endpoint', return_value='unix://' + str(endpoint)), \
                    patch.object(TmuxBinding, 'locate'), \
                    patch.object(TmuxBinding, 'probe', side_effect=lambda: dict(status='deferred', reason='busy')
                                 if state['active'] else dict(status='ready')), \
                    patch.object(TmuxBinding, 'deliver', return_value=dict(status='submitted', receipt_id='fixture-delivery')) as submit:
                cli('dnd', 'hold', '--capability', str(capability))
                original = fixture.mailbox.send(fixture.actors[0], recipient, body='exact message',
                                                idempotency_key='exact')['message']['message_id']
                args = (original, '--operator-capability', str(fixture.operator))
                cli('intervene', *args, '--override-dnd', '--interrupt-turn', turn)
                self.assertEqual(fixture.dispatcher.tick()['results'][0]['reason'], 'interrupt_requested')
                self.assertEqual(state['interrupts'], [dict(threadId=recipient.thread_id, turnId=turn)])
                submit.assert_not_called()
                fixture.wall_clock += 5
                self.assertEqual(fixture.dispatcher.tick()['results'][0]['reason'], 'interrupt_observed')
                self.assertEqual(cli('intervene', *args, '--status')['policy']['interruption'], 'interrupted')
                submit.assert_not_called()
                fixture.wall_clock += 5
                self.assertEqual(fixture.dispatcher.tick()['submitted'], 1)
                submit.assert_called_once()
                self.assertEqual(len(state['interrupts']), 1)
