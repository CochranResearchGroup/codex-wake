#!/usr/bin/env python3
"""Installed controller CLI, real stdio MCP, authenticated HTTP and OAuth MCP."""
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
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',required=True);args=parser.parse_args()
    import codex_wake
    from codex_wake.controller_tabs import controller_tabs_from_root
    assert 'site-packages' in codex_wake.__file__
    executable=str(Path(sys.executable).parent/'codex-wake')
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    report=dict(package=codex_wake.__file__,uid=os.geteuid(),checks=[],production_effects=False)
    with tempfile.TemporaryDirectory(prefix='wake547-surfaces-') as directory:
        root=Path(directory);account=root/'controller-accounts.toml';account.write_text('[profiles]\nstate_root='+json.dumps(str(root/'profiles'))+'\nsource_root='+json.dumps(str(root/'source'))+'\n');account.chmod(0o600);p=root/'controller-tabs.json';p.write_text(json.dumps(dict(schema_version=1,workspaces={})));p.chmod(0o600)
        def cli(*parts):
            value=subprocess.run([executable,'--wake-root',str(root),*parts],cwd=root,env=env,text=True,capture_output=True,timeout=20)
            assert value.returncode==0,(parts,value.returncode,value.stdout,value.stderr)
            return value.stdout
        def controller(*parts):return json.loads(cli('controller',*parts))
        helptext=cli('tabs','monitor-start','--help')
        for flag in ('--no-activity','--no-health','--no-errors','--health-interval','--error-interval'):assert flag in helptext,flag
        cli('tabs','monitor-start','--no-activity','--no-errors','--health-interval','90')
        text=cli('tabs','monitor-status');assert 'Tiers:' in text and 'activity=off' in text,text
        cli('tabs','monitor-stop');report['checks'].append('installed CLI tier controls and readable status')
        async def stdio():
            from mcp import ClientSession,StdioServerParameters
            from mcp.client.stdio import stdio_client
            params=StdioServerParameters(command=str(Path(sys.executable).parent/'codex-wake-mcp'),args=['--wake-root',str(root)],env=env)
            async with stdio_client(params) as (reader,writer):
                async with ClientSession(reader,writer) as session:
                    await session.initialize();tools={t.name:t for t in (await session.list_tools()).tools}
                    for name in ('wake_tabs_monitor_start','wake_tabs_monitor_stop','wake_tabs_monitor_status','wake_tabs_monitor_refresh'):assert name in tools,name
                    schema=tools['wake_tabs_monitor_start'].input_schema['properties']
                    assert {'activity','health','errors','health_interval','error_interval'}<=schema.keys()
                    value=await session.call_tool('wake_tabs_monitor_status',{})
                    assert not value.is_error
        asyncio.run(stdio());report['checks'].append('actual installed stdio MCP schema and monitor status')
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        endpoint='http://127.0.0.1:'+str(port);resource=endpoint+'/controller'
        controller('auth-configure','--issuer',endpoint,'--resource',resource,'--owner','qualification-owner')
        process=subprocess.Popen([executable,'--wake-root',str(root),'controller','serve','--port',str(port)],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        def http(path,body=None,token=None):
            headers={'Content-Type':'application/json'}
            if token:headers['Authorization']='Bearer '+token
            request=Request(endpoint+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
            try:
                with urlopen(request,timeout=15) as response:return response.status,json.load(response)
            except HTTPError as error:return error.code,json.load(error)
        try:
            until=time.monotonic()+10
            while True:
                try:
                    if http('/.well-known/oauth-protected-resource')[0]==200:break
                except OSError:pass
                assert time.monotonic()<until;time.sleep(.02)
            assert http('/operations',dict(operation='tabs.monitor.status',arguments={}))[0]==401
            client=http('/register',dict(redirect_uris=['http://127.0.0.1:45000/callback']))[1]
            verifier='x'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            owner=controller_tabs_from_root(root)
            code=controller('authorize-client','--client-id='+client['client_id'],'--redirect-uri',client['redirect_uris'][0],
                '--subject','qualification-client','--principal-kind','service','--scope','observe','--scope','control',
                '--targets',json.dumps([dict(host=owner.host,environment=owner.environment,workspace='@monitor',presentation='logical')]),'--code-challenge',challenge)['code']
            status,tokens=http('/token',dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=resource));assert status==200
            token=tokens['access_token']
            def api(operation,arguments):
                status,value=http('/operations',dict(operation=operation,arguments=arguments),token)
                assert status==200,(status,value)
                return value
            assert api('tabs.monitor.status',{})['status']=='completed'
            def mutation_args(identifier,**options):
                target=owner.monitor_target()
                return dict(expected_target=target,_request=dict(operation_id=identifier,idempotency_key=identifier,
                    correlation_id=identifier,binding='qualification-controller',target=target),**options)
            result=api('tabs.monitor.start',mutation_args('http-start',activity=False,health=True,errors=False,health_interval=90))
            assert result['result']['operation']['execution']=='completed',result
            result=api('tabs.monitor.stop',mutation_args('http-stop'));assert result['result']['operation']['execution']=='completed',result
            report['checks'].append('authenticated HTTP independent tier start/status/stop and anonymous refusal')
            status,value=http('/mcp',dict(jsonrpc='2.0',id=1,method='initialize',params=dict(protocolVersion='2025-03-26',capabilities={},clientInfo=dict(name='qualification',version='1'))),token);assert status==200
            listed=http('/mcp',dict(jsonrpc='2.0',id=2,method='tools/list'),token)[1]['result']['tools']
            schema=next(t for t in listed if t['name']=='wake_tabs_monitor_start')['inputSchema']['properties']
            assert {'activity','health','errors','health_interval','error_interval'}<=schema.keys()
            def mcp(name,arguments):
                status,value=http('/mcp',dict(jsonrpc='2.0',id=3,method='tools/call',params=dict(name=name,arguments=arguments)),token)
                assert status==200 and not value['result']['isError'],value
                return value['result']['structuredContent']
            result=mcp('wake_tabs_monitor_start',mutation_args('mcp-start',activity=True,health=False,errors=True))
            assert result['result']['operation']['execution']=='completed',result
            assert mcp('wake_tabs_monitor_status',{})['status']=='completed'
            result=mcp('wake_tabs_monitor_stop',mutation_args('mcp-stop'));assert result['result']['operation']['execution']=='completed',result
            report['checks'].append('actual OAuth MCP schema independent tier start/status/stop')
        finally:
            try:cli('tabs','monitor-stop')
            finally:process.terminate();process.wait(timeout=5)
    report['status']='passed';Path(args.receipt).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
