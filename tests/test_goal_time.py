"""Qualified relative allowance time; never substitute guest UTC or rebase."""
import unittest
from unittest.mock import patch


ANCHOR = dict(epoch='00000000-0000-4000-8000-000000000468', counter=1000, frequency=1000, rate_ppm=100)


class GoalTimeTests(unittest.TestCase):
    def test_fresh_allowance_uses_authenticated_counter_without_inventing_utc(self):
        from codex_wake.goal_time import admit, public_time, upper
        clock=dict(utc=None,counter=ANCHOR,reason='authenticated_counter_only')
        with patch('codex_wake.lifecycle_budget.trusted_upper',side_effect=ValueError('admissible time unavailable')), patch('codex_wake.native_clock.snapshot',return_value=clock):
            now, fields=admit(None,allow_counter=True)
        self.assertEqual(now,0)
        self.assertEqual(fields['time_basis'],'authenticated_host_counter')
        self.assertEqual(fields['clock_anchor'],ANCHOR)
        receipt=dict(fields,deadline=10,time_limit_seconds=10,started_upper=0,time_origin=0)
        later=dict(clock,counter=dict(ANCHOR,counter=2000))
        with patch('codex_wake.native_clock.snapshot',return_value=later):
            elapsed=upper(receipt)
        self.assertGreaterEqual(elapsed,1)
        self.assertLess(elapsed,1.002)
        shown=public_time(receipt)
        self.assertIsNone(shown['deadline'])
        self.assertIsNone(shown['deadline_utc'])
        self.assertEqual(shown['elapsed_limit_seconds'],10)

    def test_counter_readiness_and_notice_never_format_elapsed_as_utc(self):
        import tempfile,time
        from pathlib import Path
        from codex_wake.goal_readiness import engagement
        from codex_wake.goal_notices import record_notice
        receipt=dict(thread_id='00000000-0000-4000-8000-000000000468',allocation_id='own',
            generation='receipt',enrollment_revision=1,state='armed',accounting=dict(state='qualified'),
            used_tokens=1,token_limit=10,token_accounting='fresh',deadline=10,
            time_limit_seconds=10,time_origin=0,started_upper=0,
            started_boottime=time.clock_gettime(time.CLOCK_BOOTTIME),
            checkpoint_token_percent=5,checkpoint_seconds=1,session_scope=True,native_goal_status=None,
            time_basis='authenticated_host_counter',clock_anchor=ANCHOR,
            clock_observation=dict(ANCHOR,counter=2000),clock_elapsed_upper=1.0012,
            poll_ack=dict(enrollment_revision=1,receipt_generation='receipt',
                controller_generation='controller',observed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME)))
        controller=dict(fresh=True,generation='controller',interval=1)
        self.assertFalse(engagement(receipt,controller)['engaged'])
        controller.update(time_bases=['qualified_utc','authenticated_host_counter'],session_scope_without_goal=True)
        view=engagement(receipt,controller)
        self.assertTrue(view['engaged'])
        self.assertIsNone(view['card']['deadline_utc'])
        self.assertIsNone(view['card']['timezone'])
        self.assertEqual(view['card']['time_basis'],'authenticated_host_counter')
        with tempfile.TemporaryDirectory() as directory:
            event=record_notice(Path(directory),receipt,'activation')
            self.assertNotIn('1970',event['text'])
            self.assertIn('authenticated host elapsed',event['text'])
            self.assertIsNone(event['snapshot']['deadline'])

    def test_counter_anchor_cannot_switch_basis_or_survive_continuity_loss(self):
        from codex_wake.goal_time import admit,GoalTimeUnavailable
        original=dict(time_basis='authenticated_host_counter',clock_anchor=dict(ANCHOR),
            clock_observation=dict(ANCHOR),clock_elapsed_upper=0,time_limit_seconds=10)
        with patch('codex_wake.native_clock.snapshot',return_value=dict(
                utc=dict(lower=100,upper=100),counter=dict(ANCHOR,counter=2000),reason='authenticated_utc')):
            _,later=admit(original)
        self.assertEqual(later['clock_anchor'],ANCHOR)
        self.assertEqual(later['time_basis'],'authenticated_host_counter')
        for counter in (None,dict(ANCHOR,epoch='replacement'),dict(ANCHOR,counter=999)):
            with self.subTest(counter=counter),patch('codex_wake.native_clock.snapshot',return_value=dict(
                    utc=None,counter=counter,reason='authenticated_counter_only')):
                with self.assertRaises(GoalTimeUnavailable):admit(original)
        self.assertEqual(original['clock_elapsed_upper'],0)
        self.assertEqual(original['clock_anchor'],ANCHOR)

    def test_inherited_utc_scope_cannot_use_counter_fallback(self):
        from codex_wake.goal_time import admit
        with patch('codex_wake.lifecycle_budget.trusted_upper',side_effect=ValueError('admissible time unavailable')),patch(
                'codex_wake.native_clock.snapshot') as snapshot:
            with self.assertRaisesRegex(ValueError,'admissible time unavailable'):
                admit(dict(time_basis='qualified_utc',deadline=100),allow_counter=True)
            snapshot.assert_not_called()
