#!/usr/bin/env python3
"""Installed durable condition recovery after real caller process death.

The server supplies deterministic native-shaped sessions/turns. This proves Wake
transport and custody, not a provider/model turn or packaged Codex capability.
"""
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import Request,urlopen
from websockets.sync.server import unix_serve


def main():
    import codex_wake
    from codex_wake.build_commands import owner_from_root
    from codex_wake.controller_flow_sessions import ControllerFlowSessions
    from codex_wake.controller_auth import OAuthAuthority
    from codex_wake.controller_http import ControllerHTTPServer
    from codex_wake.controller_operations import ControllerOperations
    from codex_wake.managed_inventory import ManagedInventory
    from codex_wake.process import process_identity
    with tempfile.TemporaryDirectory(prefix='wake-conditions410-') as directory:
        root=Path(directory);home=root/'homes/codex-alice';home.mkdir(parents=True)
        manifest=root/'builds.json'
        manifest.write_text(json.dumps(dict(schema_version=1,builds={'modded':dict(executable=str(Path(sys.executable).resolve()),
            sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),upstream_version='0.164.0+fixture',revision='protocol-fixture',source='disposable Python protocol fixture')})))
        (root/'controller-accounts.toml').write_text(f'''[profiles]\nstate_root="{root/'homes'}"\nknown_profiles=["alice"]\n[builds]\nmanifest="{manifest}"\n''')
        base=next(row['target'] for row in owner_from_root(root).execute('builds.list',dict(account='alice'))['builds'] if row['name']=='modded')
        threads={'predicate-source':dict(id='predicate-source',cwd=str(root),modelProvider='openai',turns=[])};effects=[];auto=[True];fail_initializations=[0];failed_prompts=set();defer_interrupt=[False]
        def handler(ws):
            for raw in ws:
                message=json.loads(raw)
                if 'id' not in message:continue
                method,params=message['method'],message.get('params',{})
                if method=='initialize' and fail_initializations[0]:
                    fail_initializations[0]-=1
                    ws.send(json.dumps(dict(id=message['id'],error=dict(code=-32000,message='temporary fixture source unavailable'))));continue
                if method=='initialize':value=dict(codexHome=str(home))
                elif method=='thread/start':
                    identifier='fixture-thread-'+str(len(threads))
                    thread=dict(id=identifier,cwd=str(root),modelProvider='openai',turns=[])
                    threads[identifier]=thread;effects.append(('create',identifier));value=dict(thread=thread)
                elif method=='thread/read':value=dict(thread=threads[params['threadId']])
                elif method=='turn/start':
                    thread=threads[params['threadId']]
                    turn=dict(id='turn-'+str(len(thread['turns'])),status=('failed' if params['input'][0]['text'] in failed_prompts else 'completed') if auto[0] or params['input'][0]['text'].startswith('parent-predicate') else 'inProgress',
                        items=[dict(type='agentMessage',text=json.dumps({'call':{'function':'leaf','version':1,'arguments':{'text':'nested fixture'}}} if params['input'][0]['text'].startswith('parent-predicate') else {'value':True}))])
                    thread['turns'].append(turn);effects.append(('prompt',thread['id'],params['input'][0]['text']));value=dict(turn=turn)
                elif method=='turn/interrupt':
                    turn=next(t for t in threads[params['threadId']]['turns'] if t['id']==params['turnId'])
                    if defer_interrupt[0]:turn['interruptRequested']=True
                    else:turn['status']='interrupted'
                    effects.append(('interrupt',params['threadId'],params['turnId']));value={}
                else:raise AssertionError(method)
                ws.send(json.dumps(dict(id=message['id'],result=value)))
        endpoint=root/'native.sock';server=unix_serve(handler,str(endpoint))
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        native=process_identity(os.getpid())
        profile=dict(target=base,endpoint='unix://'+str(endpoint),process=dict(pid=os.getpid(),start_ticks=native['start_time_ticks'],boot_id=native['boot_id']),
            modes=['new_session','sequential'],cwd=str(root),native_provider='openai',methods=['thread/start','turn/start','thread/read','turn/interrupt'])
        path=root/'controller-flow-sessions.json';path.write_text(json.dumps(dict(version=1,profiles={'fixture':profile})));path.chmod(0o600)
        target=dict(ControllerFlowSessions(root).target('fixture'),conversation_id='predicate-source')
        flow_target=dict(host=socket.gethostname(),environment=os.environ.get('WSL_DISTRO_NAME') or os.name,flow_id='fixture')
        caller=dict(subject='fixture-author',client_id='fixture-client',grant_id='fixture-grant',issuer='local://fixture',resource='wake:controller',
            scopes=['observe','control'],targets=[base,flow_target],expires_at=time.time()+600)
        sender='11111111-1111-4111-8111-111111111111'
        path=root/'controller-messaging.json';path.write_text(json.dumps(dict(version=1,local_caller=caller,flow_callers={sender:dict(caller,grant_id='native-fixture')})));path.chmod(0o600)
        def cli(group,verb,args):
            value=subprocess.run([sys.executable,'-m','codex_wake.cli','--wake-root',str(root),group,verb,'--arguments',json.dumps(args)],text=True,capture_output=True)
            assert value.returncode==0,(value.stdout,value.stderr)
            return json.loads(value.stdout)['result']
        registry=root/'controller-conditions.json'
        registry.write_text(json.dumps(dict(version=1,functions={
            'positive@1':dict(kind='deterministic',inputs={'n':'integer'},expression=dict(op='gt',left={'ref':'arguments.n'},right=0)),
            'semantic@1':dict(kind='semantic',inputs={'text':'string'},profile='fixture',expected_target=target,
                prompt='parent-predicate',effects='action',tools='inherited',estimated_tokens=16,callees=['leaf@1']),
            'leaf@1':dict(kind='semantic',inputs={'text':'string'},profile='fixture',expected_target=target,prompt='leaf-predicate',effects='action',tools='inherited',estimated_tokens=16)})))
        registry.chmod(0o600)
        def definition(version,short=False):
            condition=dict(op='and',operands=[False if short else dict(function='positive',version=1,arguments={'n':1}),
                dict(function='semantic',version=1,arguments={'text':'provider-free fixture'})])
            return dict(id='fixture',version=version,entry='condition',limits=dict(max_calls=8,max_depth=4,max_seconds=300,max_tokens=64,metering='estimate_opt_in'),nodes=[
                dict(id='condition',type='branch',condition=condition,then='yes',**{'else':'no'}),
                dict(id='yes',type='end',value=True),dict(id='no',type='end',value=False)])
        def finish_turns():
            for thread in threads.values():
                for turn in thread['turns']:
                    if turn['status']=='inProgress':turn['status']='completed'
        http=None;http_worker=None;child=None
        try:
            # One host-approved original service identity is mapped to each
            # transport. Transport replacement confers no new identity/grant.
            auth=OAuthAuthority(root/'oauth.sqlite',issuer='https://wake.test',resource='https://wake.test/controller',
                on_revoke=__import__('codex_wake.operation_commands',fromlist=['owner']).owner(root).revoke_grant)
            client=auth.register(dict(redirect_uris=['http://localhost/callback']))
            verifier='v'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            code=auth.authorize(subject='service',principal_kind='service',client_id=client['client_id'],redirect_uri='http://localhost/callback',resource=auth.resource,
                scopes=['observe','control'],targets=[base,flow_target],code_challenge=challenge)
            token=auth.token(dict(grant_type='authorization_code',code=code,client_id=client['client_id'],redirect_uri='http://localhost/callback',resource=auth.resource,code_verifier=verifier))['access_token']
            actor=auth.authenticate(token)
            caller={key:value for key,value in vars(actor).items() if key!='principal_kind'};caller['scopes']=sorted(actor.scopes)
            path=root/'controller-messaging.json';path.write_text(json.dumps(dict(version=1,local_caller=caller,flow_callers={sender:caller})));path.chmod(0o600)
            http=ControllerHTTPServer(('127.0.0.1',0),auth,ControllerOperations(ManagedInventory(root),host=flow_target['host'],environment=flow_target['environment']))
            http_worker=threading.Thread(target=http.serve_forever,daemon=True);http_worker.start()
            endpoint_http='http://127.0.0.1:'+str(http.server_port)
            token_path=root/'token';token_path.write_text(token);token_path.chmod(0o600)
            def api(verb,args,mcp=False):
                body=dict(operation='flows.'+verb,arguments=args)
                if mcp:body=dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='wake_flows_'+verb,arguments=args))
                req=Request(endpoint_http+('/mcp' if mcp else '/operations'),data=json.dumps(body).encode(),
                    headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
                with urlopen(req) as response:value=json.load(response)
                return value['result']['structuredContent']['result'] if mcp else value['result']
            def remote(verb,args):
                answer=subprocess.run([sys.executable,'-m','codex_wake.cli','controller','remote','--endpoint',endpoint_http,
                    '--token-file',str(token_path),'flows.'+verb,'--arguments',json.dumps(args)],text=True,capture_output=True,timeout=20)
                assert answer.returncode==0,(answer.stdout,answer.stderr)
                return json.loads(answer.stdout)['result']
            async def native(verb,args):
                from mcp import ClientSession,StdioServerParameters
                from mcp.client.stdio import stdio_client
                parameters=StdioServerParameters(command=str(Path(sys.executable).parent/'codex-wake-mcp'),args=['--wake-root',str(root)],
                    env={key:value for key,value in os.environ.items() if key!='PYTHONPATH'})
                meta=dict(threadId=sender,sessionId=sender,callId='recovery',**{'x-codex-turn-metadata':dict(thread_id=sender,session_id=sender,turn_id='fixture')})
                async with stdio_client(parameters) as (reader,writer):
                    async with ClientSession(reader,writer) as session:
                        await session.initialize()
                        answer=await session.call_tool('wake_flows_'+verb,dict(args,caller_thread_id=sender),meta=meta)
                        assert not answer.is_error,answer
                        return json.loads(answer.content[0].text)['result']
            surfaces=dict(cli=lambda verb,args:cli('flows',verb,args),api=api,oauth_mcp=lambda verb,args:api(verb,args,True),
                          remote_cli=remote,native_mcp=lambda verb,args:asyncio.run(native(verb,args)))
            receipts=[]
            for version,(surface,call) in enumerate(surfaces.items(),1):
                auto[0]=False
                call('publish',dict(definition=definition(version)))
                run=call('start',dict(flow_id='fixture',version=version,inputs={},intent='recovery-'+surface,binding='original-caller'))
                child=subprocess.Popen([sys.executable,'-m','codex_wake.cli','--wake-root',str(root),'flows','advance','--arguments',json.dumps(dict(run_id=run['run_id']))],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    state=cli('flows','inspect',dict(run_id=run['run_id']))
                    trace=state.get('condition_trace',[])
                    if len(trace)==3 and trace[-1].get('native_operation_id'):
                        operation=cli('flow-sessions','wait',dict(operation_id=trace[-1]['native_operation_id'],timeout=0))['operation']
                        if operation['phase']=='waiting':break
                    if child.poll() is not None:raise AssertionError(child.communicate())
                    time.sleep(.03)
                else:raise AssertionError('semantic child was not durably admitted')
                original_operation=trace[-1]['native_operation_id']
                assert state['condition_usage']==dict(calls=3,tokens=32),state
                if surface=='cli':
                    busy=call('reconcile',dict(run_id=run['run_id']))
                    assert busy['reason']=='condition_in_progress',busy
                child.kill();child.communicate(timeout=5);assert child.returncode==-9;child=None
                before=list(effects)
                pending=call('reconcile',dict(run_id=run['run_id']))
                assert pending['phase']=='uncertain' and pending['condition_usage']==dict(calls=3,tokens=32),pending
                assert effects==before,effects
                # Publication of a newer version never migrates an active run.
                call('publish',dict(definition=definition(version+100,short=True)))
                finish_turns()
                resumed=call('reconcile',dict(run_id=run['run_id']))
                assert resumed['phase']=='ready' and resumed['cursor']=='yes',resumed
                done=call('advance',dict(run_id=run['run_id']))
                assert done['phase']=='completed' and done['result'] is True and done['version']==version,done
                assert done['condition_usage']==dict(calls=3,tokens=32) and len(done['condition_trace'])==3,done
                assert done['condition_trace'][-1]['native_operation_id']==original_operation
                assert effects==before,effects
                assert call('reconcile',dict(run_id=run['run_id']))==done
                receipts.append(dict(surface=surface,flow_version=version,phase=done['phase'],usage=done['condition_usage'],
                    original_operation=original_operation,real_caller_sigkill=True,newer_version_did_not_migrate=True,effects_replayed=0))
            print(json.dumps(dict(status='passed',package=codex_wake.__file__,source_sha=os.environ.get('WAKE_ACCEPTANCE_SOURCE_SHA'),checks=receipts,
                original_principal_preserved=True,resource_renewals=0,governor_enrollments=0,
                boundary='deterministic disposable Python Unix protocol fixture; real caller process death and all five installed public surfaces; no model/provider call or native packaged capability claim'),sort_keys=True))
        finally:
            if child and child.poll() is None:child.kill();child.communicate(timeout=5)
            if http:http.shutdown();http.server_close();http_worker.join(timeout=2)
            server.shutdown();worker.join(timeout=2)


if __name__=='__main__':main()
