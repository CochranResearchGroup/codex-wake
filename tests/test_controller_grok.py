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
