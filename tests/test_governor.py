"""Ordinary governor controls use the retained accounting/controller owners."""
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


class GovernorTests(unittest.TestCase):
    def test_status_does_not_provision_an_allowance_or_watcher(self):
        from codex_wake.governor import execute
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'uncreated'
            row = dict(thread_id='11111111-1111-1111-1111-111111111111', endpoint='unix:///owned')
            with patch('codex_wake.local_sessions.resolve', return_value=row):
                result = execute(root, 'status', dict(selector=row['thread_id']))
            self.assertEqual(result['state'], 'disconnected')
            self.assertIsNone(result['usage']['used_tokens'])
            self.assertEqual(result['reason'], 'not_enrolled')
            self.assertFalse(root.exists())

    def test_activation_starts_new_window_without_erasing_lifetime_history(self):
        import json
        import test_goal_supervision as fixtures
        from codex_wake.goal_supervision import enroll, poll
        harness = fixtures.GoalSupervisionTests()
        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, _ = harness.fixture(directory)
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW):
                first = enroll(root, policy, fixtures.THREAD, 100, 120,
                    session_scope=True, activation_baseline=True)
                self.assertEqual(first['used_tokens'], 0)
                self.assertEqual(first['lifetime_used_tokens'], 40)
                self.assertEqual(first['deadline'], fixtures.NOW+120)
                again = enroll(root, policy, fixtures.THREAD, 90, 110,
                    session_scope=True, activation_baseline=True)
                self.assertEqual(again['generation'], first['generation'])
                self.assertEqual(again['lifetime_used_tokens'], 40)

    def test_operator_controls_retain_usage_and_model_cannot_loosen(self):
        import test_goal_supervision as fixtures
        from codex_wake.governor import execute, local_operator_principal
        from codex_wake.goal_supervision import enroll
        from codex_wake.session_permissions import Principal
        harness = fixtures.GoalSupervisionTests()
        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, _ = harness.fixture(directory)
            native['goal']['status'] = 'paused'
            native['active'] = []
            row = dict(thread_id=fixtures.THREAD, endpoint='unix:///owned')
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW), patch('codex_wake.local_sessions.resolve', return_value=row):
                enroll(root, policy, fixtures.THREAD, 100, 120)
                with self.assertRaisesRegex(ValueError, 'authenticated operator'):
                    execute(root, 'extend', dict(selector=fixtures.THREAD, add_tokens=50), principal=Principal(fixtures.THREAD))
                args = dict(selector=fixtures.THREAD, add_tokens=50, add_seconds=30, request_id='extend-once')
                extended = execute(root, 'extend', args, principal=local_operator_principal())
                self.assertEqual(extended['limits']['token_limit'], 150)
                self.assertEqual(extended['usage']['used_tokens'], 40)
                self.assertEqual(execute(root, 'extend', args, principal=local_operator_principal())['limits']['token_limit'], 150)
                reset = execute(root, 'reset', dict(selector=fixtures.THREAD, request_id='reset-once'), principal=local_operator_principal())
                self.assertEqual(reset['usage']['used_tokens'], 0)
                self.assertEqual(reset['usage']['lifetime_used_tokens'], 40)
                advisory = execute(root, 'advisory', dict(selector=fixtures.THREAD), principal=local_operator_principal())
                self.assertEqual(advisory['state'], 'advisory')
                disabled = execute(root, 'disable', dict(selector=fixtures.THREAD), principal=local_operator_principal())
                self.assertEqual(disabled['state'], 'disabled')
                self.assertEqual(disabled['usage']['lifetime_used_tokens'], 40)
                self.assertEqual(native['goal']['status'], 'paused')
