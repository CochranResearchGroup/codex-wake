"""Permission decisions preserve the original resource envelope (#322/#319)."""
from contextlib import redirect_stdout
from io import StringIO
import json
import tempfile
import subprocess
import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import test_goal_supervision as fixtures
from codex_wake.goal_supervision import enroll, poll, show
from codex_wake.session_permissions import PermissionStore, Principal, PermissionDenied

THREAD=fixtures.THREAD
NOW=fixtures.NOW


def native_context(thread=THREAD):
    return dict(threadId=thread,sessionId=thread,callId='enforcement-call',
        **{'x-codex-turn-metadata':dict(thread_id=thread,session_id=thread,turn_id='work')})


class EnforcementPermissionTests(unittest.TestCase):
    fixture=fixtures.GoalSupervisionTests.fixture
    controller=fixtures.GoalSupervisionTests.controller

    def configure(self,root,policy=None,revision=0):
        return PermissionStore(root,now=lambda:NOW).configure(policy or {'version':1},
            Principal('operator','operator'),expected_revision=revision)

    def test_explicit_enrollment_deny_blocks_public_supervision_without_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,policy,_,native,_=self.fixture(tmp)
            self.configure(root,{'version':1,'global':{'actions':{'enforcement.enroll':'deny'}}})
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                with self.assertRaises(PermissionDenied):
                    enroll(root,policy,THREAD,100,120,native_context=native_context())
            self.assertEqual(native['calls'],[])
            self.assertFalse(list((root/'goal-supervision').glob('[0-9a-f]'*64+'.json')))

    def test_operator_cli_enrolls_but_recovery_does_not_clear_stop(self):
        from codex_wake.a2a_bus import BusStore
        from codex_wake.cli import run
        with tempfile.TemporaryDirectory() as tmp:
            root,policy,_,native,_=self.fixture(tmp)
            self.configure(root)
            bus,capability=BusStore.configure(Path(tmp)/'bus')
            base=['--wake-root',str(root),'goal-limits']
            options=['--policy',str(policy),'--caller-thread-id',THREAD,'--bus-root',str(bus.root),
                '--operator-capability',str(capability),'--json']
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                output=StringIO()
                with redirect_stdout(output):code=run(base+['set',*options,'--token-limit','100','--time-limit-seconds','120'])
                self.assertEqual(code,0,output.getvalue())
                first=json.loads(output.getvalue())
                self.assertEqual(first['enforcement_permission']['permission'],'allow')
                self.assertEqual(first['used_tokens'],40)
                from codex_wake import goal_supervision as supervision
                original_request=supervision._request
                def failed_read(grant,method,params):
                    if method=='thread/read':raise TimeoutError('fixture observation timeout')
                    return original_request(grant,method,params)
                with patch('codex_wake.goal_supervision._request',side_effect=failed_read):
                    stopped=poll(root)[0]
                self.assertTrue(stopped['stop_latched'])
                path=next(p for p in (root/'goal-supervision').glob('*.json') if p.name!='controller.json')
                preserved=path.read_bytes()
                native['goal']['status']='active'
                output=StringIO()
                with redirect_stdout(output):code=run(base+['recover',*options])
                value=json.loads(output.getvalue())
                self.assertEqual(code,2)
                self.assertEqual(value['permission']['permission'],'allow')
                self.assertEqual(value['capability'],'unsupported')
                self.assertEqual(value['reason'],'observation_stop_recovery_unsupported')
                self.assertFalse(value['effect_attempted'])
                self.assertEqual(path.read_bytes(),preserved)
                self.assertEqual(value['campaign']['used_tokens'],first['used_tokens'])
                self.assertEqual(value['campaign']['deadline'],first['deadline'])
                self.assertTrue(value['campaign']['stop_latched'])

    def test_increase_needs_its_own_approval_before_native_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,policy,_,native,_=self.fixture(tmp)
            self.configure(root)
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                first=enroll(root,policy,THREAD,100,120,native_context=native_context())
                native['calls'].clear()
                with self.assertRaises(PermissionDenied) as raised:
                    enroll(root,policy,THREAD,110,120,native_context=native_context())
                self.assertEqual(raised.exception.decision['action'],'enforcement.increase')
                self.assertEqual(native['calls'],[])
                later=show(root,policy,THREAD,native_context=native_context())
                self.assertEqual(later['deadline'],first['deadline'])
                self.assertEqual(later['used_tokens'],first['used_tokens'])
                self.assertEqual(later['enforcement_permissions']['enforcement.recover']['capability'],'unsupported')

    def test_unverified_cli_cannot_use_a_copied_caller_grant(self):
        from codex_wake.cli import run
        with tempfile.TemporaryDirectory() as tmp:
            root,policy,_,native,_=self.fixture(tmp)
            self.configure(root)
            output=StringIO()
            with redirect_stdout(output):
                code=run(['--wake-root',str(root),'goal-limits','set','--policy',str(policy),
                    '--caller-thread-id',THREAD,'--token-limit','100','--time-limit-seconds','120','--json'])
            self.assertEqual(code,2)
            self.assertEqual(json.loads(output.getvalue())['state'],'held')
            self.assertEqual(native['calls'],[])

    def test_controller_rechecks_revocation_without_interrupting_or_disabling_safety(self):
        peer='00000000-0000-7000-8000-000000000322'
        with tempfile.TemporaryDirectory() as tmp:
            root,policy,log,native,_=self.fixture(tmp)
            raw=json.loads(policy.read_text())
            raw['callers'][peer]=dict(raw['callers'][THREAD])
            policy.write_text(json.dumps(raw));policy.chmod(0o600)
            peer_log=log.with_name('peer.jsonl')
            peer_log.write_text(log.read_text().replace(THREAD,peer))
            native['siblings']={peer:dict(goal=dict(threadId=peer,createdAt=NOW,status='active'),active=['peer-work'],calls=[])}
            self.configure(root)
            def independent_poll():
                result=subprocess.run([sys.executable,'-c',
                    'import json,sys; from codex_wake.goal_supervision import poll; print(json.dumps(poll(sys.argv[1])))',str(root)],
                    cwd=Path(__file__).resolve().parents[1],env=dict(os.environ,PYTHONPATH='src'),
                    capture_output=True,text=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr)
                return {item['thread_id']:item for item in json.loads(result.stdout)}
            with self.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=NOW):
                first=enroll(root,policy,THREAD,100,120,native_context=native_context())
                second=enroll(root,policy,peer,100,120,native_context=native_context(peer))
                self.configure(root,{'version':1,'sessions':{THREAD:{'actions':{'enforcement.enroll':'deny'}}}},revision=1)
                native['calls'].clear()
                samples=independent_poll();revoked=samples[THREAD]
                self.assertEqual(revoked['state'],'held')
                self.assertEqual(revoked['reason'],'permission_revoked')
                self.assertFalse(revoked.get('stop_latched',False))
                self.assertFalse(any(m in ('thread/goal/set','turn/interrupt','turn/steer') for m,_ in native['calls']))
                for key in ('deadline','used_tokens','generation','token_accounting'):
                    self.assertEqual(revoked[key],first[key])
                    self.assertEqual(samples[peer][key],second[key])
                self.assertEqual(samples[peer]['state'],'armed')
                # Restarted controller retains original safety authority at the
                # actual original token limit, despite the revoked enrollment.
                charge=json.loads(log.read_text().splitlines()[-1])
                charge['payload']['response_id']='response-2'
                charge['payload']['usage']=dict(input_tokens=60,cached_input_tokens=0,output_tokens=0,total_tokens=60)
                with log.open('a') as stream:stream.write(json.dumps(charge)+'\n')
                samples=independent_poll();exhausted=samples[THREAD]
                self.assertTrue(exhausted['stop_latched'])
                self.assertEqual(exhausted['reason'],'allocation_exhausted')
                self.assertEqual(exhausted['deadline'],first['deadline'])
                self.assertEqual(native['goal']['status'],'paused')
                self.assertEqual(native['active'],[])
                self.assertEqual(samples[peer]['state'],'armed')
                self.assertEqual(samples[peer]['used_tokens'],second['used_tokens'])
                self.assertEqual(native['siblings'][peer]['goal']['status'],'active')

    def test_native_adapter_reuses_only_its_verified_assignment_approval(self):
        from types import SimpleNamespace
        from codex_wake.task_briefs import TaskBriefStore,BriefAuthority
        from codex_wake.permission_enforcement import mcp_call
        with tempfile.TemporaryDirectory() as tmp:
            root,policy,_,native,_=self.fixture(tmp)
            task='implementation-task';assignment='same-task-worker'
            store=TaskBriefStore(root)
            worker=BriefAuthority('native:'+THREAD,'worker',(task,))
            controller=BriefAuthority('operator-controller','controller',(task,))
            brief=dict(objective='Implement policy',phase='implementation',non_goals=['No deployment'],
                acceptance=['Public refusal'],context=[],workspace=tmp,
                allocation_ref='existing',permission_ref='common')
            proposed=store.propose(task,brief,authority=worker)
            store.approve(task,proposed['revision'],authority=controller)
            store.admit(task,assignment,authority=worker,revision=proposed['revision'])
            self.configure(root,{'version':1,'approvals':[dict(id='recover-task',action='enforcement.recover',
                subject=THREAD,scope='task',task_id=task,issuer='operator',expires_at='2030-01-01T01:00:00Z')]})
            runner=SimpleNamespace(wake_root=root,goal_limits_root=None,goal_limits_policy=policy,harness_policy=None)
            result=mcp_call(runner,'recover',dict(caller_thread_id=THREAD,
                task_id=task,assignment_id=assignment),native_context())
            self.assertEqual(result['permission']['permission'],'allow')
            self.assertEqual(result['permission']['approval_id'],'recover-task')
            self.assertEqual(result['capability'],'unsupported')
            self.assertFalse(result['effect_attempted'])
            self.assertEqual(native['calls'],[])
            with self.assertRaises(PermissionDenied):
                mcp_call(runner,'recover',dict(caller_thread_id=THREAD,task_id=task),native_context())
            with self.assertRaises(ValueError):
                mcp_call(runner,'recover',dict(caller_thread_id=THREAD),{})
