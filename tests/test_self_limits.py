"""Own-session setup through the public hook and real controller process."""
from contextlib import contextmanager
import json
import os
import signal
import tempfile
import time
import unittest
from unittest.mock import patch
import test_goal_supervision as fixtures
THREAD, NOW = fixtures.THREAD, fixtures.NOW


class SelfLimitsTests(unittest.TestCase):
    fixture = fixtures.GoalSupervisionTests.fixture
    def test_own_setup_starts_controller_and_stops_at_existing_usage(self):
        from codex_wake.self_limits import execute
        with tempfile.TemporaryDirectory() as directory, self.controllers():
            root, policy, _, native, _ = self.fixture(directory)
            grant = json.loads(policy.read_text())['callers'][THREAD]
            grant.pop('allocation_id')
            policy.write_text(json.dumps(dict(version=2, native_caller_binding=True,
                allocations={}, self_enrollment=grant)))
            context = dict(threadId=THREAD, sessionId=THREAD, callId='self-test',
                **{'x-codex-turn-metadata': dict(thread_id=THREAD,session_id=THREAD,turn_id='work')})
            with patch('codex_wake.lifecycle_budget.trusted_upper', return_value=NOW), patch('codex_wake.goal_watcher.watcher_status', return_value=dict(reason='watcher_not_installed')):
                first = execute(root, policy, 'set', dict(token_limit=100,time_limit_seconds=120), native_context=context)
                self.assertIn('pid', first['controller'], (first, (root/'goal-supervision/self-watcher.log').read_text() if (root/'goal-supervision/self-watcher.log').exists() else 'no log'))
                pid = first['controller']['pid']
                self.assertTrue(first['controller']['fresh'])
                self.assertEqual(first['used_tokens'],40)
                with self.assertRaisesRegex(ValueError, 'tighten'):
                    execute(root,policy,'set',dict(token_limit=101,time_limit_seconds=120),native_context=context)
                tightened = execute(root,policy,'set',dict(token_limit=39,time_limit_seconds=120),native_context=context)
                self.assertEqual(tightened['lifetime_used_tokens'],40)
                end=time.monotonic()+6
                while time.monotonic()<end and native['goal']['status']!='paused':
                    time.sleep(.05)
                self.assertEqual(native['goal']['status'],'paused')
                self.assertEqual(native['active'],[])

    def test_mask_and_inherited_ceiling_are_preserved(self):
        from codex_wake.self_limits import execute, _CHILDREN
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,_=self.fixture(directory)
            context=dict(threadId=THREAD,sessionId=THREAD,callId='self-test',
                **{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='work')})
            with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW), patch(
                    'codex_wake.goal_watcher.watcher_status',return_value=dict(reason='watcher_masked')):
                with self.assertRaisesRegex(ValueError,'inherited host ceilings'):
                    execute(root,policy,'set',dict(token_limit=1001,time_limit_seconds=120),native_context=context)
                result=execute(root,policy,'set',dict(token_limit=100,time_limit_seconds=120),native_context=context)
                self.assertEqual(result['watcher_setup']['reason'],'watcher_masked')
                self.assertFalse(result['engagement']['engaged'])
                self.assertFalse(_CHILDREN)
                with self.assertRaisesRegex(ValueError,'show and set/tighten only'):
                    execute(root,policy,'disable',{},native_context=context)
                self.assertFalse(any(method in ('thread/goal/set','turn/interrupt') for method,_ in native['calls']))

    def test_default_policy_allows_self_watcher_but_external_deny_wins(self):
        from codex_wake.self_limits import execute
        from codex_wake.session_permissions import PermissionStore, Principal
        for denied in (False, True):
            with self.subTest(denied=denied), tempfile.TemporaryDirectory() as directory, self.controllers():
                root,policy,_,_,_=self.fixture(directory)
                rules={'version':1}
                if denied:
                    rules['mandatory']=['enforcement.watcher_start']
                PermissionStore(root).configure(rules,Principal('operator','operator'),expected_revision=0)
                context=dict(threadId=THREAD,sessionId=THREAD,callId='self-test',
                    **{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='work')})
                with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW), patch(
                        'codex_wake.goal_watcher.watcher_status',return_value=dict(reason='watcher_not_installed')):
                    result=execute(root,policy,'set',dict(token_limit=100,time_limit_seconds=120),native_context=context)
                    self.assertEqual(result['engagement']['engaged'],not denied)
                    if denied:
                        self.assertEqual(result['watcher_setup']['reason'],'permission_deny')
                        self.assertFalse(result['watcher_setup']['start_attempted'])

    def test_fresh_usage_has_no_goal_or_grant_requirement(self):
        from codex_wake.goal_usage import observe_session_usage
        with tempfile.TemporaryDirectory() as directory:
            _, _, log, _, _ = self.fixture(directory)
            rows=[json.loads(row) for row in log.read_text().splitlines()]
            log.write_text(''.join(json.dumps(row)+'\n' for row in rows if row.get('payload',{}).get('type')!='thread_goal_updated'))
            usage=observe_session_usage(log.parent.parent,THREAD)
            self.assertEqual(usage['state'],'qualified')
            self.assertEqual(usage['used_tokens'],40)

    @contextmanager
    def controllers(self):
        from codex_wake.self_limits import _CHILDREN
        try:
            yield
        finally:
            for pid, process in list(_CHILDREN.items()):
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=5)
                del _CHILDREN[pid]
