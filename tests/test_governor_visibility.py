"""Governor activation and intervention are explicit through public journeys."""
import tempfile
import unittest
from unittest.mock import patch

import test_goal_supervision as fixtures
from codex_wake.goal_supervision import enroll, show, poll
from codex_wake.goal_notices import list_notices


class GovernorVisibilityTests(unittest.TestCase):
    fixture = fixtures.GoalSupervisionTests.fixture
    controller = fixtures.GoalSupervisionTests.controller

    def test_activation_precedes_poll_and_exposes_mode_and_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, _ = self.fixture(directory)
            with self.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW):
                enrolled = enroll(root, policy, fixtures.THREAD, 100, 120)
                notices = list_notices(root, fixtures.THREAD)
                self.assertEqual([n['identity']['kind'] for n in notices], ['activation'])
                notice = notices[0]
                self.assertIn('sampled_stop', notice['text'])
                self.assertIn('maximum overshoot is not bounded', notice['text'])
                self.assertIn('Deactivate governor', notice['text'])
                self.assertIsNotNone(notice['recorded_at'])
                self.assertLessEqual(len(notice['text'].encode()), 768)
                self.assertEqual(enrolled['governor']['mode'], 'sampled_stop')
                self.assertFalse(any(m in ('thread/goal/set', 'turn/interrupt') for m, _ in native['calls']))
                enroll(root, policy, fixtures.THREAD, 100, 120)
                self.assertEqual(len(list_notices(root, fixtures.THREAD)), 1)

    def test_stop_presentation_failure_is_visible_outside_model_delivery(self):
        from codex_wake.goal_notices import present_notice
        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, _ = self.fixture(directory)
            with self.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW):
                enroll(root, policy, fixtures.THREAD, 40, 120)
                stopped = poll(root)[0]
                event_id = stopped['notice_ids']['stop']
                class Unsupported:
                    def reconcile(self, event):
                        raise ValueError('notice transport unsupported')
                present_notice(root, event_id, adapter=Unsupported())
                status = show(root, policy, fixtures.THREAD)['governor']
                self.assertEqual(status['intervention']['reason'], 'allocation_exhausted')
                self.assertEqual(status['intervention']['presentation'], 'unsupported')
                self.assertTrue(status['intervention']['next_action'])
                self.assertEqual(status['intervention']['ui'], 'unverified')
                self.assertEqual(native['goal']['status'], 'paused')
                self.assertFalse(any(m == 'turn/start' for m, _ in native['calls']))
