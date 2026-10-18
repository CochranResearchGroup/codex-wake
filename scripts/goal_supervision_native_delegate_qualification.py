"""Bounded native delegation with localhost-injected Responses, never real billing.

Explicit opt-in. Max90seconds,5 local POSTs. Response/function SSE shapes follow
openai/codex rust-v0.163.0 core/tests/common/responses.rs. No credentials used.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import socket
import stat
import struct
import subprocess
import sys
import threading
import time

from codex_wake.native_protocol import native_request
from codex_wake.goal_usage import observe_usage
from codex_wake.process import process_identity


def qualify(base,codex):
    base.mkdir(parents=True,mode=0o700,exist_ok=False);home=base/'home';home.mkdir(mode=0o700)
    calls=[];root_identity=[None];child_done=threading.Event();lock=threading.Lock();expiry=time.monotonic()+90
    result=dict(verdict='INCOMPLETE',external_provider_calls=0,usage_provenance='injected localhost SSE, not real billing',expected_tokens=45)
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args):pass
        def do_GET(self):self.send_error(404)
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
            metadata=body.get('client_metadata',{});nested=metadata.get('x-codex-turn-metadata','{}')
            if isinstance(nested,str):nested=json.loads(nested)
            identity=nested.get('thread_id') or metadata.get('thread_id') or nested.get('session_id')
            with lock:
                if root_identity[0] is None:root_identity[0]=identity
                root=identity==root_identity[0];root_number=sum(c['root'] for c in calls)+1 if root else 0
                number=len(calls)+1
                tools=body.get('tools',[])
                calls.append(dict(number=number,path=self.path,thread_id=identity,root=root,
                    root_turn_id=nested.get('root_turn_id'),tool_names=[t.get('name') for t in tools],
                    body_sha256=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()))
            if number>5:self.send_error(429);return
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.end_headers()
            def emit(value):self.wfile.write(('event: '+value['type']+'\ndata: '+json.dumps(value)+'\n\n').encode());self.wfile.flush()
            response_id='local-delegate-'+str(number)
            try:
                emit(dict(type='response.created',response=dict(id=response_id)))
                if number==1:
                    namespace='multi_agent_v1';name='spawn_agent'
                    # Prefer the actual advertised namespace when available.
                    for tool in tools:
                        if tool.get('type')=='namespace' and any(x.get('name')=='spawn_agent' for x in tool.get('tools',[])):
                            namespace=tool['name']
                    arguments=dict(message='Complete only this local injected fixture task.',fork_context=True)
                    emit(dict(type='response.output_item.done',item=dict(type='function_call',call_id='local-spawn',namespace=namespace,name=name,arguments=json.dumps(arguments))))
                    total=20
                else:
                    if root and root_number==2:
                        child_done.wait(max(0,min(10,expiry-time.monotonic())));total=40
                    elif not root:
                        total=30;child_done.set()
                    else:total=0
                    emit(dict(type='response.output_item.done',item=dict(type='message',role='assistant',id='message-'+str(number),content=[dict(type='output_text',text='LOCAL DELEGATE FIXTURE DONE')])) )
                calls[number-1].update(response_id=response_id,injected_total_tokens=total)
                emit(dict(type='response.completed',response=dict(id=response_id,usage=dict(input_tokens=total,input_tokens_details=dict(cached_tokens=total//2),output_tokens=0,output_tokens_details=None,total_tokens=total))))
            except (BrokenPipeError,ConnectionResetError):pass
            finally:self.close_connection=True
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True;threading.Thread(target=server.serve_forever,daemon=True).start();port=server.server_address[1]
    (home/'config.toml').write_text('model="gpt-5.4-mini"\nmodel_provider="local_fixture"\napproval_policy="never"\nsandbox_mode="danger-full-access"\n[features]\nmulti_agent=true\nmulti_agent_v2=false\ncode_mode=false\n[model_providers.local_fixture]\nname="Local only"\nbase_url="http://127.0.0.1:'+str(port)+'/v1"\nwire_api="responses"\nrequires_openai_auth=false\nrequest_max_retries=0\nstream_max_retries=0\nsupports_websockets=false\n');(home/'config.toml').chmod(0o600)
    env=dict(os.environ,CODEX_HOME=str(home),OPENAI_BASE_URL='http://127.0.0.1:'+str(port)+'/v1')
    for key in ('PYTHONPATH','CODEX_THREAD_ID','OPENAI_API_KEY','CHATGPT_ACCESS_TOKEN','CODEX_API_KEY'):env.pop(key,None)
    log=(base/'native.log').open('w');native=None
    def save(name,value):p=base/name;p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o600)
    try:
        alias=base/'native.sock';native=subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(alias)],env=env,cwd=base,stdout=log,stderr=log,start_new_session=True);result.update(native_pid=native.pid,native_identity=process_identity(native.pid))
        end=time.monotonic()+10
        while not(alias.exists() and stat.S_ISSOCK(alias.stat().st_mode)):
            if native.poll() is not None or time.monotonic()>end:raise RuntimeError('native socket unavailable')
            time.sleep(.05)
        target=alias.resolve(strict=True);info=target.lstat();assert info.st_uid==os.geteuid() and stat.S_ISSOCK(info.st_mode)
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
            peer.settimeout(2);peer.connect(str(target));pid,uid,_=struct.unpack('3i',peer.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        assert pid==native.pid and uid==os.geteuid();endpoint='unix://'+str(target)
        def rpc(method,params):return native_request(endpoint,str(codex),method,params,3)
        root=rpc('thread/start',dict(cwd=str(base),historyMode='legacy',experimentalRawEvents=True))['thread']['id'];result['root_thread_id']=root
        goal=rpc('thread/goal/set',dict(threadId=root,status='blocked',origin='user',tokenBudget=1000,objective='Bounded local native delegated accounting fixture'))['goal'];result['goal']=goal
        rpc('turn/start',dict(threadId=root,input=[dict(type='text',text='Run only the approved local delegated fixture.')]))
        while time.monotonic()<expiry:
            read=rpc('thread/read',dict(threadId=root,includeTurns=True))['thread'];result['root_native_turns']=[dict(id=t['id'],status=t['status']) for t in read['turns']]
            if child_done.is_set() and read['turns'] and all(t['status']=='completed' for t in read['turns']):break
            if len(calls)>5:raise RuntimeError('local HTTP request cap exceeded')
            time.sleep(.1)
        else:raise RuntimeError('native delegation packet90second limit')
        inventories=[];responses=[]
        for path in (home/'sessions').rglob('*.jsonl'):
            rows=[json.loads(line) for line in path.read_text().splitlines()];meta=rows[0]['payload'];inventories.append({k:meta.get(k) for k in ['id','session_id','parent_thread_id','source','history_mode','history_base','subagent_history_start_ordinal']})
            for row in rows:
                if row['type']=='token_usage_record':responses.append(row['payload'])
        result.update(metadata=inventories,native_response_records=responses,accounting=observe_usage(home,root,goal['createdAt']))
        assert any(m['parent_thread_id']==root for m in inventories),'no actual child metadata'
        assert len(calls)<=5
        if result['accounting']['state']=='qualified':
            assert result['accounting']['used_tokens']==45,result['accounting']
            inclusive=observe_usage(home,root,goal['createdAt'],token_accounting='cache_inclusive')
            assert inclusive['state']=='qualified' and inclusive['used_tokens']==90,inclusive
            result['cache_inclusive_accounting']=inclusive
            result['verdict']='PASS_NATIVE_DELEGATE_INJECTED_ACCOUNTING'
        else:result['verdict']='NATIVE_DELEGATE_ACCOUNTING_UNKNOWN'
    except BaseException as exc:result.update(verdict='FAILED_PACKET',error=type(exc).__name__+': '+str(exc))
    finally:
        if native is not None and native.poll() is None:
            os.killpg(native.pid,signal.SIGTERM)
            try:native.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(native.pid,signal.SIGKILL);native.wait()
        server.shutdown();server.server_close();log.close()
        if native is not None:result.update(native_exit=native.returncode,native_after_identity=process_identity(native.pid))
        result.update(http_calls=calls,elapsed_seconds=90-max(0,expiry-time.monotonic()))
        save('result.json',result)
    print(json.dumps({k:result.get(k) for k in ['verdict','error','accounting','elapsed_seconds']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--codex',type=Path,required=True);a=p.parse_args();qualify(a.output.resolve(),a.codex.absolute())
