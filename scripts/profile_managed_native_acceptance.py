#!/usr/bin/env python3
"""Installed independent-store frozen batch and managed native acceptance.

Run under the separate Linux test user inside unshare -Urn. The caller supplies
complete public packages and a NEW retained artifact directory. Never use a live
Wake root. Native seed RPCs only prepare declared synthetic saved conversations;
all lifecycle and cross-account transfer effects go through installed Wake.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import http.server
import threading
import importlib.metadata
import json
import os
import pty
import select
import signal
import struct
import fcntl
import termios
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--modded', type=Path, required=True)
    p.add_argument('--stock', type=Path, required=True)
    p.add_argument('--source-commit', required=True)
    p.add_argument('--wheel-sha256', required=True)
    p.add_argument('--models', type=Path, required=True)
    p.add_argument('--outer-netns', required=True, help='network namespace identity read by the outer launcher')
    args = p.parse_args()
    root = args.root.absolute()
    assert int(Path('/proc/self/uid_map').read_text().split()[1]) == 1017
    assert str(Path(sys.executable).parent) == '/home/codex-daemon-test/qualification205/wake/bin'
    root.mkdir(mode=0o700, exist_ok=False)
    if os.readlink('/proc/self/ns/net') == args.outer_netns:
        raise RuntimeError('external network must be isolated with unshare -Urn')
    subprocess.run(['ip','link','set','lo','up'],check=True,timeout=5)
    cli = str(Path(sys.executable).parent / 'codex-wake')
    env = {k: os.environ[k] for k in ('PATH', 'LANG', 'TERM') if k in os.environ}
    for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME'):
        directory = root / key.lower()
        directory.mkdir(mode=0o700)
        env[key] = str(directory)
    os.environ.clear()
    os.environ.update(env)
    os.environ.pop('PYTHONPATH', None)
    events, server, owned, clients = [], None, [], []
    def record(kind, value):
        events.append(dict(kind=kind, value=value))
        with (root / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(events[-1], sort_keys=True) + '\n')
    def call(*command, check=True):
        if command and command[0] == 'daemons' and '--json' not in command:
            command = (*command, '--json')
        result = subprocess.run([cli, '--wake-root', str(root), *command], env=env,
            capture_output=True, text=True, timeout=110, cwd=root)
        value = json.loads(result.stdout)
        # Auth codes are temporary secrets, never retained in command receipts.
        if command[:2] != ('controller','authorize-client'):
            record('cli', dict(command=command, exit_code=result.returncode, result=value, stderr=result.stderr[-2000:]))
        if check:
            assert result.returncode == 0, value
        return value
    def daemon(name, channel=None):
        channel = channel or ('stock' if name == 'stock' else 'modded')
        return call('daemons','status',name,'--channel',channel)['result']['daemon']
    def mutate(verb, name, key, channel=None):
        channel = channel or ('stock' if name == 'stock' else 'modded')
        before = daemon(name, channel)
        arguments = ('daemons',verb,name,'--channel',channel,'--expected-target',json.dumps(before['target']),
                     '--idempotency-key',key,'--yes')
        value = call(*arguments)
        operation = value['result']['operation']
        assert operation['execution'] == 'completed', operation
        return operation['result']['daemon'], arguments, operation
    from codex_wake.native_protocol import native_request
    def rpc(daemon, method, params):
        value = native_request(daemon['endpoint'],daemon['target']['executable'],method,params,10)
        record('native_saved_history',dict(account=daemon['account'],method=method,result=value))
        return value
    def read(daemon, thread):
        return rpc(daemon,'thread/read',dict(threadId=thread,includeTurns=True))['thread']
    def seed(daemon, who):
        thread = str(uuid4());stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        turn = str(uuid4())
        question, answer = 'SYNTHETIC '+who+' question', 'SYNTHETIC '+who+' saved answer'
        rows=[dict(type='session_meta',payload=dict(id=thread,timestamp=stamp,cwd=str(root),originator='codex_cli_rs',cli_version='0.167.0',source='cli',model_provider='fixture'))]
        for payload in (dict(type='task_started',turn_id=turn,model_context_window=200000),
            dict(type='user_message',message=question,images=[],local_images=[],text_elements=[]),
            dict(type='agent_message',message=answer,phase='final_answer'),
            dict(type='task_complete',turn_id=turn,last_agent_message=answer)):
            rows.append(dict(type='event_msg',payload=payload))
        path=root/(who+'-seed.jsonl')
        path.write_text(''.join(json.dumps(dict(timestamp=stamp,**row))+'\n' for row in rows))
        result=rpc(daemon,'thread/fork',dict(threadId=thread,path=str(path),ephemeral=False,approvalPolicy='never',sandbox='read-only'))
        child=result['thread']['id']
        native=read(daemon,child)
        assert answer in json.dumps(native['turns']), native
        return child
    def open_tui(name, thread, marker, label):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH',45,140,0,0))
        process=subprocess.Popen([cli,'--wake-root',str(root),'resume',name,thread],
            env=dict(env,TERM='xterm-256color'),stdin=slave,stdout=slave,stderr=slave,start_new_session=True,cwd=root)
        os.close(slave)
        client=dict(process=process,master=master,label=label,content=b'')
        clients.append(client)
        deadline=time.monotonic()+18
        while time.monotonic()<deadline:
            if select.select([master],[],[],.1)[0]:
                try:chunk=os.read(master,65536)
                except OSError:break
                if not chunk:break
                client['content']+=chunk
                if b'\x1b[6n' in chunk:os.write(master,b'\x1b[1;1R')
                if marker.encode() in client['content']:
                    record('tui',dict(account=name,thread_id=thread,pid=process.pid,visible=marker,label=label))
                    return client
            if process.poll() is not None:break
        (root/(label+'.ansi')).write_bytes(client['content'])
        raise AssertionError('native TUI did not display saved history: '+label)
    def close_tui(client):
        process=client['process']
        if process.poll() is None:
            for unused in range(2):
                os.write(client['master'],b'\x03')
                try:process.wait(timeout=2);break
                except subprocess.TimeoutExpired:pass
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
        (root/(client['label']+'.ansi')).write_bytes(client['content'])
        os.close(client['master']);clients.remove(client)
    requests = []
    class Provider(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length', '0')))
            requests.append(self.path)
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
            message=dict(id='msg_fixture',type='message',status='completed',role='assistant',content=[dict(type='output_text',text='SYNTHETIC private copied notify completed',annotations=[])])
            values=[dict(type='response.created',response=dict(id='resp_fixture',status='in_progress',output=[])),dict(type='response.output_item.done',output_index=0,item=message),dict(type='response.completed',response=dict(id='resp_fixture',status='completed',output=[message],usage=dict(input_tokens=1,output_tokens=1,total_tokens=2,input_tokens_details=dict(cached_tokens=0),output_tokens_details=dict(reasoning_tokens=0))))]
            for value in values:self.wfile.write(('data: '+json.dumps(value)+'\n\n').encode())
            self.wfile.flush()
        def log_message(self,*unused):pass
    provider=http.server.ThreadingHTTPServer(('127.0.0.1',0),Provider)
    threading.Thread(target=provider.serve_forever,daemon=True).start()
    import codex_wake
    receipt=dict(status='incomplete',source_commit=args.source_commit,wheel_sha256=args.wheel_sha256,
        installed_prefix=str(Path(sys.executable).parent.parent),installed_module=str(Path(codex_wake.__file__).resolve()),
        installed_version=importlib.metadata.version('codex-wake'),host_uid=1017,external_network=False,
        root=str(root),checks={},native_packages={})
    actual = {}
    def private_files(home):
        return {str(p.relative_to(home)):hashlib.sha256(p.read_bytes()).hexdigest() for p in home.rglob('*') if p.is_file()}
    try:
        call('accounts','init','--json')
        stock=root/'stock';stock.mkdir(mode=0o700);(stock/'hooks').mkdir(mode=0o700)
        notify=stock/'hooks/notify.py'
        notify.write_text('import json,sys\nfrom pathlib import Path\nwith Path(sys.argv[1]).open("a") as output: output.write(json.dumps({"script":__file__,"event":json.loads(sys.argv[-1])})+"\\n")\n')
        stock.joinpath('config.toml').write_text(
            'model="gpt-5.1"\nmodel_provider="fixture"\nmodel_catalog_json='+json.dumps(str(args.models))+'\n'
            'notify='+json.dumps([sys.executable,str(notify),str(root/'notifications.jsonl')])+'\n'
            'check_for_update_on_startup=false\n[analytics]\nenabled=false\n'
            '[model_providers.fixture]\nname="Isolated local scripted responses"\nbase_url='+json.dumps('http://127.0.0.1:'+str(provider.server_port)+'/v1')+'\nwire_api="responses"\nrequires_openai_auth=false\n'
            '[projects.'+json.dumps(str(root))+']\ntrust_level="trusted"\n')
        source_config=private_files(stock)
        call('stores','register','stock','--home',str(stock),'--json')
        for name in ('alice','bob'):call('accounts','create',name,'--mode','independent','--source','stock','--json')
        assert private_files(stock)==source_config
        manifest=dict(schema_version=1,builds={})
        for channel,package in (('stock',args.stock),('modded',args.modded)):
            binary=package.absolute()/'bin/codex'
            digest=hashlib.sha256(binary.read_bytes()).hexdigest()
            manifest['builds'][channel]=dict(executable=str(binary),sha256=digest,upstream_version='0.167.0',revision=channel+'-167',source='https://github.com/openai/codex/releases/download/rust-v0.167.0/codex-package-x86_64-unknown-linux-musl.tar.gz' if channel=='stock' else 'qualified-modified167',read_schemas=[5],backend='managed')
            receipt['native_packages'][channel]=dict(root=str(package),sha256=digest)
        (root/'builds.json').write_text(json.dumps(manifest))
        with (root/'controller-accounts.toml').open('a') as output:
            output.write('\n[builds]\nmanifest='+json.dumps(str(root/'builds.json'))+'\n[history]\nreadable_accounts=["stock","alice","bob"]\n')
        for name in ('alice','bob'):
            account=call('accounts','resolve',name,'--json')['result']['account']
            home=Path(account['home'])
            assert account['independent'] is True
            assert not home.joinpath('config.toml').is_symlink()
            text=home.joinpath('config.toml').read_text()
            assert str(home/'hooks/notify.py') in text and str(stock/'hooks/notify.py') not in text
            assert home.joinpath('hooks/notify.py').read_bytes()==notify.read_bytes()
            assert not home.joinpath('auth.json').exists()
            receipt['checks'][name+'_private_seed']=True
        assert private_files(stock)==source_config
        for name in ('stock','alice','bob'):
            current,unused,unused_operation=mutate('start',name,'managed-start-'+name)
            owned.append(name);actual[name]=current
            assert current['state']=='running' and current['selected_build_running'] is True,current
            assert current['target']['build_channel']==('stock' if name=='stock' else 'modded')
            receipt['checks'][name+'_managed_ready']=current
        for source,destination in (('stock','alice'),('alice','stock'),('alice','bob')):
            label=source+'-to-'+destination
            seeded=[seed(actual[source],label+'-'+str(index)) for index in range(2)]
            before={identifier:Path(read(actual[source],identifier)['path']).read_bytes() for identifier in seeded}
            preview=call('history','import-recent','--owner',source,'--destination',destination,'--limit','2','--preview','--json')
            assert len(preview['entries'])==2 and not preview['holds'],preview
            assert {entry['thread_id'] for entry in preview['entries']}==set(seeded),preview
            for entry in preview['entries']:
                assert entry['arguments']['channel']=='modded'
                assert entry['arguments']['expected_target']['build_channel']==('stock' if destination=='stock' else 'modded')
            applied=call('history','import-recent','--batch',preview['id'],'--yes','--json')
            assert applied['status']=='completed' and all(entry['status']=='copied' for entry in applied['entries']),applied
            replay=call('history','import-recent','--batch',preview['id'],'--yes','--json')
            assert replay==applied,replay
            for identifier in seeded:assert Path(read(actual[source],identifier)['path']).read_bytes()==before[identifier]
            children=[entry['destination_thread_id'] for entry in applied['entries']]
            for child in children:assert read(actual[destination],child)['id']==child
            receipt['checks'][label+'_frozen_batch']=dict(batch_id=preview['id'],selected=seeded,children=children,preview_apply_replay=True,source_unchanged=True)
        # Normal installed shortcut resumes copied history in both build families.
        for name in ('stock','bob'):
            selected=next(value for key,value in receipt['checks'].items() if key.endswith('-to-'+name+'_frozen_batch'))
            child=selected['children'][0]
            # Saved fixture answers are distinct and visible in the actual TUI.
            source='alice-to-'+name
            visible='SYNTHETIC '+source
            client=open_tui(name,child,visible,'resume-'+name)
            close_tui(client)
            receipt['checks'][name+'_shortcut_resume_tui']=True
        # A genuine completed local turn executes the copied profile notify script.
        thread=seed(actual['alice'],'notify')
        rpc(actual['alice'],'thread/resume',dict(threadId=thread,approvalPolicy='never',sandbox='read-only'))
        turn=rpc(actual['alice'],'turn/start',dict(threadId=thread,input=[dict(type='text',text='SYNTHETIC notify acceptance',text_elements=[])]))['turn']['id']
        deadline=time.monotonic()+20
        while True:
            observed=read(actual['alice'],thread)
            notification=root/'notifications.jsonl'
            if observed['turns'][-1]['status']=='completed' and notification.exists():break
            assert time.monotonic()<deadline,observed
            time.sleep(.05)
        notifications=[json.loads(line) for line in notification.read_text().splitlines()]
        expected_script=str(root/'accounts/codex-alice/hooks/notify.py')
        assert any(value['script']==expected_script for value in notifications),notifications
        assert requests and all(path=='/v1/responses' for path in requests),requests
        receipt['checks']['copied_notify_executed']=dict(script=expected_script,turn_id=turn,events=notifications)
        receipt['local_provider_requests']=len(requests)
        receipt['status']='passed'
    except Exception as error:
        import traceback
        receipt.update(status='failed',error=str(error),traceback=traceback.format_exc())
    finally:
        for client in list(clients):close_tui(client)
        for name in reversed(owned):
            try:mutate('stop',name,'managed-stop-'+name)
            except Exception as error:record('cleanup_error',dict(account=name,error=str(error)))
        # Fresh OS census checks the exact synthetic homes, including detached daemons.
        leftovers=[]
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():continue
            try:
                executable=proc.joinpath('exe').resolve().name
                environment=proc.joinpath('environ').read_bytes().split(b'\0')
                if executable=='codex' and any(value.startswith(b'CODEX_HOME='+str(root).encode()+b'/') for value in environment):
                    leftovers.append(dict(pid=int(proc.name),command=proc.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')))
            except (OSError,RuntimeError):pass
        receipt['final_owned_processes']=leftovers
        if leftovers:receipt['status']='failed'
        provider.shutdown();provider.server_close()
        (root/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,sort_keys=True))
    return 0 if receipt['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
