#!/usr/bin/env python3
"""Installed provider-free two-identity A2A inbox workflow, no turn operations."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading

from websockets.sync.server import unix_serve


def smoke(cli: str, *, scheduler=False):
    methods, closed = [], []
    with tempfile.TemporaryDirectory(prefix='wake-mailbox-smoke-') as temporary:
        root=Path(temporary)
        sender_root=root/'sender';sender_root.mkdir()
        recipient_root=root/'recipient';recipient_root.mkdir()
        home=root/'codex';home.mkdir()
        socket_path=root/'server.sock'
        bus_root=root/'bus'
        thread_ids=['00000000-0000-7000-8000-000000000011','00000000-0000-7000-8000-000000000012']
        threads={identifier:dict(id=identifier,name='Fixture '+name,cwd=str(cwd),modelProvider='fixture',
                                 parentThreadId=None,status=dict(type='active' if name == 'recipient' else 'idle'))
                 for identifier,name,cwd in zip(thread_ids,['sender','recipient'],[sender_root,recipient_root])}
        def handle(connection):
            try:
                for raw in connection:
                    request=json.loads(raw); method=request['method'];methods.append(method)
                    if method=='initialized':continue
                    if method=='initialize':value=dict(codexHome=str(home),userAgent='fixture')
                    elif method=='thread/loaded/list':value=dict(data=thread_ids,nextCursor=None)
                    elif method=='thread/read':
                        assert request['params']['includeTurns'] is False
                        value=dict(thread=threads[request['params']['threadId']])
                    else:raise AssertionError('unexpected runtime effect: '+method)
                    connection.send(json.dumps(dict(id=request['id'],result=value)))
            finally:closed.append(True)
        tools=root/'bin';tools.mkdir()
        tmux=tools/'tmux';tmux.write_text('#!/bin/sh\nexit 0\n');tmux.chmod(0o700)
        environment=dict(os.environ,PATH=str(tools)+os.pathsep+os.environ.get('PATH',''))
        for key in ['PYTHONPATH','TMUX','TMUX_PANE','CODEX_WAKE_A2A_CAPABILITY']:
            environment.pop(key,None)
        request_body=sender_root/'request.txt';request_body.write_text('Fixture mailbox request\n')
        reply_body=recipient_root/'reply.txt';reply_body.write_text('Fixture mailbox result\n')
        def invoke(arguments, *, actor=None, capability=None, expected=0):
            env=dict(environment)
            if actor is not None:env['CODEX_THREAD_ID']=thread_ids[actor]
            group=arguments[0]
            command=[cli,*arguments,'--bus-root',str(bus_root),'--json']
            if group=='messages':
                command+=['--app-server','unix://'+str(socket_path)]
                if capability:command+=['--capability',str(capability)]
            completed=subprocess.run(command,cwd=sender_root if actor in (None,0) else recipient_root,
                                     env=env,capture_output=True,text=True,timeout=15)
            assert completed.returncode==expected,(arguments,completed.returncode,completed.stderr,completed.stdout)
            return json.loads(completed.stdout)
        children_path=Path('/proc/self/task')/str(os.getpid())/'children'
        children_before=len(children_path.read_text().split())
        with unix_serve(handle,path=str(socket_path)) as server:
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                configured=invoke(['a2a','configure','--allow-cross-root'])
                operator=configured['operator_capability_file']
                capabilities=[]
                for identifier,cwd in zip(thread_ids,[sender_root,recipient_root]):
                    value=invoke(['a2a','enroll',str(cwd),'--thread','thread:'+identifier,
                                  '--app-server','unix://'+str(socket_path),'--operator-capability',operator])
                    capabilities.append(value['actor_capability_file'])
                def message(actor,arguments,expected=0):
                    return invoke(['messages',*arguments],actor=actor,capability=capabilities[actor],expected=expected)
                admission=message(0,['send','--to','thread:'+thread_ids[1],'--body-file',str(request_body),
                                     '--idempotency-key','installed-request','--delivery','inbox'])
                identifier=admission['message']['message_id']
                assert admission['message']['state']==dict(admission='accepted',notification='suppressed',recipient='unread')
                denied=invoke(['messages','read',identifier],actor=1,capability=capabilities[0],expected=7)
                assert denied['error']['code']=='authorization_denied' and 'body' not in denied
                shown=message(0,['show',identifier]);assert 'Fixture mailbox request' not in json.dumps(shown)
                retrieved=message(1,['read',identifier]);assert retrieved['body']==request_body.read_text()
                assert retrieved['peer_content_trust']=='untrusted' and retrieved['receipt_id']
                claimed=message(1,['ack',identifier,'--outcome','accepted']);assert claimed['claimed']
                duplicate=message(1,['ack',identifier,'--outcome','accepted']);assert not duplicate['claimed']
                assert duplicate['receipt_id']==claimed['receipt_id']
                reply=message(1,['reply',identifier,'--body-file',str(reply_body),'--idempotency-key','installed-reply',
                                 '--delivery','inbox','--outcome','completed','--evidence','/fixture/result'])
                reply_id=reply['message']['message_id']
                assert reply['message']['in_reply_to']==identifier
                satisfied=message(0,['wait',identifier,'--for','reply','--timeout','1s'])
                assert satisfied['event']=='satisfied' and satisfied['replies'][0]['message_id']==reply_id
                returned=message(0,['read',reply_id]);assert returned['body']==reply_body.read_text()
                assert returned['receipt_id']
                status=invoke(['a2a','status','--operator-capability',operator])
                assert status['bus']['enrolled_roots']==2 and status['bus']['active_actors']==2
                assert status['bus']['paused'] and status['bus']['notification_capability']=='unqualified'
                original=message(0,['show',identifier])['message']
                assert original['state']['recipient']=='completed'
                received_ids=[retrieved['receipt_id'],returned['receipt_id']]
                projected=[]
                if scheduler:
                    pending=message(0,['send','--to','thread:'+thread_ids[1],'--body-file',str(request_body),
                                       '--idempotency-key','installed-projection','--delivery','notify'])
                    projection_root=root/'jobs'
                    for _ in range(2):
                        tick=invoke(['a2a','tick','--operator-capability',operator,
                                     '--projection-root',str(projection_root)])
                        assert tick['status']=='projection_only' and tick['dispatched']==0
                        assert tick['notification_capability']=='unqualified'
                        projected=tick['published'];assert len(projected)==1
                    path=Path(projected[0]['path'])
                    assert path.stat().st_mode & 0o777 == 0o600
                    job=json.loads(path.read_text())
                    assert job['message_id']==pending['message']['message_id']
                    assert 'Fixture mailbox request' not in path.read_text()
                    message(0,['cancel',job['message_id']])
                    tick=invoke(['a2a','tick','--operator-capability',operator,
                                 '--projection-root',str(projection_root)])
                    assert tick['published']==[] and tick['dispatched']==0

            finally:
                server.shutdown();worker.join(timeout=5);assert not worker.is_alive()
        children_after=len(children_path.read_text().split())
        assert children_after==children_before
    assert set(methods)<={'initialize','initialized','thread/loaded/list','thread/read'}
    assert len(closed)==methods.count('initialize')
    return dict(schema_version=1,status='accepted_provider_free',mode='inbox_and_projection' if scheduler else 'inbox_only',requests=2 if scheduler else 1,replies=1,
                scheduler_projections=len(projected),scheduler_dispatches=0,
                received_receipts=len(received_ids),explicit_completion_claim=True,cross_root_policy='explicit',
                wrong_actor_denied=True,runtime_effect_methods=0,connections_closed=len(closed),
                children_before=children_before,children_after=children_after,cleanup='temporary_bus_and_roots_removed')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cli',required=True);parser.add_argument('--scheduler',action='store_true');args=parser.parse_args()
    print(json.dumps(smoke(args.cli,scheduler=args.scheduler),sort_keys=True))
