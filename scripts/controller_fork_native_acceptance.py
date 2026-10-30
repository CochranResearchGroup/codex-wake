#!/usr/bin/env python3
"""Read/fork only qualification of an explicit complete native package.

Seeds canonical synthetic persisted history; never starts a model/provider turn.
Private daemon, home and blocked egress are destroyed only by their owning run.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import http.server
import json
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import threading
import time
from uuid import uuid4


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--models',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,required=True)
    args=parser.parse_args()
    from codex_wake.controller_auth import Actor
    from codex_wake.controller_flow_sessions import ControllerFlowSessions
    from codex_wake.native_protocol import native_request
    from codex_wake.process import process_identity
    package=args.package.resolve();manifest=json.loads((package/'codex-package.json').read_text())
    assert manifest['entrypoint']=='bin/codex' and manifest['layoutVersion']==1
    binary=package/manifest['entrypoint']
    digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    assert digest=='f1775c5dd0a1c450a6eec2c76b2f35c5197b0d3df7e9eb2cfb156bdfb403d448'
    for component in ('bin/codex-code-mode-host','codex-path/rg','codex-resources/bwrap','codex-resources','codex-path'):
        assert (package/component).exists(),component
    root=args.artifacts.resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    home=root/'home';home.mkdir();cwd=root/'work';cwd.mkdir();wake=root/'wake';wake.mkdir()
    requests=[]
    class Trap(http.server.BaseHTTPRequestHandler):
        def reject(self):
            requests.append(dict(method=self.command,path=self.path));self.send_response(503);self.end_headers()
        do_GET=do_POST=do_CONNECT=reject
        def log_message(self,*unused):pass
    trap=http.server.ThreadingHTTPServer(('127.0.0.1',0),Trap)
    worker=threading.Thread(target=trap.serve_forever,daemon=True);worker.start()
    url='http://127.0.0.1:'+str(trap.server_port)
    model=json.loads(args.models.read_text())['models'][0];catalog=home/'models.json'
    catalog.write_text(json.dumps(dict(models=[model])))
    (home/'config.toml').write_text(f'''model = {json.dumps(model['slug'])}
model_provider = "fork_fixture"
model_catalog_json = {json.dumps(str(catalog))}
check_for_update_on_startup = false
[analytics]
enabled = false
[model_providers.fork_fixture]
name = "Provider-free persisted fork fixture"
base_url = "{url}/never-query"
wire_api = "responses"
requires_openai_auth = false
[projects.{json.dumps(str(cwd))}]
trust_level = "trusted"
''')
    env={key:os.environ[key] for key in ('PATH','LANG','LD_LIBRARY_PATH') if key in os.environ}
    env.update(HOME=str(home),CODEX_HOME=str(home),XDG_CONFIG_HOME=str(root/'config'),XDG_DATA_HOME=str(root/'data'),
               XDG_STATE_HOME=str(root/'state'),XDG_CACHE_HOME=str(root/'cache'),NO_PROXY='127.0.0.1,localhost',
               HTTPS_PROXY=url,HTTP_PROXY=url,ALL_PROXY=url)
    source=str(uuid4());turn_ids=[str(uuid4()) for unused in range(3)]
    now=datetime.now(timezone.utc);stamp=now.isoformat().replace('+00:00','Z')
    rollout=home/'sessions'/now.strftime('%Y/%m/%d')/('rollout-'+now.strftime('%Y-%m-%dT%H-%M-%S')+'-'+source+'.jsonl')
    rollout.parent.mkdir(parents=True)
    records=[dict(timestamp=stamp,type='session_meta',payload=dict(id=source,session_id=source,timestamp=stamp,cwd=str(cwd),
        originator='codex_cli_rs',cli_version='0.164.0',source='cli',model_provider='fork_fixture',base_instructions=dict(text='Synthetic persisted history, no provider turn.')))]
    for index,identifier in enumerate(turn_ids):
        for payload in (dict(type='task_started',turn_id=identifier,model_context_window=10000),
                        dict(type='user_message',message='synthetic input '+str(index)),
                        dict(type='agent_message',message='synthetic answer '+str(index)),
                        dict(type='task_complete',turn_id=identifier,last_agent_message='synthetic answer '+str(index))):
            records.append(dict(timestamp=stamp,type='event_msg',payload=payload))
    rollout.write_text(''.join(json.dumps(record)+'\n' for record in records[:9]))
    original=rollout.read_bytes()
    endpoint='unix://'+str(root/'native.sock');log=(root/'daemon.log').open('wb')
    daemon=subprocess.Popen([str(binary),'app-server','--listen',endpoint],cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    methods=[];receipt={}
    try:
        until=time.monotonic()+20
        while not (Path(endpoint[7:]).exists() and stat.S_ISSOCK(Path(endpoint[7:]).stat().st_mode)):
            assert daemon.poll() is None,'private native daemon exited'
            assert time.monotonic()<until,'private socket deadline';time.sleep(.05)
        endpoint='unix://'+str(Path(endpoint[7:]).resolve(strict=True))
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
            peer.connect(endpoint[7:]);pid,uid,unused=struct.unpack('3i',peer.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            assert pid==daemon.pid and uid==os.geteuid()
        def request(endpoint,executable,method,params,timeout):
            methods.append(dict(method=method,params=params))
            value=native_request(endpoint,executable,method,params,timeout)
            with (root/'rpc.jsonl').open('a') as stream:stream.write(json.dumps(dict(method=method,result=value))+'\n')
            return value
        birth=process_identity(daemon.pid)
        base=dict(host='fixture',environment='private',provider='codex',account='synthetic',home=str(home),home_generation='fixture',
            configuration_revision='fixture',build_channel='modded',build_sha256=digest,build_revision='95cd89dd5f3cddeb241a9de75a3cc255a9484606',executable=str(binary))
        profile=dict(target=base,endpoint=endpoint,process=dict(pid=daemon.pid,start_ticks=birth['start_time_ticks'],boot_id=birth['boot_id']),
            modes=['fork'],native_provider='fork_fixture',cwd=str(cwd),methods=['thread/start','turn/start','thread/read','turn/interrupt','thread/fork'])
        path=wake/'controller-flow-sessions.json';path.write_text(json.dumps(dict(version=1,profiles={'fixture':profile})));path.chmod(0o600)
        owner=ControllerFlowSessions(wake,resolve_build=lambda target:base,request=request)
        target=dict(owner.target('fixture'),conversation_id=source)
        actor=Actor('fixture','service','client','grant','local://fixture','wake:controller',frozenset({'observe','control'}),[base],time.time()+600)
        pinned=owner.execute(actor,'sessions.checkpoint',dict(profile='fixture',expected_target=target),authorize=lambda:actor)['result']['checkpoint']
        assert pinned['last_turn_id']==turn_ids[1]
        # Advance only this synthetic source fixture after common-prefix selection.
        with rollout.open('a') as stream:stream.write(''.join(json.dumps(record)+'\n' for record in records[9:]))
        original=rollout.read_bytes()
        children=[]
        for index in range(2):
            key='fork-'+str(index)
            result=owner.execute(actor,'sessions.fork',dict(profile='fixture',expected_target=target,checkpoint=pinned,
                _request=dict(operation_id=key,idempotency_key=key,correlation_id=key,binding='fixture',target=target)),authorize=lambda:actor)
            operation=result['result']['operation']
            assert operation['execution']=='completed' and operation['result'] is not None,operation
            child=operation['result'];assert child['provenance']['retainedTurnIds']==turn_ids[:2]
            children.append(child['target']['conversation_id'])
        assert len(set(children+[source]))==3
        assert rollout.read_bytes()==original,'source rollout changed'
        assert not any(call['method']=='turn/start' for call in methods)
        assert not any(call['method'] in ('thread/revert','thread/rollback') for call in methods)
        assert not any(item['method']!='CONNECT' for item in requests),requests
        receipt=dict(status='passed',ticket=408,package=str(package),manifest=manifest,native_sha256=digest,
            source_revision=base['build_revision'],wake_package=__import__('codex_wake').__file__,
            source_rollout_sha256=hashlib.sha256(original).hexdigest(),source_unchanged=True,
            source_turn_count=3,children=children,child_readback_verified=True,checkpoint=pinned,
            rpc_methods=[call['method'] for call in methods],blocked_metadata_requests=requests,
            provider_model_turns=0,boundary='synthetic canonical persisted rollout consumed by actual installed native parser and existing thread/fork.lastTurnId; no model turn, goal defer, allocation or live session')
    finally:
        daemon.terminate()
        try:daemon.wait(timeout=10)
        except subprocess.TimeoutExpired:daemon.kill();daemon.wait(timeout=5)
        log.close();trap.shutdown();trap.server_close();worker.join(timeout=2)
    receipt['owned_daemon_exitcode']=daemon.returncode
    (root/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':main()
