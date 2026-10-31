"""Owned long-lived old-client pin and actual no-turn operator notice witness.

Only disposable wsl-test state is accepted. The old private client owns the
future account lock while a separate, exact-health-bound TUI receives notices.
"""
import argparse
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import http.server
import json
import os
from pathlib import Path
import pty
import select
import signal
import socket
import struct
import subprocess
import sys
import termios
import threading
import time
from uuid import uuid4


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path,data):
    from codex_profiles.upgrades import _atomic
    _atomic(Path(path),data)



def register_notice_recipient(root,target):
    """Add the scoped notice capability while retaining the original grant."""
    path=Path(root)/'controller-messaging.json'
    caller=json.loads(path.read_text())
    grant=caller['local_caller']
    expiry=grant['expires_at'];before_scopes=list(grant['scopes'])
    identity={key:value for key,value in grant.items() if key not in ('scopes','targets')}
    if target not in grant['targets']:grant['targets'].append(target)
    if 'control' not in grant['scopes']:grant['scopes'].append('control')
    write(path,caller)
    persisted=json.loads(path.read_text())['local_caller']
    assert persisted['expires_at']==expiry, 'notice registration renewed grant expiry'
    assert {key:value for key,value in persisted.items() if key not in ('scopes','targets')}==identity, 'notice registration changed grant identity'
    return dict(expires_at_before=expiry,expires_at_after=persisted['expires_at'],expiry_unchanged=True,
        scopes_added=[scope for scope in persisted['scopes'] if scope not in before_scopes],
        scopes_after=persisted['scopes'],recipient=target)


def seed(home,workspace,models,url):
    home.mkdir(parents=True,exist_ok=True,mode=0o700)
    model=json.loads(models.read_text())['models'][0]
    (home/'operator-models.json').write_text(json.dumps(dict(models=[model])))
    (home/'config.toml').write_text('model='+json.dumps(model['slug'])+'\nmodel_provider="operator_fixture"\nmodel_catalog_json='+json.dumps(str(home/'operator-models.json'))+'\ncheck_for_update_on_startup=false\n[analytics]\nenabled=false\n[model_providers.operator_fixture]\nname="No model operator witness"\nbase_url='+json.dumps(url+'/never-query')+'\nwire_api="responses"\nrequires_openai_auth=false\n[projects.'+json.dumps(str(workspace))+']\ntrust_level="trusted"\n')
    tid=str(uuid4());now=datetime.now(timezone.utc);stamp=now.isoformat().replace('+00:00','Z')
    rollout=home/'sessions'/now.strftime('%Y/%m/%d')/('rollout-'+now.strftime('%Y-%m-%dT%H-%M-%S')+'-'+tid+'.jsonl')
    rollout.parent.mkdir(parents=True,exist_ok=True)
    meta=dict(id=tid,session_id=tid,timestamp=stamp,cwd=str(workspace),originator='codex_cli_rs',cli_version='0.165.0',source='cli',model_provider='operator_fixture',base_instructions={'text':'Synthetic provider-free upgrade operator witness.'})
    rollout.write_text(json.dumps(dict(timestamp=stamp,type='session_meta',payload=meta))+'\n')
    return tid


class Terminal:
    def __init__(self,argv,env,cwd,root,name):
        import pyte
        self.master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',45,180,0,0))
        def child_setup():
            os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0)
        self.process=subprocess.Popen(argv,stdin=slave,stdout=slave,stderr=slave,cwd=cwd,env=env,preexec_fn=child_setup)
        os.close(slave);os.set_blocking(self.master,False)
        self.screen=pyte.Screen(180,45);self.stream=pyte.ByteStream(self.screen)
        self.log=(root/(name+'.terminal')).open('wb')
    def drain(self,seconds=.1):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            ready,_,_=select.select([self.master],[],[],min(.02,max(0,until-time.monotonic())))
            if not ready:continue
            try:data=os.read(self.master,65536)
            except OSError as error:
                if error.errno in (errno.EIO,errno.EAGAIN):return
                raise
            if not data:return
            self.log.write(data);self.log.flush();self.stream.feed(data)
            if b'\x1b[6n' in data:os.write(self.master,f'\x1b[{self.screen.cursor.y+1};{self.screen.cursor.x+1}R'.encode())
            if b'\x1b[c' in data:os.write(self.master,b'\x1b[?1;2c')
    def stop(self):
        try:os.killpg(self.process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=2)
        os.close(self.master);self.log.close()


