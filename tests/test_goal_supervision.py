"""Public controller seams, real files/accounting and native RPC boundary only."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from codex_wake.goal_supervision import enroll,show,poll

THREAD='00000000-0000-7000-8000-000000000279'
NOW=1893456000


class GoalSupervisionTests(unittest.TestCase):
    def fixture(self,directory):
        root=Path(directory)/'wake';root.mkdir(mode=0o700)
        home=Path(directory)/'home';home.mkdir(mode=0o700);(home/'sessions').mkdir(mode=0o700)
        policy=Path(directory)/'policy.json'
        policy.write_text(json.dumps(dict(version=1,callers={THREAD:dict(app_server='unix://'+directory+'/unused.sock',
            codex_path=sys.executable,codex_home=str(home),allocation_id='allocation-1',max_tokens=1000,max_seconds=300,rpc_timeout=1)})))
        policy.chmod(0o600)
        rows=[dict(type='session_meta',payload=dict(id=THREAD,session_id=THREAD,source='cli')),
            dict(type='event_msg',payload=dict(type='thread_goal_updated',threadId=THREAD,
                goal=dict(threadId=THREAD,createdAt=NOW,status='active'))),
            dict(type='event_msg',payload=dict(type='task_started',turn_id='work')),
            dict(type='token_usage_record',payload=dict(thread_id=THREAD,turn_id='work',session_id=THREAD,root_turn_id='work',
                response_id='response-1',usage=dict(input_tokens=38,cached_input_tokens=37,output_tokens=2,total_tokens=40),
                turn_token_usage={},thread_token_usage={}))]
        log=home/'sessions/owned.jsonl'
        log.write_text(''.join(json.dumps(dict(timestamp='2030-01-01T00:00:00Z',**row))+'\n' for row in rows))
        native=dict(goal=dict(threadId=THREAD,createdAt=NOW,status='active'),active=['work'],calls=[])
        def request(endpoint,executable,method,params,timeout):
            self.assertEqual(params['threadId'],THREAD)
            native['calls'].append((method,params))
            if method=='thread/goal/get':return {'goal':dict(native['goal'])}
            if method=='thread/read':return {'thread':dict(id=THREAD,turns=[dict(id=t,status='inProgress') for t in native['active']])}
            receipts=list((root/'goal-supervision').glob('*.json'))
            saved=[json.loads(p.read_text()) for p in receipts if p.name!='controller.json'][0]
            self.assertTrue(any(effect['state']=='intended' and effect['method']==method for effect in saved['effects'].values()))
            if native.get('lose')==method:raise TimeoutError('lost response')
            if method=='thread/goal/set':native['goal']['status']='paused'
            if method=='turn/interrupt':native['active'].remove(params['turnId'])
            if method=='turn/steer':self.assertEqual(params['expectedTurnId'],'work')
            return {}
        return root,policy,log,native,request

    @contextmanager
    def controller(self,root):
        process=subprocess.Popen([sys.executable,'-c',
            'from codex_wake.goal_supervision import watch; import sys; watch(sys.argv[1],interval=5)',str(root)],
            stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            until=time.monotonic()+3
            while not (root/'goal-supervision/controller.json').exists():
                if process.poll() is not None:self.fail(process.stderr.read().decode())
                if time.monotonic()>until:self.fail('watch heartbeat missing')
                time.sleep(.01)
            yield process
        finally:
            process.kill();process.wait(timeout=3);process.stderr.close()

    def test_same_allocation_preserves_original_limits_across_replacement_native_goal(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,request=self.fixture(directory)
            with patch('codex_wake.goal_supervision.native_request',side_effect=request),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                first=enroll(root,policy,THREAD,100,120)
                self.assertEqual(first['state'],'held')
                self.assertEqual(first['used_tokens'],40)
                native['goal']['createdAt']=NOW+20
                second=enroll(root,policy,THREAD,90,100)
                self.assertEqual(second['goal_created_at'],NOW)
                self.assertEqual(second['deadline'],NOW+100)
                self.assertEqual(first['started_boottime'],second['started_boottime'])
                self.assertEqual(first['generation'],second['generation'])
                with self.assertRaisesRegex(ValueError,'only tighten'):enroll(root,policy,THREAD,100,120)
                self.assertNotIn('grant',second)

    def test_checkpoint_then_original_token_limit_pause_and_interrupt_exact_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,request=self.fixture(directory)
            with self.controller(root),patch('codex_wake.goal_supervision.native_request',side_effect=request),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                result=enroll(root,policy,THREAD,100,120,checkpoint_token_percent=60,checkpoint_seconds=0)
                self.assertEqual(result['state'],'armed')
                result=poll(root)[0]
                self.assertEqual(result['state'],'checkpoint_requested')
                self.assertEqual(result['checkpoint']['state'],'acknowledged')
                enroll(root,policy,THREAD,40,120)
                result=poll(root)[0]
                self.assertEqual(result['state'],'stopped')
                self.assertEqual(native['goal']['status'],'paused')
                self.assertEqual(native['active'],[])
                self.assertEqual([m for m,p in native['calls'] if m=='turn/steer'],['turn/steer'])

    def test_lost_checkpoint_response_is_not_replayed_and_does_not_delay_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,request=self.fixture(directory);native['lose']='turn/steer'
            with self.controller(root),patch('codex_wake.goal_supervision.native_request',side_effect=request),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,100,120,checkpoint_token_percent=60,checkpoint_seconds=0)
                self.assertEqual(poll(root)[0]['checkpoint']['state'],'uncertain')
                poll(root)
                self.assertEqual([m for m,p in native['calls']].count('turn/steer'),1)
                enroll(root,policy,THREAD,40,120)
                self.assertEqual(poll(root)[0]['state'],'stopped')

    def test_explicit_host_allocation_reset_is_only_way_to_reset_spend(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,_,request=self.fixture(directory)
            with patch('codex_wake.goal_supervision.native_request',side_effect=request),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                first=enroll(root,policy,THREAD,100,120)
                value=json.loads(policy.read_text());value['callers'][THREAD]['allocation_id']='operator-reset-2'
                policy.write_text(json.dumps(value))
                self.assertEqual(show(root,policy,THREAD)['state'],'held')
                reset=enroll(root,policy,THREAD,200,200)
                self.assertEqual(reset['used_tokens'],0)
                self.assertNotEqual(first['generation'],reset['generation'])
                self.assertEqual(reset['goal_created_at'],NOW)

    def test_unknown_stop_response_and_same_generation_enrollment_cannot_replay_or_rearm(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,request=self.fixture(directory);native['lose']='thread/goal/set'
            with self.controller(root),patch('codex_wake.goal_supervision.native_request',side_effect=request),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,40,120)
                self.assertEqual(poll(root)[0]['state'],'stop_unverified')
                enrollment=enroll(root,policy,THREAD,40,120)
                self.assertEqual(enrollment['state'],'held')
                self.assertEqual(poll(root)[0]['state'],'stop_unverified')
                self.assertEqual([m for m,p in native['calls']].count('thread/goal/set'),1)
                self.assertEqual([m for m,p in native['calls']].count('turn/interrupt'),1)

    def test_default_checkpoint_and_original_elapsed_deadline_survive_controller_reconstruction(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,request=self.fixture(directory)
            with self.controller(root),patch('codex_wake.goal_supervision.native_request',side_effect=request),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                receipt=enroll(root,policy,THREAD,42,120)
                self.assertEqual(poll(root)[0]['state'],'checkpoint_requested')
                with patch('codex_wake.goal_supervision.time.clock_gettime',return_value=receipt['started_boottime']+121):
                    self.assertEqual(poll(root)[0]['state'],'stopped')
                self.assertEqual(native['active'],[])

    def test_revoked_host_grant_stops_only_persisted_exact_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,request=self.fixture(directory)
            with self.controller(root),patch('codex_wake.goal_supervision.native_request',side_effect=request),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,100,120)
                value=json.loads(policy.read_text());value['callers']={};policy.write_text(json.dumps(value))
                result=poll(root)[0]
                self.assertEqual(result['state'],'stopped')
                self.assertEqual(native['goal']['status'],'paused')
                self.assertEqual(native['active'],[])

    def test_stale_or_dead_independent_controller_is_never_displayed_as_armed(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,_,request=self.fixture(directory)
            with patch('codex_wake.goal_supervision.native_request',side_effect=request),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                with self.controller(root):
                    self.assertEqual(enroll(root,policy,THREAD,100,120)['state'],'armed')
                status=show(root,policy,THREAD)
                self.assertEqual(status['state'],'held')
                self.assertFalse(status['controller']['fresh'])

    def test_malformed_host_policy_is_refused_as_value_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,_,_=self.fixture(directory)
            for text in ('{"version":true,"callers":{}}','{"version":1,"version":1,"callers":{}}',
                         '{"version":1,"callers":{}}'):
                policy.write_text(text)
                with self.assertRaises(ValueError):enroll(root,policy,THREAD,100,120)
