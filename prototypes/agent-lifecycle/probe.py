"""PROTOTYPE: disposable real-Codex refresh/handoff observation, not a controller."""
import argparse, hashlib, json, os, pathlib, shlex, subprocess, sys, time, tomllib
ROOT = pathlib.Path(os.environ.get('LIFECYCLE_PROBE_ROOT', '/home/ecochran76/.local/state/codex-wake/plan0155/runtime'))
HOME = ROOT / 'codex-home'
WORK = ROOT / 'workspace'
SOCKET = ROOT / 'app.sock'
SESSION = 'wake-lifecycle-probe-P155'
ENDPOINT = 'unix://' + str(SOCKET.resolve())
CODEX = pathlib.Path('/home/ecochran76/.local/bin/codex').resolve()
WRAPPER = ROOT / 'codex-probe'
STATE = ROOT / 'state.json'

def shell(*args, **kw):
    r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=65,**kw)
    if r.returncode:
        record('last-command-failure',dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        raise RuntimeError('command failed; inspect retained receipt before retry')
    return r.stdout.strip()

def readstate(): return json.loads(STATE.read_text())
def save(state): STATE.write_text(json.dumps(state,indent=2)+'\n')
def request(method, params):
    from codex_wake.native_protocol import native_request
    return native_request(ENDPOINT,str(WRAPPER),method,params,30)

def record(name, value):
    (ROOT/(name+'-'+str(time.monotonic_ns())+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    with (ROOT/'events.jsonl').open('a') as f:f.write(json.dumps(dict(event=name,value=value))+'\n')
    print(json.dumps(value))

def setup():
    assert not STATE.exists(), 'existing probe: reconcile, do not replace'
    ROOT.mkdir(parents=True,exist_ok=True); ROOT.chmod(0o700)
    HOME.mkdir(); WORK.mkdir()
    (HOME/'auth.json').symlink_to(pathlib.Path.home()/'.codex/auth.json')
    original=tomllib.loads((pathlib.Path.home()/'.codex/config.toml').read_text())
    lines=[f'{k} = {json.dumps(original[k])}' for k in ['model','model_reasoning_effort'] if k in original]
    lines += ['approval_policy = "never"','sandbox_mode = "workspace-write"',
              f'[projects.{json.dumps(str(WORK))}]','trust_level = "trusted"',
              '[mcp_servers.lifecycle_probe]','command = "python3"',
              'args = ['+json.dumps(str(ROOT/'mcp.py'))+']']
    (HOME/'config.toml').write_text('\n'.join(lines)+'\n')
    WRAPPER.write_text('#!/bin/sh\nexec env CODEX_HOME='+shlex.quote(str(HOME))+' '+shlex.quote(str(CODEX))+' "$@"\n');WRAPPER.chmod(0o700)
    (ROOT/'mcp.py').write_text('''import json,sys,pathlib,os
root=pathlib.Path(__file__).parent
version=(root/'version').read_text().strip()
with (root/'mcp-events.jsonl').open('a') as f: f.write(json.dumps(dict(event='start',version=version,pid=os.getpid()))+'\\n')
for line in sys.stdin:
 p=json.loads(line); method=p.get('method'); identifier=p.get('id')
 if identifier is None: continue
 if method=='initialize': result=dict(protocolVersion=p['params']['protocolVersion'],capabilities=dict(tools={}),serverInfo=dict(name='lifecycle-probe',version=version))
 elif method=='tools/list': result=dict(tools=[dict(name='probe_'+version,description='Return the isolated lifecycle marker '+version,inputSchema=dict(type='object',properties={},additionalProperties=False))])
 elif method=='tools/call':
  with (root/'mcp-events.jsonl').open('a') as f: f.write(json.dumps(dict(event='call',version=version,name=p['params']['name'],pid=os.getpid()))+'\\n')
  result=dict(content=[dict(type='text',text='MCP_MARKER_'+version)],isError=False)
 elif method=='resources/list': result=dict(resources=[])
 elif method=='prompts/list': result=dict(prompts=[])
 else: result={}
 print(json.dumps(dict(jsonrpc='2.0',id=identifier,result=result)),flush=True)
''')
    stage('v1')
    (WORK/'AGENTS.md').write_text('Disposable lifecycle probe. Read-only outside this workspace. No Git, external messages, services, enrollment, goals or budgets changes. Only the explicit probe/handoff task is authorized.\n')
    log=(ROOT/'server.log').open('wb')
    env=dict(os.environ,CODEX_HOME=str(HOME));env.pop('CODEX_THREAD_ID',None);env.pop('TMUX_PANE',None)
    server=subprocess.Popen([str(CODEX),'app-server','--listen',ENDPOINT],env=env,stdout=log,stderr=log,start_new_session=True,cwd=WORK)
    save(dict(server_pid=server.pid,session=SESSION,threads=[],tabs=[],created_monotonic=time.monotonic()))
    deadline=time.monotonic()+30
    while not SOCKET.exists() and time.monotonic()<deadline:
        if server.poll() is not None: raise RuntimeError('server exited; inspect private log')
        time.sleep(.2)
    assert SOCKET.exists(),'server unavailable'
    shell('tmux','new-session','-d','-s',SESSION,'-n','controller')
    record('setup',dict(server_pid=server.pid,session=SESSION,codex=shell(CODEX,'--version'),isolated=True))

def stage(version):
    (ROOT/'version').write_text(version)
    skill=WORK/'.agents/skills/lifecycle-probe';skill.mkdir(parents=True,exist_ok=True)
    (skill/'SKILL.md').write_text('---\nname: lifecycle-probe\ndescription: Disposable refresh probe marker '+version+'\n---\nReport SKILL_MARKER_'+version+' and call the lifecycle_probe MCP marker tool. No other task is authorized by this skill.\n')

def open_tab(thread=None):
    result=json.loads(shell('codex-wake','sessions','open',*(['--resume',thread] if thread else ['--new','--cwd',WORK]),
         '--name','lifecycle-probe','--tmux-session',SESSION,'--app-server',ENDPOINT,'--codex-path',WRAPPER,'--timeout','25','--json'))
    state=readstate()
    if result['thread_id'] not in state['threads']:state['threads'].append(result['thread_id'])
    if result.get('attachments'):
        state['tabs'] += [x['pane_id'] for x in result['attachments'] if x['pane_id'] not in state['tabs']]
    elif result.get('pane_id'):state['tabs'].append(result['pane_id'])
    save(state);record('open-'+str(len(state['threads']))+'-'+str(len(state['tabs'])),result)

def status(thread):
    r=request('thread/read',dict(threadId=thread,includeTurns=True))
    record('thread-'+thread,r)

def send(thread,prompt):
    # One exact request. An ambiguous response is never retried by this probe.
    result=shell(WRAPPER,'queue','--thread',thread,'--message',prompt,'--remote',ENDPOINT)
    print(result)

def quit_tab(pane):
    state=readstate();assert pane in state['tabs']
    shell('tmux','send-keys','-t',pane,'-l','/quit');shell('tmux','send-keys','-t',pane,'Enter')
    record('quit-'+pane.replace('%',''),dict(pane_id=pane,command='quit_requested'))

def cleanup():
    state=readstate()
    shell('tmux','kill-session','-t',SESSION)
    os.kill(state['server_pid'],15)
    record('cleanup',dict(session=SESSION,server_pid=state['server_pid'],termination_requested=True))

p=argparse.ArgumentParser();p.add_argument('action');p.add_argument('values',nargs='*');a=p.parse_args()
if a.action=='setup':setup()
elif a.action=='stage':stage(a.values[0]);print('staged '+a.values[0])
elif a.action=='open':open_tab(a.values[0] if a.values else None)
elif a.action=='status':status(a.values[0])
elif a.action=='send':send(*a.values)
elif a.action=='quit':quit_tab(a.values[0])
elif a.action=='cleanup':cleanup()
