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


class HostNativeObservationTests(unittest.TestCase):
    def test_host_readback_binds_resource_to_source_and_successor(self):
        calls = []
        def request(method, params):
            calls.append((method, params))
            if method == 'thread/goal/get':
                return {'goal': {'threadId': 'source', 'status': 'paused'}}
            if method == 'skills/list':
                return {'data': [{'skills': [{'path': '/guide', 'enabled': True}]}]}
            return {'content': [{'text': '{"session":{"thread_id":"source"},"complete":true}'}]}
        result = runner.observe_native_preflight(request, 'source', 'successor', '/guide', '/workspace')
        self.assertEqual(result['source_thread_id'], 'source')
        self.assertEqual(result['successor_thread_id'], 'successor')
        self.assertEqual(result['native_resource']['state'], 'passed')
        self.assertEqual(calls[-1][1]['threadId'], 'successor')
        self.assertEqual(calls[-1][1]['arguments'], {'selector': 'thread:source'})

    def test_host_readback_rejects_another_resource_identity(self):
        def request(method, params):
            if method == 'thread/goal/get':
                return {'goal': {'threadId': 'source', 'status': 'paused'}}
            if method == 'skills/list':
                return {'data': [{'skills': [{'path': '/guide', 'enabled': True}]}]}
            return {'content': [{'text': '{"session":{"thread_id":"foreign"},"complete":true}'}]}
        with self.assertRaisesRegex(RuntimeError, 'identity/readiness mismatch'):
            runner.observe_native_preflight(request, 'source', 'successor', '/guide', '/workspace')


if __name__ == '__main__':
    unittest.main()
