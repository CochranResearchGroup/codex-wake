"""Acceptance runner keeps the same native assignment alive during clock holds."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import agent_handoff_acceptance as runner


class PreflightSupervisionTests(unittest.TestCase):
    def test_transient_time_hold_observes_same_intent_until_preflight_ready(self):
        intent = ['sessions', 'handoff', '--intent', 'original']
        states = iter([
            (2, dict(state='blocked', reason='admissible_time_unavailable',
                     successor_thread_id='receiver', successor={'submission_id': 'task'})),
            (0, dict(state='awaiting_activation', successor_thread_id='receiver')),
        ])
        calls, observations = [], []
        def invoke(args):
            calls.append(args)
            return next(states)
        with patch.object(runner.time, 'monotonic', return_value=0), patch.object(runner.time, 'sleep'):
            result = runner.wait_for_preflight(invoke, intent, 10, observations.append)
        self.assertEqual(result['state'], 'awaiting_activation')
        self.assertEqual(calls, [intent, intent])
        self.assertEqual(len(observations), 2)

    def test_clock_hold_cannot_extend_observation_deadline(self):
        state = dict(state='blocked', reason='admissible_time_unavailable')
        calls = []
        def invoke(args):
            calls.append(args)
            return 2, state
        with patch.object(runner.time, 'monotonic', return_value=11), patch.object(runner.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'admissible_time_unavailable'):
                runner.wait_for_preflight(invoke, ['original'], 10, lambda state: None)
        self.assertEqual(calls, [['original']])

    def test_exhausted_allowance_remains_terminal(self):
        state = dict(state='blocked', reason='preflight_allowance_exhausted')
        with patch.object(runner.time, 'monotonic', return_value=0):
            with self.assertRaisesRegex(RuntimeError, 'preflight_allowance_exhausted'):
                runner.wait_for_preflight(lambda args: (2, state), ['original'], 10, lambda state: None)


if __name__ == '__main__':
    unittest.main()
