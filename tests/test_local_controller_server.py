"""One same-user server exposes the same real native discovery through API and MCP."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError
from websockets.sync.server import unix_serve


class LocalControllerServerTests(unittest.TestCase):
    def test_auto_connection_api_and_mcp_share_owned_discovery(self):
        from codex_wake.local_control_server import LocalControllerServer,connection_info
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);home=root/'home';home.mkdir()
            endpoint='unix://'+str(root/'native.sock')
            received=[]
            answer='transport response Δ\nsecond line'
            def native(ws):
                for raw in ws:
                    message=json.loads(raw)
                    if 'id' not in message:continue
                    if message['method']=='initialize':value={'codexHome':str(home)}
                    elif message['method']=='thread/loaded/list':value={'data':['owned-one'],'nextCursor':None}
                    elif message['method'] in ('thread/read','thread/resume'):value={'thread':{'id':'owned-one','name':'owned tab','cwd':str(root),'status':{'type':'idle'},'modelProvider':'openai'}}
                    elif message['method']=='turn/start':
                        received.append(message['params']['input'][0]['text']);value={'turn':{'id':'native-turn'}}
                    else:raise AssertionError(message['method'])
                    ws.send(json.dumps({'id':message['id'],'result':value}))
                    if message['method']=='turn/start':
                        for method,params in [('turn/started',{'threadId':'owned-one','turn':{'id':'native-turn','status':'inProgress'}}),('item/agentMessage/delta',{'threadId':'owned-one','turnId':'native-turn','itemId':'answer','delta':answer}),('item/completed',{'threadId':'owned-one','turnId':'native-turn','item':{'id':'answer','type':'agentMessage','phase':'final_answer','text':answer}}),('turn/completed',{'threadId':'owned-one','turn':{'id':'native-turn','status':'completed'}})]:
                            ws.send(json.dumps({'method':method,'params':params}))
            with unix_serve(native,str(root/'native.sock')) as peer:
                threading.Thread(target=peer.serve_forever,daemon=True).start()
                with LocalControllerServer(root,native_endpoint=endpoint) as server:
                    threading.Thread(target=server.serve_forever,daemon=True).start()
                    info=connection_info(root);url=info['url'];opener=build_opener(ProxyHandler({}))
                    def call(path,body,authorized=True,origin=None):
                        headers={'Content-Type':'application/json'}
                        if authorized:headers['Authorization']='Bearer '+info['token']
                        if origin:headers['Origin']=origin
                        with opener.open(Request(url+path,json.dumps(body).encode(),headers),timeout=10) as response:return json.loads(response.read())
                    with self.assertRaises(HTTPError) as unauthorized:call('/operations',{'operation':'local.list','arguments':{}},False)
                    self.assertEqual(unauthorized.exception.code,401)
                    listed=call('/operations',{'operation':'local.list','arguments':{}})
                    self.assertEqual([r['thread_id'] for r in listed['sessions']],['owned-one'])
                    tools=call('/mcp',{'jsonrpc':'2.0','id':1,'method':'tools/list'})
                    self.assertIn('wake_local_list',[t['name'] for t in tools['result']['tools']])
                    mcp=call('/mcp',{'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'wake_local_list','arguments':{}}})
                    self.assertEqual(mcp['result']['structuredContent']['sessions'][0]['target'],listed['sessions'][0]['target'])
                    with self.assertRaises(HTTPError) as browser:call('/operations',{'operation':'local.list','arguments':{}},origin='https://unrelated.example')
                    self.assertEqual(browser.exception.code,403)
                    import asyncio
                    async def sdk():
                        import httpx2
                        from mcp import ClientSession
                        from mcp.client.streamable_http import streamable_http_client
                        async with httpx2.AsyncClient(headers={'Authorization':'Bearer '+info['token']},trust_env=False) as http:
                            async with streamable_http_client(url+'/mcp',http_client=http) as streams:
                                async with ClientSession(streams[0],streams[1]) as session:
                                    await session.initialize()
                                    tools=await session.list_tools()
                                    self.assertIn('wake_local_list',[tool.name for tool in tools.tools])
                                    value=await session.call_tool('wake_local_list',{})
                                    self.assertEqual(value.model_dump(by_alias=True)['structuredContent']['sessions'][0]['thread_id'],'owned-one')
                                    failure=await session.call_tool('wake_local_resolve',{'selector':'missing'})
                                    self.assertTrue(failure.model_dump(by_alias=True)['isError'])
                                    self.assertEqual(failure.model_dump(by_alias=True)['structuredContent']['error']['code'],'target_unavailable')
                    asyncio.run(sdk())
                    async def stdio_sdk():
                        import sys
                        from mcp import ClientSession,StdioServerParameters
                        from mcp.client.stdio import stdio_client
                        parameters=StdioServerParameters(command=sys.executable,args=['-m','codex_wake','--wake-root',str(root),'control','mcp'],env={'PYTHONPATH':str(Path('src').absolute())})
                        async with stdio_client(parameters) as streams:
                            async with ClientSession(streams[0],streams[1]) as session:
                                await session.initialize()
                                result=await session.call_tool('wake_local_list',{})
                                self.assertEqual(result.model_dump(by_alias=True)['structuredContent']['sessions'][0]['thread_id'],'owned-one')
                    asyncio.run(stdio_sdk())
                    # The actual remote CLI adapter consumes streamed frames, not server stdout.
                    from codex_wake.local_control_client import cli_frames
                    frames=list(cli_frames(server.owner,['control','resolve','owned tab']))
                    self.assertEqual(frames[-1]['exit_code'],0,frames)
                    self.assertEqual(json.loads(frames[0]['stdout'])['thread_id'],'owned-one')
                    import os,subprocess,sys,base64
                    powershell=Path('/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
                    if powershell.is_file():
                        from codex_wake.powershell_client import render
                        wrapper=root/'wake-cli'
                        wrapper.write_text('#!/bin/sh\nexport PYTHONPATH='+str(Path('src').absolute())+'\nexec '+sys.executable+' -m codex_wake "$@"\n')
                        wrapper.chmod(0o700)
                        client=root/'wake.ps1';client.write_text(render(root,cli=wrapper,distro=os.environ.get('WSL_DISTRO_NAME','Ubuntu')))
                        windows=subprocess.check_output(['wslpath','-w',str(client)],text=True).strip()
                        command="& '"+windows.replace("'","''")+"' control resolve 'owned tab'; exit $LASTEXITCODE"
                        encoded=base64.b64encode(command.encode('utf-16-le')).decode()
                        called=subprocess.run([str(powershell),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',encoded],capture_output=True,timeout=30)
                        self.assertEqual(called.returncode,0,called.stderr.decode(errors='replace'))
                        self.assertEqual(json.loads(called.stdout.decode('utf-8'))['thread_id'],'owned-one')
                        prompt='Unicode question Δ\nsecond line'
                        def ps(*words):
                            literal=lambda value:"'"+value.replace("'","''")+"'"
                            command='& '+literal(windows)+' '+ ' '.join(literal(w) for w in words)+'; exit $LASTEXITCODE'
                            encoded=base64.b64encode(command.encode('utf-16-le')).decode()
                            return subprocess.run([str(powershell),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',encoded],capture_output=True,timeout=30)
                        sent=ps('control','prompt','thread:owned-one',prompt,'--mode','final','--timeout','10','--idempotency-key=powershell-fixture')
                        self.assertEqual(sent.returncode,0,sent.stderr.decode(errors='replace'))
                        self.assertEqual(sent.stdout.decode('utf-8'),answer)
                        self.assertEqual(received,[prompt])
                        retry=ps('control','prompt','thread:owned-one',prompt,'--mode','final','--timeout','10','--idempotency-key','powershell-fixture')
                        self.assertEqual(retry.returncode,0,retry.stderr.decode(errors='replace'))
                        self.assertEqual(received,[prompt])
                        import hashlib
                        operation='local-prompt-'+hashlib.sha256(b'powershell-fixture').hexdigest()[:32]
                        final=call('/mcp',{'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'wake_local_output','arguments':{'operation_id':operation,'mode':'final'}}})
                        self.assertEqual(final['result']['structuredContent']['result']['output']['text'],answer)
                        for mode in ('stream','transcript','silent'):
                            output=ps('control','output',operation,'--mode',mode,'--timeout','10')
                            self.assertEqual(output.returncode,0,output.stderr.decode(errors='replace'))
                            self.assertEqual(output.stderr,b'')
                            if mode=='silent':self.assertEqual(output.stdout,b'')
                            elif mode=='stream':self.assertEqual(output.stdout.decode('utf-8'),answer)
                            else:self.assertTrue(json.loads(output.stdout)['retention']['history_complete'])
                        request=Request(url+'/operations',json.dumps({'operation':'local.output','arguments':{'operation_id':operation,'mode':'transcript'}}).encode(),{'Content-Type':'application/json','Authorization':'Bearer '+info['token'],'Accept':'application/x-ndjson'})
                        with opener.open(request,timeout=10) as response:streamed=[json.loads(line) for line in response]
                        self.assertEqual(streamed[-1]['exit_code'],0)
                        self.assertTrue(any(frame.get('output',{}).get('events') for frame in streamed))
                        print('QUALIFIED actual Windows PowerShell: Unicode/multiline prompt, four modes, same API/MCP operation')
                    server.shutdown()
                peer.shutdown()
