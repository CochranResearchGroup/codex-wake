#!/usr/bin/env python3
"""Installed ACPv1-shaped fixture composition; no Grok/model/provider experiment.

Actual native metadata qualification is separate. This fixture speaks only the
observed/documented ACPv1 shapes and proves Wake custody, guards and adapters.
"""
import argparse,asyncio,base64,hashlib,json,os,socket,subprocess,sys,threading,time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs,urlsplit,urlencode
from urllib.request import Request,ProxyHandler,build_opener


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--bin-dir',type=Path,required=True);parser.add_argument('--artifacts',type=Path,required=True);args=parser.parse_args()
    import codex_wake
    from codex_wake.process import process_identity
    from websockets.sync.server import serve
    assert 'site-packages' in str(Path(codex_wake.__file__).resolve())
    root=args.artifacts.resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    wake=root/'wake';wake.mkdir();home=root/'home';home.mkdir();work=root/'work';work.mkdir()
    env={k:os.environ[k] for k in ('PATH','LANG') if k in os.environ};env.update(HOME=str(home),CODEX_HOME=str(home),XDG_CONFIG_HOME=str(root/'config'),XDG_STATE_HOME=str(root/'state'),XDG_DATA_HOME=str(root/'data'),XDG_CACHE_HOME=str(root/'cache'),NO_PROXY='127.0.0.1,localhost')
    state=dict(sessions={'existing':{}},effects=[],calls=[],generation='fixture-instance',load=True,permission_denied=0)
    hold=threading.Event();started=threading.Event();secret='fixture-controller-transport-only'
    def handler(ws):
        assert parse_qs(urlsplit(ws.request.path).query).get('server-key')==[secret]
        for raw in ws:
            request=json.loads(raw);method=request['method'];params=request.get('params') or {};identifier=request.get('id')
            state['calls'].append(method)
            if method=='initialize':value=dict(protocolVersion=1,agentCapabilities=dict(loadSession=state['load'],promptCapabilities=dict(image=True,audio=False,embeddedContext=True),sessionCapabilities=dict(list={},resume={},close={})),authMethods=[dict(id='grok.com',name='Grok')],_meta=dict(agentVersion='1.0.70',agentId='fixture-agent',agentInstanceId=state['generation'],currentWorkingDirectory=str(work)))
            elif method=='session/new':
                session='created-'+str(len(state['sessions']));state['sessions'][session]={};state['effects'].append(('create',session));value=dict(sessionId=session)
            elif method=='session/load':
                assert params['sessionId'] in state['sessions'];value={}
            elif method=='session/prompt':
                session=params['sessionId'];assert session in state['sessions'];text=params['prompt'][0]['text']
                if text=='refuse-auth':ws.send(json.dumps(dict(jsonrpc='2.0',id=identifier,error=dict(code=-32000,message='fixture ACP authentication required'))));continue
                state['effects'].append(('prompt',session,text,identifier))
                if text=='lose-reply':ws.close();return
                if text=='slow-final':started.set();assert hold.wait(15),'fixture bounded completion gate'
                if text=='permission-request':
                    ws.send(json.dumps(dict(jsonrpc='2.0',id=identifier,method='session/request_permission',params=dict(sessionId=session,toolCall=dict(toolCallId='fixture',title='fixture tool',kind='read',status='pending'),options=[]))))
                    response=json.loads(ws.recv(timeout=5));assert response['result']['outcome']['outcome']=='cancelled';state['permission_denied']+=1
                answer='{"value": true}' if text.startswith('fixture-semantic') else 'fixture-answer'
                for other,kind,content in (('unrelated-peer','agent_message_chunk','peer-must-not-leak'),(session,'agent_thought_chunk','reasoning-must-not-leak'),(session,'agent_message_chunk',answer)):
                    ws.send(json.dumps(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId=other,update=dict(sessionUpdate=kind,content=dict(type='text',text=content))))))
                if text=='error-after-progress':ws.send(json.dumps(dict(jsonrpc='2.0',id=identifier,error=dict(code=-32000,message='fixture error after work'))));continue
                value=dict(stopReason='cancelled' if text=='cancelled-final' else 'end_turn')
            else:raise AssertionError('unnegotiated fixture method '+method)
            ws.send(json.dumps(dict(jsonrpc='2.0',id=identifier,result=value)))
    native=serve(handler,'127.0.0.1',0);threading.Thread(target=native.serve_forever,daemon=True).start();native_port=native.socket.getsockname()[1]
    birth=process_identity(os.getpid());binary=Path(sys.executable).resolve()
    base_target=dict(host='fixture',environment='isolated-linux',runtime='grok',provider='grok',account='fixture',home=str(home),namespace='grok:fixture',
        build_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),backend_id='fixture-agent',channel='acp-websocket',connection_generation='fixture-instance',configuration_revision='fixture-v1',
        process_pid=str(os.getpid()),process_start_ticks=str(birth['start_time_ticks']),process_boot_id=birth['boot_id'])
    target=dict(base_target,conversation_id='existing')
    token_path=root/'native-transport.secret';token_path.write_text(secret);token_path.chmod(0o600)
    profile=dict(target=base_target,endpoint=f'ws://127.0.0.1:{native_port}/ws',secret_file=str(token_path),cwd=str(work),agent_version='1.0.70',timeout=15)
    path=wake/'controller-grok.json';path.write_text(json.dumps(dict(version=1,profiles={'fixture':profile})));path.chmod(0o600)
    flow_target=dict(host=socket.gethostname(),environment=os.name,flow_id='grok-fixture')
    condition=wake/'controller-conditions.json';condition.write_text(json.dumps(dict(version=1,functions={'truth@1':dict(kind='semantic',inputs={'text':'string'},profile='grok:fixture',expected_target=target,prompt='fixture-semantic',effects='action',tools='inherited',estimated_tokens=8)})));condition.chmod(0o600)
    cli=args.bin_dir.resolve()/'codex-wake'
    def command(*items):
        result=subprocess.run([str(cli),'--wake-root',str(wake),*items],cwd=work,env=env,capture_output=True,text=True,timeout=40)
        assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
        return json.loads(result.stdout)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close();url=f'http://127.0.0.1:{port}';resource=url+'/controller'
    command('controller','auth-configure','--issuer',url,'--resource',resource,'--owner','fixture-owner')
    log=(root/'controller.log').open('wb');server=subprocess.Popen([str(cli),'--wake-root',str(wake),'controller','serve','--port',str(port)],env=env,cwd=work,stdout=log,stderr=subprocess.STDOUT)
    opener=build_opener(ProxyHandler({}));proof={}
    def http(path,body=None,token=None,form=False):
        headers={}
        if token:headers['Authorization']='Bearer '+token
        if body is not None:headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json';body=(urlencode(body) if form else json.dumps(body)).encode()
        try:
            with opener.open(Request(url+path,data=body,headers=headers),timeout=35) as response:return response.status,json.loads(response.read())
        except HTTPError as error:return error.code,json.loads(error.read())
    try:
        deadline=time.monotonic()+20
        while True:
            try:
                if http('/.well-known/oauth-authorization-server')[0]==200:break
            except OSError:pass
            assert server.poll() is None and time.monotonic()<deadline;time.sleep(.05)
        client=http('/register',dict(redirect_uris=['http://127.0.0.1:45000/callback'],client_name='grok412-fixture'))[1]
        verifier='g'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        def token_for(scopes,targets):
            arguments=['controller','authorize-client','--client-id='+client['client_id'],'--redirect-uri',client['redirect_uris'][0],'--subject','fixture','--principal-kind','service','--targets',json.dumps(targets),'--code-challenge',challenge]
            for scope in scopes:arguments+=['--scope',scope]
            code=command(*arguments)['code'];status,value=http('/token',dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=resource),form=True);assert status==200,value
            return value['access_token']
        token=token_for(['observe','control'],[base_target,flow_target]);observer=token_for(['observe'],[base_target]);broad=token_for(['observe','control'],[dict(host='fixture',environment='isolated-linux')])
        caller=dict(subject='host-fixture',client_id='host-local',grant_id='host-local',issuer=url,resource=resource,scopes=['observe','control'],targets=[base_target,flow_target],expires_at=time.time()+600)
        sender='11111111-1111-4111-8111-111111111111';path=wake/'controller-messaging.json';path.write_text(json.dumps(dict(version=1,local_caller=caller,flow_callers={sender:dict(caller,grant_id='native-flow-fixture')})));path.chmod(0o600)
        oauth_file=root/'oauth.token';oauth_file.write_text(token);oauth_file.chmod(0o600)
        def direct(operation,arguments):
            status,value=http('/operations',dict(operation=operation,arguments=arguments),token);assert status==200,value;return value
        def oauth_mcp(operation,arguments):
            group,verb=operation.split('.');name='wake_flows_'+verb if group=='flows' else 'wake_controller_grok_'+verb
            status,value=http('/mcp',dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name=name,arguments=arguments)),token);assert status==200,value;assert not value['result'].get('isError'),value
            return value['result']['structuredContent']
        async def native_mcp(operation,arguments):
            from mcp import ClientSession,StdioServerParameters
            from mcp.client.stdio import stdio_client
            from mcp.types import RequestParamsMeta
            group,verb=operation.split('.');name='wake_flows_'+verb if group=='flows' else 'wake_controller_grok_'+verb
            meta=None
            if group=='flows':
                arguments=dict(arguments,caller_thread_id=sender);meta=RequestParamsMeta(**dict(threadId=sender,sessionId=sender,callId='fixture-call',**{'x-codex-turn-metadata':dict(thread_id=sender,session_id=sender,turn_id='fixture-turn')}))
            parameters=StdioServerParameters(command=str(args.bin_dir.resolve()/'codex-wake-mcp'),args=['--wake-root',str(wake)],env=env)
            async with stdio_client(parameters) as (reader,writer):
                async with ClientSession(reader,writer) as session:
                    await session.initialize();value=await session.call_tool(name,arguments,meta=meta);assert not value.is_error,value
                    return json.loads(value.content[0].text)
        drivers={'cli':lambda operation,arguments:command(operation.split('.')[0],operation.split('.')[1],'--arguments',json.dumps(arguments)),
            'api':direct,'oauth_mcp':oauth_mcp,'remote_cli':lambda operation,arguments:command('controller','remote','--endpoint',url,'--token-file',str(oauth_file),operation,'--arguments',json.dumps(arguments)),
            'native_mcp':lambda operation,arguments:asyncio.run(native_mcp(operation,arguments))}
        def request(name,prompt='fixture'):
            return dict(profile='fixture',expected_target=target,prompt=prompt,_request=dict(operation_id=name,idempotency_key=name,correlation_id=name,binding='fixture',target=target))
        def flow(version,mode):
            if mode=='semantic':return dict(id='grok-fixture',version=version,entry='predicate',limits=dict(max_calls=2,max_depth=2,max_seconds=20,max_tokens=8,metering='estimate_opt_in'),nodes=[dict(id='predicate',type='branch',condition=dict(function='truth',version=1,arguments={'text':'fixture'}),then='yes',**{'else':'no'}),dict(id='yes',type='end',value=True),dict(id='no',type='end',value=False)])
            return dict(id='grok-fixture',version=version,entry='each',nodes=[dict(id='each',type='foreach',items=['one','two'],mode=mode,profile='grok:fixture',expected_target=base_target if mode=='new_session' else target,prompt={'ref':'item'},parallelism=1,next='done'),dict(id='done',type='end',value={'ref':'steps.each'})])
        outcomes={};version=0
        for name,driver in drivers.items():
            caps=driver('grok.capabilities',dict(profile='fixture',expected_target=base_target))['result'];assert caps['protocol_version']==1 and caps['capabilities']['fork']['status']=='unsupported' and caps['native_identity']['agent_instance_id']=='fixture-instance' and caps['target']==base_target and caps['authority']['native_account_verified'] is False
            before=len(state['effects']);first=driver('grok.prompt',request('prompt-'+name));result=first['result']['operation'];assert result['phase']=='terminal' and result['answer']['text']=='fixture-answer',first
            driver('grok.prompt',request('prompt-'+name));assert len(state['effects'])==before+1
            waited=driver('grok.wait',dict(operation_id='prompt-'+name,timeout=0));assert waited['result']['operation']['answer']['text']=='fixture-answer'
            health=driver('grok.health',dict(profile='fixture',expected_target=base_target));assert health['result']['status']=='unsupported' and health['result']['responsive'] is False
            modes={}
            for mode in ('new_session','sequential','semantic'):
                version+=1;driver('flows.publish',dict(definition=flow(version,mode)))
                started_run=driver('flows.start',dict(flow_id='grok-fixture',version=version,inputs={},intent=name+'-'+mode,binding='fixture-'+name))['result']
                state_run=driver('flows.advance',dict(run_id=started_run['run_id']))['result']
                assert state_run['phase']=='completed',state_run
                if mode=='semantic':assert state_run['result'] is True and state_run['condition_usage']==dict(calls=1,tokens=8),state_run
                else:
                    items=state_run['result']['items'];assert len(items)==2 and all(row['result']['answer']['text']=='fixture-answer' for row in items),state_run
                    if mode=='new_session':assert items[0]['result']['target']['conversation_id']!=items[1]['result']['target']['conversation_id']
                    else:assert all(row['result']['target']['conversation_id']=='existing' for row in items)
                modes[mode]='passed'
            outcomes[name]=dict(prompt='retained',idempotent=True,health='unsupported',flow_modes=modes)
        # Definite native authentication refusal is not an uncertain submission.
        refused=direct('grok.prompt',request('auth-refusal','refuse-auth'))['result']['operation'];assert refused['execution']=='not_started' and refused['reason']=='native_auth_required'
        unknown=direct('grok.prompt',request('lost','lose-reply'))['result']['operation'];assert unknown['phase']=='uncertain'
        count=len(state['effects']);direct('grok.prompt',request('lost','lose-reply'));assert len(state['effects'])==count
        calls=len(state['calls']);cancel=direct('grok.cancel',dict(operation_id='lost'));assert cancel['result']['operation']['cancellation']=='uncertain' and len(state['calls'])==calls
        partial=direct('grok.prompt',request('partial','error-after-progress'))['result']['operation'];assert partial['phase']=='uncertain' and partial['execution']=='unknown'
        approved=direct('grok.prompt',request('permission','permission-request'))['result']['operation'];assert approved['answer']['text']=='fixture-answer' and state['permission_denied']==1
        cancelled=direct('grok.prompt',request('cancelled','cancelled-final'))['result']['operation'];assert cancelled['execution']=='cancelled'
        before=len(state['effects']);assert http('/operations',dict(operation='grok.prompt',arguments=request('observer-denied')),observer)[0]==403
        assert http('/operations',dict(operation='grok.capabilities',arguments=dict(profile='fixture',expected_target=base_target)),broad)[0]==403
        state['generation']='replacement';assert http('/operations',dict(operation='grok.prompt',arguments=request('stale')),token)[0]==400;state['generation']='fixture-instance';assert len(state['effects'])==before
        state['load']=False
        load=dict(profile='fixture',expected_target=target,_request=request('unsupported-load')['_request'])
        assert http('/operations',dict(operation='grok.load',arguments=load),token)[0]==400;state['load']=True
        # Caller closes HTTP connection; original bounded host request still owns
        # native receipt custody and must persist its final answer before delivery.
        body=json.dumps(dict(operation='grok.prompt',arguments=request('disconnected','slow-final'))).encode()
        connection=socket.create_connection(('127.0.0.1',port));packet=b'POST /operations HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer '+token.encode()+b'\r\nContent-Type: application/json\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body;connection.sendall(packet);connection.close()
        assert started.wait(5);hold.set();deadline=time.monotonic()+10
        while True:
            retained=direct('grok.wait',dict(operation_id='disconnected',timeout=0))['result']['operation']
            if retained['phase']=='terminal':break
            assert time.monotonic()<deadline;time.sleep(.05)
        assert retained['answer']['text']=='fixture-answer'
        assert http('/revoke',dict(token=token,client_id=client['client_id']),form=True)[0]==200
        assert http('/operations',dict(operation='grok.wait',arguments=dict(operation_id='disconnected',timeout=0)),token)[0]==401
        assert 'session/cancel' not in state['calls'] and not (wake/'runtime-bindings').exists() and not (wake/'goal-supervision').exists()
        proof.update(status='passed',qualification='installed ACPv1-shaped protocol fixture; not native Grok/model acceptance',frontdoors=outcomes,
            definitive_auth_refusal=True,unknown_no_replay=True,exact_turn_cancel_unsupported_no_io=True,partial_error_not_mislabeled_not_started=True,
            permission_denied_without_client_capability=True,caller_disconnect_retained=True,cancelled_final_classified=True,broad_observer_stale_revoked_denied=True,
            native_request_count=len(state['calls']),effect_count=len(state['effects']),no_terminal_fallback=True,no_resources_or_governor=True,
            hashes={name:hashlib.sha256((Path(codex_wake.__file__).parent/name).read_bytes()).hexdigest() for name in ('controller_grok.py','controller_grok_sessions.py','grok_acp.py','grok_commands.py','controller_runtime.py','controller_flow_sessions.py','controller_http.py','mcp_server.py','cli.py')})
    finally:
        hold.set();server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
        log.close();native.shutdown();proof['owned_controller_exited']=server.poll() is not None
        (root/'receipt.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    print(json.dumps(proof,sort_keys=True))


if __name__=='__main__':main()
