#!/usr/bin/env python3
"""Installed all-interface policy composition against an owned Unix RPC fixture.

The fixture is not native TUI-loop proof. #390 and #403 retain that separate
native qualification. This run qualifies policy persistence, original authority,
scoped-refresh composition, deactivation and uncertain notice readback only.
"""
import argparse
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request,ProxyHandler,build_opener


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--bin-dir',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,required=True)
    args=parser.parse_args()
    import codex_wake
    from codex_wake.controller_notices import flat_target
    from codex_wake.process import process_identity
    from websockets.sync.server import unix_serve
    assert 'site-packages' in str(Path(codex_wake.__file__).resolve())
    artifacts=args.artifacts.resolve();artifacts.mkdir(mode=0o700,parents=True,exist_ok=False)
    wake=artifacts/'wake';wake.mkdir();home=artifacts/'home';home.mkdir();work=artifacts/'work';work.mkdir()
    env={key:os.environ[key] for key in ('PATH','LANG') if key in os.environ}
    env.update(HOME=str(home),CODEX_HOME=str(home),XDG_CONFIG_HOME=str(artifacts/'config'),XDG_DATA_HOME=str(artifacts/'data'),XDG_STATE_HOME=str(artifacts/'state'),XDG_CACHE_HOME=str(artifacts/'cache'),NO_PROXY='127.0.0.1,localhost')
    binary=Path(sys.executable).resolve();image=hashlib.sha256(binary.read_bytes()).hexdigest();birth=process_identity(os.getpid())
    native_endpoint='unix://'+str(artifacts/'native.sock')
    fixture=dict(calls=[],notices={},reloads=0,lose_notice=False)
    def handler(ws):
        for raw in ws:
            request=json.loads(raw)
            if 'id' not in request:continue
            method=request['method'];params=request.get('params') or {}
            fixture['calls'].append(dict(method=method,params=params))
            if method=='initialize':value=dict(codexHome=str(home),userAgent='synthetic-recovery404-fixture')
            elif method=='tui/health/probe':value=dict(state='unknown',reason='fixture_loop_stalled_background_rpc_alive')
            elif method=='thread/notice/append':
                assert len(params['text'].encode())<=768 and params['text'].endswith('[External supervision event '+params['eventId']+']')
                fixture['notices'][params['eventId']]=dict(eventId=params['eventId'],text=params['text'])
                if fixture['lose_notice']:
                    fixture['lose_notice']=False;ws.close();return
                value=dict(eventId=params['eventId'],recorded=True,modelContextAvailable=True,notificationPublished=True)
            elif method=='thread/notice/read':value=dict(notice=fixture['notices'].get(params['eventId']),modelContextAvailable=True)
            elif method=='thread/read':value=dict(thread=dict(id='fixture-thread',cwd=str(work),modelProvider='fixture',status=dict(type='idle')))
            elif method=='thread/goal/get':value={'goal':None}
            elif method=='thread/mcpServer/reload':
                if not params.get('dryRun'):fixture['reloads']+=1
                value=dict(threadId='fixture-thread',queued=not params.get('dryRun',False))
            elif method=='mcpServerStatus/list':value=dict(data=[dict(name='fixture',serverInfo=dict(version='1'),tools=dict(ping=dict(inputSchema=dict(properties={}))))])
            else:raise AssertionError('unexpected fixture RPC '+method)
            ws.send(json.dumps(dict(id=request['id'],result=value)))
    fixture_server=unix_serve(handler,path=native_endpoint[7:]);threading.Thread(target=fixture_server.serve_forever,daemon=True).start()
    raw=dict(host='fixture',environment='isolated-linux',runtime='codex',namespace='codex:'+hashlib.sha256(json.dumps([str(home),'fixture'],separators=(',',':')).encode()).hexdigest(),
        build_sha256=image,conversation_id='fixture-thread',home=str(home),provider='fixture',backend_id='fixture-daemon',channel='tui',connection_generation='fixture-connection',
        process=dict(pid=os.getpid(),start_ticks=str(birth['start_time_ticks']),boot_id=birth['boot_id']))
    target=flat_target(raw)
    binding=wake/'controller-health.json';binding.write_text(json.dumps(dict(version=1,bindings=[dict(target=raw,endpoint=native_endpoint,codex_cmd=[str(binary)])])));binding.chmod(0o600)
    profile=dict(refresh_mode='thread_mcp_idle',scope_approval='owned fixture policy',cwd=str(work),app_server=native_endpoint,codex_path=str(binary),timeout=1,
        resources=dict(catalog=dict(kind='mcp_catalog',server='fixture',version='1',tools={'ping':[]})))
    registry=wake/'controller-recovery.json';registry.write_text(json.dumps(dict(version=1,profiles={'fixture':dict(target=target,refresh=profile)})));registry.chmod(0o600)
    cli=args.bin_dir.resolve()/'codex-wake'
    def command(*items):
        result=subprocess.run([str(cli),'--wake-root',str(wake),*items],cwd=work,env=env,capture_output=True,text=True,timeout=30)
        assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
        return json.loads(result.stdout)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    base=f'http://127.0.0.1:{port}';resource=base+'/controller'
    command('controller','auth-configure','--issuer',base,'--resource',resource,'--owner','recovery-fixture-owner')
    log=(artifacts/'controller.log').open('wb')
    server=subprocess.Popen([str(cli),'--wake-root',str(wake),'controller','serve','--port',str(port)],env=env,cwd=work,stdout=log,stderr=subprocess.STDOUT)
    opener=build_opener(ProxyHandler({}));proof={}
    def http(path,body=None,token=None,form=False):
        headers={}
        if token:headers['Authorization']='Bearer '+token
        if body is not None:
            headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json';body=(urlencode(body) if form else json.dumps(body)).encode()
        try:
            with opener.open(Request(base+path,data=body,headers=headers),timeout=20) as response:return response.status,json.loads(response.read())
        except HTTPError as error:return error.code,json.loads(error.read())
    try:
        deadline=time.monotonic()+15
        while True:
            try:
                if http('/.well-known/oauth-authorization-server')[0]==200:break
            except OSError:pass
            assert server.poll() is None and time.monotonic()<deadline,'private controller readiness'
            time.sleep(.05)
        client=http('/register',dict(redirect_uris=['http://127.0.0.1:45000/callback'],client_name='recovery404-fixture'))[1]
        verifier='r'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        def token_for(scopes,targets):
            arguments=['controller','authorize-client','--client-id='+client['client_id'],'--redirect-uri',client['redirect_uris'][0],'--subject','fixture','--principal-kind','service','--targets',json.dumps(targets),'--code-challenge',challenge]
            for scope in scopes:arguments+=['--scope',scope]
            code=command(*arguments)['code']
            status,value=http('/token',dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=resource),form=True)
            assert status==200,value
            return value['access_token']
        token=token_for(['observe','recovery'],[target]);observer=token_for(['observe'],[target]);broad=token_for(['observe','recovery'],[dict(host=target['host'],environment=target['environment'])])
        caller=dict(subject='fixture',client_id='host-local',grant_id='host-local',issuer=base,resource=resource,scopes=['observe','recovery'],targets=[target],expires_at=time.time()+600)
        path=wake/'controller-messaging.json';path.write_text(json.dumps(dict(version=1,host=target['host'],environment=target['environment'],bindings={},local_caller=caller)));path.chmod(0o600)
        token_file=artifacts/'oauth.token';token_file.write_text(token);token_file.chmod(0o600)
        def direct(verb,arguments):
            status,value=http('/operations',dict(operation='recovery.'+verb,arguments=arguments),token)
            assert status==200,value
            return value
        def oauth_mcp(verb,arguments):
            status,value=http('/mcp',dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='wake_controller_recovery_'+verb,arguments=arguments)),token)
            assert status==200,value
            return value['result']['structuredContent']
        async def native(verb,arguments):
            from mcp import ClientSession,StdioServerParameters
            from mcp.client.stdio import stdio_client
            parameters=StdioServerParameters(command=str(args.bin_dir.resolve()/'codex-wake-mcp'),args=['--wake-root',str(wake)],env=env)
            async with stdio_client(parameters) as (reader,writer):
                async with ClientSession(reader,writer) as session:
                    await session.initialize();result=await session.call_tool('wake_controller_recovery_'+verb,arguments)
                    assert not result.is_error,result
                    return json.loads(result.content[0].text)
        drivers={'cli':lambda verb,arguments:command('recovery',verb,'--arguments',json.dumps(arguments)),
            'api':direct,'oauth_mcp':oauth_mcp,
            'remote_cli':lambda verb,arguments:command('controller','remote','--endpoint',base,'--token-file',str(token_file),'recovery.'+verb,'--arguments',json.dumps(arguments)),
            'native_mcp':lambda verb,arguments:asyncio.run(native(verb,arguments))}
        def request(policy_id,step,**extra):
            key=policy_id+'-'+step
            return dict(policy_id=policy_id,expected_target=target,_request=dict(operation_id=key,idempotency_key=key,correlation_id=key,binding='fixture',target=target),**extra)
        declaration=dict(interval_seconds=1,probe_timeout=1,unknown_threshold=2,cooldown_seconds=1,max_attempts=1,evidence='suspected_unresponsive',actions=[dict(kind='thread_mcp_refresh',profile='fixture')])
        outcomes={}
        for name,driver in drivers.items():
            configured=driver('configure',request(name,'configure',policy=declaration))
            assert configured['result']['operation']['result']['mode']=='observe'
            driver('check',request(name,'check1'));driver('check',request(name,'check2'))
            state=driver('show',dict(policy_id=name,expected_target=target))['result']['policy']
            assert state['health_status']=='suspected_unresponsive' and state['attempts']==0
            before=fixture['reloads']
            activated=driver('enable',request(name,'enable'));assert activated['result']['notification']['status']=='recorded',activated
            # No public tick/apply: the already-running controller's maintenance
            # loop must drive the enabled original policy under retained authority.
            deadline=time.monotonic()+25
            while True:
                state=driver('show',dict(policy_id=name,expected_target=target))['result']['policy']
                if state['attempts']==1 and state['in_flight'] is None and state['action_status'] in ('completed','exhausted'):break
                assert time.monotonic()<deadline,('scheduled action did not complete',name,state)
                time.sleep(.1)
            assert fixture['reloads']==before+1
            driver('enable',request(name,'enable'));assert fixture['reloads']==before+1
            disabled=driver('disable',request(name,'disable'));assert disabled['result']['operation']['result']['mode']=='off'
            baseline=driver('show',dict(policy_id=name,expected_target=target))['result']['policy']['checks']
            deadline=time.monotonic()+15
            while True:
                after=driver('show',dict(policy_id=name,expected_target=target))['result']['policy']
                if after['checks']>baseline:break
                assert time.monotonic()<deadline,('deactivation lost authorized scheduled observation',name,after)
                time.sleep(.1)
            assert after['mode']=='off' and after['attempts']==1
            assert fixture['reloads']==before+1
            outcomes[name]=dict(mode=after['mode'],checks=after['checks'],attempts=after['attempts'],native_scope='thread_mcp_connections',replayed=False)
        # Lost activation notice acknowledgement must hold automatic work until readback.
        direct('configure',request('lost','configure',policy=declaration));fixture['lose_notice']=True
        pending=direct('enable',request('lost','enable'));assert pending['result']['notification']['status']=='uncertain'
        assert direct('show',dict(policy_id='lost',expected_target=target))['result']['policy']['mode']=='activation_pending'
        appends=sum(row['method']=='thread/notice/append' for row in fixture['calls'])
        reconciled=direct('reconcile',dict(policy_id='lost',expected_target=target))
        assert reconciled['result']['policy']['mode']=='automatic'
        assert sum(row['method']=='thread/notice/append' for row in fixture['calls'])==appends
        direct('disable',request('lost','disable'))
        assert http('/operations',dict(operation='recovery.enable',arguments=request('api','observer-enable')),observer)[0]==403
        assert http('/operations',dict(operation='recovery.list',arguments=dict(expected_target=target)),broad)[0]==403
        assert http('/revoke',dict(token=token,client_id=client['client_id']),form=True)[0]==200
        assert http('/operations',dict(operation='recovery.list',arguments=dict(expected_target=target)),token)[0]==401
        assert not any(row['method'] in ('config/mcpServer/reload','thread/goal/set','turn/start') for row in fixture['calls'])
        assert not (wake/'goal-supervision').exists()
        proof.update(status='passed',qualification='installed owned Unix protocol fixture composition; not native TUI or platform acceptance',frontdoors=outcomes,
            scheduled_without_public_tick=True,authorized_observation_continues_after_off=True,lost_activation_notice_readback_no_reappend=True,observer_denied=True,broad_denied=True,revoked_denied=True,
            exact_thread_reload_count=fixture['reloads'],no_shared_restart=True,no_goal_change=True,no_model_turn=True,no_resource_renewal=True,
            hashes={name:hashlib.sha256((Path(codex_wake.__file__).parent/name).read_bytes()).hexdigest() for name in ('controller_recovery.py','recovery_commands.py','scoped_refresh.py','shared_refresh.py','controller_notices.py','controller_runtime.py','controller_http.py','cli.py','mcp_server.py')})
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
        log.close();fixture_server.shutdown()
        proof['owned_controller_exited']=server.poll() is not None
        (artifacts/'receipt.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    print(json.dumps(proof,sort_keys=True))


if __name__=='__main__':main()
