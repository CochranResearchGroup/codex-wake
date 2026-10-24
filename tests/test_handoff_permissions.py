"""Policy guards on public handoff admission and independent effects (#321)."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codex_wake.session_permissions import PermissionDenied,PermissionStore,Principal


class HandoffPermissionsTests(unittest.TestCase):
    def test_configured_trigger_reuses_task_approval_without_copying_allowance(self):
        from codex_wake.permission_handoff import admission_context
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            store=PermissionStore(root)
            store.configure({'version':1,'global':{'actions':{'handoff.self':'approval_required'}},
                'approvals':[dict(id='task-approval',action='handoff.self',subject='source',
                    scope='task',task_id='task',expires_at='2030-01-01T00:00:00Z',issuer='op')]},
                Principal('op','operator'),expected_revision=0)
            profiles=root/'profiles.json'
            profiles.write_text(json.dumps({'version':1,'callers':{},'profiles':{'worker':{}}}));profiles.chmod(0o600)
            args=SimpleNamespace(profiles=profiles,profile='worker',thread_id='source',intent='handoff-1',trigger='context_limit',
                _permission_principal=Principal('source'))
            body={'task_brief':{'task_id':'task'}}
            with patch('codex_wake.permission_handoff.validated_task',return_value='task'):
                context=admission_context(root,args,{'handoff_triggers':['context_limit']},body)
            self.assertEqual(context['approval_id'],'task-approval')
            self.assertEqual(context['task_id'],'task')
            self.assertNotIn('token_cap',context)
            self.assertNotIn('time_cap_seconds',context)
            args.trigger='update'
            with patch('codex_wake.permission_handoff.validated_task',return_value='task'):
                with self.assertRaises(PermissionDenied):
                    admission_context(root,args,{'handoff_triggers':['context_limit']},body)

    def test_verified_successor_reuses_only_applicable_task_approval(self):
        from codex_wake.permission_handoff import verified_successor_principal,record_succession
        from codex_wake.task_briefs import BriefAuthority,TaskBriefStore
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);briefs=TaskBriefStore(root);operator=BriefAuthority('op','operator')
            content=dict(objective='Continue task',phase='implementation',non_goals=['No deploy'],
                acceptance=['Verified result'],context=[],workspace=tmp,allocation_ref='allocation',permission_ref='worker')
            briefs.propose('task',content,authority=operator);briefs.approve('task',1,authority=operator)
            briefs.admit('task','assignment',authority=operator);pin=briefs.assignment_pin('task','assignment')
            intent=dict(operation='handoff',source_thread_id='source',task_brief=pin)
            receipt=dict(thread_id='source',successor_thread_id='successor',intent=intent,
                fingerprint=hashlib.sha256(json.dumps(intent,sort_keys=True).encode()).hexdigest(),
                permission_context=dict(task_id='task',subject='source'))
            record_succession(root,receipt,'successor')
            journal=root/'lifecycle';journal.mkdir(mode=0o700)
            path=journal/'receipt.json';path.write_text(json.dumps(receipt));path.chmod(0o600)
            store=PermissionStore(root)
            policy={'version':1,'global':{'actions':{'handoff.self':'approval_required'}},'approvals':[
                dict(id='task-approval',action='handoff.self',subject='source',scope='task',
                    task_id='task',expires_at='2030-01-01T00:00:00Z',issuer='op')]}
            store.configure(policy,Principal('op','operator'),expected_revision=0)
            principal=verified_successor_principal(root,'successor','task')
            result=store.evaluate('handoff.self',principal,task_id='task')
            self.assertEqual(result['approval_id'],'task-approval')
            next_intent=dict(operation='handoff',source_thread_id='successor',task_brief=pin)
            next_receipt=dict(thread_id='successor',successor_thread_id='third',intent=next_intent,
                fingerprint=hashlib.sha256(json.dumps(next_intent,sort_keys=True).encode()).hexdigest(),
                permission_context=dict(task_id='task',subject='successor',predecessor='source',ancestors=[]))
            record_succession(root,next_receipt,'third')
            next_path=journal/'next.json';next_path.write_text(json.dumps(next_receipt));next_path.chmod(0o600)
            third=verified_successor_principal(root,'third','task')
            self.assertEqual(third.predecessor,'successor')
            self.assertEqual(third.ancestors,('source',))
            self.assertEqual(store.evaluate('handoff.self',third,task_id='task')['approval_id'],'task-approval')
            first_bytes=path.read_bytes();path.unlink()
            with self.assertRaises(PermissionDenied):verified_successor_principal(root,'third','task')
            path.write_bytes(first_bytes);path.chmod(0o600)
            cyclic=json.loads(first_bytes)
            cyclic['thread_id']='third';cyclic['intent']['source_thread_id']='third'
            cyclic['fingerprint']=hashlib.sha256(json.dumps(cyclic['intent'],sort_keys=True).encode()).hexdigest()
            cyclic['permission_context'].update(subject='third',predecessor='successor',ancestors=[])
            cyclic['permission_succession']['source']='third'
            path.write_text(json.dumps(cyclic))
            with self.assertRaises(PermissionDenied):verified_successor_principal(root,'third','task')
            path.write_bytes(first_bytes)
            store.now=lambda:1893456001
            self.assertEqual(store.evaluate('handoff.self',principal,task_id='task')['permission'],'approval_required')
            import time
            store.now=time.time
            policy['approvals'][0]['successors']=False
            store.configure(policy,Principal('op','operator'),expected_revision=1)
            self.assertEqual(store.evaluate('handoff.self',principal,task_id='task')['permission'],'approval_required')
            policy['approvals'][0]['successors']=True
            policy['sessions']={'successor':{'actions':{'handoff.self':'deny'}}}
            store.configure(policy,Principal('op','operator'),expected_revision=2)
            self.assertEqual(store.evaluate('handoff.self',principal,task_id='task')['permission'],'deny')
            from codex_wake.wake_policy import complete_owner
            complete_owner(root,dict(kind='task',id='task'),'task-done',actor='operator:fixture')
            with self.assertRaises(PermissionDenied):verified_successor_principal(root,'successor','task')

    def test_independent_monitor_observes_but_does_not_activate_after_revocation(self):
        from codex_wake.agent_handoff import poll_handoffs
        from codex_wake.agent_lifecycle import save
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=PermissionStore(root)
            store.configure({'version':1,'mandatory':['handoff.self']},Principal('op','operator'),expected_revision=0)
            journal=root/'lifecycle';journal.mkdir(mode=0o700)
            profile=dict(app_server='unix:///fixture',codex_path='/bin/true',timeout=1)
            goal=dict(objective='Continue task',status='paused',tokenBudget=100,tokensUsed=20,timeUsedSeconds=10,createdAt=1)
            intent=dict(operation='handoff',source_thread_id='source',launch=profile,
                continuation={'activation':{'approved':True,'max_poll_seconds':1,'deadline_margin_seconds':10}})
            receipt=dict(thread_id='source',successor_thread_id='successor',intent=intent,fingerprint='fingerprint',
                state='awaiting_activation',continuation_deadline=2000,
                source_goal=dict(goal,threadId='source'),successor_goal=dict(goal,threadId='successor'),
                permission_context=dict(action='handoff.self',subject='source',target='source',task_id=None,
                    operation_id='handoff-1',predecessor=None,trigger='manual'))
            path=journal/'receipt.json';save(path,receipt)
            owner=dict(intent_fingerprint='fingerprint',source_thread_id='source',successor_thread_id='successor',state='successor_prepared')
            import hashlib
            save(journal/('owner-'+hashlib.sha256(b'source').hexdigest()+'.json'),owner)
            methods=[]
            def native(_endpoint,_codex,method,params,_timeout):
                methods.append(method)
                if method!='thread/goal/get':raise AssertionError('Unexpected effect '+method)
                return {'goal':dict(goal,threadId=params['threadId'])}
            with patch('codex_wake.agent_handoff.native_request',side_effect=native),patch('codex_wake.native_clock.snapshot',return_value={'utc':{'upper':1000,'lower':999}}):
                poll_handoffs(root,supervision={'interval':1})
            saved=json.loads(path.read_text())
            self.assertEqual(saved['state'],'blocked')
            self.assertEqual(saved['reason'],'permission_deny')
            self.assertEqual(methods,['thread/goal/get','thread/goal/get'])
            self.assertEqual(saved['source_goal']['tokensUsed'],20)
            self.assertEqual(saved['continuation_deadline'],2000)

    def test_lost_effect_remains_uncertain_after_permission_revocation(self):
        from codex_wake.permission_handoff import before_effect
        from codex_wake.agent_lifecycle import save
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);PermissionStore(root).configure({'version':1,'mandatory':['handoff.self']},Principal('op','operator'),expected_revision=0)
            journal=root/'lifecycle';journal.mkdir(mode=0o700)
            receipt=dict(state='uncertain',uncertain_effect='thread/start',intent={'operation':'handoff','source_thread_id':'source','continuation':{}},
                permission_context=dict(action='handoff.self',subject='source',target='source',task_id=None,
                    operation_id='intent',predecessor=None,trigger='manual'))
            path=journal/'receipt.json';save(path,receipt)
            self.assertFalse(before_effect(path,receipt))
            self.assertEqual(receipt['state'],'uncertain')
            self.assertEqual(receipt['uncertain_effect'],'thread/start')

    def test_public_mcp_admission_reuses_approval_and_revocation_fences_native_reads(self):
        import hashlib
        import threading
        from websockets.sync.server import unix_serve
        from codex_wake.mcp_server import CommandRunner
        from codex_wake.task_briefs import BriefAuthority,TaskBriefStore
        source='00000000-0000-7000-8000-000000000321'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=root/'state'
            briefs=TaskBriefStore(state);authority=BriefAuthority('operator:fixture','operator')
            briefs.propose('task',dict(objective='Continue task',phase='implementation',non_goals=['No deploy'],
                acceptance=['Verified result'],context=[],workspace=tmp,allocation_ref='allocation',permission_ref='worker'),authority=authority)
            briefs.approve('task',1,authority=authority);briefs.admit('task','assignment',authority=authority)
            pin=briefs.assignment_pin('task','assignment')
            store=PermissionStore(state)
            store.configure({'version':1,'global':{'actions':{'handoff.self':'approval_required'}},
                'approvals':[dict(id='task-approval',action='handoff.self',subject=source,scope='task',
                    task_id='task',expires_at='2030-01-01T00:00:00Z',issuer='operator')]},Principal('op','operator'),expected_revision=0)
            endpoint=root/'native.sock';methods=[]
            def handler(ws):
                for raw in ws:
                    value=json.loads(raw)
                    if 'id' not in value:continue
                    method=value['method'];methods.append(method)
                    if method=='initialize':result={}
                    elif method=='thread/goal/get':
                        result={'goal':dict(threadId=source,objective='Continue task',status='paused',
                            tokenBudget=1000,timeUsedSeconds=12,createdAt=100,updatedAt=100)}
                    elif method=='thread/read':result={'thread':dict(id=source,status={'type':'idle'})}
                    else:raise AssertionError('Unexpected effect '+method)
                    ws.send(json.dumps({'id':value['id'],'result':result}))
            server=unix_serve(handler,str(endpoint));worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            self.addCleanup(lambda:worker.join(timeout=2));self.addCleanup(server.shutdown)
            continuation=dict(objective='Continue task',token_cap=1000,time_cap_seconds=100,
                tokens_before_source=0,seconds_before_source=0,approval='operator fixture',
                started_at='2030-01-01T00:00:00Z',handoff_triggers=['context_limit'])
            profiles=root/'profiles.json';profiles.write_text(json.dumps(dict(version=1,callers={},
                profiles={'worker':dict(cwd=tmp,app_server='unix://'+str(endpoint),codex_path='/bin/true',tmux_session='fixture',timeout=1)},
                continuations={source:continuation})));profiles.chmod(0o600)
            checkpoint=dict(source_thread_id=source,objective='Continue task',authority='operator fixture',next_packet='Continue approved work',
                pending_obligations=[],repo=tmp,worktree=tmp,commit='a'*40,dirty_work='No changes',acceptance_remaining=['Verified result'],
                evidence=['Native checkpoint writer'],pending_wakes=[],pending_messages=[],claim_holders=[],reply_route='original session',
                hard_stops=['Original limits'],expires_at='2030-01-01T00:01:00Z',task_brief=pin,
                resources={key:continuation[key] for key in ('token_cap','time_cap_seconds','tokens_before_source','seconds_before_source','started_at')})
            path=root/'checkpoint.json';path.write_text(json.dumps(checkpoint))
            args=dict(profile='worker',intent='mcp-handoff',thread_id=source,caller_thread_id=source,
                checkpoint='checkpoint.json',checkpoint_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                mode='new-tab',expires_at=checkpoint['expires_at'],trigger='context_limit')
            metadata=dict(threadId=source,sessionId=source,callId='call',**{'x-codex-turn-metadata':
                dict(thread_id=source,session_id=source,turn_id='turn')})
            runner=CommandRunner(wake_root=state,lifecycle_root=state,lifecycle_profiles=profiles)
            result,failed=runner.call('wake_sessions_handoff',args,native_context=metadata)
            self.assertTrue(failed,result)  # Runtime safely holds unknown accounting; policy admission succeeds.
            self.assertEqual(result['permission_context']['approval_id'],'task-approval')
            self.assertEqual(result['intent']['task_brief'],pin)
            self.assertEqual(result['reason'],'source_usage_unknown')
            self.assertEqual(json.loads(profiles.read_text())['callers'],{})
            self.assertEqual(methods.count('thread/goal/get'),1)
            store.configure({'version':1,'mandatory':['handoff.self']},Principal('op','operator'),expected_revision=1)
            before=list(methods)
            denied,failed=runner.call('wake_sessions_handoff',args,native_context=metadata)
            self.assertTrue(failed,denied)
            self.assertEqual(denied['error']['code'],'permission_deny')
            self.assertEqual(methods,before)
            journal=state/'lifecycle'/(hashlib.sha256(args['intent'].encode()).hexdigest()+'.json')
            retained=json.loads(journal.read_text());retained.update(state='uncertain',uncertain_effect='thread/start')
            from codex_wake.agent_lifecycle import save
            save(journal,retained)
            observed,failed=runner.call('wake_sessions_handoff',args,native_context=metadata)
            self.assertTrue(failed,observed)
            self.assertTrue(observed['read_only'])
            self.assertEqual(observed['receipt']['state'],'uncertain')
            self.assertEqual(observed['receipt']['uncertain_effect'],'thread/start')
            self.assertEqual(methods[len(before):],['initialize','thread/goal/get','initialize','thread/read'])
            before=list(methods)
            spoofed,failed=runner.call('wake_sessions_handoff',args,native_context={})
            self.assertTrue(failed,spoofed)
            self.assertEqual(spoofed['error']['code'],'permission_identity_unverified')
            self.assertEqual(methods,before)
