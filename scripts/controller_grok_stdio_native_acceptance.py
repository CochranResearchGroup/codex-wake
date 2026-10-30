#!/usr/bin/env python3
"""Installed explicit Grok stdio host, genuine native metadata only.

No session creation, model prompt, provider authentication or credential copying.
Every downstream capability query uses the one initialized native stdio child.
"""
import argparse,asyncio,base64,hashlib,json,os,socket,subprocess,time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request,ProxyHandler,build_opener


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--bin-dir',type=Path,required=True);parser.add_argument('--binary',type=Path,required=True);parser.add_argument('--artifacts',type=Path,required=True);args=parser.parse_args()
    import codex_wake
    from codex_wake.process import process_identity
    assert 'site-packages' in str(Path(codex_wake.__file__).resolve())
    root=args.artifacts.resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    wake=root/'wake';home=root/'home';home.mkdir();work=root/'work';work.mkdir();ready=root/'ready.json'
    env={k:os.environ[k] for k in ('PATH','LANG') if k in os.environ};env.update(HOME=str(home),CODEX_HOME=str(home),XDG_CONFIG_HOME=str(root/'config'),XDG_STATE_HOME=str(root/'state'),XDG_DATA_HOME=str(root/'data'),XDG_CACHE_HOME=str(root/'cache'),NO_PROXY='127.0.0.1,localhost')
    cli=args.bin_dir.resolve()/'codex-wake';bridge_log=(root/'bridge.log').open('wb')
    bridge=subprocess.Popen([str(cli),'--wake-root',str(wake),'grok','stdio-host','--profile','native','--binary',str(args.binary.resolve()),'--home',str(home),'--cwd',str(work),'--account','native-metadata-only','--ready-file',str(ready),'--block-network'],env=env,cwd=work,stdout=bridge_log,stderr=subprocess.STDOUT)
    controller=None;controller_log=None;native_pid=None;proof={}
    def run(*items):
        result=subprocess.run([str(cli),'--wake-root',str(wake),*items],env=env,cwd=work,capture_output=True,text=True,timeout=25)
        assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
        return json.loads(result.stdout)
    try:
        deadline=time.monotonic()+15
        while not ready.exists():
            assert bridge.poll() is None,('explicit native stdio host exited',(root/'bridge.log').read_text(errors='replace'))
            assert time.monotonic()<deadline,'explicit native stdio metadata readiness deadline';time.sleep(.05)
        metadata=json.loads(ready.read_text());assert metadata['status']=='ready'
        target=metadata['target'];native_pid=int(target['process_pid'])
        assert native_pid!=bridge.pid and metadata['transport_owner']['pid']==bridge.pid
        assert target['build_sha256']==hashlib.sha256(args.binary.resolve().read_bytes()).hexdigest()
        assert metadata['native_metadata']['protocolVersion']==1
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close();url=f'http://127.0.0.1:{port}';resource=url+'/controller'
        run('controller','auth-configure','--issuer',url,'--resource',resource,'--owner','metadata-fixture-owner')
        controller_log=(root/'controller.log').open('wb');controller=subprocess.Popen([str(cli),'--wake-root',str(wake),'controller','serve','--port',str(port)],env=env,cwd=work,stdout=controller_log,stderr=subprocess.STDOUT)
        opener=build_opener(ProxyHandler({}))
        def http(path,body=None,token=None,form=False):
            headers={}
            if token:headers['Authorization']='Bearer '+token
            if body is not None:headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json';body=(urlencode(body) if form else json.dumps(body)).encode()
            try:
                with opener.open(Request(url+path,data=body,headers=headers),timeout=15) as response:return response.status,json.loads(response.read())
            except HTTPError as error:return error.code,json.loads(error.read())
        deadline=time.monotonic()+15
        while True:
            try:
                if http('/.well-known/oauth-authorization-server')[0]==200:break
            except OSError:pass
            assert controller.poll() is None and time.monotonic()<deadline;time.sleep(.05)
        client=http('/register',dict(redirect_uris=['http://127.0.0.1:45000/callback'],client_name='native-metadata-only'))[1]
        verifier='s'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        code=run('controller','authorize-client','--client-id='+client['client_id'],'--redirect-uri',client['redirect_uris'][0],'--subject','metadata-service','--principal-kind','service','--scope','observe','--targets',json.dumps([target]),'--code-challenge',challenge)['code']
        status,tokens=http('/token',dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=resource),form=True);assert status==200
        token=tokens['access_token'];token_file=root/'oauth.token';token_file.write_text(token);token_file.chmod(0o600)
        caller=dict(subject='native-metadata-local',client_id='host-local',grant_id='host-local',issuer=url,resource=resource,scopes=['observe'],targets=[target],expires_at=time.time()+120)
        path=wake/'controller-messaging.json';path.write_text(json.dumps(dict(version=1,local_caller=caller)));path.chmod(0o600)
        arguments=dict(profile='native',expected_target=target)
        def qualified(value):
            assert value['status']=='completed',value
            result=value['result'];assert result['protocol_version']==1 and result['target']==target
            assert result['native_identity']['agent_instance_id']==metadata['native_metadata']['_meta']['agentInstanceId']
            assert result['authority']['native_account_verified'] is False
            assert result['capabilities']['exact_tui_health']['status']=='unsupported'
            return result['native_identity']
        identities={'cli':qualified(run('grok','capabilities','--arguments',json.dumps(arguments)))}
        status,value=http('/operations',dict(operation='grok.capabilities',arguments=arguments),token);assert status==200;identities['api']=qualified(value)
        status,value=http('/mcp',dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='wake_controller_grok_capabilities',arguments=arguments)),token);assert status==200;identities['oauth_mcp']=qualified(value['result']['structuredContent'])
        identities['remote_cli']=qualified(run('controller','remote','--endpoint',url,'--token-file',str(token_file),'grok.capabilities','--arguments',json.dumps(arguments)))
        async def native_mcp():
            from mcp import ClientSession,StdioServerParameters
            from mcp.client.stdio import stdio_client
            parameters=StdioServerParameters(command=str(args.bin_dir.resolve()/'codex-wake-mcp'),args=['--wake-root',str(wake)],env=env)
            async with stdio_client(parameters) as (reader,writer):
                async with ClientSession(reader,writer) as session:
                    await session.initialize();value=await session.call_tool('wake_controller_grok_capabilities',arguments);assert not value.is_error,value
                    return qualified(json.loads(value.content[0].text))
        identities['native_mcp']=asyncio.run(native_mcp())
        assert all(value==identities['cli'] for value in identities.values())
        # No operation with control scope was authorized; only genuine cached
        # initialize metadata traversed the host. The bridge created no session.
        import sqlite3
        operations=wake/'controller-operations/operations.sqlite'
        if operations.exists():assert sqlite3.connect(operations).execute('SELECT COUNT(*) FROM operations').fetchone()[0]==0
        proof.update(status='passed',frontdoors=identities,native_binary=str(args.binary.resolve()),native_sha256=target['build_sha256'],native_version=metadata['native_metadata']['_meta']['agentVersion'],
            actual_native_pid=native_pid,actual_bridge_pid=bridge.pid,child_is_distinct_from_transport_owner=True,genuine_initialize_once=True,no_native_session=True,no_native_model_prompt=True,
            no_provider_authentication=True,no_provider_credential_read=True,native_account_verified=False,exact_tui_health='unsupported',transport='explicit sole-owned native ACP stdio; local bridge forwarding',
            native_capabilities=metadata['native_metadata']['agentCapabilities'],hashes={name:hashlib.sha256((Path(codex_wake.__file__).parent/name).read_bytes()).hexdigest() for name in ('grok_stdio_host.py','grok_acp.py','controller_grok.py','grok_commands.py','runtime_wakes.py','cli.py')})
    finally:
        for process in (controller,bridge):
            if process is None:continue
            process.terminate()
            try:process.wait(timeout=7)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        bridge_log.close()
        if controller_log:controller_log.close()
        proof['owned_processes_exited']=bridge.poll() is not None and (controller is None or controller.poll() is not None) and (native_pid is None or process_identity(native_pid) is None)
        (root/'receipt.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    assert proof['owned_processes_exited'];print(json.dumps(proof,sort_keys=True))


if __name__=='__main__':main()
