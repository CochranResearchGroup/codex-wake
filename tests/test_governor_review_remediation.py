"""Regressions from the single governor Standards/Spec review."""
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from codex_wake.goal_governance import change
from codex_wake.session_permissions import Principal
import test_goal_supervision as fixtures
import test_completion_reserve as completion_fixtures


class GovernorReviewTests(unittest.TestCase):
    fixture = completion_fixtures.CompletionReserveTests.fixture
    controller = completion_fixtures.CompletionReserveTests.controller
    campaign = completion_fixtures.CompletionReserveTests.campaign

    def test_missing_current_activation_prevents_provider_submission(self):
        with self.campaign() as (gateway, submit, status, source, obligations, clock, native, calls, ledger):
            native['notices'] = {}
            code, body = submit()
            self.assertEqual(code, 503, body)
            self.assertIn(b'governor_activation_unavailable', body)
            self.assertEqual(calls, [])
            self.assertEqual(ledger.inspect(now=clock[0])['tokens_used'], 40)

    def test_disabled_governor_allows_completion_after_its_former_timeout(self):
        release, arrived = threading.Event(), threading.Event()
        with self.campaign(request_timeout=0.05, provider_release=release, provider_arrived=arrived) as (gateway, submit, status, source, obligations, clock, native, calls, ledger):
            change(gateway.root, fixtures.THREAD, enabled=False,
                principal=Principal(fixtures.THREAD, 'operator'), allocation_id='allocation-1')
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(submit)
                try:
                    self.assertTrue(arrived.wait(2), 'provider never received the inactive request')
                    # This wait tests the duration policy, not service readiness.
                    threading.Event().wait(0.15)
                finally:
                    release.set()
                code, body = future.result(timeout=3)
            self.assertEqual(code, 200, body)
            self.assertEqual(status()['mode'], 'inactive')
            self.assertEqual(ledger.inspect(now=clock[0])['tokens_used'], 50)

    def test_listener_refuses_nonprivate_shared_accounting_state(self):
        with self.campaign(shared_allocation=True) as (gateway, submit, status, source, obligations, clock, native, calls, ledger):
            # Simulate a host permission change after successful construction.
            allocation, = (gateway.root / 'goal-supervision' / 'allocations').glob('*.json')
            allocation.chmod(0o644)
            try:
                with self.assertRaisesRegex(ValueError, 'private and owned'):
                    gateway.bind_listener('http://127.0.0.1:12345')
            finally:
                allocation.chmod(0o600)
