"""Public durable notice seam; native/frontend proof is qualified separately."""
import tempfile
import unittest
from pathlib import Path

from codex_wake.goal_notices import record_notice, read_notice, list_notices, render_notice, present_notice


class GoalNoticeTests(unittest.TestCase):
    def test_stop_survives_restart_and_deduplicates_controller_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dict(thread_id='00000000-0000-7000-8000-000000000001',
                allocation_id='objective-1', generation='window-1', enrollment_revision=1,
                state='stopped', reason='allocation_exhausted', used_tokens=100000,
                token_limit=100000, token_accounting='fresh', deadline=1792908000,
                stop_turns=['work-1'], stop_proof=True,
                first_stop=dict(observed_boottime=100, reason='allocation_exhausted'))
            original = record_notice(root, receipt, 'stop', controller={'generation':'watcher-1'})
            again = record_notice(root, receipt, 'stop', controller={'generation':'watcher-2'})
            self.assertEqual(original['event_id'], again['event_id'])
            self.assertEqual(len(list_notices(root, receipt['thread_id'])), 1)
            retained = read_notice(root, original['event_id'])
            self.assertTrue(retained['proof']['control']['stop_verified'])
            self.assertEqual(retained['proof']['transcript']['state'], 'pending')
            self.assertEqual(retained['proof']['ui']['state'], 'unverified')
            card = render_notice(retained)
            self.assertIn('100,000 of 100,000', card)
            self.assertIn('Extend allowance', card)
            self.assertIn('Native /goal resume alone does not renew', card)
            self.assertNotIn('operator has read', card)

    def test_lost_delivery_ack_is_reconciled_without_replaying_notice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dict(thread_id='00000000-0000-7000-8000-000000000001',
                allocation_id='objective-1', generation='window-1', state='stopped',
                reason='allocation_exhausted', used_tokens=100, token_limit=100,
                token_accounting='fresh', deadline=1792908000, stop_turns=['work-1'])
            event = record_notice(root, receipt, 'stop')
            class LostAck:
                def __init__(self): self.sent = []
                def append(self, event):
                    self.sent.append(event['event_id'])
                    raise TimeoutError('ack lost')
                def reconcile(self, event):
                    return dict(transcript=bool(self.sent), model_context=bool(self.sent), notification_published=bool(self.sent))
            adapter = LostAck()
            first = present_notice(root, event['event_id'], adapter=adapter)
            self.assertEqual(first['delivery']['state'], 'unknown')
            reconciled = present_notice(root, event['event_id'], adapter=adapter)
            self.assertEqual(reconciled['delivery']['state'], 'recorded')
            self.assertEqual(adapter.sent, [event['event_id']])
            self.assertEqual(reconciled['proof']['ui']['state'], 'unverified')
            self.assertEqual(reconciled['proof']['model_context']['state'], 'available')

    def test_recorded_stop_text_reflects_control_proof_before_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dict(thread_id='00000000-0000-7000-8000-000000000001',
                allocation_id='objective-1', generation='window-1', state='stop_unverified',
                reason='allocation_exhausted', used_tokens=100, token_limit=100,
                token_accounting='fresh', deadline=1792908000, stop_turns=['work-1'])
            pending = record_notice(root, receipt, 'stop')
            self.assertIn('interruption unverified', pending['text'])
            receipt.update(state='stopped', stop_proof=True)
            verified = record_notice(root, receipt, 'stop')
            self.assertEqual(verified['event_id'], pending['event_id'])
            self.assertIn('Goal paused.', verified['text'])
            self.assertNotIn('interruption unverified', verified['text'])

    def test_unknown_native_append_is_not_replayed_when_readback_proves_absence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dict(thread_id='00000000-0000-7000-8000-000000000001',
                allocation_id='objective-1', generation='window-1', state='stopped',
                reason='allocation_exhausted', used_tokens=100, token_limit=100,
                token_accounting='fresh', deadline=1792908000, stop_turns=['work-1'])
            event = record_notice(root, receipt, 'stop')
            class LostRequest:
                def __init__(self): self.sent = 0
                def append(self, event):
                    self.sent += 1
                    raise TimeoutError()
                def reconcile(self, event):
                    return dict(transcript=False, model_context=False, notification_published=False)
            adapter = LostRequest()
            present_notice(root, event['event_id'], adapter=adapter)
            again = present_notice(root, event['event_id'], adapter=adapter)
            self.assertEqual(adapter.sent, 1)
            self.assertEqual(again['delivery']['state'], 'unknown')

    def test_unsupported_runtime_retains_notice_without_attempting_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dict(thread_id='00000000-0000-7000-8000-000000000001',
                allocation_id='objective-1', generation='window-1', state='stopped',
                reason='allocation_exhausted', used_tokens=100, token_limit=100,
                token_accounting='fresh', deadline=1792908000)
            event = record_notice(root, receipt, 'stop')
            class Unsupported:
                def reconcile(self, event): raise ValueError('unsupported')
                def append(self, event): raise AssertionError('must not append')
            retained = present_notice(root, event['event_id'], adapter=Unsupported())
            self.assertEqual(retained['delivery']['state'], 'unsupported')
            self.assertEqual(retained['delivery']['attempts'], 0)
            self.assertEqual(read_notice(root, event['event_id'])['event_id'], event['event_id'])
