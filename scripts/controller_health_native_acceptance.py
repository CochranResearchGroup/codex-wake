#!/usr/bin/env python3
"""390 disposable native PTY qualification. Requires Linux, pyte==0.8.2 and websockets.

Only supplied private package processes are started/attached. All homes/endpoints
are new fixture-owned paths. No prompt is submitted and no credentials are read.
"""
import argparse
import ctypes
import errno
import fcntl
import hashlib
import http.server
import threading
import json
import os
from pathlib import Path
import pty
import select
import signal
import stat
import struct
import socket
import subprocess
import termios
import time
from uuid import uuid4


def require(value, message):
    if not value: raise AssertionError(message)


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--codex',type=Path,required=True)
    parser.add_argument('--models',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,required=True)
    parser.add_argument('--expect-unsupported',action='store_true')
    args=parser.parse_args()
    import pyte
    from codex_wake.native_protocol import native_request,NativeCapabilityUnavailable
    from codex_wake.controller_health import ControllerHealth
    root=args.artifacts.resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    home=root/'home';home.mkdir();cwd=root/'work';cwd.mkdir();wake=root/'wake';wake.mkdir()
    requests=[]
    class Trap(http.server.BaseHTTPRequestHandler):
        def reject(self):
            requests.append(self.command);self.send_response(503);self.end_headers()
        do_GET=do_POST=do_CONNECT=reject
        def log_message(self,*args):pass
    trap=http.server.ThreadingHTTPServer(('127.0.0.1',0),Trap)
    trap_thread=threading.Thread(target=trap.serve_forever,daemon=True);trap_thread.start()
    trap_url=f'http://127.0.0.1:{trap.server_port}'
    model=json.loads(args.models.read_text())['models'][0]
    catalog=home/'models.json';catalog.write_text(json.dumps({'models':[model]}))
    config=f'''model = {json.dumps(model['slug'])}
model_provider = "health_fixture"
model_catalog_json = {json.dumps(str(catalog))}
check_for_update_on_startup = false
[analytics]
enabled = false
[model_providers.health_fixture]
name = "No model turn qualification fixture"
base_url = "{trap_url}/never-query"
wire_api = "responses"
requires_openai_auth = false
[projects.{json.dumps(str(cwd))}]
trust_level = "trusted"
'''
    (home/'config.toml').write_text(config)
    env={key:os.environ[key] for key in ('PATH','LANG','LD_LIBRARY_PATH') if key in os.environ}
    env.update(HOME=str(home),CODEX_HOME=str(home),XDG_CONFIG_HOME=str(root/'config'),XDG_DATA_HOME=str(root/'data'),XDG_STATE_HOME=str(root/'state'),XDG_CACHE_HOME=str(root/'cache'),TERM='xterm-256color',NO_PROXY='127.0.0.1,localhost',HTTPS_PROXY=trap_url,HTTP_PROXY=trap_url,ALL_PROXY=trap_url)
    binary=args.codex.resolve();endpoint='unix://'+str(root/'native.sock')
    daemon_log=(root/'daemon.log').open('wb');daemon=subprocess.Popen([str(binary),'app-server','--listen',endpoint],cwd=cwd,env=env,stdout=daemon_log,stderr=subprocess.STDOUT,start_new_session=True)
    ui=None;master=None;stopped_tid=None
    receipt={'schema_version':1,'ticket':390,'native_executable':str(binary),'native_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'fixture_only':True}
    def rpc(method,body,timeout=3):
        from websockets.sync.client import unix_connect
        from codex_wake.records import WakeError
        deadline=time.monotonic()+timeout
        with unix_connect(endpoint[7:],open_timeout=timeout,close_timeout=.2,max_size=1048576,compression=None) as ws:
            def call(identifier,name,params):
                ws.send(json.dumps({'id':identifier,'method':name,'params':params}))
                while True:
                    frame=json.loads(ws.recv(timeout=max(.001,deadline-time.monotonic())))
                    if frame.get('id')!=identifier:continue
                    if 'error' in frame:
                        with (root/'rpc-rejections.jsonl').open('a') as out:out.write(json.dumps({'method':name,'frame':frame})+'\n')
                        raise WakeError(json.dumps(frame['error']))
                    return frame['result']
            call(1,'initialize',{'clientInfo':{'name':'health390_fixture','version':'1'},'capabilities':{'experimentalApi':True}})
            ws.send(json.dumps({'method':'initialized'}))
            return call(2,method,body)
    try:
        until=time.monotonic()+20
        while not (Path(endpoint[7:]).exists() and stat.S_ISSOCK(Path(endpoint[7:]).stat().st_mode)):
            require(daemon.poll() is None,'private daemon exited');require(time.monotonic()<until,'private daemon startup deadline');time.sleep(.05)
        endpoint='unix://'+str(Path(endpoint[7:]).resolve(strict=True))
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
            peer.connect(endpoint[7:]);peer_pid,peer_uid,_=struct.unpack('3i',peer.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            require(peer_pid==daemon.pid and peer_uid==os.geteuid(),'fixture endpoint does not belong to exact private daemon')
        receipt['socket_identity']={'mode':Path(endpoint[7:]).lstat().st_mode,'uid':Path(endpoint[7:]).lstat().st_uid,'euid':os.geteuid(),'link':str(Path(endpoint[7:]).readlink()) if Path(endpoint[7:]).is_symlink() else None}
        if args.expect_unsupported:
            try:rpc('tui/health/describe',{'pid':os.getpid()})
            except Exception as error:
                require(any(word in str(error).lower() for word in ('unknown','unrecognized','not found')), 'baseline refusal was not unsupported method: '+str(error))
                receipt['baseline']='unsupported_rpc';receipt['raw_refusal']=str(error);return receipt
            raise AssertionError('baseline unexpectedly supports foreground health')
        master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,120,0,0))
        def child_setup():
            os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0)
        ui=subprocess.Popen([str(binary),'--remote',endpoint,'--no-alt-screen'],cwd=cwd,env=env,stdin=slave,stdout=slave,stderr=slave,preexec_fn=child_setup)
        os.close(slave);os.set_blocking(master,False)
        screen=pyte.Screen(120,40);stream=pyte.ByteStream(screen);raw=(root/'terminal.raw').open('wb')
        def drain(seconds=.15):
            until=time.monotonic()+seconds
            while time.monotonic()<until:
                ready,_,_=select.select([master],[],[],min(.05,max(0,until-time.monotonic())))
                if ready:
                    try:data=os.read(master,65536)
                    except BlockingIOError:continue
                    if not data:break
                    raw.write(data);raw.flush();stream.feed(data)
                    # Answer terminal device queries locally; never submit a user prompt.
                    if b'\x1b[6n' in data:os.write(master,f'\x1b[{screen.cursor.y+1};{screen.cursor.x+1}R'.encode())
                    if b'\x1b[c' in data:os.write(master,b'\x1b[?1;2c')
        until=time.monotonic()+45;binding=None;thread=None
        while time.monotonic()<until:
            drain(.2);require(ui.poll() is None,'private TUI exited')
            rows=rpc('tui/health/describe',{'pid':ui.pid})['bindings']
            listed=rpc('thread/list',{'limit':10})['data']
            if len(rows)==1 and len(listed)==1:
                binding=rows[0];thread=listed[0]['id'];break
        require(binding is not None and thread is not None,'actual controlling TUI binding/thread unavailable')
        rpc('thread/queue/add',{'threadId':thread,'input':[{'type':'text','text':'health390 synthetic queued item','textElements':[]}],'clientUserMessageId':str(uuid4())})
        drain(.4)
        # This is a private typed draft, never Return/input submission.
        draft='PRIVATE_HEALTH390_DRAFT_'+uuid4().hex
        os.write(master,draft.encode()+b'\x1b[D'*7);drain(1)
        require(any(draft in line for line in screen.display),'fixture draft is not visible in actual TUI')
        snapshot=(tuple(screen.display),screen.cursor.x,screen.cursor.y)
        def history():
            return {str(p.relative_to(home)):hashlib.sha256(p.read_bytes()).hexdigest() for p in home.rglob('*') if p.is_file() and (p.suffix=='.jsonl' or p.name=='history.jsonl')}
        before_history=history();before_queue=rpc('thread/queue/list',{'threadId':thread});before_turns=rpc('thread/read',{'threadId':thread,'includeTurns':True})['thread']['turns']
        target=dict(host='synthetic-linux',environment='disposable',runtime='codex',namespace='codex:'+hashlib.sha256(json.dumps([str(home),binding['provider']],separators=(',',':')).encode()).hexdigest(),build_sha256=receipt['native_sha256'],conversation_id=thread,home=binding['home'],provider=binding['provider'],backend_id=binding['backendId'],channel=binding['channel'],process=dict(pid=binding['pid'],start_ticks=binding['startTicks'],boot_id=binding['bootId']),connection_generation=binding['connectionGeneration'])
        registry=wake/'controller-health.json';registry.write_text(json.dumps({'version':1,'bindings':[{'target':target,'endpoint':endpoint,'codex_cmd':[str(binary)]}]}));registry.chmod(0o600)
        service=ControllerHealth(wake)
        def observe(timeout=2):return service.execute('health.observe',{'expected_target':target,'timeout':timeout})['observation']
        require(len(before_queue['data'])==1,'synthetic native queue fixture unavailable')
        first=observe(5);require(first['responsive'],'actual loop did not acknowledge: '+str(first));tid=first['loop_tid'];receipt['loop_tid']=tid
        require(tid!=ui.pid and (Path('/proc')/str(ui.pid)/'task'/str(tid)/'comm').read_text().strip()=='codex-main','loop is not pinned to native codex-main OS thread')
        drain(.3);require(snapshot==(tuple(screen.display),screen.cursor.x,screen.cursor.y),'health modified draft/screen/cursor')
        libc=ctypes.CDLL(None,use_errno=True)
        def ptrace(request):
            result=libc.ptrace(request,tid,None,None)
            if result==-1:raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
        ptrace(0x4206);ptrace(0x4207);stopped_tid=tid
        until=time.monotonic()+3
        while True:
            waited,status=os.waitpid(tid,os.WNOHANG|0x40000000)
            if waited:require(os.WIFSTOPPED(status),'loop did not stop');break
            require(time.monotonic()<until,'thread stop deadline');time.sleep(.01)
        require(rpc('server/diagnostics',{})['process']['id']==daemon.pid,'background daemon RPC not healthy during exact UI-loop stop')
        negatives=[observe(.1) for _ in range(9)]
        require(all(not v['responsive'] for v in negatives),'stopped UI loop falsely acknowledged')
        receipt['stopped_loop_background_rpc']=True;receipt['stalled_probe_statuses']=[v['status'] for v in negatives]
        ptrace(17);stopped_tid=None;drain(.4)
        final=observe(3);require(final['responsive'] and final['challenge']!=first['challenge'] and final['loop_tid']==tid,'fresh post-resume loop challenge failed')
        # Replay and wrong native target/generation are rejected by the real daemon.
        from codex_wake.records import WakeError
        request=dict(binding=binding,threadId=thread,challenge=final['challenge'],timeoutMs=100)
        wrong_bindings=[dict(binding,**{key:value}) for key,value in [('connectionGeneration','wrong-generation'),('backendId','wrong-backend'),('home',str(root/'wrong-account')),('provider','wrong-provider'),('startTicks','0'),('bootId','wrong-boot'),('channel','wrong-channel')]]
        for changed in [request,dict(request,challenge=uuid4().hex*2,threadId=str(uuid4()))]+[dict(request,binding=b,challenge=uuid4().hex*2) for b in wrong_bindings]:
            try:rpc('tui/health/probe',changed,.5)
            except WakeError:pass
            else:raise AssertionError('duplicate or wrong-target native probe accepted')
        try:rpc('tui/health/register',{'binding':binding})
        except WakeError:pass
        else:raise AssertionError('unrelated process registered actual TUI PID')
        drain(.3);require(snapshot==(tuple(screen.display),screen.cursor.x,screen.cursor.y),'probe changed private draft/cursor')
        require(history()==before_history,'probe appended native conversation/input history')
        require(rpc('thread/queue/list',{'threadId':thread})==before_queue,'probe changed native queue')
        require(rpc('thread/read',{'threadId':thread,'includeTurns':True})['thread']['turns']==before_turns==[],'probe started a model turn')
        require(requests==[],'fixture attempted a provider/proxy query')
        receipt.update(result='passed',draft_cursor_preserved=True,history_preserved=True,queue_preserved=True,no_turn=True,expired_reply_not_reused=True,fresh_ack=True,duplicate_wrong_target_denied=True,target=target)
        return receipt
    finally:
        if stopped_tid is not None:
            libc.ptrace(17,stopped_tid,None,None)
        for proc in (ui,daemon):
            if proc is not None:
                try:os.killpg(proc.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
        if master is not None:os.close(master)
        daemon_log.close()
        trap.shutdown();trap.server_close();trap_thread.join(timeout=2)
        receipt['provider_proxy_requests']=len(requests)
        (root/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')

if __name__=='__main__':print(json.dumps(main(),sort_keys=True))
