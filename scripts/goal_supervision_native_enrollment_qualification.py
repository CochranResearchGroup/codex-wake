"""Owned native-to-public-MCP enrollment; localhost Responses only, no billing proof.

Eight HTTP requests and120seconds maximum. No production configuration/grants.
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


def qualify(base, codex, import_boundary=False, governor=False):
    if governor and os.geteuid()!=1017:raise RuntimeError("governor native qualification requires UID1017")
    if governor and import_boundary:raise ValueError("governor and import-boundary modes are separate")
    tool_name="wake_governor_activate" if governor else "wake_goal_limits_set"
    os.umask(0o077)
    base.mkdir(mode=0o700, parents=True, exist_ok=False)
    home=base/'home';home.mkdir(mode=0o700)
    root=base/'runtime';policy=base/'policy.json'
    expiry=time.monotonic()+120;requests=[];ready=threading.Event();finish=threading.Event()
    result=dict(verdict='INCOMPLETE',external_provider_calls=0,http_request_cap=8,
                usage_provenance='injected localhost SSE; not billing')
    native=None;watcher=None;thread=None
    def save(name,value):
        path=base/name;path.write_text(json.dumps(value,indent=2)+'\n');path.chmod(0o600)
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args):pass
        def do_POST(self):
            size=int(self.headers.get('Content-Length','0'))
            if size>1024*1024:self.send_error(413);return
            data=json.loads(self.rfile.read(size));requests.append(data);number=len(requests)
            save('response-request-'+str(number)+'.json',data)
            if number>8:self.send_error(429);return
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.end_headers()
            def emit(value):
                self.wfile.write(('event: '+value['type']+'\ndata: '+json.dumps(value)+'\n\n').encode());self.wfile.flush()
            try:
                emit(dict(type='response.created',response=dict(id='local-'+str(number))))
                phase=(number-1)%3
                if phase==0:
                    item=dict(type='message',role='assistant',id='warmup-message',content=[dict(type='output_text',text='LOCAL READY')])
                elif phase==1:
                    namespaces=[t for t in data.get('tools',[]) if t.get('type')=='namespace' and any(v.get('name')==tool_name for v in t.get('tools',[]))]
                    if len(namespaces)!=1:raise RuntimeError('public enrollment tool namespace unavailable')
                    item=dict(type='function_call',namespace=namespaces[0]['name'],name=tool_name,call_id='owned-native-enrollment-'+str((number-1)//3+1),
                        arguments=json.dumps(dict(token_limit=1000,time_limit_seconds=120) if governor else dict(caller_thread_id=thread,token_limit=1000,time_limit_seconds=120,
                            checkpoint_token_percent=0,checkpoint_seconds=0)))
                else:
                    ready.set()
                    while not finish.wait(.1) and time.monotonic()<expiry:
                        self.wfile.write(b': local fixture pending\n\n');self.wfile.flush()
                    return
                emit(dict(type='response.output_item.done',item=item))
                emit(dict(type='response.completed',response=dict(id='local-'+str(number),usage=dict(
                    input_tokens=20,input_tokens_details=dict(cached_tokens=10),output_tokens=0,total_tokens=20))))
            except (BrokenPipeError,ConnectionResetError):pass
            except BaseException as exc:result['fixture_error']=type(exc).__name__+': '+str(exc)
            finally:self.close_connection=True
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True).start();port=server.server_address[1]
    config='model="gpt-5.4-mini"\nmodel_provider="local_fixture"\napproval_policy="never"\nsandbox_mode="danger-full-access"\n[model_providers.local_fixture]\nname="Local fixture only"\nbase_url="http://127.0.0.1:'+str(port)+'/v1"\nwire_api="responses"\nrequires_openai_auth=false\nrequest_max_retries=0\nstream_max_retries=0\nsupports_websockets=false\n[mcp_servers.wake]\ncommand='+json.dumps(sys.executable)+'\nargs='+json.dumps(['-m','codex_wake.mcp_server','--goal-limits-policy',str(policy),'--goal-limits-root',str(root),'--app-server','unix://'+str(base/'native.sock')])+'\n'
    (home/'config.toml').write_text(config);(home/'config.toml').chmod(0o600)
    config_hash=hashlib.sha256((home/'config.toml').read_bytes()).hexdigest()
    env=dict(os.environ,CODEX_HOME=str(home),OPENAI_BASE_URL='http://127.0.0.1:'+str(port)+'/v1')
    for key in ('CODEX_THREAD_ID','PYTHONPATH','OPENAI_API_KEY','CHATGPT_ACCESS_TOKEN','CODEX_API_KEY'):env.pop(key,None)
    alias=base/'native.sock';log=(base/'native.log').open('w');watchlog=(base/'watcher.log').open('w')
    try:
        native=subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(alias)],cwd=base,env=env,stdout=log,stderr=log,start_new_session=True)
        result.update(native_pid=native.pid,native_identity=process_identity(native.pid))
        end=min(expiry,time.monotonic()+10)
        while not(alias.exists() and stat.S_ISSOCK(alias.stat().st_mode)):
            if native.poll() is not None or time.monotonic()>end:raise RuntimeError('native startup unavailable')
            time.sleep(.05)
        physical=alias.resolve(strict=True);assert physical.parent.stat().st_uid==os.geteuid() and physical.parent.stat().st_mode&0o077==0
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
            peer.settimeout(2);peer.connect(str(physical));pid,uid,_=struct.unpack('3i',peer.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        assert pid==native.pid and uid==os.geteuid();endpoint='unix://'+str(physical);result['peer']=dict(pid=pid,uid=uid)
        # Discovery accepts the peer-qualified physical socket, not an arbitrary alias.
        config=config.replace(json.dumps('unix://'+str(alias)),json.dumps(endpoint))
        (home/'config.toml').write_text(config);(home/'config.toml').chmod(0o600)
        config_hash=hashlib.sha256((home/'config.toml').read_bytes()).hexdigest()
        result['mcp_endpoint']=endpoint
        def rpc(method,params):return native_request(endpoint,str(codex),method,params,5)
        def read_thread(identity):
            value=rpc('thread/read',dict(threadId=identity,includeTurns=not governor))['thread']
            if governor:
                turns=[];cursor=None;seen=set()
                while True:
                    params=dict(threadId=identity,limit=128,sortDirection='asc',itemsView='full')
                    if cursor is not None:params['cursor']=cursor
                    page=rpc('thread/turns/list',params);turns.extend(page['data'])
                    cursor=page.get('nextCursor')
                    if cursor is None:break
                    if cursor in seen or len(turns)>256:raise RuntimeError('bounded native turns pagination unavailable')
                    seen.add(cursor)
                value['turns']=turns
            return value
        grant=dict(app_server=endpoint,codex_path=str(codex),codex_home=str(home),max_tokens=1000,max_seconds=120,rpc_timeout=3)
        save('policy.json',dict(version=2,native_caller_binding=True,allocations={},self_enrollment=grant) if governor else dict(version=2,default_allocation='owned-objective',native_caller_binding=True,allocations={'owned-objective':grant}))
        policy_hash=hashlib.sha256(policy.read_bytes()).hexdigest()
        unrelated=rpc('thread/start',dict(cwd=str(base),historyMode='paginated' if governor else 'legacy',experimentalRawEvents=True))['thread']['id']
        unrelated_before=rpc('thread/goal/set',dict(threadId=unrelated,objective='Unrelated owned control; no model work',status='blocked',origin='user',tokenBudget=1000000))['goal']
        result['unrelated_control']=dict(thread_id=unrelated,goal_before=unrelated_before)
        watcher=subprocess.Popen([sys.executable,'-m','codex_wake','--wake-root',str(root),'goal-limits','watch','--interval','.1'],env=env,stdin=subprocess.DEVNULL,stdout=watchlog,stderr=watchlog,start_new_session=True)
        result.update(watcher_pid=watcher.pid,watcher_identity=process_identity(watcher.pid),participants=[])
        def show(caller):
            command=([sys.executable,'-m','codex_wake','--wake-root',str(root),'governor','status',caller,'--endpoint',endpoint,'--json'] if governor else [sys.executable,'-m','codex_wake','--wake-root',str(root),'goal-limits','show','--policy',str(policy),'--caller-thread-id',caller,'--json'])
            completed=subprocess.run(command,env=env,capture_output=True,text=True,timeout=8)
            if not completed.stdout:raise RuntimeError('public show unavailable: '+completed.stderr[:200])
            return json.loads(completed.stdout)
        first_state=None
        for index in range(2):
            ready.clear()
            thread=rpc('thread/start',dict(cwd=str(base),historyMode='paginated' if governor else 'legacy',experimentalRawEvents=True))['thread']['id']
            goal=rpc('thread/goal/set',dict(threadId=thread,objective='Owned public MCP resource continuation fixture',status='blocked',origin='user',tokenBudget=1000000))['goal']
            participant=dict(thread_id=thread,goal_before=goal);result['participants'].append(participant)
            rpc('turn/start',dict(threadId=thread,input=[dict(type='text',text='Local fixture warmup only.')]))
            end=min(expiry,time.monotonic()+15)
            while True:
                read=read_thread(thread)
                if read['turns'] and all(t['status']=='completed' for t in read['turns']):break
                if time.monotonic()>end:raise RuntimeError('warmup not completed')
                time.sleep(.1)
            from codex_wake.goal_supervision import _heartbeat, _directory
            while not (_heartbeat(_directory(root)).get('fresh') if governor else show(thread).get('controller',{}).get('fresh')):
                if time.monotonic()>end:raise RuntimeError('watcher not fresh')
                time.sleep(.1)
            from codex_wake.lifecycle_budget import trusted_upper
            while not governor and trusted_upper()<goal['createdAt']:
                if time.monotonic()>end:raise RuntimeError('qualified clock unavailable')
                time.sleep(.1)
            if import_boundary and index==0:
                from codex_wake.goal_usage import observe_usage
                observed=observe_usage(home,thread,goal['createdAt'],token_accounting='fresh')
                assert observed['state']=='qualified',observed
                boundary=dict(started_at=trusted_upper(),token_accounting='fresh',reset_anchor=observed['anchor'])
                host_policy=json.loads(policy.read_text())
                host_policy['allocations']['owned-objective']['initial_boundary']=boundary
                save('policy.json',host_policy);policy_hash=hashlib.sha256(policy.read_bytes()).hexdigest()
                result['imported_boundary']=dict(started_at=boundary['started_at'],prior_fresh_tokens=observed['used_tokens'])
            rpc('thread/goal/set',dict(threadId=thread,status='active',origin='user',tokenBudget=1000000))
            if not ready.wait(min(20,max(0,expiry-time.monotonic()))):raise RuntimeError('public tool result not observed')
            read=read_thread(thread);save('native-tool-readback-'+str(index+1)+'.json',read)
            items=[v for t in read['turns'] for v in t['items'] if v['type']=='mcpToolCall' and v.get('tool')==tool_name]
            assert len(items)==1,'expected exactly one native public enrollment'
            participant['native_tool_call']=items[0];assert not items[0].get('error') and items[0].get('status')!='failed',json.dumps(items[0])
            state=show(thread)
            if governor:
                until=min(expiry,time.monotonic()+8)
                while state.get('state')!='enforced' and time.monotonic()<until:
                    time.sleep(.1);state=show(thread)
            participant['public_status']=state
            if governor:
                assert state['state']=='enforced',json.dumps(state)
                assert state['watcher']['fresh'] is True,json.dumps(state)
                owner=state['owner_receipt']
                assert owner['native_guard']['status']=='armed', json.dumps(state)
                assert owner['allocation_id'].startswith('native-'),json.dumps(state)
                assert state['limits']['token_limit']==1000,json.dumps(state)
                assert state['usage']['lifetime_used_tokens']>=10,json.dumps(state)
                assert state['usage']['used_tokens']<=10,json.dumps(state)
                arguments=items[0].get('arguments',{})
                if isinstance(arguments,str):arguments=json.loads(arguments)
                assert set(arguments)=={'token_limit','time_limit_seconds'},arguments
            else:
                assert state['state']=='armed',json.dumps(state)
                assert state['controller']['fresh'] is True
                assert state['allocation_id']=='owned-objective' and state['token_accounting']=='fresh'
                assert state['used_tokens']==20*(index+1)-(10 if import_boundary else 0),json.dumps(state)
                if import_boundary:assert state['time_origin']==result['imported_boundary']['started_at']
                if first_state is None:first_state=state
                assert state['deadline']==first_state['deadline'] and state['time_origin']==first_state['time_origin']
                assert state['deadline']==state['time_origin']+120
            assert 'callers' not in json.loads(policy.read_text())
            assert hashlib.sha256(policy.read_bytes()).hexdigest()==policy_hash
            assert hashlib.sha256((home/'config.toml').read_bytes()).hexdigest()==config_hash
            rpc('thread/goal/set',dict(threadId=thread,status='paused',origin='user'))
            for turn in read['turns']:
                if turn['status']=='inProgress':rpc('turn/interrupt',dict(threadId=thread,turnId=turn['id']))
        result['unrelated_control']['goal_after']=rpc('thread/goal/get',dict(threadId=unrelated))['goal']
        assert result['unrelated_control']['goal_after']==unrelated_before,'unrelated control goal changed'
        result.update(policy_unchanged=True,config_unchanged=True,no_per_caller_grants=True,
            original_deadline_preserved=not governor,cumulative_tokens=None if governor else (30 if import_boundary else 40),unrelated_control_unchanged=True,model_activation_without_uuid=governor)
        result['verdict']='PASS_NATIVE_MODEL_GOVERNOR_ACTIVATION' if governor else ('PASS_NATIVE_PUBLIC_IMPORTED_BOUNDARY_AND_CONTINUATION' if import_boundary else 'PASS_NATIVE_PUBLIC_SELF_ENROLLMENT_AND_CONTINUATION')
    except BaseException as exc:result.update(verdict='FAILED_PACKET',error=type(exc).__name__+': '+str(exc))
    finally:
        finish.set()
        for name,process in [('watcher',watcher),('native',native)]:
            if process is not None and process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
            if process is not None:result[name+'_exit']=process.returncode;result[name+'_after_identity']=process_identity(process.pid)
        census=subprocess.run(['ps','-eo','pid=,ppid=,pgid=,args='],capture_output=True,text=True).stdout
        groups={str(p.pid) for p in (native,watcher) if p is not None}
        result['remaining_owned_processes']=[line for line in census.splitlines() if len(line.split(None,3))>=3 and line.split(None,3)[2] in groups]
        if result['remaining_owned_processes']:result['verdict']='FAILED_CLEANUP'
        server.shutdown();server.server_close();log.close();watchlog.close()
        result.update(http_requests=len(requests),elapsed_seconds=120-max(0,expiry-time.monotonic()))
        save('result.json',result)
    print(json.dumps(dict(verdict=result['verdict'],error=result.get('error'),http_requests=len(requests),receipt=str(base/'result.json'))))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--codex',type=Path,required=True)
    parser.add_argument('--import-boundary',action='store_true',help='prove initial host renewal anchor/time import before admission')
    parser.add_argument('--governor',action='store_true',help='model activates governor using native caller identity, without UUID grants; UID1017 only')
    args=parser.parse_args();outcome=qualify(args.output.resolve(),args.codex.absolute(),args.import_boundary,args.governor)
    if args.governor:raise SystemExit(0 if outcome['verdict'].startswith('PASS_') else 1)
