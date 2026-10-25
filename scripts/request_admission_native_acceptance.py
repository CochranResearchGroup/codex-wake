"""Owned native request admission and zero-allowance operator control proof.

Only an inert localhost provider is called. Warmup precedes the declared hard
coverage window and its measured charge is imported, never erased. No shared
runtime or external provider credentials are used.
"""
import argparse
from contextlib import ExitStack
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import tempfile
import threading
import time

from codex_wake.native_protocol import native_request
from codex_wake.process import process_identity


def sse(identifier, text, *, input_tokens, cached, output_tokens):
    events = [dict(type='response.created', response=dict(id=identifier)),
        dict(type='response.output_item.done', item=dict(type='message', role='assistant',
            id='message-'+identifier, content=[dict(type='output_text', text=text)])),
        dict(type='response.completed', response=dict(id=identifier, usage=dict(
            input_tokens=input_tokens, input_tokens_details=dict(cached_tokens=cached),
            output_tokens=output_tokens, total_tokens=input_tokens+output_tokens)))]
    return ''.join('event: '+row['type']+'\ndata: '+json.dumps(row)+'\n\n' for row in events).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-server', type=Path, required=True)
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    options = parser.parse_args()
    options.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    appserver, frontend = options.app_server.resolve(strict=True), options.frontend.resolve(strict=True)
    report = dict(state='running', external_provider_calls=0, shared_runtime_changed=False,
        warmup_outside_hard_coverage=True, provider='owned inert bounded Responses adapter')
    for name, path in (('native', appserver), ('frontend', frontend)):
        with path.open('rb') as stream:
            report[name+'_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    report['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    expiry = time.monotonic()+150
    calls, inbound = [], []
    selected = {'gateway': None}
    token = secrets.token_urlsafe(32)
    processes = []
    tmux_name = 'cw354-owned-'+str(os.getpid())
    with tempfile.TemporaryDirectory(prefix='cw354-native-') as temporary, ExitStack() as stack:
        base = Path(temporary)
        home, root = base/'home', base/'wake'
        home.mkdir(mode=0o700); root.mkdir(mode=0o700)
        env = dict(os.environ, CODEX_HOME=str(home), REQUEST_GATEWAY_TOKEN=token)
        def save(name, value):
            path = options.output/name
            path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
            path.chmod(0o600)
        def wait_for(callback, timeout=25):
            until=min(expiry,time.monotonic()+timeout)
            while time.monotonic()<until:
                value = callback()
                if value:
                    return value
                if any(process.poll() is not None for process in processes):
                    raise RuntimeError('owned native process exited')
                time.sleep(.05)
            raise TimeoutError('150-second owned qualification bound reached')
        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                size = int(self.headers.get('Content-Length', '0'))
                if not 0<size<=2*1024*1024:
                    self.send_error(413); return
                body = json.loads(self.rfile.read(size))
                number = len(calls)+1
                assert number<=3, 'bounded provider request count exceeded'
                guarded = selected['gateway'] is not None
                if guarded:
                    assert body.get('max_output_tokens') == 5
                calls.append(dict(number=number, guarded=guarded,
                    injected_output_bound=body.get('max_output_tokens')))
                response = sse('owned-'+str(number), 'INERT PROVIDER RESULT',
                    input_tokens=45 if guarded else 8, cached=0 if guarded else 3,
                    output_tokens=5 if guarded else 2)
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Content-Length', str(len(response))); self.end_headers()
                self.wfile.write(response)
        provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
        provider.daemon_threads = True
        threading.Thread(target=provider.serve_forever, daemon=True).start()
        stack.callback(provider.server_close); stack.callback(provider.shutdown)
        class Listener(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                if self.headers.get('Authorization') != 'Bearer '+token:
                    self.send_error(401); return
                if self.path!='/status' or selected['gateway'] is None:
                    self.send_error(404); return
                data=json.dumps(selected['gateway'].status()).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(data)))
                self.end_headers(); self.wfile.write(data)
            def do_POST(self):
                if self.headers.get('Authorization') != 'Bearer '+token:
                    self.send_error(401); return
                length=int(self.headers.get('Content-Length','0'))
                if self.path!='/v1/responses' or not 0<length<=2*1024*1024:
                    self.send_error(400); return
                body=json.loads(self.rfile.read(length))
                inbound.append(dict(metadata=body.get('client_metadata',{}), model=body.get('model')))
                save('observed-requests.json',dict(provider=calls,native_metadata=inbound))
                if selected['gateway'] is None:
                    from http.client import HTTPConnection
                    connection=HTTPConnection('127.0.0.1',provider.server_port,timeout=5)
                    try:
                        connection.request('POST','/v1/responses',json.dumps(body),{'Content-Type':'application/json'})
                        response=connection.getresponse(); status=response.status
                        content_type=response.getheader('Content-Type'); data=response.read()
                    finally:
                        connection.close()
                else:
                    try:
                        status,content_type,data=selected['gateway'].execute(body)
                    except ValueError as error:
                        status,content_type,data=403,'application/json',json.dumps(dict(error=dict(type='governor_identity_unqualified',message=str(error)))).encode()
                self.send_response(status); self.send_header('Content-Type',content_type)
                self.send_header('Content-Length',str(len(data))); self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError,ConnectionResetError):
                    pass
        listener=ThreadingHTTPServer(('127.0.0.1',0),Listener); listener.daemon_threads=True
        threading.Thread(target=listener.serve_forever,daemon=True).start()
        stack.callback(listener.server_close); stack.callback(listener.shutdown)
        listener_url='http://127.0.0.1:'+str(listener.server_port)
        (home/'config.toml').write_text('model="mock-model"\nmodel_provider="owned_gateway"\napproval_policy="never"\nsandbox_mode="read-only"\n'
            '[model_providers.owned_gateway]\nname="Owned gateway qualification"\nbase_url='+json.dumps(listener_url+'/v1')+'\nwire_api="responses"\n'
            'requires_openai_auth=false\nenv_key="REQUEST_GATEWAY_TOKEN"\nrequest_max_retries=0\nstream_max_retries=0\nsupports_websockets=false\n'
            '[projects.'+json.dumps(str(base))+']\ntrust_level="trusted"\n')
        log=stack.enter_context((options.output/'native.log').open('w'))
        endpoint=base/'native.sock'
        native=subprocess.Popen([str(appserver),'--listen','unix://'+str(endpoint)],cwd=base,env=env,stdout=log,stderr=subprocess.STDOUT)
        processes.append(native)
        def rpc(method, **params):
            return native_request('unix://'+str(endpoint),str(frontend),method,params,5)
        def tmux(*args, check=True):
            return subprocess.run(['tmux','-L',tmux_name,*args],capture_output=True,text=True,check=check,timeout=10,env=env)
        def capture():
            return tmux('capture-pane','-t','governor:0.0','-p','-S','-200',check=False).stdout
        def turn(text):
            current=rpc('turn/start',threadId=thread,input=[dict(type='text',text=text)])['turn']['id']
            return wait_for(lambda: next((row for row in rpc('thread/turns/list',threadId=thread,limit=128,itemsView='notLoaded')['data']
                if row['id']==current and row['status']!='inProgress'),None))
        try:
            wait_for(endpoint.exists)
            native_thread=rpc('thread/start',cwd=str(base))['thread']; thread=native_thread['id']
            # Load/flush the owned session before creating its accounting origin.
            rpc('thread/notice/read',threadId=thread,eventId='owned-origin-ready')
            rpc('thread/name/set',threadId=thread,name='Owned request admission fixture')
            goal=rpc('thread/goal/set',threadId=thread,objective='Owned bounded request qualification',status='paused')['goal']
            turn('Warm up the inert provider; do not use tools.')
            assert len(calls)==1
            from codex_wake.goal_supervision import enroll
            from codex_wake.lifecycle_budget import trusted_upper
            # Qualify the native whole-second creation against the real trusted
            # clock before enrollment; do not rewrite timestamps or accounting.
            wait_for(lambda: trusted_upper() >= goal['createdAt']+1)
            from codex_wake.objective_ledger import ObjectiveLedger
            from codex_wake.request_admission import RequestGateway, contract_digest
            policy=root/'policy.json'
            policy.write_text(json.dumps(dict(version=1,callers={thread:dict(app_server='unix://'+str(endpoint),
                codex_path=str(frontend),codex_home=str(home),allocation_id='owned-request-scope',
                max_tokens=57,max_seconds=120,rpc_timeout=5)})))
            policy.chmod(0o600)
            enrolled=enroll(root,policy,thread,57,120,checkpoint_token_percent=0,checkpoint_seconds=0)
            save('enrollment.json',enrolled)
            assert enrolled['used_tokens']==7, enrolled
            # Interactive warmup may activate the goal. Pause it outside the hard
            # window before attaching the frontend, then prove activation live.
            rpc('thread/goal/set', threadId=thread, status='paused', origin='automatic')
            tmux('new-session','-d','-s','governor','-x','170','-y','60',str(frontend),'--remote','unix://'+str(endpoint),'--no-alt-screen','resume',thread)
            tmux('set-option','-g','exit-empty','off')
            wait_for(lambda: 'Resume paused goal?' in capture())
            tmux('send-keys','-t','governor:0.0','Escape')
            wait_for(lambda: 'Resume paused goal?' not in capture())
            report['native_startup_dialog_dismissed_before_coverage']=True
            wait_for(lambda: 'Ask Codex to do anything' in capture() and not any(
                row['status']=='inProgress' for row in rpc('thread/turns/list',threadId=thread,limit=128,itemsView='notLoaded')['data']))
            assert len(calls)==1, 'frontend warmup created an unaccounted request'
            now=trusted_upper()
            configuration=dict(revision='owned-native-request-v1',objective_token_limit=57,objective_time_limit_seconds=120,
                session_token_limit=57,session_time_limit_seconds=120,max_correction_cycles=1,
                started_at=enrolled['time_origin'],objective_deadline=enrolled['deadline'])
            ledger=ObjectiveLedger(root,'owned-request-scope')
            ledger.configure(configuration,'explicit owned provider-free qualification',prior_tokens=7,now=now)
            contract=dict(version=1,provider='owned-inert-adapter',model='mock-model',max_input_tokens=45,max_output_tokens=5,
                input_limit='provider_enforced_reject_before_billing',output_limit='max_output_tokens_enforced',
                usage='response.completed:fresh-v1',review='This owned provider emits input<=45 and output<=5, with no external model.')
            gateway=RequestGateway(root,'owned-request-scope',upstream_url='http://127.0.0.1:'+str(provider.server_port)+'/v1/responses',
                contract=contract,reviewed_contract_sha256=contract_digest(contract),thread_ids=[thread],
                now=trusted_upper,request_timeout=10,client_token=token)
            gateway.bind_listener(listener_url); selected['gateway']=gateway
            activation_frame=wait_for(lambda: value if 'Effective mode hard_admission' in (value:=capture()) else None)
            (options.output/'hard-activation-tui.txt').write_text(activation_frame)
            report['hard_activation_rendered_before_guarded_request']=True
            first=turn('Run exactly one inert guarded request. Do not use tools.')
            assert first['status']=='completed',first
            assert len(calls)==2,calls
            status=gateway.status(); save('after-admitted.json',status)
            assert status['accounting']['tokens_used']==57,status
            denied=turn('This request must be stopped by the governor before reaching the provider.')
            assert len(calls)==2,calls
            save('after-denied.json',gateway.status())
            assert rpc('thread/goal/get',threadId=thread)['goal']['status']=='paused', 'Admission denial did not pause autonomous continuation'
            wait_for(lambda: 'Ask Codex to do anything' in capture() and not any(
                row['status']=='inProgress' for row in rpc('thread/turns/list',threadId=thread,limit=128,itemsView='notLoaded')['data']))
            tmux('set-buffer','-b','governor-control','Deactivate governor')
            tmux('paste-buffer','-p','-b','governor-control','-t','governor:0.0')
            wait_for(lambda: '› Deactivate governor' in capture())
            tmux('send-keys','-t','governor:0.0','Enter')
            wait_for(lambda: gateway.status()['mode']=='inactive')
            frame=wait_for(lambda: value if 'Governor inactive' in (value:=capture()) or 'Governor deactivated' in value else None)
            (options.output/'deactivated-tui.txt').write_text(frame)
            wait_for(lambda: not any(row['status']=='inProgress' for row in rpc('thread/turns/list',threadId=thread,limit=128,itemsView='notLoaded')['data']))
            ack=wait_for(lambda: value if 'Governor-generated acknowledgement' in (value:=capture()) else None)
            (options.output/'zero-inference-control-ack.txt').write_text(ack)
            assert len(calls)==2,'control action reached provider'
            final=gateway.status(); save('after-control.json',final)
            assert final['accounting']['objective_token_limit']==57,final
            assert final['accounting']['tokens_used']==57,final
            assert rpc('thread/goal/get',threadId=thread)['goal']['status']=='paused'
            report.update(state='passed',warmup_requests=1,guarded_provider_requests=1,
                denied_request_never_forwarded=True,control_at_zero_allowance=True,
                control_external_inference=0,control_rendered_in_stock_tui=True,
                original_usage_and_cap_preserved=True,thread_id=thread,denied_turn_status=denied['status'])
        except Exception as error:
            report.update(state='failed',failure=type(error).__name__,message=str(error)[:1000])
            (options.output/'last-frame.txt').write_text(capture())
            save('observed-requests.json',dict(provider=calls,native_metadata=inbound))
            if 'native_thread' in locals() and native_thread.get('path'):
                accounting=[]
                for line in Path(native_thread['path']).read_text().splitlines():
                    row=json.loads(line); payload=row.get('payload',{})
                    if row.get('type')=='event_msg' and payload.get('type') in (
                            'thread_goal_updated','task_started','task_complete','raw_response_completed'):
                        accounting.append(dict(timestamp=row.get('timestamp'),event=payload.get('type'),
                            goal_created_at=payload.get('goal',{}).get('createdAt'),
                            goal_status=payload.get('goal',{}).get('status'),
                            response_id=payload.get('response_id'),token_usage=payload.get('token_usage')))
                save('accounting-events.json',accounting)
            raise
        finally:
            # Capture identities while parents still exist, then check fresh
            # unique-home ownership as well as lineage after stopping them.
            parents={int(pid):int(ppid) for pid,ppid in (row.split() for row in subprocess.check_output(['ps','-eo','pid=,ppid='],text=True).splitlines())}
            owned={process.pid for process in processes}
            tmux_pid=tmux('display-message','-p','#{pid}',check=False).stdout.strip()
            if tmux_pid.isdigit():owned.add(int(tmux_pid))
            while True:
                expanded=owned|{pid for pid,parent in parents.items() if parent in owned}
                if expanded==owned:break
                owned=expanded
            identities={}
            for pid in owned:
                try:identities[pid]=process_identity(pid)
                except (OSError,ValueError):pass
            tmux('kill-server',check=False)
            for pid,identity in identities.items():
                try:
                    if process_identity(pid)==identity:os.kill(pid,signal.SIGTERM)
                except (OSError,ValueError):pass
            for process in processes:
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            remaining=[]
            for path in Path('/proc').iterdir():
                if not path.name.isdigit():continue
                try:
                    if b'CODEX_HOME='+str(home).encode()+b'\0' in (path/'environ').read_bytes():
                        os.kill(int(path.name),signal.SIGTERM);remaining.append(int(path.name))
                except (OSError,ValueError):pass
            report['fresh_owned_home_cleanup_signaled']=remaining
            until=time.monotonic()+5
            while True:
                remaining=[]
                for path in Path('/proc').iterdir():
                    if not path.name.isdigit():continue
                    try:
                        if (b'CODEX_HOME='+str(home).encode()+b'\0' in (path/'environ').read_bytes()
                                and (path/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'):
                            remaining.append(int(path.name))
                    except (OSError,ValueError):pass
                if not remaining or time.monotonic()>=until:break
                time.sleep(.02)
            report['remaining_owned_pids']=remaining
            report['owned_processes_terminal']=not remaining and all(process.poll() is not None for process in processes)
            if not report['owned_processes_terminal']:report['state']='cleanup_incomplete' 
            save('receipt.json',report)
    print(json.dumps(report))


if __name__=='__main__':
    main()
