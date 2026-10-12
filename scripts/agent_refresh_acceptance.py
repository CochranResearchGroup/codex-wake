"""Opt-in installed, owned, no-model refresh and stale-MCP qualification."""
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
import tomllib

from codex_wake.native_protocol import native_request
from codex_wake.sessions import observe


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    path.chmod(0o600)


def execute(root, prefix, paused_goal=False, rollback=False):
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    workspace, home = root / 'workspace', root / 'codex-home'
    workspace.mkdir(); home.mkdir(mode=0o700)
    codex = Path(subprocess.check_output(['which', 'codex'], text=True).strip()).resolve()
    config = tomllib.loads((Path.home() / '.codex/config.toml').read_text())
    selected = {k: config[k] for k in ('model', 'model_reasoning_effort', 'model_provider') if k in config}
    version = root / 'version.txt'; version.write_text('v1')
    toy = root / 'toy-mcp.py'
    toy.write_text('''import json,sys,os,pathlib
version=pathlib.Path(sys.argv[1]).read_text().strip()
with pathlib.Path(sys.argv[2]).open('a') as f:f.write(json.dumps(dict(pid=os.getpid(),version=version))+'\\n')
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r:continue
 method=r['method']
 if method=='initialize':v=dict(protocolVersion=r['params']['protocolVersion'],capabilities={'tools':{}},serverInfo=dict(name='toy',version=version))
 elif method=='tools/list':v={'tools':[dict(name='version',description='Read toy version '+version,inputSchema={'type':'object','properties':{},'additionalProperties':False},annotations={'readOnlyHint':True})]}
 elif method=='tools/call':v={'content':[{'type':'text','text':version}],'isError':False}
 elif method=='ping':v={}
 else:v={}
 print(json.dumps(dict(jsonrpc='2.0',id=r['id'],result=v)),flush=True)
''')
    profiles = root / 'profiles.json'
    lines = [f'{k} = {json.dumps(v)}' for k, v in selected.items()]
    lines += ['approval_policy = "never"', 'sandbox_mode = "workspace-write"',
        f'[projects.{json.dumps(str(workspace))}]', 'trust_level = "trusted"',
        '[mcp_servers.toy]', f'command = {json.dumps(str(prefix / "bin/python"))}',
        'args = ' + json.dumps([str(toy), str(version), str(root/'mcp-processes.jsonl')]),
        '[mcp_servers.wake_lifecycle]', f'command = {json.dumps(str(prefix / "bin/codex-wake-mcp"))}',
        'args = ' + json.dumps(['--cli', str(prefix/'bin/codex-wake'), '--wake-root', str(root/'wake'),
                               '--lifecycle-profiles', str(profiles), '--call-timeout', '45'])]
    (home/'config.toml').write_text('\n'.join(lines)+'\n')
    (home/'auth.json').symlink_to(Path.home()/'.codex/auth.json')
    skill = workspace/'.agents/skills/refresh-marker/SKILL.md'; skill.parent.mkdir(parents=True)
    def skill_version(marker):
        skill.write_text('---\nname: refresh-marker\ndescription: Refresh marker '+marker+'\n---\nMarker '+marker+'.\n')
    skill_version('v1')
    env = dict(os.environ, CODEX_HOME=str(home), XDG_STATE_HOME=str(root/'state'))
    for key in ('CODEX_THREAD_ID','TMUX','TMUX_PANE','CODEX_WAKE_A2A_CAPABILITY',
                'CODEX_WAKE_A2A_BUS_ROOT','CODEX_WAKE_SENDER_RECEIPT_AUTHORITY','PYTHONPATH'):
        env.pop(key,None)
    endpoint = root/'native.sock'; socket = root/'tmux.sock'; session = 'owned-refresh'
    log = (root/'server.log').open('w'); server = None; created = False
    receipt = dict(state='preparing',root=str(root),prefix=str(prefix),model_turn_limit=0,
        authority='execute Plan0156; disposable no-model resource refresh proof',codex=str(codex))
    write(root/'state.json',receipt)
    def tmux(*args):
        return subprocess.check_output(['tmux','-S',str(socket),*args],env=env,text=True,timeout=10)
    def invoke(args):
        result = subprocess.run([str(prefix/'bin/codex-wake'),*args],env=env,text=True,
                                capture_output=True,timeout=45)
        return result.returncode,json.loads(result.stdout)
    try:
        server = subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(endpoint)],
            env=env,stdout=log,stderr=log,start_new_session=True)
        deadline=time.monotonic()+15
        while not endpoint.exists() and server.poll() is None and time.monotonic()<deadline:time.sleep(.1)
        if not endpoint.exists():raise RuntimeError('owned native socket unavailable')
        endpoint=endpoint.resolve()
        def request(method,params):return native_request('unix://'+str(endpoint),str(codex),method,params,10)
        thread=request('thread/start',{'cwd':str(workspace),'ephemeral':False})['thread']['id']
        request('thread/name/set',{'threadId':thread,'name':'owned-refresh-worker'})
        receipt['thread_id']=thread
        write(root/'state.json',receipt)
        tmux('new-session','-d','-s',session,'-x','160','-y','40','sleep 600');created=True
        code,opened=invoke(['sessions','open','--resume',thread,'--name','worker','--cwd',str(workspace),
            '--app-server','unix://'+str(endpoint),'--tmux-socket',str(socket),'--tmux-session',session,
            '--codex-path',str(codex),'--json'])
        if code or not opened.get('ready'):raise RuntimeError('initial owned client not ready')
        old=opened['attachments'][0];receipt['old_attachment']=old
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            if 'Ask Codex to do anything' in tmux('capture-pane','-p','-t',old['pane_id']):break
            time.sleep(.1)
        else:raise RuntimeError('initial empty composer unavailable')
        initial=request('mcpServer/tool/call',{'threadId':thread,'server':'toy','tool':'version','arguments':{}})
        if initial['content'] != [{'type':'text','text':'v1'}]:raise RuntimeError('initial MCP behavior mismatch')
        receipt['initial_mcp']=initial
        if paused_goal:
            # Automatic provenance is deliberate: this probe must not forge a
            # new user-origin authorization for an agent-created fixture goal.
            receipt['goal_creation']=request('thread/goal/set',dict(threadId=thread,
                objective='Plan0156 disposable paused-goal continuity probe',
                status='paused',tokenBudget=1000,origin='automatic'))
        goal=request('thread/goal/get',{'threadId':thread})['goal'];receipt['goal_before']=goal
        if paused_goal and (not goal or goal['status']!='paused'):
            raise RuntimeError('paused native fixture goal not observed')
        skill_version('v2');version.write_text('v2')
        profile=dict(cwd=str(workspace),codex_home=str(home),codex_path=str(codex),
            app_server='unix://'+str(endpoint),tmux_socket=str(socket),tmux_session=session,timeout=10,
            resources={'skill':dict(kind='skill',path=str(skill),description='Refresh marker v2',
                sha256=hashlib.sha256(skill.read_bytes()).hexdigest()),
                'mcp':dict(kind='mcp',server='toy',tool='version',arguments={},read_only=True,
                    expected_content=[{'type':'text','text':'v2'}])})
        write(profiles,dict(version=1,profiles={'worker':profile},callers={thread:['worker']}))
        checkpoint=workspace/'checkpoint.json'
        write(checkpoint,dict(source_thread_id=thread,objective='Qualify owned refresh',
            authority='operator execute Plan0156; no autonomous work',next_packet='Check changed resources',
            pending_obligations=[]))
        clock=json.loads(subprocess.check_output([str(prefix/'bin/python'),'-I','-c',
            'import json; from codex_wake.native_clock import snapshot; print(json.dumps(snapshot()))'],env=env,text=True))
        if not clock.get('utc'):raise RuntimeError('admissible UTC unavailable')
        expiry=datetime.fromtimestamp(clock['utc']['upper']+180,UTC).isoformat()
        body=dict(profile='worker',intent='refresh-resources',thread_id=thread,checkpoint='checkpoint.json',
            checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),resources=['skill','mcp'],
            expires_at=expiry,caller_thread_id=thread)
        result=request('mcpServer/tool/call',{'threadId':thread,'server':'wake_lifecycle',
            'tool':'wake_sessions_refresh','arguments':body})
        lifecycle=json.loads(result['content'][0]['text']);receipt['mcp_refresh']=lifecycle
        # Startup is observed through the same intent; never start a replacement.
        deadline=time.monotonic()+30
        while lifecycle['state']=='awaiting_preflight' and time.monotonic()<deadline:
            result=request('mcpServer/tool/call',{'threadId':thread,'server':'wake_lifecycle',
                'tool':'wake_sessions_refresh','arguments':body})
            lifecycle=json.loads(result['content'][0]['text']);time.sleep(.2)
        receipt['mcp_refresh']=lifecycle
        if (lifecycle['state']!='blocked' or lifecycle.get('reason')!='requested_resources_not_ready'
                or lifecycle['resources']['skill']['state']!='ready'
                or lifecycle['resources']['mcp']['observed_content']!=[{'type':'text','text':'v1'}]):
            raise RuntimeError('stale MCP must block despite updated skill/new client')
        if lifecycle['attachment']['client_pid']==old['client_pid']:raise RuntimeError('old generation retained')
        receipt['state']='passed_stale_resource_axis'
        write(root/'state.json',receipt)
        goal_after=request('thread/goal/get',{'threadId':thread})['goal'];receipt['goal_after']=goal_after
        if goal_after!=goal:raise RuntimeError('native goal changed')
        if rollback:
            result=request('mcpServer/tool/call',{'threadId':thread,'server':'wake_lifecycle',
                'tool':'wake_sessions_refresh','arguments':dict(body,rollback=True)})
            restored=json.loads(result['content'][0]['text']);receipt['mcp_rollback']=restored
            if restored.get('rollback',{}).get('state')!='completed':
                raise RuntimeError('native original conversation rollback not completed')
            if restored['rollback']['goal']!=goal:
                raise RuntimeError('rollback changed native goal')
        history=request('thread/read',{'threadId':thread,'includeTurns':True})['thread']['turns']
        if history:raise RuntimeError('no-model proof unexpectedly created native turns')
        receipt.update(state='passed',model_turns=0)
    except Exception as exc:receipt.update(state='failed',error=str(exc))
    finally:
        if created:subprocess.run(['tmux','-S',str(socket),'kill-session','-t',session],env=env,capture_output=True,timeout=10)
        if server is not None and server.poll() is None:
            os.killpg(server.pid,signal.SIGTERM)
            try:server.wait(timeout=20)
            except subprocess.TimeoutExpired:receipt['shutdown']='timed_out'
        log.close();receipt['server_exit']=server.poll() if server else None
        matches=[];denied=[]
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                if p.stat().st_uid!=os.getuid():continue
                if ('CODEX_HOME='+str(home)).encode() in (p/'environ').read_bytes().split(b'\0'):matches.append(int(p.name))
            except PermissionError:denied.append(int(p.name))
            except (FileNotFoundError,ProcessLookupError):pass
        receipt['cleanup']=dict(private_readable_environment_matches=matches,denied_environment_pids=denied)
        if matches or receipt['server_exit'] is None:receipt.update(state='failed',cleanup_error='owned processes remain')
        write(root/'state.json',receipt)
    print(json.dumps({k:receipt.get(k) for k in ('state','error','root','cleanup')}))
    return 0 if receipt['state']=='passed' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--prefix',type=Path,required=True)
    parser.add_argument('--paused-goal',action='store_true')
    parser.add_argument('--rollback',action='store_true')
    args=parser.parse_args()
    raise SystemExit(execute(args.root.resolve(),args.prefix.resolve(),args.paused_goal,args.rollback))
