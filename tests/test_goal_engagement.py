"""Watcher engagement is a completed independent poll, not successful configuration."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import test_goal_supervision as fixtures
THREAD, NOW = fixtures.THREAD, fixtures.NOW
from codex_wake.goal_supervision import enroll, show


class GoalEngagementTests(unittest.TestCase):
    fixture = fixtures.GoalSupervisionTests.fixture
    controller = fixtures.GoalSupervisionTests.controller


def test_enrollment_waits_for_exact_first_poll(self):
    with tempfile.TemporaryDirectory() as directory:
        root, policy, _, _, _ = self.fixture(directory)
        with self.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=NOW):
            first = enroll(root, policy, THREAD, 100, 120)
            self.assertEqual(first['engagement']['status'], 'waiting_for_first_poll')
            self.assertFalse(first['engagement']['engaged'])
            self.assertEqual(show(root, policy, THREAD)['engagement']['status'], 'waiting_for_first_poll')
            again = enroll(root, policy, THREAD, 100, 120)
            self.assertEqual(again['enrollment_revision'], first['enrollment_revision'])


def test_real_watcher_acknowledges_enrollment_and_preserves_budget(self):
    with tempfile.TemporaryDirectory() as directory:
        root, policy, _, _, _ = self.fixture(directory)
        source = ("import sys; from unittest.mock import patch; "
                  "from codex_wake.goal_supervision import watch; "
                  "p=patch('codex_wake.lifecycle_budget.trusted_upper',return_value=" + str(NOW) + "); p.start(); "
                  "watch(sys.argv[1],interval=.05)")
        process = subprocess.Popen([sys.executable, '-c', source, str(root)], stderr=subprocess.PIPE)
        try:
            until = time.monotonic()+5
            while not (root/'goal-supervision/controller.json').exists():
                if process.poll() is not None:
                    self.fail(process.stderr.read().decode())
                if time.monotonic()>until:
                    self.fail('independent watcher did not start')
                time.sleep(.01)
            with patch('codex_wake.lifecycle_budget.trusted_upper', return_value=NOW):
                first = enroll(root, policy, THREAD, 100, 120)
                while True:
                    current = show(root, policy, THREAD)
                    if current['engagement']['engaged']:
                        break
                    if process.poll() is not None or time.monotonic()>until:
                        self.fail('watcher did not acknowledge exact enrollment')
                    time.sleep(.01)
                self.assertEqual(current['poll_ack']['enrollment_revision'], first['enrollment_revision'])
                self.assertEqual(current['poll_ack']['controller_generation'], current['controller']['generation'])
                self.assertEqual(current['engagement']['card']['used_tokens'], 40)
                self.assertEqual(current['engagement']['card']['remaining_tokens'], 60)
                self.assertEqual(current['engagement']['card']['deadline_utc'], '2030-01-01T00:02:00Z')
                again = enroll(root, policy, THREAD, 100, 120)
                self.assertEqual(again['deadline'], first['deadline'])
                self.assertEqual(again['generation'], first['generation'])
                self.assertEqual(again['enrollment_revision'], first['enrollment_revision'])
                tightened=enroll(root,policy,THREAD,90,120)
                self.assertEqual(tightened['enrollment_revision'],first['enrollment_revision']+1)
                self.assertEqual(tightened['engagement']['status'],'waiting_for_first_poll')
                self.assertEqual(tightened['used_tokens'],40)
                self.assertEqual(tightened['deadline'],first['deadline'])
        finally:
            process.kill()
            process.wait(timeout=3)
            process.stderr.close()
        with patch('codex_wake.lifecycle_budget.trusted_upper', return_value=NOW):
            stopped = show(root, policy, THREAD)
            self.assertFalse(stopped['engagement']['engaged'])
            self.assertEqual(stopped['engagement']['status'], 'watcher_not_running')


GoalEngagementTests.test_enrollment_waits_for_exact_first_poll = test_enrollment_waits_for_exact_first_poll
GoalEngagementTests.test_real_watcher_acknowledges_enrollment_and_preserves_budget = test_real_watcher_acknowledges_enrollment_and_preserves_budget


def test_diagnose_reports_missing_history_without_enrolling(self):
    from codex_wake.goal_supervision import diagnose
    with tempfile.TemporaryDirectory() as directory:
        root, policy, log, native, _ = self.fixture(directory)
        log.unlink()
        result = diagnose(root, policy, THREAD)
        self.assertEqual(result['readiness']['status'], 'accounting_unavailable')
        self.assertEqual(result['accounting']['state'], 'unknown')
        self.assertTrue(result['accounting']['reason'])
        self.assertFalse(result['enrolled'])
        self.assertFalse(result['effect_attempted'])
        self.assertFalse(any(method in ('thread/goal/set','turn/interrupt','turn/start') for method,_ in native['calls']))

GoalEngagementTests.test_diagnose_reports_missing_history_without_enrolling = test_diagnose_reports_missing_history_without_enrolling


def test_native_diagnose_and_cli_report_same_accounting_blocker(self):
    from contextlib import redirect_stdout
    from io import StringIO
    from codex_wake.cli import run
    from codex_wake.mcp_server import CommandRunner
    with tempfile.TemporaryDirectory() as directory:
        root, policy, log, _, _ = self.fixture(directory)
        log.unlink()
        output=StringIO()
        with redirect_stdout(output):
            code=run(['--wake-root',str(root),'goal-limits','diagnose','--policy',str(policy),
                '--caller-thread-id',THREAD,'--json'])
        self.assertEqual(code,0)
        cli=json.loads(output.getvalue())
        context=dict(threadId=THREAD,sessionId=THREAD,callId='readiness-diagnosis',
            **{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='work')})
        runner=CommandRunner(wake_root=root,goal_limits_root=root,goal_limits_policy=policy)
        value,failed=runner.call('wake_goal_limits_diagnose',dict(caller_thread_id=THREAD),native_context=context)
        self.assertFalse(failed,value)
        self.assertEqual(value['accounting'],cli['accounting'])
        self.assertEqual(value['readiness']['status'],'accounting_unavailable')
        denied,failed=runner.call('wake_goal_limits_diagnose',dict(caller_thread_id=THREAD),native_context=None)
        self.assertTrue(failed)
        self.assertFalse(denied['effect_attempted'])

GoalEngagementTests.test_native_diagnose_and_cli_report_same_accounting_blocker = test_native_diagnose_and_cli_report_same_accounting_blocker


def test_hard_stop_retains_notice_even_when_native_visibility_is_unsupported(self):
    from codex_wake.goal_supervision import poll
    from codex_wake.goal_notice_commands import execute
    with tempfile.TemporaryDirectory() as directory:
        root,policy,_,native,_=self.fixture(directory)
        with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
            enroll(root,policy,THREAD,40,120)
            stopped=poll(root)[0]
            self.assertEqual(stopped['state'],'stopped')
            notices=execute(root,policy,THREAD)['notices']
            self.assertEqual({event['identity']['kind'] for event in notices}, {'activation', 'stop'})
            notices=[event for event in notices if event['identity']['kind']=='stop']
            self.assertEqual(notices[0]['identity']['kind'],'stop')
            self.assertIn('Used 40 of 40',notices[0]['text'])
            self.assertEqual(notices[0]['proof']['ui']['state'],'unverified')
            self.assertEqual(native['goal']['status'],'paused')
            self.assertEqual(native['active'],[])
            self.assertFalse(any(method=='turn/start' for method,_ in native['calls']))

GoalEngagementTests.test_hard_stop_retains_notice_even_when_native_visibility_is_unsupported = test_hard_stop_retains_notice_even_when_native_visibility_is_unsupported
