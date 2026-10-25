"""Opt-in, isolated two-thread scoped MCP reload acceptance; zero model turns.

This is a runtime probe, never part of default tests. Only the supplied empty
fixture root, its private native server, and identity-owned children are changed.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from codex_wake.native_protocol import native_request


def write(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');path.chmod(0o600)


def execute(root,prefix,app_server=None,previous_prefix=None,wake_workflow=False):
    root.mkdir(mode=0o700,parents=True,exist_ok=False)
    home=root/'home';home.mkdir(mode=0o700)
    workspace=root/'workspace';workspace.mkdir(mode=0o700)
    wake_root=root/'wake';wake_root.mkdir(mode=0o700)
    codex=Path(subprocess.check_output(['which','codex'],text=True).strip()).resolve()
    python=prefix/'bin/python';cli=prefix/'bin/codex-wake'
    profiles=root/'profiles.json';write(profiles,dict(version=1,profiles={},callers={}))
    toy=root/'toy.py';toy_pids=root/'toy-pids.jsonl'
    toy.write_text('''import json,sys,os
version=sys.argv[1]
with open(sys.argv[2],'a') as f:f.write(json.dumps(dict(pid=os.getpid(),version=version))+'\\n')
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r:continue
 method=r['method']
 if method=='initialize':v=dict(protocolVersion=r['params']['protocolVersion'],capabilities={'tools':{}},serverInfo=dict(name='owned-shared-refresh-toy',version=version))
 elif method=='tools/list':v={'tools':[dict(name=name,description=name+' '+version,inputSchema={'type':'object','properties':{},'additionalProperties':False},annotations={'readOnlyHint':True}) for name in (['version','extra_v2'] if version=='v2' else ['version'])]}
 elif method=='tools/call':v={'content':[{'type':'text','text':version}],'isError':False}
 else:v={}
 print(json.dumps(dict(jsonrpc='2.0',id=r['id'],result=v)),flush=True)
''')
    def config(version):
        active_prefix=previous_prefix if version=='v1' and previous_prefix else prefix
        (home/'config.toml').write_text('model = "gpt-5.4"\nmodel_provider = "owned_no_provider"\napproval_policy = "never"\n'+
            '[model_providers.owned_no_provider]\nname = "Owned no-provider fixture"\nbase_url = "http://127.0.0.1:1/v1"\nwire_api = "responses"\nrequires_openai_auth = false\nsupports_websockets = false\nrequest_max_retries = 0\nstream_max_retries = 0\n'+
            '[projects.'+json.dumps(str(workspace))+']\ntrust_level = "trusted"\n'+
            '[mcp_servers.toy]\ncommand = '+json.dumps(str(python))+'\nargs = '+json.dumps([str(toy),version,str(toy_pids)])+'\n'+
            '[mcp_servers.wake_lifecycle]\ncommand = '+json.dumps(str(active_prefix/'bin/codex-wake-mcp'))+'\nargs = '+json.dumps([
                '--cli',str(active_prefix/'bin/codex-wake'),'--wake-root',str(wake_root),'--lifecycle-profiles',str(profiles),'--call-timeout','15'])+'\n')
    config('v1')
    env=dict(os.environ,CODEX_HOME=str(home),XDG_STATE_HOME=str(root/'state'))
    for key in ('CODEX_THREAD_ID','TMUX','TMUX_PANE','CODEX_WAKE_A2A_CAPABILITY','CODEX_WAKE_A2A_BUS_ROOT',
                'CODEX_WAKE_SENDER_RECEIPT_AUTHORITY','PYTHONPATH','OPENAI_API_KEY','OPENAI_BASE_URL',
                'CODEX_API_KEY','AZURE_OPENAI_API_KEY'):
        env.pop(key,None)
    receipt=dict(state='preparing',root=str(root),prefix=str(prefix),codex=str(codex),model_turn_limit=0,
        authority='Issues318/319 disposable two-thread scoped reload acceptance')
    server=None;watcher=None;native_log=(root/'native.log').open('w');watch_log=(root/'watch.log').open('w')
    started=time.monotonic()
    def request(method,params):
        if time.monotonic()-started>100:raise TimeoutError('owned probe attempt budget exhausted')
        return native_request(endpoint,str(codex),method,params,8)
    def snapshot(thread):
        return dict(goal=request('thread/goal/get',{'threadId':thread})['goal'],
            native=request('thread/read',{'threadId':thread,'includeTurns':True})['thread'],
            catalog=request('mcpServerStatus/list',{'threadId':thread,'serverName':'toy','detail':'toolsAndAuthOnly','runtimeOnly':True}),
            behavior=request('mcpServer/tool/call',{'threadId':thread,'server':'toy','tool':'version','arguments':{}}))
    def emit():write(root/'receipt.json',receipt)
    try:
        server=subprocess.Popen(([str(app_server)] if app_server else [str(codex),'app-server'])+['--listen','unix://'+str(root/'native.sock')],
            env=env,stdout=native_log,stderr=native_log,start_new_session=True)
        until=time.monotonic()+15
        while not (root/'native.sock').exists() and server.poll() is None and time.monotonic()<until:time.sleep(.05)
        endpoint='unix://'+str((root/'native.sock').resolve(strict=True))
        receipt.update(server_pid=server.pid,endpoint=endpoint)
        threads=[request('thread/start',{'cwd':str(workspace),'ephemeral':False})['thread']['id'] for _ in range(2)]
        receipt['threads']=threads;emit()
        for thread in threads:
            request('thread/goal/set',dict(threadId=thread,objective='Owned zero-turn shared refresh acceptance',
                status='paused',tokenBudget=1000,origin='automatic'))
        receipt['before']={thread:snapshot(thread) for thread in threads}
        if any(value['behavior'].get('content')!=[{'type':'text','text':'v1'}] for value in receipt['before'].values()):
            raise RuntimeError('startup toy v1 proof failed')
        config('v2')
        receipt['capability']=request('thread/mcpServer/reload',dict(threadId=threads[0],dryRun=True))
        if receipt['capability']!={'threadId':threads[0],'queued':False}:raise RuntimeError('scoped read-only capability proof failed')
        receipt['after_inspection']={thread:snapshot(thread) for thread in threads}
        if receipt['after_inspection']!=receipt['before']:raise RuntimeError('inspection changed a thread')
        if wake_workflow:
            from codex_wake.a2a_bus import BusStore
            from codex_wake.session_permissions import PermissionStore, Principal
            PermissionStore(wake_root).configure({'version':1},Principal('operator','operator'),expected_revision=0)
            bus,capability=BusStore.configure(root/'operator-bus')
            checkpoint=workspace/'checkpoint.json'
            write(checkpoint,dict(source_thread_id=threads[0],objective='Keep exact goal',
                authority='User-approved scoped refresh proof',next_packet='Inspect refreshed resource',pending_obligations=[]))
            write(profiles,dict(version=1,callers={},profiles={'owned':dict(
                refresh_mode='thread_mcp_idle',scope_approval='Exact selected thread only',
                cwd=str(workspace),app_server=endpoint,codex_path=str(codex),timeout=4,
                resources={'toy':dict(kind='mcp',server='toy',tool='version',arguments={},read_only=True,
                    expected_content=[dict(type='text',text='v2')]),
                    'wake':dict(kind='mcp_catalog',server='wake_lifecycle',
                        version=subprocess.check_output([str(cli),'--version'],text=True).strip().split()[-1],
                        tools={'wake_permissions_show':[]})})}))
            watcher=subprocess.Popen([str(cli),'--wake-root',str(wake_root),'sessions','refresh-watch','--interval','0.1'],
                env=env,stdout=watch_log,stderr=watch_log,start_new_session=True)
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                heartbeat=wake_root/'shared-refresh/controller.json'
                if heartbeat.exists() and json.loads(heartbeat.read_text()).get('active'):break
                time.sleep(.05)
            expiry=datetime.fromtimestamp(time.time()+45,timezone.utc).isoformat()
            argv=[str(cli),'--wake-root',str(wake_root),'sessions','refresh','--profiles',str(profiles),
                '--profile','owned','--thread-id',threads[0],'--caller-thread-id',threads[0],
                '--scope','current_connection','--bus-root',str(bus.root),'--operator-capability',str(capability),
                '--checkpoint','checkpoint.json','--checkpoint-sha256',hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                '--resource','toy','--resource','wake','--expires-at',expiry,'--intent','owned-scoped-refresh','--json']
            deadline=time.monotonic()+40
            while time.monotonic()<deadline:
                process=subprocess.run(argv,env=env,text=True,capture_output=True,timeout=15)
                value=json.loads(process.stdout)
                receipt['wake_refresh']=value
                if process.returncode or value.get('state') in ('completed','blocked','expired'):break
                time.sleep(.1)
            if process.returncode or value.get('state')!='completed':raise RuntimeError('Wake workflow incomplete: '+str(value))
        else:
            receipt['admission']=request('thread/mcpServer/reload',dict(threadId=threads[0]))
            if receipt['admission']!={'threadId':threads[0],'queued':True}:raise RuntimeError('scope admission mismatch')
        until=time.monotonic()+15
        while time.monotonic()<until:
            selected=snapshot(threads[0])
            if selected['behavior'].get('content')==[{'type':'text','text':'v2'}]:break
            time.sleep(.05)
        receipt['after']={thread:snapshot(thread) for thread in threads}
        receipt['same_threads']=all(receipt['after'][thread]['native']['id']==thread for thread in threads)
        receipt['goals_unchanged']=all(receipt['before'][thread]['goal']==receipt['after'][thread]['goal'] for thread in threads)
        receipt['model_turns']=sum(len(value['native']['turns']) for value in receipt['after'].values())
        receipt['selected_v2_peer_v1']=(receipt['after'][threads[0]]['behavior'].get('content')==[{'type':'text','text':'v2'}] and receipt['after'][threads[1]]['behavior'].get('content')==[{'type':'text','text':'v1'}])
        receipt['selected_new_catalog_peer_unchanged']=('extra_v2' in receipt['after'][threads[0]]['catalog']['data'][0]['tools'] and 'extra_v2' not in receipt['after'][threads[1]]['catalog']['data'][0]['tools'])
        receipt['toy_processes']=[json.loads(line) for line in toy_pids.read_text().splitlines()]
        receipt['exact_toy_startups']=sorted(row['version'] for row in receipt['toy_processes'])==['v1','v1','v2']
        if previous_prefix:
            def wake_version(section,thread):
                return next(row['serverInfo']['version'] for row in receipt[section][thread]['catalog']['data'] if row['name']=='wake_lifecycle')
            receipt['selected_wake_version']=wake_version('after',threads[0])
            receipt['peer_wake_version']=wake_version('after',threads[1])
            if receipt['selected_wake_version']==receipt['peer_wake_version']:raise RuntimeError('selected Wake process did not upgrade independently')
            if receipt['peer_wake_version']!=wake_version('before',threads[1]):raise RuntimeError('peer Wake process changed')
        if not all((receipt['exact_toy_startups'],receipt['same_threads'],receipt['goals_unchanged'],receipt['model_turns']==0,
                    receipt['selected_v2_peer_v1'],receipt['selected_new_catalog_peer_unchanged'])):raise RuntimeError('continuity or v2 proof failed')
        receipt['state']='passed'
    except Exception as exc:receipt.update(state='failed',error=type(exc).__name__+': '+str(exc))
    finally:
        for process in (watcher,server):
            if process is not None and process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=8)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
        native_log.close();watch_log.close()
        remaining=[];denied=[]
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:
                if entry.stat().st_uid==os.getuid() and ('CODEX_HOME='+str(home)).encode() in (entry/'environ').read_bytes().split(b'\0'):
                    remaining.append(int(entry.name))
            except PermissionError:denied.append(int(entry.name))
            except (FileNotFoundError,ProcessLookupError):pass
        toy_survivors=[]
        if toy_pids.exists():
            for line in toy_pids.read_text().splitlines():
                pid=json.loads(line)['pid']
                try:
                    if str(toy).encode() in Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0'):
                        toy_survivors.append(pid)
                except (FileNotFoundError,ProcessLookupError):pass
        receipt['cleanup']=dict(toy_process_survivors=toy_survivors,server_exit=server.poll() if server else None,watcher_exit=watcher.poll() if watcher else None,
            private_home_processes=remaining,denied_environment_pids=denied)
        if remaining or toy_survivors:receipt.update(state='failed',cleanup_error='owned processes remain')
        receipt['elapsed_seconds']=time.monotonic()-started;emit()
    print(json.dumps({key:receipt.get(key) for key in ('state','error','root','model_turns','cleanup','elapsed_seconds')}))
    return 0 if receipt['state']=='passed' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--prefix',type=Path,required=True)
    parser.add_argument('--app-server',type=Path)
    parser.add_argument('--previous-prefix',type=Path)
    parser.add_argument('--wake-workflow',action='store_true')
    args=parser.parse_args()
    raise SystemExit(execute(args.root.resolve(),args.prefix.resolve(),args.app_server,args.previous_prefix,args.wake_workflow))
