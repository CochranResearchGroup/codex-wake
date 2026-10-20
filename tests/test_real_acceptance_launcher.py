"""Public launcher rejects the known blocked setup before native/model dispatch."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest


def launcher():
    path=Path(__file__).resolve().parents[1]/'scripts/goal_supervision_real_acceptance.py'
    spec=importlib.util.spec_from_file_location('real_acceptance_launcher',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class RealAcceptanceLauncherTests(unittest.TestCase):
    def test_workspace_never_fails_setup_before_any_native_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            options=SimpleNamespace(output=Path(directory)/'acceptance',approved=True,token_limit=100000,
                seconds=180,sandbox='workspace-write',approval_policy='never')
            calls=[]
            result=launcher().run(options,lambda method,params: calls.append((method,params)))
            self.assertEqual(result['failure_stage'],'setup')
            self.assertEqual(result['reason'],'unattended_mcp_permissions_unqualified')
            self.assertFalse(result['model_dispatch_attempted'])
            self.assertEqual(calls,[])
            self.assertTrue((options.output/'result.json').is_file())

    def test_actual_permission_mismatch_is_setup_failure_before_goal_activation(self):
        with tempfile.TemporaryDirectory() as directory:
            options=SimpleNamespace(output=Path(directory)/'acceptance',approved=True,token_limit=100000,
                seconds=180,sandbox='danger-full-access',approval_policy='never',expected_version='0.18.6',
                codex_home=Path('/fixture/home'),model='fixture-model',wake_python=Path('/fixture/python'),policy=Path('/fixture/policy'),
                wake_root=Path('/fixture/root'))
            calls=[]
            def request(method,params):
                calls.append((method,params))
                if method=='thread/start':return dict(thread=dict(id='owned',path='/fixture/home/sessions/thread.jsonl'),approvalPolicy='never',sandbox=dict(type='workspaceWrite'))
                if method=='thread/goal/get':return dict(goal=None)
                if method=='thread/backgroundTerminals/list':return dict(data=[],nextCursor=None)
                if method=='thread/turns/list':return dict(data=[],nextCursor=None)
                raise AssertionError(method)
            result=launcher().run(options,request)
            self.assertEqual(result['reason'],'native_permissions_do_not_match_approval')
            self.assertFalse(result['model_dispatch_attempted'])
            self.assertFalse(any(m in ('turn/start','thread/goal/set') for m,_ in calls))

    def test_verified_run_enrolls_then_checkpoints_and_preserves_operator_reply(self):
        for scenario in ('pass','stale','held','final-stale','final-held'):
            with self.subTest(scenario=scenario),tempfile.TemporaryDirectory() as directory:
                output=Path(directory)/'acceptance'
                options=SimpleNamespace(output=output,approved=True,token_limit=100000,seconds=180,
                    sandbox='danger-full-access',approval_policy='never',expected_version='0.18.6',
                    codex_home=Path('/fixture/home'),model='fixture-model',wake_python=Path('/fixture/python'),policy=Path('/fixture/policy'),
                    wake_root=Path('/fixture/root'))
                calls=[];goal=None;operator=False
                def request(method,params):
                    nonlocal goal,operator
                    calls.append((method,params))
                    if method=='thread/start':return dict(thread=dict(id='owned',path='/fixture/home/sessions/thread.jsonl'),approvalPolicy='never',sandbox=dict(type='dangerFullAccess'))
                    if method=='mcpServerStatus/list':return dict(data=[dict(name='wake_acceptance',serverInfo=dict(version='0.18.6'),tools={
                        'wake_goal_limits_set':dict(inputSchema=dict(properties={'caller_thread_id':{},'token_limit':{},'time_limit_seconds':{}})),
                        'wake_goal_limits_show':dict(inputSchema=dict(properties={'caller_thread_id':{}}))})])
                    if method=='thread/goal/set':
                        goal=dict(threadId='owned',status=params['status'],createdAt=100,objective=params.get('objective','fixture'))
                        return dict(goal=dict(goal))
                    if method=='thread/goal/get':return dict(goal=goal)
                    if method=='thread/read':return dict(thread=dict(id='owned',turns=[dict(id='operator' if operator else 'work',status='completed',items=[dict(type='agentMessage',text='REAL_DEMO_CHAT_OK' if operator else 'checkpoint')])]))
                    if method=='turn/start':operator=True;return dict(turn=dict(id='operator'))
                    if method=='thread/backgroundTerminals/list':return dict(data=[],nextCursor=None)
                    if method=='thread/turns/list':return dict(data=[],nextCursor=None)
                    if method=='thread/backgroundTerminals/list':return dict(data=[],nextCursor=None)
                    raise AssertionError(method)
                observations=0
                def status(thread):
                    nonlocal observations
                    if goal is None:return dict(state='held',reason='not_enrolled',controller=dict(fresh=True))
                    observations+=1
                    goal['status']='paused';(output/'checkpoint.md').write_text('Owned checkpoint')
                    proof=dict(state='checkpoint_requested',generation='same',allocation_id='native-owned',
                        deadline=280,used_tokens=20,token_limit=100000,time_limit_seconds=180,token_accounting='fresh',controller=dict(fresh=True),
                        accounting=dict(state='qualified'),checkpoint=dict(state='acknowledged'))
                    if observations==1:
                        goal['status']='active';proof.update(state='armed',checkpoint=None)
                    elif scenario=='stale' or (scenario=='final-stale' and operator):proof['controller']['fresh']=False
                    elif scenario=='held' or (scenario=='final-held' and operator):proof.update(state='held',reason='observation_unavailable')
                    return proof
                result=launcher().run(options,request,status,sleep=lambda _:None)
                if scenario!='pass':
                    self.assertEqual(result['verdict'],'FAIL',result)
                    self.assertEqual(result['failure_stage'],'enforcement')
                    self.assertTrue(result['cleanup']['verified'])
                    continue
                self.assertEqual(result['verdict'],'PASS')
                self.assertEqual(result['allocation_id'],'native-owned')
                self.assertTrue(result['operator_reply_completed'])
                self.assertTrue(result['cleanup']['verified'])
                self.assertEqual(sum(m=='thread/start' for m,_ in calls),1)

    def test_cli_permission_refusal_writes_classified_receipt_without_native_endpoint(self):
        import json
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'acceptance'
            script=Path(__file__).resolve().parents[1]/'scripts/goal_supervision_real_acceptance.py'
            completed=subprocess.run([sys.executable,str(script),'--approve-real-agent','--output',str(output),
                '--token-limit','100000','--seconds','180','--sandbox','workspace-write','--approval-policy','never',
                '--codex','/absent/codex','--wake-python','/absent/python','--app-server','unix:///absent/socket',
                '--policy','/absent/policy','--wake-root','/absent/root','--expected-version','0.18.6','--model','fixture'],
                capture_output=True,text=True,timeout=5)
            self.assertEqual(completed.returncode,1)
            result=json.loads((output/'result.json').read_text())
            self.assertEqual(result['failure_stage'],'setup')
            self.assertEqual(result['reason'],'unattended_mcp_permissions_unqualified')
            self.assertFalse(result['model_dispatch_attempted'])

    def test_failure_stage_distinguishes_setup_enrollment_and_enforcement(self):
        for defect,stage,reason in [('catalog','setup','installed_mcp_version_unqualified'),
                ('enrollment','enrollment','enrollment_not_armed'),
                ('checkpoint','enforcement','pause_without_acknowledged_checkpoint')]:
            with self.subTest(defect=defect),tempfile.TemporaryDirectory() as directory:
                output=Path(directory)/'acceptance';calls=[];goal=None
                options=SimpleNamespace(output=output,approved=True,token_limit=100000,seconds=180,
                    sandbox='danger-full-access',approval_policy='never',expected_version='0.18.6',
                    codex_home=Path('/fixture/home'),model='fixture-model',wake_python=Path('/fixture/python'),
                    policy=Path('/fixture/policy'),wake_root=Path('/fixture/root'))
                def request(method,params):
                    nonlocal goal
                    calls.append((method,params))
                    if method=='thread/start':return dict(thread=dict(id='owned',path='/fixture/home/sessions/owned'),approvalPolicy='never',sandbox=dict(type='dangerFullAccess'))
                    if method=='mcpServerStatus/list':return dict(data=[dict(name='wake_acceptance',serverInfo=dict(version='old' if defect=='catalog' else '0.18.6'),tools={
                        'wake_goal_limits_set':dict(inputSchema=dict(properties={'caller_thread_id':{},'token_limit':{},'time_limit_seconds':{}})),
                        'wake_goal_limits_show':dict(inputSchema=dict(properties={}))})])
                    if method=='thread/goal/set':
                        goal=dict(threadId='owned',status=params['status'],objective=params.get('objective','fixture'),createdAt=100)
                        return dict(goal=dict(goal))
                    if method=='thread/goal/get':return dict(goal=goal)
                    if method=='thread/turns/list':return dict(data=[],nextCursor=None)
                    if method=='thread/backgroundTerminals/list':return dict(data=[],nextCursor=None)
                    if method=='thread/read':return dict(thread=dict(id='owned',turns=[]))
                    raise AssertionError(method)
                def status(thread):
                    if goal is None:return dict(state='held',reason='not_enrolled',controller=dict(fresh=True))
                    if defect=='enrollment':return dict(state='held',reason='host_scope_unavailable')
                    goal['status']='paused'
                    return dict(state='armed',accounting=dict(state='qualified'),controller=dict(fresh=True),
                        token_limit=100000,time_limit_seconds=180,token_accounting='fresh',used_tokens=20,
                        allocation_id='native-owned',generation='same',deadline=280)
                result=launcher().run(options,request,status,sleep=lambda _:None)
                self.assertEqual(result['failure_stage'],stage,result)
                self.assertEqual(result['reason'],reason)
                self.assertTrue(result['cleanup']['verified'])
                self.assertEqual(result['model_dispatch_attempted'],defect!='catalog')
                self.assertFalse(any(m=='turn/start' for m,_ in calls))
