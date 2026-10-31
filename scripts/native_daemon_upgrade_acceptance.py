"""Opt-in UID1017 cooperative-upgrade qualification; never uses working-account state.

Requires the staged dummy-account launcher and complete immutable native packages.
Run as codex-daemon-test with one unique case name. Provider traffic stays on localhost.
CODEX_QUALIFICATION_TARGET selects the candidate; optional BASELINE and MODE select
legacy/refuse/hang controls. Full receipts and terminal captures remain in dummy state.
"""
import os,json,time,pathlib,subprocess,threading,shlex,hashlib,signal,traceback,sys,socket,struct,tempfile,re
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
assert os.getuid() == 1017, "Run this isolated acceptance harness as codex-daemon-test UID1017"
from codex_wake.native_protocol import native_request
P=pathlib.Path;b=P('/home/codex-daemon-test/daemon-qualification-0165');root=b/('upgrade-journey-'+sys.argv[1]);root.mkdir(mode=0o700)
ws=root/'workspace';ws.mkdir(mode=0o700);home=root/'accounts/codex-test';home.mkdir(mode=0o700,parents=True)
prefix=b/'wake';launcher=prefix/'bin/codex-modded';baseline=P(os.environ.get('CODEX_QUALIFICATION_BASELINE',str(b/'candidate-barrier/bin/codex')));target=P(os.environ.get('CODEX_QUALIFICATION_TARGET',str(baseline)));control=home/'app-server-control/app-server-control.sock'
report=dict(state='preparing',uid=os.getuid(),provider='Owned scripted localhost Responses fixture',external_provider_calls=0,mode=os.environ.get('CODEX_QUALIFICATION_MODE','success'));finish=threading.Event();release=threading.Event();active={};calls=[];errors=[];lock=threading.Lock();watcher=None;updater=None;native_pid=None

