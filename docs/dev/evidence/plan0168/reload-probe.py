import json,os,signal,subprocess,sys,time
from pathlib import Path
from codex_wake.native_protocol import native_request
root=Path('/tmp/cw168-reload-fixture');home=root/'home';home.mkdir(mode=0o700);workspace=root/'work';workspace.mkdir()
codex=Path('/home/ecochran76/.local/bin/codex').resolve();toy=root/'toy.py';pids=root/'toy-pids.jsonl'
toy.write_text('''import json,sys,os
version=sys.argv[1]
with open(sys.argv[2],'a') as f:f.write(json.dumps(dict(pid=os.getpid(),version=version))+'\\n')
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r:continue
 m=r['method']
 if m=='initialize':v=dict(protocolVersion=r['params']['protocolVersion'],capabilities={'tools':{}},serverInfo=dict(name='fixture-toy',version=version))
 elif m=='tools/list':v=dict(tools=[dict(name=n,description=n+' '+version,inputSchema=dict(type='object',properties={},additionalProperties=False),annotations={'readOnlyHint':True}) for n in (['version','extra_v2'] if version=='v2' else ['version'])])
 elif m=='tools/call':v=dict(content=[dict(type='text',text=version+':'+str(os.getpid()))],isError=False)
 else:v={}
 print(json.dumps(dict(jsonrpc='2.0',id=r['id'],result=v)),flush=True)
''')
def config(version):
 (home/'config.toml').write_text('model = "gpt-5.4"\napproval_policy = "never"\n[mcp_servers.toy]\ncommand = '+json.dumps(sys.executable)+'\nargs = '+json.dumps([str(toy),version,str(pids)])+'\n')
config('v1');env=dict(os.environ,CODEX_HOME=str(home),XDG_STATE_HOME=str(root/'state'))
for key in ('CODEX_THREAD_ID','TMUX','TMUX_PANE','CODEX_WAKE_A2A_CAPABILITY'):env.pop(key,None)
server=None;receipt=dict(state='preparing',model_turn_limit=0,codex=str(codex));log=(root/'server.log').open('w')
def save(): (root/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
def req(method,params):return native_request(endpoint,str(codex),method,params,8)
def snap(thread):
 status=req('mcpServerStatus/list',dict(threadId=thread,serverName='toy',detail='toolsAndAuthOnly'))
 call=req('mcpServer/tool/call',dict(threadId=thread,server='toy',tool='version',arguments={}))
 return dict(status=status,call=call,goal=req('thread/goal/get',dict(threadId=thread))['goal'],
  native=req('thread/read',dict(threadId=thread,includeTurns=True))['thread'])
try:
 server=subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(root/'native.sock')],env=env,stdout=log,stderr=log,start_new_session=True)
 deadline=time.monotonic()+15
 while not (root/'native.sock').exists() and server.poll() is None and time.monotonic()<deadline:time.sleep(.05)
 endpoint='unix://'+str((root/'native.sock').resolve(strict=True));receipt['endpoint']=endpoint;receipt['server_pid']=server.pid
 threads=[req('thread/start',dict(cwd=str(workspace),ephemeral=False))['thread']['id'] for _ in range(2)];receipt['threads']=threads;save()
 for thread in threads:req('thread/goal/set',dict(threadId=thread,objective='Owned zero-turn MCP reload fixture',status='paused',tokenBudget=1000,origin='automatic'))
 receipt['v1']={thread:snap(thread) for thread in threads};save()
 config('v2')
 receipt['resume']={}
 for thread in threads:
  result=req('thread/resume',dict(threadId=thread,cwd=str(workspace)))
  receipt['resume'][thread]=dict(thread_id=result['thread']['id'],snapshot=snap(thread))
 save()
 receipt['reload_response']=req('config/mcpServer/reload',None);save()
 receipt['after_reload']={thread:snap(thread) for thread in threads};save()
 receipt['model_turns']=sum(len(s['native']['turns']) for s in receipt['after_reload'].values())
 receipt['same_threads']=all(receipt['resume'][t]['thread_id']==t and receipt['after_reload'][t]['native']['id']==t for t in threads)
 receipt['goals_unchanged']=all(receipt['v1'][t]['goal']==receipt['after_reload'][t]['goal'] for t in threads)
 receipt['toy_processes']=[json.loads(line) for line in pids.read_text().splitlines()]
 receipt['state']='passed' if receipt['model_turns']==0 and receipt['same_threads'] and receipt['goals_unchanged'] else 'failed'
except Exception as exc:receipt.update(state='failed',error=type(exc).__name__+': '+str(exc))
finally:
 if server and server.poll() is None:
  os.killpg(server.pid,signal.SIGTERM)
  try:server.wait(timeout=15)
  except subprocess.TimeoutExpired:os.killpg(server.pid,signal.SIGKILL);server.wait(timeout=5)
 log.close();remaining=[];denied=[]
 for path in Path('/proc').iterdir():
  if not path.name.isdigit():continue
  try:
   if path.stat().st_uid==os.getuid() and ('CODEX_HOME='+str(home)).encode() in (path/'environ').read_bytes().split(b'\0'):remaining.append(int(path.name))
  except PermissionError:denied.append(int(path.name))
  except (FileNotFoundError,ProcessLookupError):pass
 receipt['cleanup']=dict(server_exit=server.poll() if server else None,private_home_processes=remaining,denied_pids=denied)
 if remaining:receipt['state']='failed'
 save()
print(json.dumps({key:receipt.get(key) for key in ('state','error','model_turns','same_threads','goals_unchanged','cleanup')}))
