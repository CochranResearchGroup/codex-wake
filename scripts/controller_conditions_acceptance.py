#!/usr/bin/env python3
"""Installed typed condition acceptance against a disposable real Unix protocol server.

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
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--join-and-retry',action='store_true')
    options=parser.parse_args()
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
                    turn=dict(id='turn-'+str(len(thread['turns'])),status=('failed' if params['input'][0]['text'] in failed_prompts else 'completed') if auto[0] else 'inProgress',
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
            return dict(id='fixture',version=version,entry='condition',limits=dict(max_calls=8,max_depth=4,max_seconds=30,max_tokens=64,metering='estimate_opt_in'),nodes=[
                dict(id='condition',type='branch',condition=condition,then='yes',**{'else':'no'}),
                dict(id='yes',type='end',value=True),dict(id='no',type='end',value=False)])
        def finish_turns():
            for thread in threads.values():
                for turn in thread['turns']:
                    if turn['status']=='inProgress':turn['status']='completed'
        http=None;http_worker=None
        try:
            cli('flows','publish',dict(definition=definition(1)))
            run=cli('flows','start',dict(flow_id='fixture',version=1,inputs={},intent='one',binding='original-cli'))
            state=cli('flows','advance',dict(run_id=run['run_id']))
            assert state['phase']=='completed' and state['result'] is True,state
            assert state['condition_usage']==dict(calls=3,tokens=32),state
            assert state['condition_trace'][-1]['metering']=='estimate_opt_in'
            assert cli('flows','advance',dict(run_id=run['run_id']))==state
            assert len(effects)==2,effects
            auth=OAuthAuthority(root/'oauth.sqlite',issuer='https://wake.test',resource='https://wake.test/controller',on_revoke=__import__('codex_wake.operation_commands',fromlist=['owner']).owner(root).revoke_grant)
            client=auth.register(dict(redirect_uris=['http://localhost/callback']))
            verifier='v'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            code=auth.authorize(subject='service',principal_kind='service',client_id=client['client_id'],redirect_uri='http://localhost/callback',resource=auth.resource,
                scopes=['observe','control'],targets=[base,flow_target],code_challenge=challenge)
            token=auth.token(dict(grant_type='authorization_code',code=code,client_id=client['client_id'],redirect_uri='http://localhost/callback',resource=auth.resource,code_verifier=verifier))['access_token']
            http=ControllerHTTPServer(('127.0.0.1',0),auth,ControllerOperations(ManagedInventory(root),host=flow_target['host'],environment=flow_target['environment']))
            http_worker=threading.Thread(target=http.serve_forever,daemon=True);http_worker.start()
            def api(verb,args,mcp=False):
                body=dict(operation='flows.'+verb,arguments=args)
                if mcp:body=dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='wake_flows_'+verb,arguments=args))
                req=Request('http://127.0.0.1:'+str(http.server_port)+('/mcp' if mcp else '/operations'),data=json.dumps(body).encode(),
                    headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
                with urlopen(req) as response:value=json.load(response)
                return value['result']['structuredContent']['result'] if mcp else value['result']
            api('publish',dict(definition=definition(2)),True)
            path=root/'token';path.write_text(token);path.chmod(0o600)
            remote=subprocess.run([sys.executable,'-m','codex_wake.cli','controller','remote','--endpoint','http://127.0.0.1:'+str(http.server_port),
                '--token-file',str(path),'flows.start','--arguments',json.dumps(dict(flow_id='fixture',version=2,inputs={},intent='sequential',binding='original-oauth'))],text=True,capture_output=True)
            assert remote.returncode==0,(remote.stdout,remote.stderr)
            run=json.loads(remote.stdout)['result'];before=len(effects)
            state=api('advance',dict(run_id=run['run_id']))
            assert state['phase']=='completed' and state['result'] is True and len(effects)==before+2,state
            assert state['condition_usage']==dict(calls=3,tokens=32)
            cli('flows','publish',dict(definition=definition(3,short=True)))
            async def native_mcp():
                from mcp import ClientSession,StdioServerParameters
                from mcp.client.stdio import stdio_client
                parameters=StdioServerParameters(command=str(Path(sys.executable).parent/'codex-wake-mcp'),args=['--wake-root',str(root)],
                    env={key:value for key,value in os.environ.items() if key!='PYTHONPATH'})
                meta=dict(threadId=sender,sessionId=sender,callId='foreach',**{'x-codex-turn-metadata':dict(thread_id=sender,session_id=sender,turn_id='fixture')})
                async with stdio_client(parameters) as (reader,writer):
                    async with ClientSession(reader,writer) as session:
                        await session.initialize()
                        async def call(verb,args):
                            answer=await session.call_tool('wake_flows_'+verb,dict(args,caller_thread_id=sender),meta=meta)
                            assert not answer.is_error,answer
                            return json.loads(answer.content[0].text)['result']
                        started=await call('start',dict(flow_id='fixture',version=3,inputs={},intent='native',binding='native-origin'))
                        done=await call('advance',dict(run_id=started['run_id']))
                        assert done['phase']=='completed' and done['result'] is False,done
                        assert done['steps']['condition']['trace'][1]['status']=='unevaluated',done
            asyncio.run(native_mcp())
            print(json.dumps(dict(status='passed',package=codex_wake.__file__,checks=[
                'actual existing Unix socket with kernel peer PID/account/build pins','installed CLI typed deterministic and existing native turn predicate with explicit inherited action',
                'condition accounting and result persist across caller process exit without re-evaluation','real OAuth API/MCP and remote CLI preserve cumulative conservative token estimates',
                'actual stdio MCP inherited grant short-circuits unevaluated semantic predicate'],
                boundary='deterministic disposable Python protocol server; no actual model/provider call or packaged Codex qualification'),sort_keys=True))
        finally:
            if http:http.shutdown();http.server_close();http_worker.join(timeout=2)
            server.shutdown();worker.join(timeout=2)


if __name__=='__main__':main()
