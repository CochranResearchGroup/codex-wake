"""Installed CLI/API/OAuth-MCP/native-MCP health qualification against an owned UI."""
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, ProxyHandler, build_opener


def qualify(wake_cli, root, target, artifacts, env):
    import codex_wake
    assert 'site-packages' in str(Path(codex_wake.__file__).resolve()),codex_wake.__file__
    env=dict(env);env.pop('PYTHONPATH',None)
    def cli(*args,expected=0):
        p=subprocess.run([str(wake_cli),'--wake-root',str(root),*args],env=env,cwd=artifacts,text=True,capture_output=True,timeout=30)
        assert p.returncode==expected,(p.returncode,p.stdout,p.stderr)
        return json.loads(p.stdout)
    def responsive(value):
        assert value['status']=='completed' and value['result']['observation']['responsive'] is True,value
        return value['result']['observation']['challenge']
    arguments={'expected_target':target,'timeout':5}
    proof={'installed_module':str(Path(codex_wake.__file__).resolve()),'cli':str(wake_cli),'cli_ack':responsive(cli('health','observe','--expected-target',json.dumps(target),'--timeout','5'))}
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    base=f'http://127.0.0.1:{port}';resource=base+'/controller'
    cli('controller','auth-configure','--issuer',base,'--resource',resource,'--owner','synthetic-health-owner')
    log=(artifacts/'controller.log').open('wb')
    server=subprocess.Popen([str(wake_cli),'--wake-root',str(root),'controller','serve','--port',str(port)],env=env,cwd=artifacts,stdout=log,stderr=subprocess.STDOUT)
    opener=build_opener(ProxyHandler({}))
    def http(path,body=None,token=None,form=False):
        headers={}
        if token:headers['Authorization']='Bearer '+token
        if body is not None:
            headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
            body=(urlencode(body) if form else json.dumps(body)).encode()
        try:
            with opener.open(Request(base+path,data=body,headers=headers),timeout=12) as response:return response.status,json.loads(response.read())
        except HTTPError as error:return error.code,json.loads(error.read())
    try:
        until=time.monotonic()+15
        while True:
            try:
                status,metadata=http('/.well-known/oauth-authorization-server')
                if status==200:break
            except OSError:pass
            assert server.poll() is None,'private controller exited'
            assert time.monotonic()<until,'private controller startup deadline'
            time.sleep(.05)
        assert metadata['issuer']==base
        client=http('/register',{'redirect_uris':['http://127.0.0.1:45000/callback'],'client_name':'health390 fixture'})[1]
        verifier='h'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        flat={key:value for key,value in target.items() if key!='process'}
        flat.update(process_pid=str(target['process']['pid']),process_start_ticks=str(target['process']['start_ticks']),process_boot_id=target['process']['boot_id'])
        def token(scopes):
            code=cli('controller','authorize-client','--client-id='+client['client_id'],'--redirect-uri',client['redirect_uris'][0],'--subject','synthetic-health-service','--principal-kind','service','--scope','observe','--targets',json.dumps(scopes),'--code-challenge',challenge)['code']
            status,tokens=http('/token',dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=resource),form=True)
            assert status==200,tokens
            return tokens['access_token']
        broad=token([{'host':target['host']}]);exact=token([flat])
        operation={'operation':'health.observe','arguments':arguments}
        status,denied=http('/operations',operation,broad)
        proof['broad_denial']={'status':status,'body':denied}
        assert status in (400,403) and ('error' in denied),denied
        status,observed=http('/operations',operation,exact);assert status==200,observed
        proof['api_ack']=responsive(observed);proof['broad_grant_denied']=True
        status,initialized=http('/mcp',dict(jsonrpc='2.0',id=1,method='initialize',params={'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'health-fixture','version':'1'}}),exact)
        assert status==200,initialized
        status,called=http('/mcp',dict(jsonrpc='2.0',id=2,method='tools/call',params={'name':'wake_controller_health','arguments':arguments}),exact)
        assert status==200,called
        proof['oauth_mcp_ack']=responsive(called['result']['structuredContent'])
        token_file=artifacts/'synthetic-oauth.token';token_file.write_text(exact);token_file.chmod(0o600)
        proof['remote_cli_ack']=responsive(cli('controller','remote','--endpoint',base,'--token-file',str(token_file),'health.observe','--arguments',json.dumps(arguments)))
        caller=dict(subject='synthetic-health-service',client_id='host-native-fixture',grant_id='host-health-fixture',issuer=base,resource=resource,scopes=['observe'],targets=[flat],expires_at=time.time()+600)
        policy=root/'controller-messaging.json';policy.write_text(json.dumps(dict(version=1,host=target['host'],environment=target['environment'],bindings={},local_caller=caller)));policy.chmod(0o600)
        async def native():
            from mcp import ClientSession,StdioServerParameters
            from mcp.client.stdio import stdio_client
            parameters=StdioServerParameters(command=str(wake_cli.parent/'codex-wake-mcp'),args=['--wake-root',str(root)],env=env)
            async with stdio_client(parameters) as (reader,writer):
                async with ClientSession(reader,writer) as session:
                    await session.initialize()
                    assert 'wake_controller_health' in {tool.name for tool in (await session.list_tools()).tools}
                    result=await session.call_tool('wake_controller_health',arguments)
                    assert not result.is_error,result
                    return responsive(json.loads(result.content[0].text))
        proof['native_mcp_ack']=asyncio.run(native())
        assert len({proof[key] for key in proof if key.endswith('_ack')})==5,'public adapters reused a stale challenge'
        status,_=http('/revoke',dict(token=exact,client_id=client['client_id']),form=True);assert status==200
        assert http('/operations',operation,exact)[0]==401
        proof['revoked_access_denied']=True
        proof['source_sha256']={name:hashlib.sha256((Path(codex_wake.__file__).parent/name).read_bytes()).hexdigest() for name in ('controller_health.py','health_commands.py','controller_http.py','controller_auth.py','controller_operations.py','mcp_server.py','cli.py')}
        return proof
    finally:
        (artifacts/'public-receipt.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n')
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
        log.close()
