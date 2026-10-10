"""Public dispatcher tests with isolated native-server and queue process peers."""
import json
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_delivery import NotificationDispatcher, binding_dict
from codex_wake.a2a_identity import RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_scheduler import MailScheduler
from codex_wake.a2a_tmux_delivery import TmuxBinding
from codex_wake.process import boot_id_value


class SavedRecipientDeliveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'repo'; self.repo.mkdir()
        self.server = dict(codexHome=str(self.root / 'codex'))
        self.thread = dict(id='00000000-0000-4000-8000-000000000002',
            cwd=str(self.repo), modelProvider='fixture', name='saved-recipient',
            status=dict(type='notLoaded'), canAcceptDirectInput=True)
        recipient = RuntimeIdentity.from_metadata(self.thread, self.server)
        self.identities = [RuntimeIdentity(recipient.namespace, '00000000-0000-4000-8000-000000000001', str(self.repo)), recipient]
        self.bus, self.operator = BusStore.configure(self.root / 'bus')
        self.bus.enroll(self.repo, self.operator, notify=True)
        self.actors = []
        for identity in self.identities:
            capability, _ = self.bus.issue_actor(identity, self.repo, self.operator)
            self.actors.append(self.bus.authenticate(capability, identity, invoking_cwd=self.repo))
        Mailbox.migrate(self.bus, self.operator)
        self.now = time.time()
        self.mailbox = Mailbox(self.bus, clock=lambda: self.now, monotonic=lambda: self.now)
        self.scheduler = MailScheduler(self.mailbox, self.operator, lease_seconds=60)
        self.bus.set_paused(False, self.operator)
        self.binding = TmuxBinding(recipient.namespace, recipient.thread_id, recipient.cwd,
            str(self.root / 'tmux.sock'), 999999999, 1, boot_id_value(), 'closed-client')
        self.bindings = self.root / 'bindings.json'
        self.bindings.write_text(json.dumps(dict(schema_version=1, bindings=[binding_dict(self.binding)])))
        self.bindings.chmod(0o600)
        self.dispatcher = NotificationDispatcher(self.scheduler, self.bindings)
        self.calls = []
        self.queue_log = self.root / 'queued.json'
        self.codex = self.root / 'codex-cli'
        self.codex.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n'
            f'Path({str(self.queue_log)!r}).write_text(json.dumps(sys.argv[1:]))\n'
            "thread=sys.argv[sys.argv.index('--thread')+1]\n"
            "print('Queued message 00000000-0000-4000-8000-000000000003 for thread '+thread+'.')\n")
        self.codex.chmod(0o700)
        owner = self
        class Reader:
            def __init__(self, *args, **kwargs):
                self.server_metadata = owner.server
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read_thread(self, identifier): return dict(owner.thread)
        def native(endpoint, codex, method, params, timeout):
            owner.calls.append((method, params))
            owner.thread['status'] = dict(type='idle')
            return dict(thread=dict(owner.thread))
        for target, replacement in [
            ('codex_wake.shared_app_server.SharedAppServerReader', Reader),
            ('codex_wake.shared_app_server.locate_shared_endpoint', lambda **kwargs: 'unix:///fixture'),
            ('codex_wake.native_protocol.native_request', native),
            ('codex_wake.app_server.resolve_codex_cmd', lambda *args, **kwargs: str(self.codex)),
            ('codex_wake.a2a_tmux_delivery.tmux_inventory', lambda *args, **kwargs: [])]:
            mock = patch(target, replacement); mock.start(); self.addCleanup(mock.stop)

    def send(self, **kwargs):
        return self.mailbox.send(self.actors[0], self.identities[1], body='Private request body',
            idempotency_key='one-original-request', **kwargs)['message']['message_id']

    def test_explicit_saved_recipient_dispatches_original_pointer_once(self):
        identifier = self.send(resume_missing=True)
        outcome = self.dispatcher.tick()
        self.assertEqual(outcome['submitted'], 1)
        self.assertEqual(self.calls, [('thread/resume', dict(threadId=self.thread['id']))])
        queued = json.loads(self.queue_log.read_text())
        self.assertIn(self.thread['id'], queued)
        prompt = queued[queued.index('--message') + 1]
        self.assertIn(identifier, prompt)
        self.assertNotIn('Private request body', prompt)
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'submitted')
        self.assertEqual(self.dispatcher.tick()['results'], [])
        self.assertEqual(len(self.calls), 1)

    def test_runtime_observation_failure_holds_original_without_attempt(self):
        from codex_wake.shared_app_server import SharedSourceError
        identifier = self.send(resume_missing=True)
        with patch('codex_wake.shared_app_server.SharedAppServerReader', side_effect=SharedSourceError('unavailable')):
            result = self.dispatcher.tick()['results'][0]
        self.assertEqual(result['status'], 'deferred')
        self.assertEqual(result['reason'], 'runtime_unavailable')
        self.assertEqual(self.calls, [])
        self.assertFalse(self.queue_log.exists())
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'deferred')

    def test_default_closed_recipient_holds_without_lifecycle_or_queue(self):
        identifier = self.send()
        result = self.dispatcher.tick()['results'][0]
        self.assertEqual(result['status'], 'deferred')
        self.assertEqual(result['reason'], 'offline')
        self.assertEqual(self.calls, [])
        self.assertFalse(self.queue_log.exists())
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'deferred')

    def test_busy_or_changed_saved_identity_has_zero_delivery_effect(self):
        self.send(resume_missing=True)
        self.thread['status'] = dict(type='active')
        self.assertEqual(self.dispatcher.tick()['results'][0]['reason'], 'busy')
        self.now += 6
        self.thread['status'] = dict(type='notLoaded')
        self.thread['cwd'] = str(self.root)
        self.assertEqual(self.dispatcher.tick()['results'][0]['reason'], 'identity_changed')
        self.assertEqual(self.calls, [])
        self.assertFalse(self.queue_log.exists())
        held = self.mailbox.show(self.actors[0], self.send(resume_missing=True))
        self.assertEqual(held['receipts'][-1]['details']['reason'], 'identity_changed')

    def test_reopened_tab_and_capability_rotation_cannot_be_adopted(self):
        self.send(resume_missing=True)
        pane = dict(pane_title=self.thread['name'], pane_current_path=str(self.repo))
        with patch('codex_wake.a2a_saved_delivery.tmux_inventory', return_value=[pane]):
            self.assertEqual(self.dispatcher.tick()['results'][0]['reason'], 'composer_protected')
        self.now += 6
        self.bus.rotate_actor(self.actors[1].actor_id, self.operator)
        self.assertEqual(self.dispatcher.tick()['results'][0]['reason'], 'authorization_denied')
        self.assertEqual(self.calls, [])
        self.assertFalse(self.queue_log.exists())

    def test_cancelled_and_expired_messages_never_reopen(self):
        identifier = self.send(resume_missing=True, ttl=10)
        self.mailbox.cancel(self.actors[0], identifier)
        self.assertEqual(self.dispatcher.tick()['results'], [])
        expired = self.mailbox.send(self.actors[0], self.identities[1], body='Expires',
            idempotency_key='expires', ttl=10, resume_missing=True)['message']['message_id']
        self.now += 11
        self.assertEqual(self.dispatcher.tick()['results'], [])
        self.assertEqual(self.mailbox.show(self.actors[0], expired)['state']['admission'], 'expired')
        self.assertEqual(self.calls, [])
        self.assertFalse(self.queue_log.exists())

    def test_lost_queue_confirmation_stays_uncertain_after_worker_restart(self):
        identifier = self.send(resume_missing=True)
        self.codex.write_text('#!/usr/bin/env python3\nimport sys\nprint("unqualified")\nsys.exit(1)\n')
        result = self.dispatcher.tick()['results'][0]
        self.assertEqual(result['status'], 'uncertain')
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'uncertain')
        restarted = NotificationDispatcher(MailScheduler(self.mailbox, self.operator, lease_seconds=60), self.bindings)
        self.assertEqual(restarted.tick()['results'], [])
        self.assertEqual(len(self.calls), 1)

    def prepare_reply(self):
        original = self.send(delivery='inbox')
        self.thread['id'] = self.identities[0].thread_id
        self.binding = replace(self.binding, thread_id=self.thread['id'])
        self.bindings.write_text(json.dumps(dict(schema_version=1, bindings=[binding_dict(self.binding)])))
        reply = self.mailbox.reply(self.actors[1], original, body='Result',
            idempotency_key='one-reply', resume_missing=True)['message']['message_id']
        return original, reply

    def test_explicit_reply_cannot_bypass_delegated_sender_arm(self):
        _, reply = self.prepare_reply()
        self.assertEqual(self.dispatcher.tick()['results'][0]['reason'], 'reply_arm_unavailable')
        self.assertEqual(self.mailbox.show(self.actors[0], reply)['state']['notification'], 'deferred')
        self.assertEqual(self.calls, [])

    def test_native_reply_receipt_survives_bookkeeping_crash_without_resend(self):
        from codex_wake.a2a_reply_wake import ReplyWakeGate, arm_reply
        from codex_wake.a2a_sender_receipts import SenderReceiptAuthority
        from codex_wake.records import find_record
        original, reply = self.prepare_reply()
        wake_root = self.root / 'wake'
        authority = self.root / 'sender-authority.json'
        SenderReceiptAuthority(authority, wake_root).delegate(self.bus, self.operator, self.actors[0])
        with patch('codex_wake.monitor.monitor_state_dir', return_value=self.root / 'health'):
            gate = ReplyWakeGate(self.scheduler, wake_root, authority)
            gate.tick()
            armed = arm_reply(self.actors[0], original, wake_root, authority, 'reply-arm',
                (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat())
            dispatcher = NotificationDispatcher(self.scheduler, self.bindings, receipt_gate=gate)
            with patch.object(gate, 'submitted', side_effect=OSError('bookkeeping crash')):
                with self.assertRaises(OSError): dispatcher.tick()
            self.assertEqual(self.mailbox.show(self.actors[0], reply)['state']['notification'], 'submitted')
            self.assertEqual(find_record(wake_root, armed['wake_id']).record['status'], 'firing')
            rebuilt = NotificationDispatcher(self.scheduler, self.bindings,
                receipt_gate=ReplyWakeGate(self.scheduler, wake_root, authority))
            self.assertEqual(rebuilt.tick()['submitted'], 0)
            self.assertEqual(find_record(wake_root, armed['wake_id']).record['status'], 'submitted')
            self.assertEqual(len(self.calls), 1)
