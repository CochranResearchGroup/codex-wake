#!/usr/bin/env python3
"""Disposable UID1017 native history acceptance; requires an isolated net namespace."""
import argparse
from datetime import datetime, timezone
import http.server
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
import traceback
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--codex', type=Path, required=True)
    parser.add_argument('--stock', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--outer-netns', required=True)
    args = parser.parse_args()
    assert os.getuid() == 0 and int(Path('/proc/self/uid_map').read_text().split()[1]) == 1017
    assert os.readlink('/proc/self/ns/net') != args.outer_netns
    subprocess.run(['ip', 'link', 'set', 'lo', 'up'], check=True)
    root = args.root
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.environ.update(HOME=str(root), XDG_CONFIG_HOME=str(root/'xdg'), XDG_STATE_HOME=str(root/'state'))
    from codex_wake.controller_accounts import ControllerAccounts
    from codex_wake.controller_history import ControllerHistory
    from codex_wake.controller_history_import import ControllerHistoryImport
    from codex_wake.controller_auth import Actor
    from codex_wake.native_protocol import native_request
    path = root/'controller-accounts.toml'
    path.write_text('[profiles]\nstate_root='+json.dumps(str(root/'profiles'))+'\nknown_profiles=[]\n[history]\nreadable_accounts=["stock","alice","bob"]\n')
    (root/'profiles').mkdir(mode=0o700)
    provider_seen = threading.Event()
    provider_release = threading.Event()
    requests = []
    class Provider(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length', '0')))
            requests.append(self.path)
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            self.wfile.flush()
            provider_seen.set()
            provider_release.wait(30)
        def log_message(self, *unused): pass
    provider = http.server.ThreadingHTTPServer(('127.0.0.1',0), Provider)
    threading.Thread(target=provider.serve_forever,daemon=True).start()
    stock = root/'stock'
    stock.mkdir(mode=0o700)
    stock.joinpath('config.toml').write_text('model="gpt-5.1"\nmodel_provider="offline"\ncheck_for_update_on_startup=false\n[analytics]\nenabled=false\n[model_providers.offline]\nname="Isolated local acceptance"\nbase_url="http://127.0.0.1:PORT/v1"\nwire_api="responses"\nrequires_openai_auth=false\n'.replace('PORT',str(provider.server_port)))
    with stock.joinpath('config.toml').open('a') as output:
        pass
    config=stock/'config.toml'
    config.write_text('model_catalog_json='+json.dumps('/home/codex-daemon-test/daemon-qualification-0167/models.json')+'\n'+config.read_text())
    accounts = ControllerAccounts(path, host='fixture', environment='isolated')
    accounts.execute('stores.register', dict(selector='stock', home=str(stock)))
    for name in ('alice', 'bob'):
        accounts.execute('accounts.create', dict(selector=name, mode='independent', source='stock'))
    binary = str(args.codex)
    processes, logs, daemons = {}, [], {}
    events = []
    receipt = dict(status='incomplete', source_commit=args.source_commit, native_sha256=hashlib.sha256(args.codex.read_bytes()).hexdigest(), stock_sha256=hashlib.sha256(args.stock.read_bytes()).hexdigest(), host_uid=1017, external_network=False, checks={}, final_owned_processes=None)
    def event(kind, value):
        events.append(dict(kind=kind, value=value))
        with (root/'events.jsonl').open('a') as stream:
            stream.write(json.dumps(events[-1], sort_keys=True)+'\n')
    def rpc(name, method, params):
        return native_request(daemons[name]['endpoint'], daemons[name]['target']['executable'], method, params, 10)
    def start(name):
        selected_binary=str(args.stock) if name=='stock' else binary
        account = accounts.execute('accounts.resolve', dict(selector=name))['account']
        endpoint = 'unix://'+str(root/(name+'.sock'))
        log = (root/(name+'-daemon.log')).open('ab');logs.append(log)
        process = subprocess.Popen([selected_binary, 'app-server', '--listen', endpoint], env=dict(PATH=os.environ['PATH'], HOME=str(root), CODEX_HOME=account['home'], XDG_CONFIG_HOME=str(root/'xdg'), XDG_STATE_HOME=str(root/'state'), NO_PROXY='127.0.0.1,localhost'), stdout=log, stderr=log, start_new_session=True)
        processes[name] = process
        daemons[name] = dict(state='running', selected_build_running=True, endpoint=endpoint, target=dict(account['target'], executable=selected_binary, process=dict(pid=process.pid), socket_generation=str(process.pid), build_channel='stock' if name=='stock' else 'modded'))
        deadline = time.monotonic()+12
        while True:
            try:
                if Path(endpoint[7:]).exists():
                    daemons[name]['endpoint']='unix://'+str(Path(endpoint[7:]).resolve(strict=True))
                rpc(name, 'thread/list', dict(limit=1));break
            except Exception:
                if process.poll() is not None or time.monotonic()>deadline:
                    location=Path(endpoint[7:])
                    event('startup-failure',dict(path=str(location),euid=os.geteuid(),mode=location.lstat().st_mode if location.exists() else None,uid=location.lstat().st_uid if location.exists() else None))
                    raise
                time.sleep(.05)
    def stop(name):
        process = processes.pop(name)
        os.killpg(process.pid, signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL);process.wait(timeout=3)
    class Daemons:
        def execute(self, operation, arguments):
            assert arguments['channel']==('stock' if arguments['account']=='stock' else 'modded'), arguments
            return dict(daemon=daemons[arguments['account']])
    reader = ControllerHistory(path, root=root, host='fixture', environment='isolated', authorized_accounts=['stock','alice','bob'])
    importer = ControllerHistoryImport(root, host='fixture', environment='isolated', daemon_owner=Daemons())
    def seed(name, label):
        identifier, turn = str(uuid4()), str(uuid4())
        stamp = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        rows = [dict(type='session_meta', payload=dict(id=identifier,timestamp=stamp,cwd=str(root),originator='codex_cli_rs',cli_version='0.167.0',source='cli',model_provider='offline'))]
        for payload in (dict(type='task_started',turn_id=turn,model_context_window=200000),dict(type='user_message',message='SYNTHETIC '+label,images=[],local_images=[],text_elements=[]),dict(type='agent_message',message='SYNTHETIC saved answer '+label,phase='final_answer'),dict(type='task_complete',turn_id=turn,last_agent_message='SYNTHETIC saved answer '+label)):
            rows.append(dict(type='event_msg',payload=payload))
        source = root/(label+'-seed.jsonl')
        source.write_text(''.join(json.dumps(dict(timestamp=stamp,**row))+'\n' for row in rows))
        result = rpc(name, 'thread/fork', dict(threadId=identifier,path=str(source),ephemeral=False,approvalPolicy='never',sandbox='read-only'))
        return result['thread']['id']
    def transfer(source, destination, thread, label):
        pin = reader.execute('history.read', dict(owner=source, thread_id=thread))['session']['target']
        target = daemons[destination]['target']
        actor = Actor('fixture','owner','acceptance','grant','local','wake',frozenset(['control','observe','history.observe']),[pin,target],time.time()+600)
        arguments = dict(owner=source,destination=destination,thread_id=thread,expected_source=pin,expected_target=target,channel='modded',_request=dict(operation_id=label,idempotency_key=label,correlation_id=label,binding='acceptance',target=target))
        value = importer.execute(actor,'history.import',arguments,authorize=lambda:actor)['result']['operation']
        event(label,value)
        assert value['execution']=='completed', value
        return value['result']
    try:
        for name in ('stock','alice','bob'):start(name)
        for source,destination in [('stock','alice'),('alice','stock'),('alice','bob')]:
            label=source+'-to-'+destination
            thread=seed(source,label)
            before=rpc(source,'thread/read',dict(threadId=thread,includeTurns=True))['thread']
            content=Path(before['path']).read_bytes()
            copied=transfer(source,destination,thread,label)
            assert Path(before['path']).read_bytes()==content
            repeated=transfer(source,destination,thread,label+'-again')
            assert repeated['thread_id']==copied['thread_id']
            stop(destination);start(destination)
            restarted=transfer(source,destination,thread,label+'-restart')
            assert restarted['thread_id']==copied['thread_id']
            receipt['checks'][label]=dict(native_copy=True,source_unchanged=True,revision_reused=True,restart_reused=True)
            retained_path=Path(copied['rollout_path']);retained_bytes=retained_path.read_bytes()
            new_turn=str(uuid4());stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            with Path(before['path']).open('a') as stream:
                for payload in (dict(type='task_started',turn_id=new_turn,model_context_window=200000),dict(type='user_message',message='SYNTHETIC advanced source',images=[],local_images=[],text_elements=[]),dict(type='agent_message',message='SYNTHETIC advanced answer',phase='final_answer'),dict(type='task_complete',turn_id=new_turn,last_agent_message='SYNTHETIC advanced answer')):
                    stream.write(json.dumps(dict(timestamp=stamp,type='event_msg',payload=payload))+'\n')
            advanced=transfer(source,destination,thread,label+'-advanced')
            assert advanced['thread_id']!=copied['thread_id']
            assert advanced['provenance']['previous_snapshot_thread_id']==copied['thread_id']
            assert retained_path.read_bytes()==retained_bytes
            receipt['checks'][label].update(advanced_linked=True,prior_copy_preserved=True)
            seed(source,label+'-recent-second')
            selected=reader.execute('history.search',dict(owners=[source],sort='recent',limit=2))
            assert len(selected['sessions'])==2 and not selected['holds'], selected
            copied_recent=[transfer(source,destination,row['thread_id'],label+'-recent-'+str(index))['thread_id'] for index,row in enumerate(selected['sessions'])]
            receipt['checks'][label]['recent_n_owner_selection']=dict(selected=2,copied=2,destination_threads=copied_recent)

        lost_thread=seed('alice','lost-result')
        actual_request=importer.request
        submitted=[]
        def lose_result(*values,**kwargs):
            value=actual_request(*values,**kwargs)
            event('recovery-native-'+values[2],value)
            if values[2]=='thread/fork':
                submitted.append(value['thread']['id'])
                raise TimeoutError('synthetic lost native fork reply')
            return value
        importer.request=lose_result
        recovered=transfer('alice','bob',lost_thread,'native-lost-recovery')
        importer.request=actual_request
        assert submitted==[recovered['thread_id']], submitted
        receipt['checks']['native_unknown_reconciled']=dict(forks=1,thread_id=recovered['thread_id'])
        thread=seed('stock','prefix')
        rpc('stock','thread/resume',dict(threadId=thread,approvalPolicy='never',sandbox='read-only'))
        running=rpc('stock','turn/start',dict(threadId=thread,input=[dict(type='text',text='SYNTHETIC hold this second turn',text_elements=[])]))
        assert provider_seen.wait(15), 'local provider was never reached'
        active=rpc('stock','thread/read',dict(threadId=thread,includeTurns=True))['thread']
        event('native-active-source',active)
        assert active['status']['type']=='active', active
        assert active['turns'][-1]['status']=='inProgress', active
        original_path=Path(active['path']);before=original_path.read_bytes()
        value=transfer('stock','bob',thread,'prefix-transfer')
        assert value['provenance']['exclusions'], value
        assert original_path.read_bytes()==before
        child=rpc('bob','thread/read',dict(threadId=value['thread_id'],includeTurns=True))['thread']
        assert child['turns']==active['turns'][:-1], child
        rpc('stock','turn/interrupt',dict(threadId=thread,turnId=running['turn']['id']))
        provider_release.set()
        receipt['checks']['real_ongoing_prefix']=dict(active=True,saved_boundary=value['provenance']['saved_boundary'],exclusions=value['provenance']['exclusions'],native_completed_turns_equal=True,source_unchanged=True)
        receipt['local_provider_requests']=len(requests)
        receipt['status']='passed'
    except Exception as error:
        receipt.update(status='failed',error=str(error),traceback=traceback.format_exc())
    finally:
        provider_release.set()
        provider.shutdown()
        provider.server_close()
        for name in list(processes):stop(name)
        for log in logs:log.close()
        # Read process state freshly; do not infer cleanup from service status.
        owned=[]
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():continue
            try:
                cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
                if str(root) in cmd and 'app-server' in cmd:owned.append(int(proc.name))
            except OSError:pass
        receipt['final_owned_processes']=owned
        if owned:receipt['status']='failed'
        (root/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,sort_keys=True))
    return 0 if receipt['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
