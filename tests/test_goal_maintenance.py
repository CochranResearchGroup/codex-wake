"""Exercise the host CLI and real controller lifecycle against private fixtures."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import test_goal_supervision as fixtures
THREAD, NOW = fixtures.THREAD, fixtures.NOW
from codex_wake.goal_supervision import enroll, poll, show


class GoalMaintenanceTests(unittest.TestCase):
    fixture = fixtures.GoalSupervisionTests.fixture
    # Fixture watcher sleeps up to5s; native finalizer observations/effects each
    # have their own1s RPC budget. Allow the complete bounded shutdown, not7s.
    controller = fixtures.GoalSupervisionTests.controller

    def policy(self, directory, root, seconds=20):
        path=Path(directory)/'maintenance-policy.json'
        path.write_text(json.dumps(dict(version=1,enabled=True,controller_root=str(root),max_seconds=seconds)))
        path.chmod(0o600)
        return path

    def prepare(self, root, policy, seconds=15):
        return subprocess.run([sys.executable,'-m','codex_wake','--wake-root',str(root),
            'goal-limits','prepare-maintenance','--policy',str(policy),'--seconds',str(seconds),'--json'],
            capture_output=True,text=True,timeout=5)

    def test_authorized_graceful_replacement_preserves_allocation_and_latch(self):
        for latched in (False,True):
            with self.subTest(latched=latched),tempfile.TemporaryDirectory() as directory:
                root,policy,_,native,_=self.fixture(directory)
                native['goal']['status']='paused';native['active']=[]
                with self.controller(root) as process,patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                    before=enroll(root,policy,THREAD,100,120)
                    path=next(p for p in (root/'goal-supervision').glob('*.json') if p.name!='controller.json')
                    if latched:
                        value=json.loads(path.read_text());value.update(stop_latched=True,reason='original_failure',state='stopped')
                        path.write_text(json.dumps(value));before=value
                    result=self.prepare(root,self.policy(directory,root))
                    self.assertEqual(result.returncode,0,result.stderr+result.stdout)
                    with self.assertRaisesRegex(ValueError,'maintenance'):
                        enroll(root,policy,THREAD,100,120)
                    process.terminate();process.wait(timeout=12)
                    after=json.loads(path.read_text())
                    for key in ('generation','deadline','token_limit','time_limit_seconds','used_tokens','stop_latched','reason'):
                        self.assertEqual(after.get(key),before.get(key),key)
                    self.assertEqual(show(root,policy,THREAD)['controller']['fresh'],False)
                    with self.controller(root) as replacement:
                        until=time.monotonic()+3
                        while show(root,policy,THREAD)['controller'].get('pid')!=replacement.pid:
                            if time.monotonic()>until:self.fail('replacement heartbeat missing')
                            time.sleep(.01)
                        current=show(root,policy,THREAD)
                        self.assertTrue(current['controller']['fresh'])
                        self.assertEqual(current['deadline'],before['deadline'])
                        self.assertEqual(current.get('stop_latched',False),latched)
                    self.assertEqual(native['goal']['status'],'paused')

    def test_active_goal_or_unapproved_policy_cannot_prepare_handover(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,_,_=self.fixture(directory)
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,100,120)
                permission=self.policy(directory,root)
                result=self.prepare(root,permission)
                self.assertEqual(result.returncode,2)
                self.assertIn('inactive',result.stdout)
                permission.chmod(0o644)
                result=self.prepare(root,permission)
                self.assertEqual(result.returncode,2)
                self.assertIn('private',result.stdout)

    def test_expired_or_changed_handover_fails_closed(self):
        for defect in ('expired','changed'):
            with self.subTest(defect=defect),tempfile.TemporaryDirectory() as directory:
                root,policy,_,native,_=self.fixture(directory)
                native['goal']['status']='paused';native['active']=[]
                with self.controller(root) as process,patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                    enroll(root,policy,THREAD,100,120)
                    permission=self.policy(directory,root)
                    result=self.prepare(root,permission,seconds=1 if defect=='expired' else 15)
                    self.assertEqual(result.returncode,0,result.stderr+result.stdout)
                    if defect=='expired':time.sleep(1.1)
                    else:permission.write_text('{}')
                    process.terminate();process.wait(timeout=12)
                    value=show(root,policy,THREAD)
                    self.assertTrue(value['stop_latched'])
                    self.assertEqual(value['reason'],'controller_stopped')

    def test_first_stop_evidence_survives_recovery_and_later_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,request=self.fixture(directory)
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enrolled=enroll(root,policy,THREAD,100,120)
                def timeout(endpoint,executable,method,params,limit):
                    if method=='thread/read':raise TimeoutError('do not persist sensitive exception text')
                    return request(endpoint,executable,method,params,limit)
                with patch('codex_wake.goal_supervision.native_request',side_effect=timeout):
                    first=poll(root)[0]
                evidence=first['first_stop']
                self.assertEqual(evidence['reason'],'observation_unavailable')
                self.assertEqual(evidence['native_method'],'thread/read')
                self.assertEqual(evidence['cause'],'TimeoutError')
                self.assertEqual(evidence['used_tokens'],40)
                self.assertEqual(evidence['deadline'],enrolled['deadline'])
                self.assertEqual(evidence['controller_generation'],enrolled['controller_generation'])
                self.assertGreaterEqual(evidence['observation_duration_seconds'],0)
                self.assertNotIn('sensitive',json.dumps(evidence))
                poll(root)
                with patch('codex_wake.goal_supervision.native_request',side_effect=OSError('later')):
                    last=poll(root)[0]
                self.assertEqual(last['first_stop'],evidence)
                self.assertEqual(last['observation_error'],'OSError')

    def test_abandoned_preparation_expires_without_reset_or_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,_=self.fixture(directory)
            native['goal']['status']='paused';native['active']=[]
            with self.controller(root) as process,patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                before=enroll(root,policy,THREAD,100,120)
                result=self.prepare(root,self.policy(directory,root),seconds=1)
                self.assertEqual(result.returncode,0,result.stdout)
                time.sleep(1.1)
                current=enroll(root,policy,THREAD,100,120)
                self.assertEqual(current['state'],'armed')
                self.assertEqual(current['generation'],before['generation'])
                self.assertEqual(current['deadline'],before['deadline'])
                self.assertEqual(current['used_tokens'],before['used_tokens'])
                self.assertIsNone(process.poll())
                self.assertEqual(json.loads((root/'goal-supervision/maintenance/permit.json').read_text())['state'],'preparation_expired')

    def test_changed_boot_never_fabricates_a_qualified_first_stop_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,_,_=self.fixture(directory)
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,100,120)
                with patch('codex_wake.goal_supervision.boot_id_value',return_value='a-different-boot'):
                    stopped=poll(root)[0]
                self.assertEqual(stopped['first_stop']['reason'],'boot_identity_changed')
                self.assertIsNone(stopped['first_stop']['observed_upper'])
                self.assertFalse(stopped['first_stop']['clock_qualified'])

    def test_delegated_ledger_authority_is_preserved_and_drift_refuses_exit(self):
        for changed in (False,True):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as directory:
                root,policy,_,native,_=self.fixture(directory)
                grant=json.loads(policy.read_text())['callers'][THREAD]
                policy.write_text(json.dumps(dict(version=2,native_caller_binding=True,
                    default_allocation='allocation-1',allocations={'allocation-1':grant})))
                native['goal']['status']='paused';native['active']=[]
                context=dict(threadId=THREAD,sessionId=THREAD,callId='maintenance-test',
                    **{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='operator')})
                with self.controller(root) as process,patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                    before=enroll(root,policy,THREAD,100,120,native_context=context)
                    allocation_path=next((root/'goal-supervision/allocations').glob('*.json'))
                    original=json.loads(allocation_path.read_text())
                    result=self.prepare(root,self.policy(directory,root))
                    self.assertEqual(result.returncode,0,result.stdout)
                    if changed:
                        value=dict(original,deadline=original['deadline']-1)
                        allocation_path.write_text(json.dumps(value))
                    process.terminate();process.wait(timeout=12)
                    after=show(root,policy,THREAD)
                    ledger=json.loads(allocation_path.read_text())
                    if changed:
                        self.assertTrue(after['stop_latched'])
                        self.assertEqual(after['reason'],'controller_stopped')
                        self.assertEqual(ledger['deadline'],original['deadline']-1)
                    else:
                        self.assertEqual(ledger,original)
                        self.assertEqual(after['generation'],before['generation'])
                        self.assertFalse(after.get('stop_latched',False))

    def test_enrollment_stop_retains_original_diagnostic_before_reenrollment(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,_=self.fixture(directory)
            native['goal']['status']='futureUnknownState';native['active']=[]
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                first=enroll(root,policy,THREAD,100,120)
                self.assertEqual(first['first_stop']['reason'],'native_goal_state_unknown')
                self.assertEqual(first['first_stop']['provenance'],'stop_decision')
                self.assertTrue(first['stop_latched'])
                native['goal']['status']='paused'
                later=enroll(root,policy,THREAD,100,120)
                self.assertEqual(later['first_stop'],first['first_stop'])
                self.assertTrue(later['stop_latched'])

    def test_crash_after_first_fault_persistence_cannot_rearm_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,_,request=self.fixture(directory)
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,100,120)
                calls=0
                def fault_then_crash(endpoint,executable,method,params,limit):
                    nonlocal calls
                    if method=='thread/read':
                        calls+=1
                        if calls==1:raise TimeoutError('first observation failed')
                        raise KeyboardInterrupt('controller exits after persisting stop diagnostic')
                    return request(endpoint,executable,method,params,limit)
                with patch('codex_wake.goal_supervision.native_request',side_effect=fault_then_crash):
                    with self.assertRaises(KeyboardInterrupt):poll(root)
                retained=show(root,policy,THREAD)
                self.assertTrue(retained['stop_latched'])
                self.assertEqual(retained['state'],'stop_unverified')
                self.assertEqual(retained['first_stop']['reason'],'observation_unavailable')
                recovered=poll(root)[0]
                self.assertEqual(recovered['state'],'stopped')
                self.assertEqual(recovered['first_stop'],retained['first_stop'])

    def test_first_fault_crash_cannot_leave_the_shared_allocation_unlatched(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,_,request=self.fixture(directory)
            grant=json.loads(policy.read_text())['callers'][THREAD]
            policy.write_text(json.dumps(dict(version=2,native_caller_binding=True,
                default_allocation='allocation-1',allocations={'allocation-1':grant})))
            context=dict(threadId=THREAD,sessionId=THREAD,callId='crash-test',
                **{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='work')})
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,100,120,native_context=context)
                real_replace=os.replace
                def crash_after_receipt_replace(source,destination):
                    real_replace(source,destination)
                    if Path(destination).parent==root/'goal-supervision' and Path(destination).name!='controller.json':
                        raise KeyboardInterrupt('process exits after receipt replace')
                def timeout(endpoint,executable,method,params,limit):
                    if method=='thread/read':raise TimeoutError('observation failed')
                    return request(endpoint,executable,method,params,limit)
                with patch('codex_wake.goal_supervision.native_request',side_effect=timeout),patch('os.replace',side_effect=crash_after_receipt_replace):
                    with self.assertRaises(KeyboardInterrupt):poll(root)
                ledger=json.loads(next((root/'goal-supervision/allocations').glob('*.json')).read_text())
                self.assertTrue(ledger['stop_latched'])
                self.assertEqual(ledger['first_stop']['reason'],'observation_unavailable')

    def test_persisting_native_fault_recovers_original_ledger_diagnostic_after_crash(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,_,_=self.fixture(directory)
            grant=json.loads(policy.read_text())['callers'][THREAD]
            policy.write_text(json.dumps(dict(version=2,native_caller_binding=True,
                default_allocation='allocation-1',allocations={'allocation-1':grant})))
            context=dict(threadId=THREAD,sessionId=THREAD,callId='recovery-test',
                **{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='work')})
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,100,120,native_context=context)
                real_replace=os.replace
                def crash_before_receipt_replace(source,destination):
                    if Path(destination).parent==root/'goal-supervision' and Path(destination).name!='controller.json':
                        raise KeyboardInterrupt('process exits before receipt replace')
                    real_replace(source,destination)
                with patch('codex_wake.goal_supervision.native_request',side_effect=TimeoutError('original')),patch('os.replace',side_effect=crash_before_receipt_replace):
                    with self.assertRaises(KeyboardInterrupt):poll(root)
                ledger=json.loads(next((root/'goal-supervision/allocations').glob('*.json')).read_text())
                with patch('codex_wake.goal_supervision.native_request',side_effect=OSError('persistent fault')):
                    recovered=poll(root)[0]
                self.assertEqual(recovered['first_stop'],ledger['first_stop'])
                self.assertEqual(recovered['first_stop']['cause'],'TimeoutError')
