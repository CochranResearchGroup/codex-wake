#!/usr/bin/env python3
"""Installed controller notices through five frontdoors and an owned native TUI.

Only disposable synthetic state is used. No model turn, goal or allowance is
created. Network proxy traps reject startup catalog traffic without forwarding.
"""
import argparse
import asyncio
import base64
import hashlib
import http.server as http_server
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, ProxyHandler, build_opener


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--bin-dir',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,required=True)
    args = parser.parse_args()
    import codex_wake
    from codex_wake.controller_auth import Actor
    from codex_wake.controller_runtime import ControllerRuntime
    from codex_wake.controller_notices import flat_target
    from codex_wake.native_protocol import native_request
    from codex_wake.process import process_identity
    assert 'site-packages' in str(Path(codex_wake.__file__).resolve())
    root = args.artifacts.resolve(); root.mkdir(mode=0o700,parents=True,exist_ok=False)
    home=root/'home';home.mkdir();work=root/'work';work.mkdir();wake=root/'wake';wake.mkdir()
    binary=args.package.resolve()/'bin/codex'; digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    cli=args.bin_dir.resolve()/'codex-wake'
    traffic=[]
    class Trap(http_server.BaseHTTPRequestHandler):
        def reject(self):
            traffic.append(self.command+' '+self.path);self.send_response(503);self.end_headers()
        do_GET=do_POST=do_CONNECT=reject
        def log_message(self,*unused): pass
    trap=http_server.ThreadingHTTPServer(('127.0.0.1',0),Trap)
    threading.Thread(target=trap.serve_forever,daemon=True).start()
    proxy='http://127.0.0.1:'+str(trap.server_port)
    (home/'config.toml').write_text(f'''model = "mock-model"
model_provider = "notice_fixture"
check_for_update_on_startup = false
[analytics]
enabled = false
[model_providers.notice_fixture]
name = "Owned controller notice fixture"
base_url = "{proxy}/never-model"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 0
stream_max_retries = 0
[projects.{json.dumps(str(work))}]
trust_level = "trusted"
''')
    env={k:os.environ[k] for k in ('PATH','LANG','LD_LIBRARY_PATH') if k in os.environ}
    env.update(HOME=str(home),CODEX_HOME=str(home),XDG_CONFIG_HOME=str(root/'config'),
        XDG_STATE_HOME=str(root/'state'),XDG_DATA_HOME=str(root/'data'),XDG_CACHE_HOME=str(root/'cache'),
        HTTPS_PROXY=proxy,HTTP_PROXY=proxy,ALL_PROXY=proxy,NO_PROXY='127.0.0.1,localhost',TERM='xterm-256color')
    endpoint='unix://'+str(root/'native.sock'); log=(root/'native.log').open('wb')
    native=subprocess.Popen([str(binary),'app-server','--listen',endpoint],env=env,cwd=work,stdout=log,stderr=subprocess.STDOUT)
    controller=None;controller_log=None;tmux_name='controller403-'+str(os.getpid());proof={}
    def tmux(*items,check=True):
        return subprocess.run(['tmux','-L',tmux_name,*items],capture_output=True,text=True,timeout=10,check=check)
    def wait_for(call,timeout=25):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            value=call()
            if value:return value
            assert native.poll() is None,'private native exited'
            time.sleep(.1)
        raise TimeoutError('private acceptance deadline')
    def run(*items):
        result=subprocess.run([str(cli),'--wake-root',str(wake),*items],env=env,cwd=work,capture_output=True,text=True,timeout=30)
        assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
        return json.loads(result.stdout)
    def rpc(method,**params):return native_request(endpoint,[str(binary)],method,params,10)
    try:
        wait_for(lambda:Path(endpoint[7:]).exists())
        endpoint='unix://'+str(Path(endpoint[7:]).resolve())
        thread=rpc('thread/start',cwd=str(work))['thread']['id']
        # No goal setter or governor enrollment; an ordinary synthetic empty thread.
        rpc('thread/notice/read',threadId=thread,eventId='controller_setup_probe')
        before=rpc('thread/read',threadId=thread,includeTurns=True)['thread']['turns']
        command='exec '+shlex.join(['env','CODEX_HOME='+str(home),'TERM=xterm-256color',str(binary),'--remote',endpoint,'--no-alt-screen','resume',thread])
        tmux('new-session','-d','-s','notice','-x','180','-y','55',command)
        tmux('set-option','-g','exit-empty','off')
        def capture():return tmux('capture-pane','-t','notice:0.0','-p','-S','-400',check=False).stdout
        wait_for(lambda:'context left' in capture() or 'mock-model' in capture())
        pid=int(tmux('display-message','-p','-t','notice:0.0','#{pane_pid}').stdout.strip())
        birth=process_identity(pid);assert birth
        raw=dict(host='fixture',environment='private-linux',runtime='codex',namespace='notice-fixture',
            build_sha256=digest,conversation_id=thread,home=str(home),provider='notice_fixture',
            backend_id='private-native',channel='tui',connection_generation='owned-fixture',
            process=dict(pid=pid,start_ticks=str(birth['start_time_ticks']),boot_id=birth['boot_id']))
        target=flat_target(raw)
        registry=wake/'controller-health.json';registry.write_text(json.dumps(dict(version=1,bindings=[dict(target=raw,endpoint=endpoint,codex_cmd=[str(binary)])])));registry.chmod(0o600)
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        base=f'http://127.0.0.1:{port}';resource=base+'/controller'
        run('controller','auth-configure','--issuer',base,'--resource',resource,'--owner','fixture-owner')
        controller_log=(root/'controller.log').open('wb')
        controller=subprocess.Popen([str(cli),'--wake-root',str(wake),'controller','serve','--port',str(port)],env=env,cwd=work,stdout=controller_log,stderr=subprocess.STDOUT)
        opener=build_opener(ProxyHandler({}))
        def http(path,body=None,token=None,form=False):
            headers={}
            if token:headers['Authorization']='Bearer '+token
            if body is not None:
                headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
                body=(urlencode(body) if form else json.dumps(body)).encode()
            try:
                with opener.open(Request(base+path,data=body,headers=headers),timeout=15) as response:return response.status,json.loads(response.read())
            except HTTPError as error:return error.code,json.loads(error.read())
        def ready():
            try:return http('/.well-known/oauth-authorization-server')[0]==200
            except OSError:return False
        wait_for(ready)
        client=http('/register',dict(redirect_uris=['http://127.0.0.1:45000/callback'],client_name='notice-fixture'))[1]
        verifier='n'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        def token_for(targets):
            code=run('controller','authorize-client','--client-id='+client['client_id'],'--redirect-uri',client['redirect_uris'][0],
                '--subject','fixture','--principal-kind','service','--scope','observe','--scope','control','--targets',json.dumps(targets),'--code-challenge',challenge)['code']
            status,value=http('/token',dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=resource),form=True)
            assert status==200,value
            return value['access_token']
        token=token_for([target]);broad=token_for([dict(host=target['host'],environment=target['environment'])])
        from codex_wake.controller_auth import OAuthAuthority
        oauth=OAuthAuthority(wake/'controller-auth'/'authority.sqlite',issuer=base,resource=resource)
        actor=oauth.authenticate(token)
        caller=Actor('fixture','service','host-local','host-local',base,resource,frozenset({'observe','control'}),[target],time.time()+600)
        policy=wake/'controller-messaging.json';policy.write_text(json.dumps(dict(version=1,host=target['host'],environment=target['environment'],bindings={},local_caller=caller.__dict__|{'scopes':sorted(caller.scopes)})));policy.chmod(0o600)
        runtime=ControllerRuntime(wake)
        def args_for(name,principal):
            def meta(identifier):return dict(operation_id=identifier,idempotency_key=identifier,correlation_id=identifier,binding='fixture',target=target)
            source='source-'+name
            runtime.execute(principal,'recovery.disable',dict(expected_target=target,_request=meta(source)),authorize=lambda:principal,
                dispatch=lambda *unused:dict(policy_id='fixture-policy',mode='off',reason='fixture operator disabled recovery',outcome='disabled'))
            return dict(expected_target=target,source_operation_id=source,_request=meta('notice-'+name))
        receipts={}
        def recorded(value):
            assert value['status']=='completed',value
            result=value['result']['operation'];assert result['phase']=='terminal',result
            event=result['result'];assert event['delivery']['status']=='recorded' and event['delivery']['model_context'],event
            return event
        receipts['cli']=recorded(run('notices','publish','--arguments',json.dumps(args_for('cli',caller))))
        payload=dict(operation='notices.publish',arguments=args_for('api',actor))
        status,value=http('/operations',payload,token);assert status==200,value;receipts['api']=recorded(value)
        assert http('/operations',dict(operation='notices.list',arguments=dict(expected_target=target)),broad)[0]==403
        status,value=http('/mcp',dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='wake_controller_notices_publish',arguments=args_for('oauth-mcp',actor))),token)
        assert status==200,value;receipts['oauth_mcp']=recorded(value['result']['structuredContent'])
        token_file=root/'oauth.token';token_file.write_text(token);token_file.chmod(0o600)
        receipts['remote_cli']=recorded(run('controller','remote','--endpoint',base,'--token-file',str(token_file),'notices.publish','--arguments',json.dumps(args_for('remote-cli',actor))))
        async def native_mcp():
            from mcp import ClientSession,StdioServerParameters
            from mcp.client.stdio import stdio_client
            parameters=StdioServerParameters(command=str(args.bin_dir.resolve()/'codex-wake-mcp'),args=['--wake-root',str(wake)],env=env)
            async with stdio_client(parameters) as (reader,writer):
                async with ClientSession(reader,writer) as session:
                    await session.initialize()
                    result=await session.call_tool('wake_controller_notices_publish',args_for('native-mcp',caller))
                    assert not result.is_error,result
                    return recorded(json.loads(result.content[0].text))
        receipts['native_mcp']=asyncio.run(native_mcp())
        frame=wait_for(lambda: text if all(event['event_id'] in (text:=capture()) for event in receipts.values()) else None)
        (root/'rendered.txt').write_text(frame)
        for event in receipts.values():
            retained=rpc('thread/notice/read',threadId=thread,eventId=event['event_id'])
            assert retained['notice']==dict(eventId=event['event_id'],text=event['text'])
            assert retained['modelContextAvailable'] is True
        after=rpc('thread/read',threadId=thread,includeTurns=True)['thread']['turns']
        assert [turn for turn in after if turn['id'] not in {event['event_id'] for event in receipts.values()}]==before
        records=[json.loads(line) for path in home.glob('sessions/**/*.jsonl') for line in path.read_text().splitlines()]
        assert not any(row.get('payload',{}).get('type')=='task_started' for row in records),'model turn started'
        assert 'Codex Wake controller' in frame and 'fixture-policy' in frame and 'disabled' in frame
        assert not (wake/'goal-supervision').exists()
        assert http('/revoke',dict(token=token,client_id=client['client_id']),form=True)[0]==200
        assert http('/operations',dict(operation='notices.list',arguments=dict(expected_target=target)),token)[0]==401
        proof.update(status='passed',frontdoors=list(receipts),native_tui_rendered=True,model_context_available=True,
            no_model_turns=True,no_governor=True,health_probe_calls=0,broad_denied=True,revoked_denied=True,
            native_binary=str(binary),native_sha256=digest,network_requests_trapped=traffic,
            source_hashes={name:hashlib.sha256((Path(codex_wake.__file__).parent/name).read_bytes()).hexdigest()
                for name in ('controller_notices.py','notice_commands.py','controller_runtime.py','native_protocol.py','controller_http.py','mcp_server.py','cli.py')})
    finally:
        tmux('kill-server',check=False)
        for process in (controller,native):
            if process is None:continue
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        log.close()
        if controller_log:controller_log.close()
        trap.shutdown();trap.server_close()
        proof['owned_processes_exited']=native.poll() is not None and (controller is None or controller.poll() is not None)
        (root/'receipt.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n')
    print(json.dumps(proof,sort_keys=True))


if __name__=='__main__':main()
