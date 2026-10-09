from dataclasses import asdict
from datetime import datetime, timezone, timedelta
import json
import unittest
from unittest.mock import patch

from codex_wake.a2a_delivery import NotificationDispatcher, bind_client
from codex_wake.a2a_identity import BusError
from codex_wake.a2a_reply_wake import ReplyWakeGate, arm_reply
from codex_wake.a2a_sender_receipts import SenderReceiptAuthority
from codex_wake.records import find_record, cancel_record
from tests import test_a2a_delivery as delivery_fixture


class ReplyWakeTests(unittest.TestCase):
    setUp = delivery_fixture.OwningClientDeliveryTests.setUp
    serve = delivery_fixture.OwningClientDeliveryTests.serve
    close = delivery_fixture.OwningClientDeliveryTests.close

    def prepare(self):
        self.wake_root = self.root / 'wake'
        self.authority_file = self.private / 'sender-authority.json'
        self.authority_file.write_text(json.dumps(dict(schema_version=1, wake_root=str(self.wake_root),
            senders=[dict(bus_root=str(self.bus.root), bus_id=self.bus.bus_id,
                operator_capability=str(self.operator), actor=asdict(self.actors[0]))])))
        self.authority_file.chmod(0o600)
        health = patch('codex_wake.monitor.monitor_state_dir', return_value=self.private / 'health')
        health.start(); self.addCleanup(health.stop)
        self.gate = ReplyWakeGate(self.scheduler, self.wake_root, self.authority_file)
        self.gate.tick()
        self.thread_id = 'sender'
        self.bindings.unlink()
        bind_client(self.bindings, self.socket_path, self.identities[0])
        self.dispatcher = NotificationDispatcher(self.scheduler, self.bindings, receipt_gate=self.gate)
        self.identifier = self.mailbox.send(self.actors[0], self.identities[1], body='request',
            idempotency_key='request', delivery='inbox')['message']['message_id']

    def arm(self):
        return arm_reply(self.actors[0], self.identifier, self.wake_root, self.authority_file,
            'reply-arm', (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat())

    def reply(self):
        return self.mailbox.reply(self.actors[1], self.identifier, body='reply',
            idempotency_key='reply')['message']['message_id']

    def test_reply_uses_durable_exact_arm_once_after_worker_reconstruction(self):
        self.prepare()
        arm = self.arm()
        self.assertEqual(self.dispatcher.tick()['submitted'], 0)
        reply_id = self.reply()
        self.gate = ReplyWakeGate(self.scheduler, self.wake_root, self.authority_file)
        self.dispatcher = NotificationDispatcher(self.scheduler, self.bindings, receipt_gate=self.gate)
        result = self.dispatcher.tick()
        self.assertEqual(result['submitted'], 1)
        self.assertEqual(self.deliveries[0]['message_id'], reply_id)
        record = find_record(self.wake_root, arm['wake_id']).record
        self.assertEqual(record['status'], 'submitted')
        self.assertEqual(record['transport_receipt']['message_id'], reply_id)
        self.assertEqual(self.dispatcher.tick()['submitted'], 0)
        self.assertEqual(len(self.deliveries), 1)

    def test_missing_arm_and_revoked_delegation_cannot_wake_sender(self):
        self.prepare()
        self.reply()
        self.assertEqual(self.dispatcher.tick()['results'][0]['reason'], 'reply_arm_unavailable')
        self.assertEqual(self.deliveries, [])
        self.arm()
        self.authority_file.write_text('{}')
        self.authority_file.chmod(0o600)
        with self.assertRaises(BusError):
            SenderReceiptAuthority(self.authority_file, self.wake_root).adapter(self.actors[0], self.identifier)
        self.assertEqual(self.deliveries, [])

    def test_sender_delegation_never_authorizes_recipient_arms(self):
        self.prepare()
        authority = SenderReceiptAuthority(self.authority_file, self.wake_root)
        with self.assertRaises(BusError):
            authority.adapter(self.actors[1], self.identifier)
        adapter = authority.adapter(self.actors[0], self.identifier)
        with self.assertRaises(BusError):
            with adapter.mailbox.transaction(self.actors[0], permission='send'):
                pass

    def test_explicit_operator_delegation_is_read_back_and_cannot_use_actor_capability(self):
        self.prepare()
        authority = SenderReceiptAuthority(self.authority_file, self.wake_root)
        result = authority.delegate(self.bus, self.operator, self.actors[0])
        self.assertEqual(result['thread_id'], self.actors[0].thread_id)
        self.assertEqual(len(authority.senders()), 1)
        capability = self.bus.root / 'capabilities' / (self.actors[0].actor_id + '.json')
        with self.assertRaises(BusError):
            authority.delegate(self.bus, capability, self.actors[0])

    def test_cancelled_reply_arm_prevents_transport(self):
        self.prepare()
        arm = self.arm()
        cancel_record(self.wake_root, arm['wake_id'])
        self.reply()
        self.assertEqual(self.dispatcher.tick()['submitted'], 0)
        self.assertEqual(self.deliveries, [])

    def test_expired_matched_arm_prevents_transport(self):
        self.prepare()
        self.arm(); self.reply()
        future = datetime.now(timezone.utc) + timedelta(minutes=3)
        with patch('codex_wake.records.utc_now', return_value=future):
            self.assertEqual(self.dispatcher.tick()['submitted'], 0)
        self.assertEqual(self.deliveries, [])

    def test_worker_crash_after_send_receipt_reconciles_arm_without_resending(self):
        self.prepare()
        arm = self.arm(); self.reply()
        with patch.object(self.gate, 'submitted', side_effect=OSError('simulated bookkeeping crash')):
            with self.assertRaises(OSError):
                self.dispatcher.tick()
        self.assertEqual(find_record(self.wake_root, arm['wake_id']).record['status'], 'firing')
        self.assertEqual(len(self.deliveries), 1)
        gate = ReplyWakeGate(self.scheduler, self.wake_root, self.authority_file)
        dispatcher = NotificationDispatcher(self.scheduler, self.bindings, receipt_gate=gate)
        self.assertEqual(dispatcher.tick()['submitted'], 0)
        self.assertEqual(find_record(self.wake_root, arm['wake_id']).record['status'], 'submitted')
        self.assertEqual(len(self.deliveries), 1)

    def test_network_bus_reply_arm_uses_network_time_despite_guest_wall_disagreement(self):
        from codex_wake.a2a_mailbox import Mailbox
        from codex_wake.time_provider import TimeDecision
        reading = TimeDecision('network', ('a','b'), 1000, 1000.1)
        with patch('codex_wake.time_inspection.network_time_decision', return_value=reading):
            Mailbox.activate_network_time(self.bus, self.operator)
            self.prepare()
            expiry = datetime.fromtimestamp(1060, timezone.utc).isoformat()
            armed = arm_reply(self.actors[0], self.identifier, self.wake_root, self.authority_file, 'network-arm', expiry)
            reply_id = self.reply()
            self.assertEqual(self.dispatcher.tick()['submitted'], 1)
            self.assertEqual(self.deliveries[0]['message_id'], reply_id)
            self.assertEqual(find_record(self.wake_root, armed['wake_id']).record['status'], 'submitted')
