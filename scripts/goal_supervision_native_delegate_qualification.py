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
from codex_wake.goal_usage import observe_usage, observe_session_usage
from codex_wake.process import process_identity



def fixture_processes(base):
    values=[]
    for process in Path('/proc').glob('[0-9]*'):
        try:
            pid=int(process.name)
            if pid==os.getpid() or process.stat().st_uid!=os.geteuid():continue
            arguments=process.joinpath('cmdline').read_bytes().decode(errors='replace').split('\0')
            cwd=process.joinpath('cwd').resolve(strict=True)
            if cwd==base or any(value==str(base) or value.startswith(str(base)+'/') or value.startswith('unix://'+str(base)+'/') for value in arguments):
                values.append(dict(pid=pid,identity=process_identity(pid),sleep=any(Path(value).name=='sleep' for value in arguments if value)))
        except (OSError,ValueError):pass
    return values

def qualify(base,codex,*,wake_cli=None,governor_stop=None):
    os.umask(0o077)
    base.mkdir(parents=True,mode=0o700,exist_ok=False);home=base/'home';home.mkdir(mode=0o700)
    calls=[];root_identity=[None];peer_identity=[None];child_identity=[None]
    child_done=threading.Event();provider_started=threading.Event();peer_started=threading.Event();child_started=threading.Event()
    lease_ready=threading.Event();release=threading.Event();lock=threading.Lock();began=time.monotonic();expiry=began+90
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
                root=identity==root_identity[0];peer=identity==peer_identity[0];root_number=sum(c['root'] for c in calls)+1 if root else 0
                number=len(calls)+1
                tools=body.get('tools',[])
                calls.append(dict(number=number,path=self.path,thread_id=identity,root=root,
                    root_turn_id=nested.get('root_turn_id'),turn_id=nested.get('turn_id'),peer=peer,tool_names=[t.get('name') for t in tools],
                    body_sha256=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()))
            if number>5:self.send_error(429);return
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.end_headers()
            def emit(value):self.wfile.write(('event: '+value['type']+'\ndata: '+json.dumps(value)+'\n\n').encode());self.wfile.flush()
            response_id='local-delegate-'+str(number)
            try:
                emit(dict(type='response.created',response=dict(id=response_id)))
                if governor_stop:
                    if number==1:
                        provider_started.set()
                        if not lease_ready.wait(max(0,min(20,expiry-time.monotonic()))):return
                    elif number==5:
                        emit(dict(type='response.output_item.done',item=dict(type='message',role='assistant',id='resumed',content=[dict(type='output_text',text='LOCAL GUARDED RESUME DONE')])))
                        emit(dict(type='response.completed',response=dict(id=response_id,usage=dict(input_tokens=2,input_tokens_details=dict(cached_tokens=0),output_tokens=0,total_tokens=2))))
                        calls[number-1].update(response_id=response_id,injected_total_tokens=2,guarded_resume=True)
                        return
                    else:
                        if peer:
                            calls[number-1].update(response_id=response_id,injected_total_tokens=None,pending_at_stop=True)
                            peer_started.set();release.wait(max(0,expiry-time.monotonic()));return
                        namespace=None
                        for tool in tools:
                            if tool.get('type')=='namespace' and any(item.get('name')=='exec_command' for item in tool.get('tools',[])):namespace=tool['name']
                        item=dict(type='function_call',call_id='local-sleep-root' if root else 'local-sleep-child',name='exec_command',
                            arguments=json.dumps(dict(cmd='sleep 90',yield_time_ms=30000,max_output_tokens=128)))
                        if namespace:item['namespace']=namespace
                        emit(dict(type='response.output_item.done',item=item))
                        total=40 if root else 30
                        calls[number-1].update(response_id=response_id,injected_total_tokens=total)
                        emit(dict(type='response.completed',response=dict(id=response_id,usage=dict(input_tokens=total,
                            input_tokens_details=dict(cached_tokens=total//2),output_tokens=0,output_tokens_details=None,total_tokens=total))))
                        if not root:child_identity[0]=identity;child_started.set()
                        return
                if number==1:
                    namespace='multi_agent_v1';name='spawn_agent'
                    # Prefer the actual advertised namespace when available.
                    for tool in tools:
                        if tool.get('type')=='namespace' and any(x.get('name')=='spawn_agent' for x in tool.get('tools',[])):
                            namespace=tool['name']
                    arguments=(dict(message='Complete only this local injected fixture task.',task_name='governor_child',fork_turns='all') if governor_stop else dict(message='Complete only this local injected fixture task.',fork_context=True))
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
    if governor_stop:
        config=(home/'config.toml').read_text().replace('multi_agent_v2=false','multi_agent_v2=true')
        (home/'config.toml').write_text(config)
    env=dict(os.environ,CODEX_HOME=str(home),OPENAI_BASE_URL='http://127.0.0.1:'+str(port)+'/v1')
    for key in ('PYTHONPATH','CODEX_THREAD_ID','OPENAI_API_KEY','CHATGPT_ACCESS_TOKEN','CODEX_API_KEY'):env.pop(key,None)
    log=(base/'native.log').open('w');native=None;watcher=None
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
        def rpc(method,params):
            remaining=min(3,expiry-time.monotonic())
            if remaining<=0:raise RuntimeError('native delegation packet90second limit')
            return native_request(endpoint,str(codex),method,params,remaining)
        root=rpc('thread/start',dict(cwd=str(base),historyMode='paginated' if governor_stop else 'legacy',experimentalRawEvents=True))['thread']['id'];result['root_thread_id']=root
        goal=None if governor_stop else rpc('thread/goal/set',dict(threadId=root,status='blocked',origin='user',tokenBudget=1000,objective='Bounded local native delegated accounting fixture'))['goal'];result['goal']=goal
        started=rpc('turn/start',dict(threadId=root,input=[dict(type='text',text='Run only the approved local delegated fixture.')]))
        result['root_initial_turn_id']=started['turn']['id']
        if governor_stop:
            if wake_cli is None:raise RuntimeError('--wake-cli is required for governor stop qualification')
            if not provider_started.wait(min(10,max(0,expiry-time.monotonic()))):raise RuntimeError('root local response did not start')
            peer_thread=rpc('thread/start',dict(cwd=str(base),historyMode='paginated' if governor_stop else 'legacy',experimentalRawEvents=True))['thread']['id']
            peer_identity[0]=peer_thread
            peer_goal=rpc('thread/goal/set',dict(threadId=peer_thread,status='blocked',origin='user',tokenBudget=1000,objective='Unrelated local fixture; must remain active'))['goal']
            peer_turn=rpc('turn/start',dict(threadId=peer_thread,input=[dict(type='text',text='Hold only the unrelated local injected response.')]))['turn']['id']
            if not peer_started.wait(min(10,max(0,expiry-time.monotonic()))):raise RuntimeError('unrelated local response did not start')
            wake_root=base/'wake';wake_root.mkdir(mode=0o700)
            watcher_log=(base/'watcher.log').open('w')
            try:
                watcher=subprocess.Popen([sys.executable,'-m','codex_wake.self_limits','watch',str(wake_root)],
                    env=env,cwd=base,stdin=subprocess.DEVNULL,stdout=watcher_log,stderr=watcher_log,start_new_session=True)
            finally:watcher_log.close()
            result.update(watcher_pid=watcher.pid,watcher_identity=process_identity(watcher.pid),governor_stop=governor_stop,
                unrelated_thread_id=peer_thread,unrelated_turn_id=peer_turn,unrelated_goal_before=peer_goal)
            until=min(expiry,time.monotonic()+5)
            while not (wake_root/'goal-supervision/controller.json').exists():
                if watcher.poll() is not None or time.monotonic()>=until:raise RuntimeError('private watcher did not become ready')
                time.sleep(.05)
            operation_number=[0]
            def governor(verb,**options):
                argv=[str(wake_cli),'--wake-root',str(wake_root),'governor',verb,root,'--endpoint',endpoint,'--json']
                for key,value in options.items():
                    if value is True:argv.append('--'+key.replace('_','-'))
                    else:argv.extend(['--'+key.replace('_','-'),str(value)])
                remaining=min(15,expiry-time.monotonic())
                if remaining<=0:raise RuntimeError('governor packet wall clock exhausted')
                completed=subprocess.run(argv,env=env,cwd=base,capture_output=True,text=True,timeout=remaining)
                operation_number[0]+=1
                try:body=json.loads(completed.stdout)
                except ValueError:raise RuntimeError('governor returned non-JSON: '+completed.stderr[-1000:])
                save('governor-'+str(operation_number[0])+'.json',dict(argv=argv,exit_code=completed.returncode,result=body,stderr=completed.stderr[-1000:]))
                return body
            activated=governor('activate',token_limit=1000,time_limit_seconds=120)
            until=min(expiry,time.monotonic()+8)
            while activated.get('state')!='enforced':
                if time.monotonic()>=until:raise RuntimeError('new governor was not actually enforced: '+str(activated.get('reason')))
                time.sleep(.1);activated=governor('status')
            owner=activated['owner_receipt'];guard=owner['native_guard']
            assert owner.get('requires_native_guard') is True and activated['watcher']['native_guard_qualified'] is True
            assert owner['controller']['pid']==watcher.pid
            assert any(item['threadId']==root and started['turn']['id'] in item['turnIds'] for item in guard['member_turns'])
            result.update(activation=activated,initial_lease=guard,child_started_after_lease=True)
            stop_guard=guard
            if governor_stop=='watcher-loss':
                os.kill(watcher.pid,signal.SIGSTOP)
                result['watcher_stopped_before_spawn']=True
            lease_ready.set()
            lease_left=guard['ttl_ms']/1000-(time.clock_gettime(time.CLOCK_BOOTTIME)-guard['ack_boottime'])
            if not child_started.wait(max(0,min(8,lease_left-.25,expiry-time.monotonic()))):raise RuntimeError('child did not start before the original native lease expiry')
            child=child_identity[0];result['child_thread_id']=child
            result['initial_lease_excludes_child']=all(item['threadId']!=child for item in guard['member_turns'])
            assert result['initial_lease_excludes_child'],'fixture did not create a late child'
            until=min(expiry,time.monotonic()+2)
            while True:
                accounting=observe_session_usage(home,root)
                if accounting.get('state')=='qualified' and accounting.get('used_tokens')==45 and child in accounting.get('thread_ids',[]):break
                if time.monotonic()>=until:raise RuntimeError('original native history did not qualify the live child before stop')
                time.sleep(.05)
            result['qualified_accounting_before_stop']=accounting
            result['child_goal_before_stop']=rpc('thread/goal/get',dict(threadId=child))['goal']
            until=min(expiry,time.monotonic()+2)
            while True:
                sleepers=[value for value in fixture_processes(base) if value['sleep']]
                if len(sleepers)==2:break
                if time.monotonic()>=until:raise RuntimeError('both real fixture sleep tools did not start')
                time.sleep(.05)
            result['active_fixture_tools']=sleepers
            if governor_stop=='watcher-loss':
                os.kill(watcher.pid,signal.SIGKILL);watcher.wait(timeout=3)
                result['watcher_killed_before_child_poll']=True
            else:
                until=min(expiry,time.monotonic()+8)
                while True:
                    observed=governor('status')
                    if child in observed['owner_receipt'].get('qualified_task_members',[]):break
                    if time.monotonic()>=until:raise RuntimeError('watcher never qualified actual child history')
                    time.sleep(.1)
                result['before_tighten']=observed
                result['tighten']=governor('activate',token_limit=1,time_limit_seconds=120)
                stop_guard=result['tighten']['owner_receipt']['native_guard']
            def view(thread):
                turns=rpc('thread/turns/list',dict(threadId=thread,limit=128,sortDirection='desc',itemsView='notLoaded'))['data']
                selected=rpc('thread/goal/get',dict(threadId=thread))['goal']
                return dict(goal=selected,turns=[dict(id=turn['id'],status=turn['status']) for turn in turns])
            until=min(expiry,time.monotonic()+20)
            while True:
                root_view=view(root);child_view=view(child)
                if root_view['goal'] is None and not any(turn['status']=='inProgress' for turn in root_view['turns']+child_view['turns']):break
                if time.monotonic()>=until:raise RuntimeError('native lease did not stop exact root and late child')
                time.sleep(.1)
            until=min(expiry,time.monotonic()+3)
            while any(process_identity(value['pid'])==value['identity'] for value in sleepers):
                if time.monotonic()>=until:raise RuntimeError('native cancellation left exact fixture tools running')
                time.sleep(.05)
            result['native_cancelled_fixture_tools']=True
            peer_view=view(peer_thread)
            assert any(turn['id']==peer_turn and turn['status']=='inProgress' for turn in peer_view['turns']),'unrelated task was interrupted'
            assert peer_view['goal']['status']==peer_goal['status'],'unrelated goal was changed'
            assert any(turn['id']==started['turn']['id'] and turn['status']=='interrupted' for turn in root_view['turns'])
            assert any(turn['status']=='interrupted' for turn in child_view['turns'])
            lease=rpc('thread/governorLease/set',dict(threadId=root,leaseId=stop_guard['lease_id'],
                controllerGeneration=stop_guard['controller_generation'],enrollmentRevision=stop_guard['enrollment_revision'],query=True))
            assert lease.get('expired') is True and lease.get('stopVerified') is True,lease
            if result['child_goal_before_stop'] is None:assert child_view['goal'] is None,'governor created a hidden child goal'
            metadata=[]
            for path in (home/'sessions').rglob('*.jsonl'):
                with path.open() as stream:header=json.loads(stream.readline(65537))
                if header.get('payload',{}).get('id') in (root,child,peer_thread):
                    item=header['payload'];metadata.append({key:item.get(key) for key in ('id','parent_thread_id','source','session_id')})
            result['metadata']=metadata
            result.update(root_after_stop=root_view,child_after_stop=child_view,unrelated_after_stop=peer_view,native_lease_after_stop=lease,
                verdict='PASS_NATIVE_GOVERNOR_'+governor_stop.upper().replace('-','_'),accounting=observe_session_usage(home,root),
                expected_tokens=45,completed_response_tokens_only=True)
            if governor_stop=='watcher-loss':
                watcher_log=(base/'watcher-repaired.log').open('w')
                try:watcher=subprocess.Popen([sys.executable,'-m','codex_wake.self_limits','watch',str(wake_root)],env=env,cwd=base,stdin=subprocess.DEVNULL,stdout=watcher_log,stderr=watcher_log,start_new_session=True)
                finally:watcher_log.close()
                result['repaired_watcher_identity']=process_identity(watcher.pid)
                from codex_wake.goal_supervision import _heartbeat, _directory
                until=min(expiry,time.monotonic()+5)
                while not _heartbeat(_directory(wake_root)).get('fresh'):
                    if time.monotonic()>=until:raise RuntimeError('repaired watcher did not become fresh')
                    time.sleep(.1)
            resumed=governor('extend',add_tokens=1000,add_seconds=60,resume=True)
            result['guarded_resume']=resumed
            assert resumed.get('operation',{}).get('resumed') is True,resumed
            until=min(expiry,time.monotonic()+8)
            while len(calls)<5:
                if time.monotonic()>=until:raise RuntimeError('guarded resume did not make exactly one local request')
                time.sleep(.05)
            assert len(calls)==5 and calls[-1].get('guarded_resume'),calls
            after=view(root);result['root_after_guarded_resume']=after
            assert after['goal'] is None,'guarded resume created hidden goal'
            old_ids={turn['id'] for turn in root_view['turns']}
            new_ids={turn['id'] for turn in after['turns']}-old_ids
            assert len(new_ids)==1,new_ids
            assert resumed['operation'].get('started_turn_id')==next(iter(new_ids)),resumed
            result['guarded_started_turn_id']=next(iter(new_ids))
            assert len(calls)<=5
            return result
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
        release.set();lease_ready.set()
        if watcher is not None and watcher.poll() is None:
            os.kill(watcher.pid,signal.SIGKILL);watcher.wait(timeout=3)
        if watcher is not None:result.update(watcher_exit=watcher.returncode,watcher_after_identity=process_identity(watcher.pid))
        if native is not None and native.poll() is None:
            os.killpg(native.pid,signal.SIGTERM)
            try:native.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(native.pid,signal.SIGKILL);native.wait()
        server.shutdown();server.server_close();log.close()
        if native is not None:result.update(native_exit=native.returncode,native_after_identity=process_identity(native.pid))
        result.update(http_calls=calls,elapsed_seconds=time.monotonic()-began)
        if result['elapsed_seconds']>90 and result['verdict'].startswith('PASS_'):result['verdict']='FAILED_PACKET_WALL_BUDGET'
        owned=fixture_processes(base)
        if owned:
            result['cleanup_owned_processes_before_signals']=owned
            for process in owned:
                if process_identity(process['pid'])==process['identity']:
                    try:os.kill(process['pid'],signal.SIGKILL)
                    except ProcessLookupError:pass
            until=time.monotonic()+3
            while fixture_processes(base) and time.monotonic()<until:time.sleep(.05)
            owned=fixture_processes(base)
        result['final_owned_processes']=owned
        if owned:result.update(verdict='FAILED_CLEANUP',cleanup_error='task-owned processes remain')
        save('result.json',result)
        print(json.dumps({k:result.get(k) for k in ['verdict','error','accounting','elapsed_seconds']}))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--codex',type=Path,required=True);p.add_argument('--wake-cli',type=Path);p.add_argument('--governor-stop',choices=('limit','watcher-loss'));a=p.parse_args()
    if a.governor_stop and a.wake_cli is None:p.error('--governor-stop requires --wake-cli')
    if a.governor_stop and os.geteuid()!=1017:p.error('governor stop qualification requires disposable codex-daemon-test UID1017')
    outcome=qualify(a.output.resolve(),a.codex.absolute(),wake_cli=a.wake_cli.absolute() if a.wake_cli else None,governor_stop=a.governor_stop)
    if a.governor_stop:raise SystemExit(0 if outcome['verdict'].startswith('PASS_') else 1)
