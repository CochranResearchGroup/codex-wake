"""Owned native timeout/recovery qualification; no model turns or provider calls.

An explicit Unix proxy delays one read to inject the transport timeout. All
healthy reads and native controls reach a private real Codex app-server.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from websockets.sync.server import unix_serve
from codex_wake.native_protocol import native_request
from codex_wake.a2a_bus import BusStore
from codex_wake.session_permissions import PermissionStore, Principal


def qualify(base,codex):
    base.mkdir(mode=0o700,parents=True,exist_ok=False)
    home=base/'home';home.mkdir(mode=0o700)
    env=dict(os.environ,CODEX_HOME=str(home),XDG_STATE_HOME=str(base/'state'))
    for key in ('PYTHONPATH','CODEX_THREAD_ID','OPENAI_API_KEY','CODEX_API_KEY','OPENAI_BASE_URL'):
        env.pop(key,None)
    root=base/'runtime';native_socket=base/'native.sock';proxy_socket=base/'proxy.sock'
    fault=base/'inject-one-timeout';calls=[];mutex=threading.Lock()
    log=(base/'native.log').open('w');watch_log=(base/'watcher.log').open('w')
    native=subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(native_socket)],
        cwd=base,env=env,stdout=log,stderr=log,start_new_session=True)
    watcher=None;result=dict(verdict='INCOMPLETE',model_calls=0,external_provider_calls=0,native_pid=native.pid)
    endpoint=None
    def rpc(method,params):return native_request(endpoint,str(codex),method,params,4)
    def proxy(ws):
        for raw in ws:
            item=json.loads(raw)
            if 'id' not in item:continue
            method=item['method']
            try:
                if method=='initialize':value={}
                else:
                    with mutex:
                        calls.append(method)
                        delay=method=='thread/read' and fault.exists()
                        if delay:fault.unlink()
                    if delay:
                        time.sleep(1.5)  # Explicit transport timeout fault, not readiness waiting.
                    value=rpc(method,item.get('params',{}))
                ws.send(json.dumps(dict(id=item['id'],result=value)))
            except Exception:return
    try:
        until=time.monotonic()+10
        while not native_socket.exists():
            if native.poll() is not None or time.monotonic()>until:raise RuntimeError('private native startup unavailable')
            time.sleep(.02)
        endpoint='unix://'+str(native_socket.resolve(strict=True))
        thread=rpc('thread/start',dict(cwd=str(base),historyMode='legacy'))['thread']['id']
        goal=rpc('thread/goal/set',dict(threadId=thread,objective='Owned observation recovery proof',
            status='blocked',origin='user',tokenBudget=100))['goal']
        with unix_serve(proxy,str(proxy_socket)) as server:
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            policy=base/'policy.json';policy.write_text(json.dumps(dict(version=1,callers={thread:dict(
                app_server='unix://'+str(proxy_socket),codex_path=str(codex),codex_home=str(home),
                allocation_id='owned-recovery',max_tokens=100,max_seconds=120,rpc_timeout=.5)})));policy.chmod(0o600)
            bus,cap=BusStore.configure(base/'bus')
            PermissionStore(root).configure({'version':1},Principal('operator','operator'),expected_revision=0)
            def cli(verb,*extra):
                p=subprocess.run([sys.executable,'-m','codex_wake','--wake-root',str(root),'goal-limits',verb,
                    '--policy',str(policy),'--caller-thread-id',thread,'--bus-root',str(bus.root),
                    '--operator-capability',str(cap),'--json',*extra],env=env,text=True,capture_output=True,timeout=10)
                return json.loads(p.stdout),p.returncode
            watcher=subprocess.Popen([sys.executable,'-m','codex_wake','--wake-root',str(root),
                'goal-limits','watch','--interval','.1'],env=env,stdout=watch_log,stderr=watch_log)
            def until(predicate):
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    value,code=cli('show')
                    if code==0 and predicate(value):return value
                    if watcher.poll() is not None:raise RuntimeError('watcher exited')
                    time.sleep(.03)
                raise AssertionError('qualification state not observed')
            until(lambda d:d.get('controller',{}).get('fresh'))
            original,code=cli('set','--token-limit','100','--time-limit-seconds','90','--checkpoint-seconds','0')
            assert code==0 and original['state']=='armed',original
            fault.write_text('one owned read timeout')
            stopped=until(lambda d:d.get('stop_latched') and d.get('stop_proof'))
            assert stopped['reason']=='observation_unavailable',stopped
            assert stopped['first_stop']['cause']=='TimeoutError',stopped['first_stop']
            healthy,code=cli('show');assert healthy['stop_latched']
            recovered,code=cli('recover','--operation-id','owned-recovery-once')
            assert code==0 and not recovered['stop_latched'],recovered
            for key in ('deadline','used_tokens','token_limit','time_limit_seconds','generation','allocation_id'):
                assert recovered[key]==original[key],key
            assert recovered['first_stop']==stopped['first_stop']
            assert rpc('thread/goal/get',dict(threadId=thread))['goal']['status']=='paused'
            continued=until(lambda d:d.get('state')=='armed' and not d.get('stop_latched'))
            result.update(verdict='PASS_NATIVE_TIMEOUT_AND_AUTHORIZED_RECOVERY',thread_id=thread,
                original=original,stopped=stopped,recovered=recovered,continued=continued,
                watcher_pid=watcher.pid,requests=calls,goal_not_auto_resumed=True)
            server.shutdown();worker.join(timeout=3)
    finally:
        if watcher is not None and watcher.poll() is None:
            watcher.terminate()
            try:watcher.wait(timeout=8)
            except subprocess.TimeoutExpired:watcher.kill();watcher.wait(timeout=3)
        if native.poll() is None:
            os.killpg(native.pid,signal.SIGTERM)
            try:native.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(native.pid,signal.SIGKILL);native.wait(timeout=3)
        log.close();watch_log.close()
        result.update(native_exit=native.poll(),watcher_exit=watcher.poll() if watcher else None,
            remaining_owned_processes=[p for p in [native.pid,watcher.pid if watcher else None] if p and Path('/proc',str(p)).exists()])
        (base/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    assert not result['remaining_owned_processes'],result
    print(json.dumps({k:result[k] for k in ('verdict','model_calls','external_provider_calls','remaining_owned_processes')}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--codex',type=Path,required=True)
    a=p.parse_args();qualify(a.output.resolve(),a.codex.resolve(strict=True))