def descendants(parent):
    found=[];pending=[parent]
    while pending:
        current=pending.pop()
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():continue
            try:
                fields=(proc/'stat').read_text().rsplit(')',1)[1].split()
                if int(fields[1])==current and int(proc.name) not in found:
                    found.append(int(proc.name));pending.append(int(proc.name))
            except (OSError,ValueError,IndexError):continue
    return found


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-launch',action='store_true')
    for name in ('root','package','models','catalog','home','artifacts'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--thread')
    args=parser.parse_args(argv)
    os.umask(0o077)
    root=args.root.resolve();art=args.artifacts.resolve();home=args.home.resolve()
    if os.environ.get('WSL_DISTRO_NAME')!='wsl-test' or os.getuid()!=1000:parser.error('disposable wsl-test ubuntu required')
    if not root.is_relative_to(Path('/home/ubuntu/codex-profile-lab')):parser.error('disposable fixture root required')
    expected=json.loads((root/'upgrade-bot.json').read_text())['promotion']
    if home!=Path(expected['account_home']).resolve() or args.catalog.resolve()!=Path(expected['manifest']).resolve() or not art.is_relative_to(root):
        parser.error('operator fixture must use the sealed future account/catalog and owned artifacts')
    workspace=art/'workspace'
    if args.private_launch:
        from codex_profiles.build_channels import load_build,run_build
        return run_build(load_build(args.catalog,'modded',home),home,'operator-witness',
            ['--no-alt-screen','resume',args.thread],output=sys.stderr)
    art.mkdir(parents=True,exist_ok=False,mode=0o700);workspace.mkdir(mode=0o700)
    requests=[]
    class Trap(http.server.BaseHTTPRequestHandler):
        def reject(self):requests.append(dict(method=self.command,path=self.path));self.send_response(503);self.end_headers()
        do_GET=do_POST=do_CONNECT=reject
        def log_message(self,*unused):pass
    trap=http.server.ThreadingHTTPServer(('127.0.0.1',0),Trap)
    threading.Thread(target=trap.serve_forever,daemon=True).start()
    url='http://127.0.0.1:'+str(trap.server_port)
    binary=(args.package/'bin/codex').resolve();old_sha=sha(binary)
    from codex_profiles.build_channels import load_build
    assert load_build(args.catalog,'modded',home).sha256==old_sha,'future catalog is not the qualified old package'
    thread=seed(home,workspace,args.models,url)
    notice_home=art/'notice-home';notice_thread=seed(notice_home,workspace,args.models,url)
    def environment(selected):
        env={key:value for key,value in os.environ.items() if key in ('PATH','LANG','LC_ALL','WSL_DISTRO_NAME')}
        env.update(HOME=str(selected),CODEX_HOME=str(selected),XDG_CONFIG_HOME=str(art/'config'),XDG_DATA_HOME=str(art/'data'),
            XDG_STATE_HOME=str(art/'state'),XDG_CACHE_HOME=str(art/'cache'),TERM='xterm-256color',NO_PROXY='127.0.0.1,localhost',
            HTTPS_PROXY=url,HTTP_PROXY=url,ALL_PROXY=url)
        return env
    env=environment(notice_home);endpoint='unix://'+str(art/'notice.sock')
    daemon_log=(art/'notice-daemon.log').open('wb')
    daemon=subprocess.Popen([str(binary),'app-server','--listen',endpoint],env=env,cwd=workspace,stdout=daemon_log,stderr=subprocess.STDOUT,start_new_session=True)
    private=None;notice=None;native_pid=None;report=dict(status='preparing',native_sha256=old_sha,model_requests=0,external_provider_requests=0)
    previous=signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(InterruptedError('owned operator witness stopped')))
    try:
        deadline=time.monotonic()+30
        while not Path(endpoint[7:]).is_socket():
            assert daemon.poll() is None and time.monotonic()<deadline,'notice backend startup failed'
            time.sleep(.05)
        endpoint='unix://'+str(Path(endpoint[7:]).resolve(strict=True))
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
            peer.connect(endpoint[7:]);peer_pid,peer_uid,_=struct.unpack('3i',peer.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            assert peer_pid==daemon.pid and peer_uid==os.geteuid(),'notice endpoint is not the owned private backend'
        from codex_wake.native_protocol import native_request
        def rpc(method,params):
            try:return native_request(endpoint,[str(binary)],method,params,5)
            except Exception:
                import traceback
                path=Path(endpoint[7:]);metadata=path.lstat()
                write(art/'rpc-failure.json',dict(endpoint=endpoint,euid=os.geteuid(),mode=oct(metadata.st_mode),uid=metadata.st_uid,traceback=traceback.format_exc()))
                raise
        private=Terminal([sys.executable,str(Path(__file__).resolve()),*[value for key in ('root','package','models','catalog','home','artifacts') for value in ('--'+key,str(getattr(args,key)))],'--private-launch','--thread',thread],environment(home),workspace,art,'old-private')
        notice=Terminal([str(binary),'--remote',endpoint,'--no-alt-screen','resume',notice_thread],env,workspace,art,'operator-notices')
        binding=None;until=time.monotonic()+45
        while time.monotonic()<until:
            private.drain();notice.drain()
            assert private.process.poll() is None and notice.process.poll() is None,'owned TUI exited during setup'
            rows=rpc('tui/health/describe',dict(pid=notice.process.pid))['bindings']
            if len(rows)==1 and 'Ask Codex to do anything' in '\n'.join(notice.screen.display):binding=rows[0];break
        assert binding,'exact operator TUI binding unavailable'
        until=time.monotonic()+30
        while native_pid is None and time.monotonic()<until:
            private.drain();notice.drain()
            assert private.process.poll() is None,'old private launcher exited before its native client was ready'
            for pid in descendants(private.process.pid):
                try:
                    if sha(Path('/proc',str(pid),'exe'))==old_sha:
                        native_pid=pid;break
                except OSError:pass
        assert native_pid,'pinned private native child unavailable'
        from codex_wake.process import process_identity
        original_process=process_identity(native_pid)
        configuration=json.loads((root/'upgrade-bot.json').read_text())
        target=dict(host=configuration['target']['host'],environment=configuration['target']['environment'],runtime='codex',
            namespace='codex:'+hashlib.sha256(json.dumps([str(Path(binding['home']).resolve()),binding['provider']],separators=(',',':')).encode()).hexdigest(),build_sha256=old_sha,conversation_id=notice_thread,home=binding['home'],provider=binding['provider'],
            backend_id=binding['backendId'],channel=binding['channel'],process=dict(pid=binding['pid'],start_ticks=binding['startTicks'],boot_id=binding['bootId']),connection_generation=binding['connectionGeneration'])
        from codex_wake.controller_notices import flat_target
        flat=flat_target(target)
        write(root/'controller-health.json',dict(version=1,bindings=[dict(target=target,endpoint=endpoint,codex_cmd=[str(binary)])]))
        configuration['notice_recipients']=[dict(target=flat)];write(root/'upgrade-bot.json',configuration)
        report['grant_registration']=register_notice_recipient(root,flat)
        write(art/'grant-registration.json',report['grant_registration'])
        from codex_wake.controller_health import ControllerHealth
        assert ControllerHealth(root).execute('health.observe',dict(expected_target=target,timeout=3))['observation']['responsive']
        report.update(status='ready',target=flat,private_native_pid=native_pid,private_identity=original_process,private_thread=thread,notice_thread=notice_thread,
            initial_provider_attempts=list(requests),registered_at=time.time())
        write(art/'ready.json',report)
        from codex_wake.operation_commands import local_actor
        from codex_wake.upgrade_notices import UpgradeNotices
        until=time.monotonic()+7500;last_drain=0
        while not (art/'stop').exists() and time.monotonic()<until:
            private.drain();notice.drain()
            assert private.process.poll() is None and notice.process.poll() is None,'owned old TUI exited before controlled close'
            if time.monotonic()-last_drain>=3:
                actor=local_actor(root);delivery=UpgradeNotices(root).drain(actor,authorize=lambda:local_actor(root))
                report['delivery']=delivery;last_drain=time.monotonic();write(art/'progress.json',report)
            state=json.loads((root/'upgrade-jobs/state.json').read_text())
            jobs=list(state['jobs'].values())
            if jobs and jobs[-1]['state'] in ('succeeded','failed','held','disabled'):
                report['job_state']=jobs[-1]['state'];report['job_id']=jobs[-1]['id']
                assert process_identity(native_pid)==original_process and sha(Path('/proc',str(native_pid),'exe'))==old_sha,'promotion interrupted/replaced the old private session'
                actor=local_actor(root);report['delivery']=UpgradeNotices(root).drain(actor,authorize=lambda:local_actor(root))
                notice.drain(1)
                native=rpc('thread/read',dict(threadId=notice_thread,includeTurns=True))['thread']
                report.update(status='passed' if jobs[-1]['state']=='succeeded' else 'observed_terminal_hold',old_session_pinned=True,
                    selected_future_sha256=load_build(args.catalog,'modded',home).sha256,
                    notice_history_sha256=hashlib.sha256(json.dumps(native,sort_keys=True).encode()).hexdigest(),provider_attempts=list(requests))
                (art/'operator-final.txt').write_text('\n'.join(notice.screen.display))
                break
        else:raise TimeoutError('operator witness deadline reached')
    except (OSError,ValueError,KeyError,AssertionError,InterruptedError,TimeoutError) as error:
        report.update(status='failed',reason=str(error))
    finally:
        for terminal in (private,notice):
            if terminal:terminal.stop()
        try:os.killpg(daemon.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:daemon.wait(timeout=2)
        except subprocess.TimeoutExpired:os.killpg(daemon.pid,signal.SIGKILL);daemon.wait()
        daemon_log.close();trap.shutdown();trap.server_close();signal.signal(signal.SIGTERM,previous)
        report['finished_at']=time.time();write(art/'receipt.json',report)
    return 0 if report['status'] in ('passed','observed_terminal_hold') else 1


if __name__=='__main__':raise SystemExit(main())
