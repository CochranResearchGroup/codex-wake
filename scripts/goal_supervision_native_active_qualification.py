"""Opt-in native active-turn controls using only an injected localhost Responses fixture.

No provider credentials, real billing or delegated accounting proof. Max5 HTTP
requests,90seconds; physical Unix socket is validated against exact owned peer.
SSE shapes follow openai/codex rust-v0.163.0 core/tests/common/responses.rs.
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
from codex_wake.process import process_identity


def qualify(base, codex):
    base.mkdir(parents=True,mode=0o700,exist_ok=False)
    home=base/'home';home.mkdir(mode=0o700)
    expiry=time.monotonic()+90
    result=dict(verdict='INCOMPLETE',usage_provenance='injected localhost SSE; not billing',
                external_provider_calls=0,http_request_cap=5)
    lock=threading.Lock();calls=[];stream_open=threading.Event();stream_disconnected=threading.Event();finish=threading.Event();operator_open=threading.Event();operator_release=threading.Event()
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args):pass
        def do_GET(self):
            self.send_error(404)
        def do_POST(self):
            length=int(self.headers.get('Content-Length','0'))
            if length>1024*1024:self.send_error(413);return
            body=self.rfile.read(length)
            with lock:
                calls.append(dict(number=len(calls)+1,path=self.path,body_sha256=hashlib.sha256(body).hexdigest()))
                number=len(calls)
            if number>5:self.send_error(429);return
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.end_headers()
            def emit(value):
                self.wfile.write(('event: '+value['type']+'\ndata: '+json.dumps(value)+'\n\n').encode());self.wfile.flush()
            try:
                emit(dict(type='response.created',response=dict(id='local-response-'+str(number))))
                if number==1:
                    emit(dict(type='response.output_item.done',item=dict(type='message',role='assistant',id='local-message',content=[dict(type='output_text',text='LOCAL FIXTURE READY')])) )
                    emit(dict(type='response.completed',response=dict(id='local-response-1',usage=dict(input_tokens=20,input_tokens_details=dict(cached_tokens=10),output_tokens=0,output_tokens_details=None,total_tokens=20))))
                elif b'Operator status question while the campaign stays paused.' in body:
                    operator_open.set()
                    while not operator_release.wait(.1) and not finish.is_set() and time.monotonic()<expiry:
                        self.wfile.write(b': operator reply pending\n\n');self.wfile.flush()
                    emit(dict(type='response.output_item.done',item=dict(type='message',role='assistant',
                        id='operator-message',content=[dict(type='output_text',text='OPERATOR REPLY AFTER PAUSE')])) )
                    emit(dict(type='response.completed',response=dict(id='local-response-3',usage=dict(
                        input_tokens=20,input_tokens_details=dict(cached_tokens=10),output_tokens=0,
                        output_tokens_details=None,total_tokens=20))))
                else:
                    stream_open.set()
                    while not finish.wait(.2) and time.monotonic()<expiry:
                        self.wfile.write(b': local fixture pending\n\n');self.wfile.flush()
            except (BrokenPipeError,ConnectionResetError):stream_disconnected.set()
            finally:self.close_connection=True
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    serving=threading.Thread(target=server.serve_forever,daemon=True);serving.start()
    port=server.server_address[1]
    (home/'config.toml').write_text('model="gpt-5.4-mini"\nmodel_provider="local_fixture"\napproval_policy="never"\nsandbox_mode="danger-full-access"\n[model_providers.local_fixture]\nname="Local fixture only"\nbase_url="http://127.0.0.1:'+str(port)+'/v1"\nwire_api="responses"\nrequires_openai_auth=false\nrequest_max_retries=0\nstream_max_retries=0\nsupports_websockets=false\n')
    (home/'config.toml').chmod(0o600)
    env=dict(os.environ,CODEX_HOME=str(home),OPENAI_BASE_URL='http://127.0.0.1:'+str(port)+'/v1')
    for key in ('CODEX_THREAD_ID','PYTHONPATH','OPENAI_API_KEY','CHATGPT_ACCESS_TOKEN','CODEX_API_KEY'):env.pop(key,None)
    alias=base/'native.sock';log=(base/'native.log').open('w');watchlog=(base/'watcher.log').open('w')
    native=None;watcher=None
    def save(name,value):
        path=base/name;path.write_text(json.dumps(value,indent=2)+'\n');path.chmod(0o600)
    try:
        native=subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(alias)],cwd=base,env=env,stdout=log,stderr=log,start_new_session=True)
        result.update(native_pid=native.pid,native_identity=process_identity(native.pid))
        end=min(expiry,time.monotonic()+10)
        while not(alias.exists() and stat.S_ISSOCK(alias.stat().st_mode)):
            if native.poll() is not None or time.monotonic()>end:raise RuntimeError('native startup unavailable')
            time.sleep(.05)
        physical=alias.resolve(strict=True);info=physical.lstat()
        assert info.st_uid==os.geteuid() and stat.S_ISSOCK(info.st_mode)
        assert physical.parent.stat().st_uid==os.geteuid() and physical.parent.stat().st_mode&0o077==0
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
            peer.settimeout(2);peer.connect(str(physical));pid,uid,_=struct.unpack('3i',peer.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        assert pid==native.pid and uid==os.geteuid()
        endpoint='unix://'+str(physical)
        def rpc(method,params):return native_request(endpoint,str(codex),method,params,3)
        thread=rpc('thread/start',dict(cwd=str(base),historyMode='legacy',experimentalRawEvents=True))['thread']['id']
        goal=rpc('thread/goal/set',dict(threadId=thread,objective='Local active supervision fixture; wait for controller checkpoint and stop',status='blocked',origin='user',tokenBudget=1000000))['goal']
        result.update(thread_id=thread,goal_before=goal,physical_endpoint=endpoint)
        first=rpc('turn/start',dict(threadId=thread,input=[dict(type='text',text='Local transport fixture: respond READY only.')]))
        end=min(expiry,time.monotonic()+15)
        while True:
            read=rpc('thread/read',dict(threadId=thread,includeTurns=True))['thread']
            if read['turns'] and all(t['status']=='completed' for t in read['turns']):break
            if time.monotonic()>end:raise RuntimeError('first local response not terminal')
            time.sleep(.1)
        result['first_native_turns']=[dict(id=t['id'],status=t['status']) for t in read['turns']]
        root=base/'runtime';policy=base/'policy.json'
        save('policy.json',dict(version=1,callers={thread:dict(app_server=endpoint,codex_path=str(codex),codex_home=str(home),allocation_id='local-active-fixture',max_tokens=1000,max_seconds=30,rpc_timeout=2)}))
        watcher=subprocess.Popen([sys.executable,'-m','codex_wake','--wake-root',str(root),'goal-limits','watch','--interval','.1'],env=env,stdin=subprocess.DEVNULL,stdout=watchlog,stderr=watchlog,start_new_session=True)
        result.update(watcher_pid=watcher.pid,watcher_identity=process_identity(watcher.pid))
        def cli(verb,*extra):
            v=subprocess.run([sys.executable,'-m','codex_wake','--wake-root',str(root),'goal-limits',verb,'--policy',str(policy),'--caller-thread-id',thread,'--json',*extra],env=env,capture_output=True,text=True,timeout=10)
            save('cli-'+verb+'.json',dict(code=v.returncode,stdout=v.stdout,stderr=v.stderr))
            if not v.stdout:raise RuntimeError('CLI '+verb+' unavailable: '+v.stderr[:200])
            return json.loads(v.stdout)
        end=min(expiry,time.monotonic()+6)
        while not cli('show').get('controller',{}).get('fresh'):
            if time.monotonic()>end:raise RuntimeError('watcher unavailable')
            time.sleep(.1)
        result['goal_active']=rpc('thread/goal/set',dict(threadId=thread,status='active',origin='user',tokenBudget=1000000))['goal']
        if not stream_open.wait(8):raise RuntimeError('active local stream not observed')
        result['active_turns_before_enrollment']=[dict(id=t['id'],status=t['status']) for t in rpc('thread/read',dict(threadId=thread,includeTurns=True))['thread']['turns']]
        from codex_wake.lifecycle_budget import trusted_upper
        end=min(expiry,time.monotonic()+8)
        while True:
            try:
                qualified_now=trusted_upper()
                if qualified_now>=goal['createdAt']:break
            except ValueError:pass
            if time.monotonic()>end:raise RuntimeError('qualified original goal clock unavailable')
            time.sleep(.1)
        result['clock_gate']=dict(qualified_upper=qualified_now,native_created_at=goal['createdAt'])
        result['enrollment']=cli('set','--token-limit','1000','--time-limit-seconds','30')
        if 'error' in result['enrollment']:
            raise RuntimeError('native enrollment rejected: '+json.dumps(result['enrollment']))
        save('progress.json',result)
        while time.monotonic()<expiry:
            state=cli('show');result['final_controller']=state
            if state.get('state')=='stopped':break
            time.sleep(.2)
        else:raise RuntimeError('90second packet wall limit')
        result['goal_after']=rpc('thread/goal/get',dict(threadId=thread))['goal']
        final=rpc('thread/read',dict(threadId=thread,includeTurns=True))['thread']
        result['final_native_turns']=[dict(id=t['id'],status=t['status']) for t in final['turns']]
        effects=state['effects'];assert state['stop_proof'] is True and result['goal_after']['status']=='paused'
        assert any(v['method']=='turn/steer' and v['state']=='acknowledged' for v in effects.values())
        assert any(v['method']=='turn/interrupt' and v['state']=='acknowledged' for v in effects.values())
        assert any(t['status']=='interrupted' for t in final['turns'])
        assert state['reason']=='allocation_exhausted'
        assert len(calls)<=5
        operator=rpc('turn/start',dict(threadId=thread,input=[dict(type='text',text='Operator status question while the campaign stays paused.')]))
        operator_turn=operator['turn']['id']
        result['operator_turn_id']=operator_turn
        if not operator_open.wait(8):raise RuntimeError('operator reply stream not observed')
        first_heartbeat=cli('show')['controller']['observed_boottime']
        end=min(expiry,time.monotonic()+8)
        while True:
            observed=cli('show')
            if observed['controller']['observed_boottime']>=first_heartbeat+.4:break
            if time.monotonic()>end:raise RuntimeError('independent operator observation unavailable')
            time.sleep(.05)
        operator_read=rpc('thread/read',dict(threadId=thread,includeTurns=True))['thread']
        result['operator_turns_before_release']=[dict(id=t['id'],status=t['status']) for t in operator_read['turns']]
        result['operator_observed_effects']=observed['effects']
        assert not any(v.get('method')=='turn/interrupt' and v.get('params',{}).get('turnId')==operator_turn
            for v in observed['effects'].values()), 'controller interrupted exact operator reply turn'
        assert any(t['id']==operator_turn and t['status']=='inProgress' for t in operator_read['turns']), 'operator turn not active before fixture release'
        assert rpc('thread/goal/get',dict(threadId=thread))['goal']['status']=='paused'
        operator_release.set()
        while time.monotonic()<end:
            operator_read=rpc('thread/read',dict(threadId=thread,includeTurns=True))['thread']
            current=next(t for t in operator_read['turns'] if t['id']==operator_turn)
            if current['status']=='completed':break
            if current['status']!='inProgress':raise RuntimeError('operator reply did not complete')
            time.sleep(.05)
        else:raise RuntimeError('operator reply completion unavailable')
        after=cli('show')
        assert not any(v.get('params',{}).get('turnId')==operator_turn for v in after['effects'].values())
        result.update(operator_turn_id=operator_turn,operator_reply_status=current['status'],
            operator_reply_preserved=True,operator_goal_status=rpc('thread/goal/get',dict(threadId=thread))['goal']['status'])
        result['verdict']='PASS_NATIVE_ACTIVE_AND_OPERATOR_REPLY_LOCAL_FIXTURE'
    except BaseException as exc:
        result.update(verdict='FAILED_PACKET',error=type(exc).__name__+': '+str(exc))
    finally:
        finish.set()
        for name,process in [('watcher',watcher),('native',native)]:
            if process is not None and process.poll() is None:
                if name=='native':os.killpg(process.pid,signal.SIGTERM)
                else:process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if name=='native':os.killpg(process.pid,signal.SIGKILL)
                    else:process.kill()
                    process.wait()
            if process is not None:result[name+'_exit']=process.returncode;result[name+'_after_identity']=process_identity(process.pid)
        server.shutdown();server.server_close();log.close();watchlog.close()
        result.update(http_calls=calls,stream_disconnected=stream_disconnected.is_set(),elapsed_seconds=90-max(0,expiry-time.monotonic()))
        save('result.json',result)
    print(json.dumps(dict(verdict=result['verdict'],error=result.get('error'),http_calls=len(calls),receipt=str(base/'result.json'))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--codex',type=Path,required=True)
    args=parser.parse_args();qualify(args.output.resolve(),args.codex.absolute())
