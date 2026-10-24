"""Common-policy decisions at the public CLI/MCP boundary (#320)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class SessionPermissionsTests(unittest.TestCase):
    def test_public_mcp_inspects_new_native_self_without_uuid_grant(self):
        from codex_wake.mcp_server import CommandRunner
        from codex_wake.session_permissions import PermissionStore, Principal
        thread='00000000-0000-7000-8000-000000000320'
        with tempfile.TemporaryDirectory() as tmp:
            store=PermissionStore(tmp)
            store.configure({'version':1},Principal('operator','operator'),expected_revision=0)
            runner=CommandRunner(wake_root=Path(tmp))
            meta=dict(threadId=thread,sessionId=thread,callId='call',**{
                'x-codex-turn-metadata':dict(thread_id=thread,session_id=thread,turn_id='turn')})
            value,failed=runner.call('wake_permissions_show',dict(caller_thread_id=thread,
                action='refresh.self'),native_context=meta)
            self.assertFalse(failed,value)
            self.assertEqual(value['permission'],'allow')
            self.assertEqual(value['relationship'],'self')
            self.assertEqual(value['readiness'],'not_observed')
            denied,failed=runner.call('wake_permissions_show',dict(caller_thread_id=thread,
                action='refresh.self'),native_context={})
            self.assertTrue(failed,denied)

    def test_global_override_mandatory_and_revision_are_enforced(self):
        from codex_wake.session_permissions import PermissionStore,Principal,PermissionDenied
        with tempfile.TemporaryDirectory() as tmp:
            store=PermissionStore(tmp);operator=Principal('op','operator');actor=Principal('self')
            store.configure({'version':1,'global':{'actions':{'refresh.self':'deny'}},
                'sessions':{'self':{'actions':{'refresh.self':'allow'}}},
                'mandatory':['refresh.shared']},operator,expected_revision=0)
            self.assertEqual(store.evaluate('refresh.self',actor)['permission'],'allow')
            self.assertEqual(store.evaluate('refresh.shared',actor,target='daemon',relationship='shared')['permission'],'deny')
            with self.assertRaises(PermissionDenied):
                store.configure({'version':1},operator,expected_revision=0)
            with self.assertRaises(PermissionDenied):
                store.change_session('self',{'actions':{'refresh.self':'allow'}},actor,expected_revision=1)
            store.change_session('self',{'actions':{'refresh.self':'deny'}},actor,expected_revision=1)
            self.assertEqual(store.evaluate('refresh.self',actor)['permission'],'deny')

    def test_new_actions_and_scoped_approvals_do_not_renew_authority(self):
        from codex_wake.session_permissions import PermissionStore,Principal
        with tempfile.TemporaryDirectory() as tmp:
            store=PermissionStore(tmp,now=lambda:100)
            store.configure({'version':1,'known_actions':['session.inspect'], 'approvals':[
                dict(id='approval',action='enforcement.increase',subject='self',scope='task',
                     task_id='task',expires_at='1970-01-01T00:03:20Z',issuer='operator')]},
                Principal('op','operator'),expected_revision=0)
            actor=Principal('self',tasks=('task',))
            self.assertEqual(store.evaluate('refresh.self',actor)['permission'],'approval_required')
            self.assertEqual(store.evaluate('enforcement.increase',actor,task_id='task')['approval_id'],'approval')
            self.assertEqual(store.evaluate('enforcement.increase',actor)['permission'],'approval_required')
            store.now=lambda:201
            self.assertEqual(store.evaluate('enforcement.increase',actor,task_id='task')['permission'],'approval_required')

    def test_scoped_refresh_refuses_shared_fallback_before_any_admission(self):
        from codex_wake.session_permissions import PermissionStore,Principal
        from codex_wake.mcp_server import CommandRunner
        thread='00000000-0000-7000-8000-000000000320'
        with tempfile.TemporaryDirectory() as tmp:
            PermissionStore(tmp).configure({'version':1},Principal('op','operator'),expected_revision=0)
            profile=Path(tmp)/'profiles.json'
            profile.write_text(json.dumps(dict(version=1,callers={},profiles={'self':dict(
                refresh_mode='shared_mcp_idle',scope_approval='standing host approval',cwd=tmp,
                app_server='unix:///missing',codex_path='/bin/true',timeout=1,resources={'wake':{}})})))
            profile.chmod(0o600)
            runner=CommandRunner(wake_root=Path(tmp),lifecycle_profiles=profile)
            meta=dict(threadId=thread,sessionId=thread,callId='call',**{'x-codex-turn-metadata':
                dict(thread_id=thread,session_id=thread,turn_id='turn')})
            result,failed=runner.call('wake_sessions_refresh',dict(caller_thread_id=thread,
                thread_id=thread,profile='self',intent='scope-test',scope='current_connection',
                checkpoint='missing',checkpoint_sha256='a'*64,resources=['wake'],expires_at='2030-01-01T00:00:00Z'),native_context=meta)
            self.assertTrue(failed,result)
            self.assertEqual(result['error']['code'],'refresh_scope_unsupported')
            self.assertFalse((Path(tmp)/'shared-refresh').exists())
            self.assertEqual(json.loads(profile.read_text())['callers'],{})

    def test_operator_cli_and_native_mcp_share_policy(self):
        from codex_wake.a2a_bus import BusStore
        from codex_wake.cli import run
        from io import StringIO
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bus,capability=BusStore.configure(root/'bus')
            policy=root/'policy.json';policy.write_text(json.dumps({'version':1,'global':{'actions':{'refresh.self':'deny'}}}));policy.chmod(0o600)
            common=['--wake-root',str(root/'state'),'permissions']
            with redirect_stdout(StringIO()):
                code=run(common+['configure','--bus-root',str(bus.root),'--operator-capability',str(capability),'--file',str(policy),'--expected-revision','0','--json'])
            self.assertEqual(code,0)
            output=StringIO()
            with redirect_stdout(output):
                code=run(common+['show','--bus-root',str(bus.root),'--operator-capability',str(capability),'--subject','self','--action','refresh.self','--json'])
            self.assertEqual(code,0)
            self.assertEqual(json.loads(output.getvalue())['permission'],'deny')
