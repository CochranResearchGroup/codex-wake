"""Live dispatcher contract with isolated runtime and native queue process peers."""
import json
import os
import socket
import unittest
from dataclasses import replace
from unittest.mock import patch

from codex_wake.a2a_delivery import binding_dict
from codex_wake.process import process_start_time_ticks
from tests import test_saved_recipient_delivery as saved_fixture

EMPTY = '› Ask Codex to do anything\n GPT-6 · /repo · session\n ← for agents · ? for shortcuts\n'


class LiveRecipientDeliveryTests(unittest.TestCase):
    def setUp(self):
        saved_fixture.SavedRecipientDeliveryTests.setUp(self)
        from codex_wake import shared_app_server
        for target, replacement in [
            ('codex_wake.a2a_tmux_delivery.SharedAppServerReader', shared_app_server.SharedAppServerReader),
            ('codex_wake.a2a_tmux_delivery.locate_shared_endpoint', shared_app_server.locate_shared_endpoint)]:
            peer_patch = patch(target, replacement)
            peer_patch.start(); self.addCleanup(peer_patch.stop)
        self.thread['status'] = dict(type='idle')
        self.binding = replace(self.binding, pid=os.getpid(),
                               process_start_ticks=process_start_time_ticks(os.getpid()))
        peer = socket.socket(socket.AF_UNIX)
        peer.bind(self.binding.tmux_socket)
        self.addCleanup(peer.close)
        self.pane = dict(pane_id='%fixture', client_pid=self.binding.pid,
                        client_start_time_ticks=self.binding.process_start_ticks,
                        pane_title=self.thread['name'], pane_current_path=str(self.repo))
        self.bindings.write_text(json.dumps(dict(schema_version=1, bindings=[binding_dict(self.binding)])))
        inventory = patch('codex_wake.a2a_tmux_delivery.tmux_inventory', return_value=[self.pane])
        inventory.start(); self.addCleanup(inventory.stop)
        self.runner_patch = patch('codex_wake.a2a_tmux_delivery.SubprocessTmuxRunner')
        self.runner = self.runner_patch.start().return_value
        self.addCleanup(self.runner_patch.stop)
        self.runner.capture_pane.return_value = EMPTY

    send = saved_fixture.SavedRecipientDeliveryTests.send

    def test_native_receipt_proves_submission_when_marker_leaves_viewport(self):
        identifier = self.send(kind='result')
        # All pre-submit screens are empty; no notification marker is ever visible.
        result = self.dispatcher.tick()
        self.assertEqual(result['submitted'], 1, result)
        self.assertEqual(result['results'][0]['receipt_id'], '00000000-0000-4000-8000-000000000003')
        queued = json.loads(self.queue_log.read_text())
        prompt = queued[queued.index('--message') + 1]
        self.assertIn('A2A_NOTIFICATION=' + identifier, prompt)
        self.assertIn('A2A_ATTEMPT_ID=' + result['results'][0]['attempt_id'], prompt)
        self.assertNotIn('Private request body', prompt)
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'submitted')
        self.assertEqual(self.dispatcher.tick()['results'], [])
        self.runner.paste_prompt.assert_not_called()

    def test_claim_instructions_complete_result_without_another_reply(self):
        import re
        identifier = self.send(kind='result')
        self.assertEqual(self.dispatcher.tick()['submitted'], 1)
        queued = json.loads(self.queue_log.read_text())
        prompt = queued[queued.index('--message') + 1]
        self.mailbox.read(self.actors[1], identifier)
        for outcome in re.findall(r'--outcome (accepted|completed)', prompt):
            acknowledgment = self.mailbox.ack(self.actors[1], identifier, outcome=outcome)
            if outcome == 'accepted': self.assertTrue(acknowledgment['claimed'])
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['recipient'], 'completed')
        self.assertIn('claimed=false', prompt)
        self.assertIn('A2A_CAPABILITY_PATH=', prompt)

    def test_busy_draft_approval_unknown_and_reused_process_have_zero_queue_effect(self):
        self.send()
        self.thread['status'] = dict(type='active')
        self.assertEqual(self.dispatcher.tick()['results'][0]['reason'], 'busy')
        self.thread['status'] = dict(type='idle')
        for screen in [EMPTY.replace('Ask Codex to do anything', 'human draft'),
                       'Approve this command?', 'unknown UI']:
            self.now += 6
            self.runner.capture_pane.return_value = screen
            self.assertEqual(self.dispatcher.tick()['results'][0]['reason'], 'composer_protected')
        self.now += 6
        self.runner.capture_pane.return_value = EMPTY
        stale = replace(self.binding, process_start_ticks=self.binding.process_start_ticks + 1)
        self.bindings.write_text(json.dumps(dict(schema_version=1, bindings=[binding_dict(stale)])))
        self.assertEqual(self.dispatcher.tick()['results'][0]['reason'], 'offline')
        self.assertFalse(self.queue_log.exists())
        self.runner.paste_prompt.assert_not_called()

    def test_revocation_during_final_composer_check_prevents_queue(self):
        self.send()
        captures = []
        def screen(*args):
            captures.append(args)
            if len(captures) == 3:
                self.bus.revoke_actor(self.actors[1].actor_id, self.operator)
            return EMPTY
        self.runner.capture_pane.side_effect = screen
        result = self.dispatcher.tick()['results'][0]
        self.assertEqual(result['status'], 'unsent', result)
        self.assertFalse(self.queue_log.exists())

    def test_unconfirmed_native_queue_stays_uncertain_without_resend(self):
        from codex_wake.a2a_delivery import NotificationDispatcher
        from codex_wake.a2a_scheduler import MailScheduler
        identifier = self.send()
        self.codex.write_text('#!/usr/bin/env python3\nimport sys\nprint("Queued message 00000000-0000-4000-8000-000000000003 for thread wrong-thread.")\n')
        result = self.dispatcher.tick()['results'][0]
        self.assertEqual(result['status'], 'uncertain')
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'uncertain')
        restarted = NotificationDispatcher(MailScheduler(self.mailbox, self.operator), self.bindings)
        self.assertEqual(restarted.tick()['results'], [])
        self.runner.paste_prompt.assert_not_called()

    def test_cancelled_and_expired_messages_have_zero_native_queue_effect(self):
        identifier = self.send(ttl=10)
        self.mailbox.cancel(self.actors[0], identifier)
        self.assertEqual(self.dispatcher.tick()['results'], [])
        expired = self.mailbox.send(self.actors[0], self.identities[1], body='expires',
                                   idempotency_key='expires', ttl=10)['message']['message_id']
        self.now += 11
        self.assertEqual(self.dispatcher.tick()['results'], [])
        self.assertEqual(self.mailbox.show(self.actors[0], expired)['state']['admission'], 'expired')
        self.assertFalse(self.queue_log.exists())

    prepare_reply = saved_fixture.SavedRecipientDeliveryTests.prepare_reply

    def test_native_reply_receipt_reconciles_bookkeeping_crash_without_resend(self):
        from datetime import datetime, timezone, timedelta
        from codex_wake.a2a_delivery import NotificationDispatcher
        from codex_wake.a2a_reply_wake import ReplyWakeGate, arm_reply
        from codex_wake.a2a_sender_receipts import SenderReceiptAuthority
        from codex_wake.records import find_record
        original, reply = self.prepare_reply()
        wake_root, authority = self.root / 'wake', self.root / 'sender-authority.json'
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
            rebuilt = NotificationDispatcher(self.scheduler, self.bindings,
                receipt_gate=ReplyWakeGate(self.scheduler, wake_root, authority))
            self.assertEqual(rebuilt.tick()['submitted'], 0)
            self.assertEqual(find_record(wake_root, armed['wake_id']).record['status'], 'submitted')
            self.runner.paste_prompt.assert_not_called()

    def assert_uncertain_native_response(self, *, response=None, error=None):
        from codex_wake.a2a_delivery import NotificationDispatcher
        from codex_wake.a2a_scheduler import MailScheduler
        identifier = self.send()
        with patch('codex_wake.a2a_tmux_delivery.subprocess.run', return_value=response, side_effect=error) as queue:
            self.assertEqual(self.dispatcher.tick()['results'][0]['status'], 'uncertain')
            restarted = NotificationDispatcher(MailScheduler(self.mailbox, self.operator), self.bindings)
            self.assertEqual(restarted.tick()['results'], [])
            self.assertEqual(queue.call_count, 1)
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'uncertain')
        self.runner.paste_prompt.assert_not_called()

    def test_malformed_and_rejected_queue_response_is_uncertain(self):
        import subprocess
        self.assert_uncertain_native_response(response=subprocess.CompletedProcess([], 1, 'unqualified', 'rejected'))

    def test_queue_timeout_is_uncertain_and_not_repeated(self):
        import subprocess
        self.assert_uncertain_native_response(error=subprocess.TimeoutExpired('fixture-codex', 10))

    def test_interrupted_queue_process_is_uncertain_and_not_repeated(self):
        self.assert_uncertain_native_response(error=OSError('fixture interruption'))

    def test_draft_appearing_during_native_preparation_prevents_queue(self):
        self.send()
        screens = []
        def screen(*args):
            screens.append(args)
            return EMPTY if len(screens) <= 3 else EMPTY.replace('Ask Codex to do anything', 'new human draft')
        self.runner.capture_pane.side_effect = screen
        result = self.dispatcher.tick()['results'][0]
        self.assertEqual(result['status'], 'unsent', result)
        self.assertFalse(self.queue_log.exists())

    def test_success_without_a_parseable_native_receipt_is_uncertain(self):
        import subprocess
        self.assert_uncertain_native_response(response=subprocess.CompletedProcess([], 0, 'unqualified', ''))

    def test_uncertain_receipt_identifies_actual_native_transport(self):
        identifier = self.send()
        self.codex.write_text('#!/usr/bin/env python3\nprint("unqualified")\n')
        self.assertEqual(self.dispatcher.tick()['results'][0]['status'], 'uncertain')
        message = self.mailbox.show(self.actors[0], identifier)
        receipt = next(r for r in message['receipts'] if r['kind'] == 'notification_uncertain')
        self.assertEqual(receipt['details']['evidence']['transport'], 'native_live_recipient_v1')
