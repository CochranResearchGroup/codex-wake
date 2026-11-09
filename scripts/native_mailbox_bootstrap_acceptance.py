#!/usr/bin/env python3
"""Private stdio/CLI acceptance with injected native metadata; no real model turns."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_mailbox import Mailbox


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    from websockets.sync.server import unix_serve
    with tempfile.TemporaryDirectory(prefix='wake-native-mailbox-') as tmp:
        root=Path(tmp);project=root/'project';project.mkdir();home=root/'home';home.mkdir()
        store,operator=BusStore.configure(root/'bus');store.enroll(project,operator);Mailbox.migrate(store,operator)
        ids=['00000000-0000-7000-8000-000000000011','00000000-0000-7000-8000-000000000012']
        methods=[]
        def handle(connection):
            for raw in connection:
                request=json.loads(raw);method=request['method'];methods.append(method)
                if method=='initialized':continue
                if method=='initialize':value=dict(codexHome=str(home),userAgent='injected-native-fixture')
                elif method=='thread/read':
                    thread=request['params']['threadId'];assert thread in ids
                    value=dict(thread=dict(id=thread,cwd=str(project),modelProvider='fixture',name='fixture',status=dict(type='idle')))
                else:raise AssertionError('Unexpected native method: '+method)
                connection.send(json.dumps(dict(id=request['id'],result=value)))
        async def workflow():
            from mcp import ClientSession,StdioServerParameters
            from mcp.client.stdio import stdio_client
            from mcp.types import RequestParamsMeta
            env=dict(os.environ)
            for key in ('CODEX_WAKE_A2A_CAPABILITY','CODEX_WAKE_A2A_BUS_ROOT'):env.pop(key,None)
            params=StdioServerParameters(command=sys.executable,
                args=['-m','codex_wake.mcp_server','--bus-root',str(store.root),
                      '--mailbox-operator-capability',str(operator),'--app-server','unix://'+str(root/'native.sock')],env=env)
            async with stdio_client(params) as (reader,writer):
                async with ClientSession(reader,writer) as client:
                    await client.initialize()
                    async def call(index,verb,**arguments):
                        thread=ids[index]
                        meta=RequestParamsMeta(threadId=thread,sessionId=thread,callId='fixture-call',
                            **{'x-codex-turn-metadata':dict(thread_id=thread,session_id=thread,turn_id='fixture-turn')})
                        r=await client.call_tool('wake_messages_'+verb,dict(caller_thread_id=thread,**arguments),meta=meta)
                        value=json.loads(r.content[0].text);assert not r.is_error,value
                        return value
                    await call(1,'inbox');await call(0,'inbox')
                    question=await call(0,'send',to='thread:'+ids[1],body='Fixture question?',kind='request',idempotency_key='question-1',delivery='inbox')
                    mid=question['message']['message_id']
                    assert (await call(1,'read',message_id=mid))['body']=='Fixture question?'
                    assert (await call(1,'ack',message_id=mid,outcome='accepted'))['claimed']
                    answer=await call(1,'reply',message_id=mid,body='Fixture answer.',idempotency_key='reply-1',delivery='inbox')
                    assert (await call(0,'read',message_id=answer['message']['message_id']))['body']=='Fixture answer.'
                    denied=await client.call_tool('wake_messages_inbox',dict(caller_thread_id=ids[0]))
                    assert denied.is_error
            assert store.status()['active_actors']==2
        with unix_serve(handle,path=str(root/'native.sock')) as server:
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:asyncio.run(workflow())
            finally:server.shutdown();worker.join(timeout=5)
        import codex_wake
        receipt=dict(status='PASS',package=str(Path(codex_wake.__file__).resolve()),python=sys.executable,
            native_evidence='injected private websocket metadata, not real native attestation',
            checks=['shared-stdio-two-distinct-actors','actual-cli-question-claim-correlated-reply',
                    'no-native-metadata-denied','actor-count-remains-two'],native_methods=sorted(set(methods)),
            provider_calls=0,production_effects=False,temporary_state_removed_on_exit=True)
    args.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()
