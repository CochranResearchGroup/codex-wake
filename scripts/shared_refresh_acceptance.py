"""Opt-in, isolated two-thread shared MCP reload acceptance; zero model turns.

This is a runtime probe, never part of default tests. Only the supplied empty
fixture root, its private native server, and identity-owned children are changed.
"""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
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


def execute(root,prefix):
    root.mkdir(mode=0o700,parents=True,exist_ok=False)
    home=root/'home';home.mkdir(mode=0o700)
    workspace=root/'workspace';workspace.mkdir(mode=0o700)
    wake_root=root/'wake';wake_root.mkdir(mode=0o700)
    codex=Path(subprocess.check_output(['which','codex'],text=True).strip()).resolve()
    python=prefix/'bin/python';cli=prefix/'bin/codex-wake';mcp=prefix/'bin/codex-wake-mcp'
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
    skill=workspace/'.agents/skills/shared-refresh-marker/SKILL.md';skill.parent.mkdir(parents=True)
    def skill_version(version):
        skill.write_text('---\nname: shared-refresh-marker\ndescription: Owned shared refresh marker '+version+'\n---\nMarker '+version+'.\n')
    def config(version):
        (home/'config.toml').write_text('model = "gpt-5.4"\napproval_policy = "never"\n'+
            '[projects.'+json.dumps(str(workspace))+']\ntrust_level = "trusted"\n'+
            '[mcp_servers.toy]\ncommand = '+json.dumps(str(python))+'\nargs = '+json.dumps([str(toy),version,str(toy_pids)])+'\n'+
            '[mcp_servers.wake_lifecycle]\ncommand = '+json.dumps(str(mcp))+'\nargs = '+json.dumps([
                '--cli',str(cli),'--wake-root',str(wake_root),'--lifecycle-profiles',str(profiles),'--call-timeout','15'])+'\n')
    config('v1');skill_version('v1')
    env=dict(os.environ,CODEX_HOME=str(home),XDG_STATE_HOME=str(root/'state'))
    for key in ('CODEX_THREAD_ID','TMUX','TMUX_PANE','CODEX_WAKE_A2A_CAPABILITY','CODEX_WAKE_A2A_BUS_ROOT',
                'CODEX_WAKE_SENDER_RECEIPT_AUTHORITY','PYTHONPATH'):
        env.pop(key,None)
    receipt=dict(state='preparing',root=str(root),prefix=str(prefix),codex=str(codex),model_turn_limit=0,
        authority='Plan0168 disposable two-thread shared idle reload acceptance')
    server=None;watcher=None;native_log=(root/'native.log').open('w');watch_log=(root/'watch.log').open('w')
    started=time.monotonic()
    def request(method,params):
        if time.monotonic()-started>100:raise TimeoutError('owned probe attempt budget exhausted')
        return native_request(endpoint,str(codex),method,params,8)
    def snapshot(thread):
        return dict(goal=request('thread/goal/get',{'threadId':thread})['goal'],
            native=request('thread/read',{'threadId':thread,'includeTurns':True})['thread'],
            catalog=request('mcpServerStatus/list',{'threadId':thread,'serverName':'toy','detail':'toolsAndAuthOnly'}),
            behavior=request('mcpServer/tool/call',{'threadId':thread,'server':'toy','tool':'version','arguments':{}}))
    def emit():write(root/'receipt.json',receipt)
    try:
        server=subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(root/'native.sock')],
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
        receipt['skills_before']=request('skills/list',{'cwds':[str(workspace)],'forceReload':False})
        if any(value['behavior'].get('content')!=[{'type':'text','text':'v1'}] for value in receipt['before'].values()):
            raise RuntimeError('startup toy v1 proof failed')
        skill_version('v2');config('v2')
        # Host-authorized resources select read-only, exact output evidence.
        profile=dict(cwd=str(workspace),codex_home=str(home),codex_path=str(codex),app_server=endpoint,timeout=5,
            refresh_mode='shared_mcp_idle',scope_approval='Plan0168 owned fixture; both loaded conversations idle; shared reload approved',
            resources=dict(skill=dict(kind='skill',path=str(skill),description='Owned shared refresh marker v2',
                sha256=hashlib.sha256(skill.read_bytes()).hexdigest()),
                mcp=dict(kind='mcp',server='toy',tool='version',arguments={},read_only=True,
                    expected_content=[{'type':'text','text':'v2'}])))
        write(profiles,dict(version=1,profiles={'owned':profile},callers={threads[0]:['owned']}))
        checkpoint=workspace/'checkpoint.json'
        write(checkpoint,dict(source_thread_id=threads[0],objective='Qualify shared idle reload',authority='Explicit owned-fixture reload approval',
            next_packet='Read selected skill and toy MCP behavior',pending_obligations=[]))
        clock=subprocess.run([str(python),'-I','-c','import json; from codex_wake.native_clock import snapshot; print(json.dumps(snapshot()))'],
            env=env,text=True,capture_output=True,timeout=15,check=True)
        upper=json.loads(clock.stdout).get('utc',{}).get('upper')
        if upper is None:raise RuntimeError('qualified fixed expiry clock unavailable')
        body=dict(profile='owned',intent='owned-shared-idle-refresh',thread_id=threads[0],caller_thread_id=threads[0],
            checkpoint='checkpoint.json',checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            resources=['skill','mcp'],expires_at=datetime.fromtimestamp(upper+75,UTC).isoformat())
        watcher=subprocess.Popen([str(cli),'--wake-root',str(wake_root),'sessions','refresh-watch','--interval','.1'],
            env=env,stdout=watch_log,stderr=watch_log,start_new_session=True)
        receipt['watcher_pid']=watcher.pid
        heartbeat=wake_root/'shared-refresh/controller.json'
        until=time.monotonic()+8
        while not heartbeat.exists() and watcher.poll() is None and time.monotonic()<until:time.sleep(.05)
        if not heartbeat.exists():raise RuntimeError('independent watcher heartbeat unavailable')
        call=request('mcpServer/tool/call',dict(threadId=threads[0],server='wake_lifecycle',tool='wake_sessions_refresh',arguments=body))
        receipt['public_mcp_result']=call
        initial=json.loads(call['content'][0]['text']);receipt['initial_refresh']=initial;emit()
        until=min(started+100,time.monotonic()+40)
        observed=initial
        while time.monotonic()<until:
            receipt['refresh']=observed
            if observed.get('state') in ('completed','blocked','uncertain','expired'):break
            if watcher.poll() is not None:raise RuntimeError('independent watcher exited')
            time.sleep(.2)
            readback=request('mcpServer/tool/call',dict(threadId=threads[0],server='wake_lifecycle',tool='wake_sessions_refresh',arguments=body))
            observed=json.loads(readback['content'][0]['text'])
        else:raise TimeoutError('shared refresh completion not observed')
        emit()
        if receipt['refresh']['state']!='completed':raise RuntimeError('public shared refresh did not complete')
        receipt['after']={thread:snapshot(thread) for thread in threads}
        receipt['same_threads']=all(receipt['after'][thread]['native']['id']==thread for thread in threads)
        receipt['goals_unchanged']=all(receipt['before'][thread]['goal']==receipt['after'][thread]['goal'] for thread in threads)
        receipt['model_turns']=sum(len(value['native']['turns']) for value in receipt['after'].values())
        receipt['toy_v2_both']=all(value['behavior'].get('content')==[{'type':'text','text':'v2'}] for value in receipt['after'].values())
        receipt['new_catalog_both']=all('extra_v2' in value['catalog']['data'][0]['tools'] for value in receipt['after'].values())
        receipt['toy_processes']=[json.loads(line) for line in toy_pids.read_text().splitlines()]
        if not all((receipt['same_threads'],receipt['goals_unchanged'],receipt['model_turns']==0,
                    receipt['toy_v2_both'],receipt['new_catalog_both'])):raise RuntimeError('continuity or v2 proof failed')
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
        receipt['cleanup']=dict(server_exit=server.poll() if server else None,watcher_exit=watcher.poll() if watcher else None,
            private_home_processes=remaining,denied_environment_pids=denied)
        if remaining:receipt.update(state='failed',cleanup_error='owned processes remain')
        receipt['elapsed_seconds']=time.monotonic()-started;emit()
    print(json.dumps({key:receipt.get(key) for key in ('state','error','root','model_turns','cleanup','elapsed_seconds')}))
    return 0 if receipt['state']=='passed' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--prefix',type=Path,required=True)
    args=parser.parse_args()
    raise SystemExit(execute(args.root.resolve(),args.prefix.resolve()))
