"""Public controller seams, real files/accounting and native RPC boundary only."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import threading
import unittest
from unittest.mock import patch
from websockets.sync.server import unix_serve

from codex_wake.goal_supervision import enroll,show,poll

THREAD='00000000-0000-7000-8000-000000000279'
NOW=1893456000


class GoalSupervisionTests(unittest.TestCase):
    def test_first_enrollment_imports_host_renewal_boundary_without_replenishing_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,log,native,_=self.fixture(directory)
            from codex_wake.goal_usage import observe_usage
            original=observe_usage(log.parent.parent,THREAD,NOW)
            self.assertEqual(original['used_tokens'],40)
            grant=json.loads(policy.read_text())['callers'][THREAD]
            grant['initial_boundary']=dict(started_at=NOW+10,token_accounting='fresh',reset_anchor=original['anchor'])
            config=dict(version=2,native_caller_binding=True,default_allocation='renewal',allocations={'renewal':grant})
            policy.write_text(json.dumps(config))
            row=json.loads(log.read_text().splitlines()[-1]);row['payload']['response_id']='after-renewal'
            row['payload']['usage']=dict(input_tokens=28,cached_input_tokens=0,output_tokens=2,total_tokens=30)
            with log.open('a') as stream:stream.write(json.dumps(row)+'\n')
            context=dict(threadId=THREAD,sessionId=THREAD,callId='native-import',
                **{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='work')})
            successor='00000000-0000-7000-8000-000000000294'
            rows=[json.loads(line) for line in log.read_text().splitlines()[:4]]
            rows=json.loads(json.dumps(rows).replace(THREAD,successor))
            rows[1]['payload']['goal']['createdAt']=NOW+15
            for event in rows[1:]:event['timestamp']='2030-01-01T00:00:15Z'
            rows[3]['payload']['usage']=dict(input_tokens=4,cached_input_tokens=0,output_tokens=1,total_tokens=5)
            (log.parent/'first-successor.jsonl').write_text(''.join(json.dumps(event)+'\n' for event in rows))
            native['siblings']={successor:dict(goal=dict(threadId=successor,createdAt=NOW+15,status='active'),active=['work'],calls=[])}
            successor_context=dict(threadId=successor,sessionId=successor,callId='native-successor-import',
                **{'x-codex-turn-metadata':dict(thread_id=successor,session_id=successor,turn_id='work')})
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW+20):
                first=enroll(root,policy,successor,100,120,native_context=successor_context)
                self.assertEqual(first['used_tokens'],35)
                self.assertEqual(first['deadline'],NOW+130)
                receipt=enroll(root,policy,THREAD,100,120,native_context=context)
                self.assertEqual(receipt['state'],'armed')
                self.assertEqual(receipt['used_tokens'],35)
                self.assertEqual(receipt['time_origin'],NOW+10)
                self.assertEqual(receipt['deadline'],NOW+130)
                again=enroll(root,policy,THREAD,100,120,native_context=context)
                self.assertEqual(again['used_tokens'],35)
                self.assertEqual(again['deadline'],NOW+130)

    def test_host_boundary_rejects_changed_history_and_future_time_before_admission(self):
        for defect in ('changed-history','future-time'):
            with self.subTest(defect=defect),tempfile.TemporaryDirectory() as directory:
                root,policy,log,_,_=self.fixture(directory)
                from codex_wake.goal_usage import observe_usage
                anchor=observe_usage(log.parent.parent,THREAD,NOW)['anchor']
                if defect=='changed-history':anchor['response_hashes']={key:'0'*64 for key in anchor['response_hashes']}
                grant=json.loads(policy.read_text())['callers'][THREAD]
                grant['initial_boundary']=dict(started_at=NOW+100 if defect=='future-time' else NOW,
                    token_accounting='fresh',reset_anchor=anchor)
                policy.write_text(json.dumps(dict(version=2,native_caller_binding=True,
                    default_allocation='import',allocations={'import':grant})))
                context=dict(threadId=THREAD,sessionId=THREAD,callId='native-import',
                    **{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='work')})
                with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW+20):
                    with self.assertRaisesRegex(ValueError,'boundary'):
                        enroll(root,policy,THREAD,100,120,native_context=context)
                self.assertFalse(list((root/'goal-supervision/allocations').glob('*.json')))

    def test_host_delegation_policy_preserves_existing_explicit_grants_and_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,_=self.fixture(directory)
            legacy=json.loads(policy.read_text())
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                first=enroll(root,policy,THREAD,100,120)
                upgraded=dict(version=2,native_caller_binding=True,callers=legacy['callers'],
                    allocations={'other':dict(legacy['callers'][THREAD],allocation_id='other')})
                policy.write_text(json.dumps(upgraded))
                again=enroll(root,policy,THREAD,100,120)
                self.assertEqual(again['state'],'armed')
                self.assertEqual(again['allocation_id'],first['allocation_id'])
                self.assertEqual(again['deadline'],first['deadline'])
                self.assertEqual(again['used_tokens'],40)
                self.assertEqual(poll(root)[0]['state'],'armed')
                self.assertEqual(native['goal']['status'],'active')
                with self.assertRaisesRegex(ValueError,'selected allocation'):
                    enroll(root,policy,THREAD,100,120,allocation_id='other')

    def test_host_delegated_caller_enrolls_without_uuid_grant(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,_=self.fixture(directory)
            old=json.loads(policy.read_text())['callers'][THREAD]
            policy.write_text(json.dumps(dict(version=2, default_allocation='allocation-1',
                allocations={'allocation-1':old}, native_caller_binding=True)))
            context=dict(threadId=THREAD, sessionId=THREAD, callId='native-call',
                **{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='work')})
            with self.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                with self.assertRaisesRegex(ValueError,'native caller'):
                    enroll(root,policy,THREAD,100,120)
                from codex_wake.mcp_server import CommandRunner
                runner=CommandRunner(goal_limits_policy=policy,goal_limits_root=root)
                arguments=dict(caller_thread_id=THREAD,token_limit=100,time_limit_seconds=120)
                denied,failed=runner.call('wake_goal_limits_set',arguments)
                self.assertTrue(failed)
                self.assertEqual(denied['state'],'held')
                forged=dict(context,threadId='00000000-0000-7000-8000-000000000290')
                self.assertTrue(runner.call('wake_goal_limits_set',arguments,native_context=forged)[1])
                receipt,failed=runner.call('wake_goal_limits_set',arguments,native_context=context)
                self.assertFalse(failed,receipt)
                self.assertEqual(receipt['state'],'armed')
                self.assertEqual(receipt['allocation_id'],'allocation-1')
                self.assertEqual(receipt['used_tokens'],40)
                self.assertEqual(receipt['deadline'],NOW+120)
                self.assertEqual(json.loads(policy.read_text())['allocations']['allocation-1'],old)
                self.assertNotIn('callers',json.loads(policy.read_text()))

    def test_successor_shares_spend_deadline_and_cannot_mint_another_allowance(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,log,native,_=self.fixture(directory)
            grant=json.loads(policy.read_text())['callers'][THREAD]
            policy.write_text(json.dumps(dict(version=2, default_allocation='allocation-1',
                allocations={'allocation-1':grant},native_caller_binding=True)))
            def context(thread):
                return dict(threadId=thread,sessionId=thread,callId='call-'+thread,
                    **{'x-codex-turn-metadata':dict(thread_id=thread,session_id=thread,turn_id='work')})
            successor='00000000-0000-7000-8000-000000000290'
            rows=[json.loads(line) for line in log.read_text().splitlines()]
            rows=json.loads(json.dumps(rows).replace(THREAD,successor))
            rows[1]['payload']['goal']['createdAt']=NOW+10
            rows[1]['timestamp']='2030-01-01T00:00:10Z'
            rows[2]['timestamp']='2030-01-01T00:00:10Z'
            rows[3]['timestamp']='2030-01-01T00:00:10Z'
            (log.parent/'successor.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
            native['siblings']={successor:dict(goal=dict(threadId=successor,createdAt=NOW+10,status='active'),active=['work'],calls=[])}
            with self.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW+10):
                first=enroll(root,policy,THREAD,100,120,native_context=context(THREAD))
                second=enroll(root,policy,successor,100,120,native_context=context(successor))
                self.assertEqual(second['used_tokens'],80)
                self.assertEqual(second['deadline'],NOW+120)
                self.assertEqual(second['time_origin'],NOW)
                repeated=enroll(root,policy,successor,100,120,native_context=context(successor))
                self.assertEqual(repeated['used_tokens'],80)
                self.assertEqual(repeated['deadline'],first['deadline'])
                with self.assertRaisesRegex(ValueError,'allocation'):
                    enroll(root,policy,successor,101,120,native_context=context(successor))
                control='00000000-0000-7000-8000-000000000292'
                control_policy=json.loads(policy.read_text())
                control_policy['allocations']['other-objective']=grant
                policy.write_text(json.dumps(control_policy))
                (log.parent/'control.jsonl').write_text(''.join(json.dumps(row).replace(successor,control)+'\n' for row in rows))
                native['siblings'][control]=dict(goal=dict(threadId=control,createdAt=NOW+10,status='active'),active=['work'],calls=[])
                unrelated=enroll(root,policy,control,100,120,native_context=context(control),allocation_id='other-objective')
                self.assertEqual(unrelated['used_tokens'],40)
                self.assertEqual(unrelated['deadline'],NOW+130)
                original=log.read_text()
                log.write_text(original+'{"type":')
                winding=poll(root)
                grace=min(value['winddown_deadline'] for value in winding if 'winddown_deadline' in value)
                self.assertEqual(next(value for value in winding if value['thread_id']==control)['state'],'armed')
                self.assertEqual(native['siblings'][control]['goal']['status'],'active')
                log.write_text(original)
                third='00000000-0000-7000-8000-000000000291'
                rows[3]['payload']['usage']=dict(input_tokens=0,cached_input_tokens=0,output_tokens=0,total_tokens=0)
                (log.parent/'third.jsonl').write_text(''.join(json.dumps(row).replace(successor,third)+'\n' for row in rows))
                native['siblings'][third]=dict(goal=dict(threadId=third,createdAt=NOW+10,status='active'),active=['work'],calls=[])
                held=enroll(root,policy,third,100,120,native_context=context(third))
                self.assertEqual(held['state'],'held')
                self.assertTrue(held['stop_latched'])
                self.assertEqual(held['allocation_winddown_deadline'],grace)


    def test_only_explicit_host_renewal_changes_allowance_and_preserves_prior_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,log,native,_=self.fixture(directory)
            grant=json.loads(policy.read_text())['callers'][THREAD]
            config=dict(version=2,default_allocation='allocation-1',native_caller_binding=True,
                allocations={'allocation-1':grant,'renewed':grant})
            policy.write_text(json.dumps(config))
            context=dict(threadId=THREAD,sessionId=THREAD,callId='native-call',
                **{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='work')})
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                first=enroll(root,policy,THREAD,100,120,native_context=context)
                other='00000000-0000-7000-8000-000000000293'
                (log.parent/'old-member.jsonl').write_text(log.read_text().replace(THREAD,other))
                native['siblings']={other:dict(goal=dict(threadId=other,createdAt=NOW,status='active'),active=['work'],calls=[])}
                other_context=dict(context,threadId=other,sessionId=other,
                    **{'x-codex-turn-metadata':dict(thread_id=other,session_id=other,turn_id='work')})
                enroll(root,policy,other,100,120,native_context=other_context)
                with self.assertRaisesRegex(ValueError,'explicit host renewal'):
                    enroll(root,policy,THREAD,200,120,native_context=context,allocation_id='renewed')
                config['allocations']['renewed']=dict(grant,renews_allocation='allocation-1')
                policy.write_text(json.dumps(config))
                with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW+10):
                    renewed=enroll(root,policy,THREAD,200,120,native_context=context,allocation_id='renewed')
                self.assertEqual(renewed['used_tokens'],0)
                self.assertEqual(renewed['time_origin'],NOW+10)
                self.assertEqual(renewed['deadline'],NOW+130)
                self.assertNotEqual(renewed['generation'],first['generation'])
                self.assertEqual(json.loads(Path(first['allocation_path']).read_text())['used_tokens'],80)
                row=json.loads(log.read_text().splitlines()[-1])
                row['payload']['response_id']='renewed-response'
                row['payload']['usage']=dict(input_tokens=28,cached_input_tokens=0,output_tokens=2,total_tokens=30)
                with log.open('a') as stream:stream.write(json.dumps(row)+'\n')
                results={value['thread_id']:value for value in poll(root)}
                self.assertEqual(results[THREAD]['used_tokens'],30)
                self.assertEqual(results[other]['used_tokens'],80)
                self.assertEqual(results[other]['state'],'armed')
                # Restart at the durable boundary after target admission but
                # before old-member finalization, with later usage now present.
                previous_path=Path(first['allocation_path'])
                previous=json.loads(previous_path.read_text())
                member=previous['members'][THREAD]
                for key in ('finalized_charges','final_anchor','renewed_into'):member.pop(key)
                previous_path.write_text(json.dumps(previous))
                receipt_path=next(path for path in (root/'goal-supervision').glob('*.json')
                    if path.name!='controller.json' and json.loads(path.read_text())['thread_id']==THREAD)
                pending=json.loads(receipt_path.read_text())['prior_allocation']
                receipt_path.write_text(json.dumps(pending))
                with self.assertRaisesRegex(ValueError,'renewal boundary'):
                    enroll(root,policy,THREAD,200,120,native_context=context,allocation_id='renewed')


    def test_resume_after_partially_verified_stop_gets_a_new_pause(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,request=self.fixture(directory)
            with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,40,120)
                native['lose']='turn/interrupt'
                first=poll(root)[0]
                self.assertEqual(first['state'],'stop_unverified')
                self.assertEqual(native['goal']['status'],'paused')
                native['active']=[]
                native['goal']['status']='active'
                native.pop('lose')
                second=poll(root)[0]
                self.assertEqual(second['state'],'stopped')
                self.assertEqual(native['goal']['status'],'paused')
                self.assertEqual(sum(method=='thread/goal/set' for method,_ in native['calls']),2)
                self.assertTrue(any(effect['state']=='uncertain' for effect in second['effects'].values()))

    def test_paused_campaign_allows_operator_reply_on_later_polls(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,_=self.fixture(directory)
            with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,40,120)
                self.assertEqual(poll(root)[0]['state'],'stopped')
                native['active']=['operator-reply']
                poll(root)
                poll(root)
                self.assertEqual(native['goal']['status'],'paused')
                self.assertEqual(native['active'],['operator-reply'])
                self.assertNotIn(('turn/interrupt',dict(threadId=THREAD,turnId='operator-reply')),native['calls'])

    def test_unknown_accounting_pauses_campaign_but_allows_bounded_checkpoint_grace(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,log,native,_=self.fixture(directory)
            with log.open('a') as stream:stream.write('{"type":')
            with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                receipt=enroll(root,policy,THREAD,100,120,checkpoint_seconds=30)
                first=poll(root)[0]
                self.assertEqual(first['state'],'winding_down')
                self.assertEqual(native['goal']['status'],'paused')
                self.assertEqual(native['active'],['work'])
                self.assertEqual(first['checkpoint']['state'],'acknowledged')
                limit=first['winddown_deadline']
                again=poll(root)[0]
                self.assertEqual(again['winddown_deadline'],limit)
                self.assertEqual(sum(m=='turn/steer' for m,_ in native['calls']),1)
                with patch('codex_wake.goal_supervision.time.clock_gettime',return_value=receipt['started_boottime']+31):
                    final=poll(root)[0]
                self.assertEqual(final['state'],'stopped',final)
                native['active']=['operator-reply']
                poll(root)
                self.assertEqual(native['active'],['operator-reply'])

    def test_winddown_grace_never_extends_original_deadline_or_restarts_on_enrollment(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,log,native,_=self.fixture(directory)
            with log.open('a') as stream:stream.write('{"type":')
            with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                receipt=enroll(root,policy,THREAD,100,20,checkpoint_seconds=60)
                first=poll(root)[0]
                self.assertEqual(first['winddown_deadline'],NOW+20)
                repeated=enroll(root,policy,THREAD,100,20,checkpoint_seconds=60)
                self.assertEqual(repeated['winddown_deadline'],first['winddown_deadline'])
                with patch('codex_wake.goal_supervision.time.clock_gettime',return_value=receipt['started_boottime']+21):
                    self.assertEqual(poll(root)[0]['state'],'stopped')
                self.assertEqual(native['active'],[])

    def test_explicit_resume_during_winddown_is_paused_again_without_renewing_grace(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,log,native,_=self.fixture(directory)
            with log.open('a') as stream:stream.write('{"type":')
            with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,100,120,checkpoint_seconds=30)
                first=poll(root)[0]
                native['goal']['status']='active'
                second=poll(root)[0]
                self.assertEqual(second['winddown_deadline'],first['winddown_deadline'])
                self.assertEqual(native['goal']['status'],'paused')
                self.assertEqual(sum(m=='thread/goal/set' for m,_ in native['calls']),2)

    def test_new_enrollment_uses_fresh_tokens_and_preserves_basis_on_reenrollment(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,_=self.fixture(directory,cached=37)
            with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                first=enroll(root,policy,THREAD,100,120)
                self.assertEqual(first['used_tokens'],3)
                self.assertEqual(first['token_accounting'],'fresh')
                second=enroll(root,policy,THREAD,100,120)
                self.assertEqual(second['used_tokens'],3)
                inclusive=enroll(root,policy,THREAD,100,120,token_accounting='cache_inclusive')
                self.assertEqual(inclusive['used_tokens'],40)
                self.assertEqual(inclusive['deadline'],first['deadline'])
                self.assertEqual(inclusive['generation'],first['generation'])
                again=enroll(root,policy,THREAD,100,120)
                self.assertEqual(again['token_accounting'],'cache_inclusive')
                self.assertEqual(again['used_tokens'],40)

    def fixture(self,directory,cached=0):
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
                response_id='response-1',usage=dict(input_tokens=38,cached_input_tokens=cached,output_tokens=2,total_tokens=40),
                turn_token_usage={},thread_token_usage={}))]
        log=home/'sessions/owned.jsonl'
        log.write_text(''.join(json.dumps(dict(timestamp='2030-01-01T00:00:00Z',**row))+'\n' for row in rows))
        native=dict(goal=dict(threadId=THREAD,createdAt=NOW,status='active'),active=['work'],calls=[])
        def request(endpoint,executable,method,params,timeout):
            selected=native if params['threadId']==THREAD else native['siblings'][params['threadId']]
            selected['calls'].append((method,params))
            if method=='thread/goal/get':return {'goal':dict(selected['goal'])}
            if method=='thread/read':return {'thread':dict(id=params['threadId'],turns=[dict(id=t,status='inProgress') for t in selected['active']])}
            receipts=list((root/'goal-supervision').glob('*.json'))
            saved=next(value for p in receipts if p.name!='controller.json'
                for value in [json.loads(p.read_text())] if value['thread_id']==params['threadId'])
            self.assertTrue(any(effect['state']=='intended' and effect['method']==method for effect in saved['effects'].values()))
            if selected.get('lose')==method:raise TimeoutError('lost response')
            if method=='thread/goal/set':selected['goal']['status']='paused'
            if method=='turn/interrupt':selected['active'].remove(params['turnId'])
            if method=='turn/steer':self.assertEqual(params['expectedTurnId'],'work')
            return {}
        def handler(ws):
            for raw in ws:
                message=json.loads(raw)
                if 'id' not in message:continue
                if message['method']=='initialize':result={}
                else:
                    try:result=request(None,None,message['method'],message['params'],None)
                    except TimeoutError:
                        ws.close();return
                ws.send(json.dumps(dict(id=message['id'],result=result)))
        server=unix_serve(handler,str(Path(directory)/'unused.sock'))
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        def close_server():
            server.shutdown();worker.join(timeout=2)
        self.addCleanup(close_server)
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
            with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
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
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
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
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,100,120,checkpoint_token_percent=60,checkpoint_seconds=0)
                self.assertEqual(poll(root)[0]['checkpoint']['state'],'uncertain')
                poll(root)
                self.assertEqual([m for m,p in native['calls']].count('turn/steer'),1)
                enroll(root,policy,THREAD,40,120)
                self.assertEqual(poll(root)[0]['state'],'stopped')

    def test_explicit_host_allocation_reset_is_only_way_to_reset_spend(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,_,request=self.fixture(directory)
            with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
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
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
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
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                receipt=enroll(root,policy,THREAD,42,120)
                self.assertEqual(poll(root)[0]['state'],'checkpoint_requested')
                with patch('codex_wake.goal_supervision.time.clock_gettime',return_value=receipt['started_boottime']+121):
                    self.assertEqual(poll(root)[0]['state'],'stopped')
                self.assertEqual(native['active'],[])

    def test_revoked_host_grant_stops_only_persisted_exact_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,native,request=self.fixture(directory)
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                enroll(root,policy,THREAD,100,120)
                value=json.loads(policy.read_text());value['callers']={};policy.write_text(json.dumps(value))
                result=poll(root)[0]
                self.assertEqual(result['state'],'stopped')
                self.assertEqual(native['goal']['status'],'paused')
                self.assertEqual(native['active'],[])

    def test_stale_or_dead_independent_controller_is_never_displayed_as_armed(self):
        with tempfile.TemporaryDirectory() as directory:
            root,policy,_,_,request=self.fixture(directory)
            with patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
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
