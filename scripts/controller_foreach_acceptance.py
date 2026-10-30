#!/usr/bin/env python3
"""Installed foreach acceptance against a disposable real Unix protocol server.

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
    with tempfile.TemporaryDirectory(prefix='wake-foreach407-') as directory:
        root=Path(directory);home=root/'homes/codex-alice';home.mkdir(parents=True)
        manifest=root/'builds.json'
        manifest.write_text(json.dumps(dict(schema_version=1,builds={'modded':dict(executable=str(Path(sys.executable).resolve()),
            sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),upstream_version='0.164.0+fixture',revision='protocol-fixture',source='disposable Python protocol fixture')})))
        (root/'controller-accounts.toml').write_text(f'''[profiles]\nstate_root="{root/'homes'}"\nknown_profiles=["alice"]\n[builds]\nmanifest="{manifest}"\n''')
        base=next(row['target'] for row in owner_from_root(root).execute('builds.list',dict(account='alice'))['builds'] if row['name']=='modded')
        threads={};effects=[];auto=[False]
        def handler(ws):
            for raw in ws:
                message=json.loads(raw)
                if 'id' not in message:continue
                method,params=message['method'],message.get('params',{})
                if method=='initialize':value=dict(codexHome=str(home))
                elif method=='thread/start':
                    identifier='fixture-thread-'+str(len(threads))
                    thread=dict(id=identifier,cwd=str(root),modelProvider='openai',turns=[])
                    threads[identifier]=thread;effects.append(('create',identifier));value=dict(thread=thread)
                elif method=='thread/read':value=dict(thread=threads[params['threadId']])
                elif method=='turn/start':
                    thread=threads[params['threadId']]
                    turn=dict(id='turn-'+str(len(thread['turns'])),status='completed' if auto[0] else 'inProgress',
                        items=[dict(type='agentMessage',text='answer:'+params['input'][0]['text'])])
                    thread['turns'].append(turn);effects.append(('prompt',thread['id'],params['input'][0]['text']));value=dict(turn=turn)
                elif method=='turn/interrupt':
                    turn=next(t for t in threads[params['threadId']]['turns'] if t['id']==params['turnId'])
                    turn['status']='interrupted';value={}
                else:raise AssertionError(method)
                ws.send(json.dumps(dict(id=message['id'],result=value)))
        endpoint=root/'native.sock';server=unix_serve(handler,str(endpoint))
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        native=process_identity(os.getpid())
        profile=dict(target=base,endpoint='unix://'+str(endpoint),process=dict(pid=os.getpid(),start_ticks=native['start_time_ticks'],boot_id=native['boot_id']),
            modes=['new_session','sequential'],cwd=str(root),native_provider='openai',methods=['thread/start','turn/start','thread/read','turn/interrupt'])
        path=root/'controller-flow-sessions.json';path.write_text(json.dumps(dict(version=1,profiles={'fixture':profile})));path.chmod(0o600)
        target=ControllerFlowSessions(root).target('fixture')
        flow_target=dict(host=socket.gethostname(),environment=os.environ.get('WSL_DISTRO_NAME') or os.name,flow_id='fixture')
        caller=dict(subject='fixture-author',client_id='fixture-client',grant_id='fixture-grant',issuer='local://fixture',resource='wake:controller',
            scopes=['observe','control'],targets=[base,flow_target],expires_at=time.time()+600)
        sender='11111111-1111-4111-8111-111111111111'
        path=root/'controller-messaging.json';path.write_text(json.dumps(dict(version=1,local_caller=caller,flow_callers={sender:dict(caller,grant_id='native-fixture')})));path.chmod(0o600)
        def cli(group,verb,args):
            value=subprocess.run([sys.executable,'-m','codex_wake.cli','--wake-root',str(root),group,verb,'--arguments',json.dumps(args)],text=True,capture_output=True)
            assert value.returncode==0,(value.stdout,value.stderr)
            return json.loads(value.stdout)['result']
        def definition(version,mode,pinned,items):
            return dict(id='fixture',version=version,entry='each',nodes=[dict(id='each',type='foreach',items={'ref':'inputs.members'},mode=mode,
                profile='fixture',expected_target=pinned,prompt={'ref':'item'},next='done'),dict(id='done',type='end',value={'ref':'steps.each'})])
        def finish_turns():
            for thread in threads.values():
                for turn in thread['turns']:
                    if turn['status']=='inProgress':turn['status']='completed'
        http=None;http_worker=None
        try:
            source=definition(1,'new_session',target,['one','two'])
            cli('flows','publish',dict(definition=source))
            run=cli('flows','start',dict(flow_id='fixture',version=1,inputs={'members':['one','two']},intent='new',binding='original-cli'))
            for unused in range(4):
                state=cli('flows','advance',dict(run_id=run['run_id']))
                if state['phase']=='completed':break
                assert state['phase']=='waiting',state
                finish_turns()
            assert state['phase']=='completed' and len(state['result']['items'])==2,state
            assert len(threads)==2 and len(effects)==4,effects
            assert cli('flows','advance',dict(run_id=run['run_id']))==state
            sequential_target=state['result']['items'][0]['target']
            auth=OAuthAuthority(root/'oauth.sqlite',issuer='https://wake.test',resource='https://wake.test/controller')
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
            api('publish',dict(definition=definition(2,'sequential',sequential_target,['three','four'])),True)
            path=root/'token';path.write_text(token);path.chmod(0o600)
            remote=subprocess.run([sys.executable,'-m','codex_wake.cli','controller','remote','--endpoint','http://127.0.0.1:'+str(http.server_port),
                '--token-file',str(path),'flows.start','--arguments',json.dumps(dict(flow_id='fixture',version=2,inputs={'members':['three','four']},intent='sequential',binding='original-oauth'))],text=True,capture_output=True)
            assert remote.returncode==0,(remote.stdout,remote.stderr)
            run=json.loads(remote.stdout)['result'];before=len(effects)
            state=api('advance',dict(run_id=run['run_id']))
            assert state['phase']=='waiting' and len(effects)==before+1,state
            for unused in range(3):
                finish_turns();state=api('advance',dict(run_id=run['run_id']),True)
                if state['phase']=='completed':break
            assert state['phase']=='completed' and len(threads)==2,state
            assert [e[1] for e in effects if e[0]=='prompt'][-2:]==[sequential_target['conversation_id']]*2
            auto[0]=True
            cli('flows','publish',dict(definition=definition(3,'new_session',target,['native'])))
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
                        started=await call('start',dict(flow_id='fixture',version=3,inputs={'members':['native']},intent='native',binding='native-origin'))
                        done=await call('advance',dict(run_id=started['run_id']))
                        assert done['phase']=='completed' and done['result']['items'][0]['result']['answer']['text']=='answer:native',done
            asyncio.run(native_mcp())
            print(json.dumps(dict(status='passed',package=codex_wake.__file__,checks=[
                'actual existing Unix socket with kernel peer PID/account/build pins','installed CLI new session per snapshotted member',
                'late native-shaped result across caller process exit with no resubmission','real OAuth API/MCP and remote CLI sequential prompts wait in same conversation',
                'actual stdio MCP inherited native grant starts structured foreach'],
                boundary='deterministic disposable Python protocol server; no actual model/provider call or packaged Codex qualification'),sort_keys=True))
        finally:
            if http:http.shutdown();http.server_close();http_worker.join(timeout=2)
            server.shutdown();worker.join(timeout=2)


if __name__=='__main__':main()
