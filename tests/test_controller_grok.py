"""Public Grok controller seam using the actually negotiated ACPv1 shape."""
import hashlib,json,os,sys,tempfile,time,unittest
from pathlib import Path
from codex_wake.controller_auth import Actor,AuthError
from codex_wake.managed_inventory import InventoryError
from codex_wake.process import process_identity


class GrokControllerTests(unittest.TestCase):
    def fixture(self,root):
        from codex_wake.controller_grok import ControllerGrok
        birth=process_identity(os.getpid())
        target=dict(host='fixture',environment='linux',runtime='grok',provider='grok',account='fixture',home=str(root/'home'),
            namespace='grok:fixture',build_sha256=hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
            configuration_revision='fixture-v1',backend_id='agent-one',channel='acp-websocket',connection_generation='instance-one',
            process_pid=str(os.getpid()),process_start_ticks=str(birth['start_time_ticks']),process_boot_id=birth['boot_id'])
        secret=root/'transport.secret';secret.write_text('fixture-only');secret.chmod(0o600)
        profile=dict(target=target,endpoint='ws://127.0.0.1:23456/ws',secret_file=str(secret),cwd=str(root),agent_version='1.0.70',timeout=2)
        registry=root/'controller-grok.json';registry.write_text(json.dumps(dict(version=1,profiles={'selected':profile})));registry.chmod(0o600)
        actor=Actor('caller','service','client','grant','issuer','resource',frozenset({'observe','control'}),[target],time.time()+600)
        calls=[]
        def request(profile,method,params,identifier,guard):
            guard();calls.append((method,params,identifier))
            if method=='initialize':return dict(protocolVersion=1,agentCapabilities=dict(loadSession=True,sessionCapabilities=dict(list={},resume={},close={})),authMethods=[dict(id='grok.com',name='Grok')],_meta=dict(agentVersion='1.0.70',agentId='agent-one',agentInstanceId='instance-one',currentWorkingDirectory=str(root)))
            if method=='session/prompt':return dict(stopReason='end_turn',_wake_updates=[dict(sessionId='conversation',update=dict(sessionUpdate='agent_message_chunk',content=dict(type='text',text='fixture answer')))])
            if method=='session/new':return dict(sessionId='new-conversation')
            if method=='session/load':return dict(configOptions=[])
            if method=='session/cancel':return dict(status='requested')
            raise AssertionError(method)
        owner=ControllerGrok(root,request=request)
        def args(name,*,conversation=False,**extra):
            selected=dict(target,conversation_id='conversation') if conversation else target
            return dict(profile='selected',expected_target=selected,_request=dict(operation_id=name,idempotency_key=name,correlation_id=name,binding='fixture',target=selected),**extra)
        return owner,actor,target,args,calls,profile

    def test_negotiated_prompt_retains_correlated_answer_without_terminal_or_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);owner,actor,target,args,calls,profile=self.fixture(root)
            capabilities=owner.execute(actor,'grok.capabilities',dict(profile='selected',expected_target=target),authorize=lambda:actor)
            self.assertEqual(capabilities['result']['protocol_version'],1)
            self.assertEqual(capabilities['result']['capabilities']['fork']['status'],'unsupported')
            arguments=args('prompt-one',conversation=True,prompt='Hello fixture')
            first=owner.execute(actor,'grok.prompt',arguments,authorize=lambda:actor)
            operation=first['result']['operation']
            self.assertEqual(operation['result']['text'],'fixture answer')
            self.assertEqual(operation['result']['session_id'],'conversation')
            again=owner.execute(actor,'grok.prompt',arguments,authorize=lambda:actor)
            self.assertEqual(again,first)
            self.assertEqual(len([m for m,p,i in calls if m=='session/prompt']),1)
            result=owner.execute(actor,'grok.wait',dict(operation_id='prompt-one',timeout=0),authorize=lambda:actor)
            self.assertEqual(result['result']['operation']['result']['text'],'fixture answer')
            peer=Actor('peer',*tuple(actor.__dict__.values())[1:])
            with self.assertRaises(AuthError):owner.execute(peer,'grok.wait',dict(operation_id='prompt-one'),authorize=lambda:peer)
            with self.assertRaises(InventoryError):owner.execute(actor,'grok.fork',args('fork-one',conversation=True),authorize=lambda:actor)
            health=owner.execute(actor,'grok.health',dict(profile='selected',expected_target=target),authorize=lambda:actor)
            self.assertEqual(health['result']['status'],'unsupported')
            self.assertFalse((root/'runtime-bindings').exists())

    def test_flow_session_facade_exposes_new_and_sequential_modes_with_original_answers(self):
        from codex_wake.controller_grok_sessions import ControllerGrokSessions
        with tempfile.TemporaryDirectory() as directory:
            owner,actor,target,args,calls,profile=self.fixture(Path(directory))
            sessions=ControllerGrokSessions(directory,owner=owner)
            capabilities=sessions.execute(actor,'sessions.capabilities',dict(profile='selected',expected_target=target),authorize=lambda:actor)
            self.assertEqual(capabilities['result']['modes'],['new_session','sequential'])
            self.assertEqual(capabilities['result']['max_parallelism'],1)
            created=sessions.execute(actor,'sessions.create',args('create-one'),authorize=lambda:actor)
            self.assertEqual(created['result']['operation']['result']['target']['conversation_id'],'new-conversation')
            submitted=sessions.execute(actor,'sessions.prompt',args('step-one',conversation=True,prompt='first'),authorize=lambda:actor)
            waited=sessions.execute(actor,'sessions.wait',dict(operation_id='step-one',timeout=0),authorize=lambda:actor)
            self.assertEqual(waited['result']['operation']['answer']['text'],'fixture answer')
            self.assertEqual(waited['result']['operation']['operation'],'grok.prompt')
            self.assertFalse(waited['result']['operation']['result']['allocation_created'])

    def test_lost_reply_is_uncertain_no_replay_or_session_scoped_cancel(self):
        with tempfile.TemporaryDirectory() as directory:
            owner,actor,target,args,calls,profile=self.fixture(Path(directory));request=owner.request
            def lost(profile,method,params,identifier,guard):
                value=request(profile,method,params,identifier,guard)
                if method=='session/prompt':raise OSError('fixture lost original reply')
                return value
            owner.request=lost;arguments=args('lost',conversation=True,prompt='fixture')
            first=owner.execute(actor,'grok.prompt',arguments,authorize=lambda:actor)
            self.assertEqual(first['result']['operation']['phase'],'uncertain')
            owner.execute(actor,'grok.prompt',arguments,authorize=lambda:actor)
            before=list(calls)
            cancelled=owner.execute(actor,'grok.cancel',dict(operation_id='lost'),authorize=lambda:actor)
            self.assertEqual(cancelled['result']['operation']['cancellation'],'uncertain')
            self.assertEqual(calls,before)
            self.assertEqual(len([method for method,params,key in calls if method=='session/prompt']),1)
            self.assertEqual(cancelled['result']['cancellation_capability']['status'],'unsupported')

    def test_definite_native_auth_refusal_is_not_started_and_final_reply_survives_grant_loss(self):
        from codex_wake.grok_acp import ACPRefusal
        with tempfile.TemporaryDirectory() as directory:
            owner,actor,target,args,calls,profile=self.fixture(Path(directory));request=owner.request
            def refused(profile,method,params,identifier,guard):
                if method=='session/prompt':raise ACPRefusal('native_auth_required','fixture ACP authentication required',-32000)
                return request(profile,method,params,identifier,guard)
            owner.request=refused
            value=owner.execute(actor,'grok.prompt',args('auth',conversation=True,prompt='fixture'),authorize=lambda:actor)['result']['operation']
            self.assertEqual(value['execution'],'not_started')
            self.assertEqual(value['reason'],'native_auth_required')
            revoked=[False]
            def authorize():
                if revoked[0]:raise AuthError()
                return actor
            def lose_authority(profile,method,params,identifier,guard):
                value=request(profile,method,params,identifier,guard)
                if method=='session/prompt':revoked[0]=True
                return value
            owner.request=lose_authority
            with self.assertRaises(AuthError):owner.execute(actor,'grok.prompt',args('retained',conversation=True,prompt='fixture'),authorize=authorize)
            revoked[0]=False
            result=owner.execute(actor,'grok.wait',dict(operation_id='retained',timeout=0),authorize=authorize)['result']['operation']
            self.assertEqual(result['answer']['text'],'fixture answer')
            self.assertEqual(result['acceptance'],'native_final_reply')