def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save():(root/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
def text_values(v):
 if isinstance(v,dict):
  for k,x in v.items():
   if k=='text' and isinstance(x,str):yield x
   else:yield from text_values(x)
 elif isinstance(v,list):
  for x in v:yield from text_values(x)
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  tid=self.headers.get('thread-id');body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  with lock:number=len(calls)+1;calls.append(dict(thread=tid,number=number))
  (root/('request-'+str(number)+'.json')).write_text(json.dumps(body))
  self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
  def emit(v):self.wfile.write(('event: '+v['type']+'\ndata: '+json.dumps(v)+'\n\n').encode());self.wfile.flush()
  try:
   assert number<=32,'Provider request cap exceeded'
   emit(dict(type='response.created',response=dict(id='upgrade-owned-'+str(number))))
   item=None;prompt=next((x.split('UPGRADE_REQUEST_JSON=',1)[1] for x in text_values(body.get('input',[])) if 'UPGRADE_REQUEST_JSON=' in x),None)
   if not body.get('tools'):
    assert 'Generate a concise' in json.dumps(body),'Unexpected auxiliary request';text='Prepare upgrade checkpoint'
   elif prompt:
    request=json.JSONDecoder().raw_decode(prompt)[0];assert request['thread_id']==tid,request
    report.setdefault('injected_requests',{})[tid]=request
    if not active[tid].get('paused'):
     item=dict(type='function_call',name='update_goal',call_id='checkpoint-pause-'+str(number),arguments=json.dumps(dict(status='paused')));active[tid]['paused']=True;text=None
    else:
     if report['mode']=='hang' and tid==report['active_threads'][-1]:
      report['hanging_checkpoint_thread']=tid
      while not finish.wait(.1):self.wfile.write(b': bounded unresponsive checkpoint control\n\n');self.wfile.flush()
      return
     handoff=dict(upgrade_id=request['upgrade_id'],thread_id=tid,ready=True,objective='Preserve isolated active work',authority='Operator-approved isolated upgrade qualification',completed=['Bounded work packet recorded'],remaining=['Resume original unfinished objective'],pending_operations=[],resource_state=dict(native_token_limit=2000,scope='unchanged'),resume_instructions='Read this checkpoint and resume original conversation only with the original remaining allowance')
     if report['mode']=='refuse' and tid==report['active_threads'][-1]:handoff.update(ready=False,reason='Isolated negative control: cannot establish a safe checkpoint')
     text=json.dumps(handoff)
     report.setdefault('agent_handoffs',{})[tid]=handoff if text.startswith('{') else dict(refused=True)
   else:
    assert tid in active,tid;active[tid]['stream_started']=True
    while not release.wait(.1) and not finish.is_set():self.wfile.write(b': bounded active work\n\n');self.wfile.flush()
    text='ACTIVE_WORK_PACKET_YIELDED'
   if item:emit(dict(type='response.output_item.done',item=item))
   if text:emit(dict(type='response.output_item.done',item=dict(type='message',role='assistant',id='upgrade-message-'+str(number),content=[dict(type='output_text',text=text)])))
   emit(dict(type='response.completed',response=dict(id='upgrade-owned-'+str(number),usage=dict(input_tokens=20,input_tokens_details=dict(cached_tokens=0),output_tokens=0,total_tokens=20))))
  except (BrokenPipeError,ConnectionResetError):
   if not finish.is_set():report.setdefault('stream_disconnects',[]).append(tid)
  except BaseException as e:errors.append(repr(e));report['provider_errors']=errors

http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.daemon_threads=True;threading.Thread(target=http.serve_forever,daemon=True).start()
config='model="mock-model"\nmodel_provider="local_fixture"\napproval_policy="never"\nsandbox_mode="read-only"\n[model_providers.local_fixture]\nname="Owned upgrade fixture"\nbase_url="http://127.0.0.1:'+str(http.server_address[1])+'/v1"\nwire_api="responses"\nrequires_openai_auth=false\nsupports_websockets=false\nrequest_max_retries=0\nstream_max_retries=0\n[projects.'+json.dumps(str(ws))+']\ntrust_level="trusted"\n'
(home/'config.toml').write_text(config)
settings=home/'app-server-daemon';settings.mkdir(mode=0o700);(settings/'settings.json').write_text(json.dumps(dict(shutdownGraceSeconds=2)))
shared=home.parent/'shared';shared.mkdir(mode=0o700);(shared/'builds.json').write_text(json.dumps(dict(schema_version=1,builds=dict(modded=dict(executable=str(baseline),sha256=digest(baseline),upstream_version='0.165.0',revision='barrier-baseline',source='local-qualified',read_schemas=[5],backend='managed')))))
profiles=root/'profiles.toml';profiles.write_text('[profiles]\nstate_root='+json.dumps(str(home.parent))+'\nselection_mode="launcher"\ndefault_profile="test"\nknown_profiles=["test"]\nshared_links=[]\ncheck_upstream_releases=false\n')
env=dict(os.environ,CODEX_HOME=str(home),CODEX_PROFILES_CONFIG=str(profiles),CODEX_BUILD_UPDATE_CHECK='0',TERM='xterm-256color');tm=['tmux','-S',str(root/'tmux.sock')]
def t(*args,check=True):return subprocess.run([*tm,*args],env=env,capture_output=True,text=True,timeout=10,check=check).stdout
def wait(fn,label,seconds=15):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if errors:raise AssertionError(errors)
  v=fn()
  if v:return v
  time.sleep(.05)
 raise AssertionError(label+' unavailable')
def raw_rpc(method,params):
 from websockets.sync.client import unix_connect
 with unix_connect(endpoint[7:],open_timeout=5,close_timeout=1) as client:
  client.send(json.dumps(dict(id=1,method='initialize',params=dict(clientInfo=dict(name='upgrade_qualification',version='0'),capabilities=dict(experimentalApi=True)))))
  while json.loads(client.recv(timeout=5)).get('id')!=1:pass
  client.send(json.dumps(dict(method='initialized')))
  client.send(json.dumps(dict(id=2,method=method,params=params)))
  while True:
   v=json.loads(client.recv(timeout=5))
   if v.get('id')==2:return v
def pane(name,tid):t('new-session','-d','-s',name,'-x','180','-y','55',shlex.join([str(launcher),'--no-alt-screen','resume',tid]));wait(lambda:'mock-model' in t('capture-pane','-p','-t',name,check=False),'Actual '+name+' TUI',20)
try:
 t('new-session','-d','-s','bootstrap','-x','180','-y','55',shlex.join([str(launcher),'--no-alt-screen','-C',str(ws)]))
 wait(lambda:'mock-model' in t('capture-pane','-p','-t','bootstrap',check=False),'Managed bootstrap',30)
 endpoint='unix://'+str(control.resolve(strict=True))
 def rpc(method,params):return native_request(endpoint,str(baseline),method,params,5)
 with socket.socket(socket.AF_UNIX) as s:s.connect(endpoint[7:]);native_pid,uid,_=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
 assert uid==os.getuid() and digest(P('/proc')/str(native_pid)/'exe')==digest(baseline)
 t('kill-session','-t','bootstrap');report['old_pid']=native_pid;report['baseline_sha256']=digest(baseline);report['target_sha256']=digest(target);report['active_threads']=[]
 for i in range(2):
  tid=rpc('thread/start',dict(cwd=str(ws),historyMode='paginated'))['thread']['id'];active[tid]={};report['active_threads'].append(tid)
  rpc('thread/goal/set',dict(threadId=tid,objective='Preserve isolated active work',status='paused',tokenBudget=2000,origin='user'))
  turn=rpc('turn/start',dict(threadId=tid,input=[dict(type='text',text='Perform a bounded isolated work packet under the existing goal. During an operator daemon upgrade, checkpoint and pause without changing limits.')]))['turn']['id'];active[tid]['turn_id']=turn
  wait(lambda:active[tid].get('stream_started'),'Active native work stream')
  rpc('thread/goal/set',dict(threadId=tid,status='active',origin='user'));pane('active'+str(i),tid)
 pane('active0mirror',report['active_threads'][0])
 idle=rpc('thread/start',dict(cwd=str(ws),historyMode='paginated'))['thread']['id'];report['idle_thread']=idle
 rpc('thread/notice/append',dict(threadId=idle,eventId='upgrade_fixture_idle',text='Idle isolated session. [External supervision event upgrade_fixture_idle]'));pane('idle',idle)
 report['goals_before']={tid:rpc('thread/goal/get',dict(threadId=tid))['goal'] for tid in active}
 report['old_selection']=os.readlink(home/'packages/app-server-daemon/current')
 log=(root/'update.log').open('w');updater=subprocess.Popen([str(target),'app-server','daemon','update','--from-cli','--yes'],env=env,cwd=ws,stdout=log,stderr=log,start_new_session=True)
 deadline=time.monotonic()+150;operation=None
 while updater.poll() is None and time.monotonic()<deadline:
  paths=list((home/'daemon-upgrades').glob('upgrade-*/state.json'))
  if paths:
   operation=max(paths,key=lambda p:p.stat().st_mtime)
   state=json.loads(operation.read_text())
   if state['phase']=='waiting' and not release.is_set():
    rejected=raw_rpc('thread/start',dict(cwd=str(ws),historyMode='paginated'))
    assert rejected.get('error',{}).get('data',{}).get('reason')=='daemonUpgradePreparing',rejected
    report['new_work_held_during_preparation']=True
    report['notices_visible']={}
    for name in ['active0','active0mirror','active1','idle']:
     screen=wait(lambda:(v if 'Daemon upgrade pending' in (v:=t('capture-pane','-p','-S','-2000','-t',name)) else None),'Visible upgrade prompt '+name,10);(root/(name+'-prompt.txt')).write_text(screen);report['notices_visible'][name]=True
    release.set()
  time.sleep(.05)
 assert updater.poll() is not None,'Updater exceeded qualification deadline'
 report['update_exit_code']=updater.returncode
 assert operation is not None,'Updater completed without a checkpoint preparation receipt'
 state=json.loads(operation.read_text());report['preparation']=state;report['operation_receipt']=str(operation)
 if report['mode'] in ('refuse','hang','legacy'):
  assert updater.returncode!=0 and state['phase']=='blocked',state
  if report['mode']=='legacy':
   assert 'save work and stop an older daemon once' in state['reason'],state
   assert not report.get('injected_requests'),'Unsupported daemon received checkpoint steering'
  assert os.readlink(home/'packages/app-server-daemon/current')==report['old_selection'],'Refusal changed installed selection'
  assert digest(P('/proc')/str(native_pid)/'exe')==digest(baseline),'Refusal stopped/replaced old daemon'
  rpc('thread/loaded/list',dict(limit=100))
  def released():
   from codex_wake.records import WakeError
   try:return rpc('thread/start',dict(cwd=str(ws),historyMode='paginated'))
   except WakeError as error:
    if str(error)=='native lifecycle request rejected: thread/start':return None
    raise
  wait(released,'Cancelled preparation released new-work admission',5)
  report.update(state='passed',refusal_holds_old_daemon=True,cancellation_releases_admission=True)
 else:
  assert updater.returncode==0 and state['phase']=='ready',state
  assert report.get('notices_visible')==dict(active0=True,active0mirror=True,active1=True,idle=True),report.get('notices_visible')
  assert report.get('new_work_held_during_preparation') is True
  files={tid:json.loads(P(v['file']).read_text()) for tid,v in state['threads'].items()}
  assert set(report['active_threads']+[idle])<=set(files),files.keys()
  for tid in active:assert files[tid]['upgrade_id']==state['operation_id'] and files[tid]['thread_id']==tid and files[tid]['ready']
  assert files[idle]['kind']=='idle_snapshot';assert idle not in report.get('agent_handoffs',{}),'Idle session unnecessarily called model'
  report['handoff_files']=files
  newendpoint='unix://'+str(control.resolve(strict=True))
  with socket.socket(socket.AF_UNIX) as s:s.connect(newendpoint[7:]);newpid,newuid,_=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
  assert newpid!=native_pid and newuid==os.getuid() and digest(P('/proc')/str(newpid)/'exe')==digest(target)
  report['new_pid']=newpid
  after={tid:native_request(newendpoint,str(target),'thread/goal/get',dict(threadId=tid),5)['goal'] for tid in active}
  for tid,g in after.items():
   before=report['goals_before'][tid];assert g['status']=='paused' and all(g[k]==before[k] for k in ['threadId','objective','createdAt','tokenBudget']) and g['tokensUsed']>=before['tokensUsed'],g
  def select_launcher_build(executable):
   manifest=shared/'builds.json';v=json.loads(manifest.read_text());row=v['builds']['modded'];row.update(executable=str(executable),sha256=digest(executable),revision='qualified-upgrade-fixture')
   staged=manifest.with_suffix('.next');staged.write_text(json.dumps(v));os.replace(staged,manifest)
   report.setdefault('fixture_build_registrations',[]).append(dict(executable=str(executable),sha256=digest(executable)))
  select_launcher_build(target);pane('fresh',report['active_threads'][0])
  def status_checks(label):
   result={}
   for name,tid in [('active0',report['active_threads'][0]),('active0mirror',report['active_threads'][0]),('active1',report['active_threads'][1]),('idle',idle),('fresh',report['active_threads'][0])]+([('rollbackfresh',report['active_threads'][0])] if label=='rollback' else []):
    frame=t('capture-pane','-p','-S','-2000','-t',name)
    if 'Resume paused goal?' in frame and 'Leave paused' in frame:t('send-keys','-t',name,'Escape')
    t('send-keys','-t',name,'-l','/status');time.sleep(0.4);t('send-keys','-t',name,'Enter')
    shown=wait(lambda:(v if re.search(r'Session:\s*'+re.escape(tid),(v:=t('capture-pane','-p','-S','-2000','-t',name))) else None),'Actual TUI session identity after '+label+' '+name,15)
    (root/(label+'-'+name+'-status.txt')).write_text(shown);result[name]=tid
   return result
  report['ui_after_upgrade']=status_checks('upgrade')
  report['work_requests_after_upgrade']={tid:sum(c['thread']==tid for c in calls) for tid in active}
  assert all(n==3 for n in report['work_requests_after_upgrade'].values()),report['work_requests_after_upgrade']
  file_hashes={tid:digest(P(state['threads'][tid]['file'])) for tid in files}
  rollback=subprocess.run([str(baseline),'app-server','daemon','update','--from-cli','--yes'],env=env,cwd=ws,capture_output=True,text=True,timeout=40)
  (root/'rollback.log').write_text(rollback.stdout+rollback.stderr);assert rollback.returncode==0,rollback.stderr
  restored='unix://'+str(control.resolve(strict=True))
  with socket.socket(socket.AF_UNIX) as s:s.connect(restored[7:]);rollback_pid,rollback_uid,_=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
  assert rollback_pid!=newpid and rollback_uid==os.getuid() and digest(P('/proc')/str(rollback_pid)/'exe')==digest(baseline)
  assert {tid:digest(P(state['threads'][tid]['file'])) for tid in files}==file_hashes,'Rollback changed durable handoffs'
  for tid in active:
   g=native_request(restored,str(baseline),'thread/goal/get',dict(threadId=tid),5)['goal'];assert g['status']=='paused' and all(g[k]==after[tid][k] for k in ['threadId','objective','createdAt','tokenBudget','tokensUsed']),g
  select_launcher_build(baseline);pane('rollbackfresh',report['active_threads'][0])
  report['ui_after_rollback']=status_checks('rollback')
  report.update(state='passed',all_tabs_notified=True,durable_handoffs_before_replacement=True,goals_after=after,counters_and_limits_preserved=True,rollback_preserves_handoffs=True,rollback_pid=rollback_pid)
except BaseException as e:
 report.update(state='failed',error=repr(e),traceback=traceback.format_exc())
 for name in ['active0','active0mirror','active1','idle','fresh','rollbackfresh']:
  (root/('failure-'+name+'.txt')).write_text(t('capture-pane','-p','-S','-2000','-t',name,check=False))
finally:
 finish.set();release.set();t('kill-server',check=False)
 if updater and updater.poll() is None:
  os.killpg(updater.pid,signal.SIGTERM)
  try:updater.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(updater.pid,signal.SIGKILL);updater.wait()
 subprocess.run([str(target),'app-server','daemon','stop'],env=env,capture_output=True,timeout=20)
 for proc in P('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:
   if proc.stat().st_uid==os.getuid() and b'pid-update-loop' in (proc/'cmdline').read_bytes() and ('CODEX_HOME='+str(home)).encode() in (proc/'environ').read_bytes().split(bytes([0])):os.kill(int(proc.name),signal.SIGTERM)
  except OSError:pass
 http.shutdown();http.server_close();report['calls']=calls;save()
print(json.dumps({k:report.get(k) for k in ['state','error','update_exit_code','all_tabs_notified','refusal_holds_old_daemon']},indent=2))
raise SystemExit(0 if report['state']=='passed' else 1)
