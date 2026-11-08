import os,sys,json,pathlib,subprocess,shlex,time,threading,http.server,shutil,uuid,hashlib,traceback,stat
from datetime import datetime,timezone
from codex_wake.native_protocol import native_request
from codex_wake.tab_traits import session_rows
from codex_wake.local_health import observe_row
from codex_wake.tab_recovery import TabRecovery
P=pathlib.Path
assert os.getuid()==1017
import tempfile
root=P(tempfile.mkdtemp(prefix='wake-recovery368-native-'))
print('STATE_ROOT',root,flush=True)
workspace=root/'workspace';workspace.mkdir(mode=0o700)
for repository in ('z-repository','a-repository'):
 selected=workspace/repository;selected.mkdir(mode=0o700);subprocess.run(['git','init','-q',str(selected)],check=True)
home=root/'accounts/codex-test';home.mkdir(mode=0o700,parents=True)
os.environ['CODEX_HOME']=str(home)
wake=root/'wake';wake.mkdir(mode=0o700)
binary=P('/tmp/recovery368-native-package/bin/codex')
model=json.loads(P('/tmp/recovery368-models.json').read_text())['models'][0]
(home/'models.json').write_text(json.dumps({'models':[model]}))
calls=[]
class Trap(http.server.BaseHTTPRequestHandler):
 def do_GET(self):calls.append(('GET',self.path));self.send_response(503);self.end_headers()
 def do_POST(self):calls.append(('POST',self.path));self.send_response(503);self.end_headers()
 def log_message(self,*args):pass
trap=http.server.ThreadingHTTPServer(('127.0.0.1',0),Trap);threading.Thread(target=trap.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(trap.server_port)
(home/'config.toml').write_text('model='+json.dumps(model['slug'])+'\nmodel_provider="recovery_fixture"\nmodel_catalog_json='+json.dumps(str(home/'models.json'))+'\ncheck_for_update_on_startup=false\n[analytics]\nenabled=false\n[model_providers.recovery_fixture]\nname="No provider turns"\nbase_url='+json.dumps(url+'/never-query')+'\nwire_api="responses"\nrequires_openai_auth=false\n[projects.'+json.dumps(str(workspace))+']\ntrust_level="trusted"\n')
with (home/'config.toml').open('a') as config:
 for repository in ('z-repository','a-repository'):
  config.write('[projects.'+json.dumps(str(workspace/repository))+']\ntrust_level="trusted"\n')
endpoint='unix://'+str(root/'native.sock');sock=str(root/'tmux.sock')
env={k:os.environ[k] for k in ('PATH','LANG','PYTHONPATH') if k in os.environ}
env.update(HOME=str(root/'house'),CODEX_HOME=str(home),TERM='xterm-256color',HTTP_PROXY=url,HTTPS_PROXY=url,ALL_PROXY=url,NO_PROXY='localhost,127.0.0.1',CODEX_BUILD_UPDATE_CHECK='0')
daemon=None
def tm(*args):return subprocess.check_output(['tmux','-S',sock,*args],text=True,env=env).strip()
def rpc(method,params):return native_request(endpoint,str(binary),method,params,5)
report=dict(uid=os.getuid(),native_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),external_provider_calls=0,model_turns=0,status='running')
import codex_wake.local_health as health_module,codex_wake.tab_recovery as recovery_module,codex_wake.tab_traits as traits_module
report['installed_modules']={m.__name__:dict(path=m.__file__,sha256=hashlib.sha256(P(m.__file__).read_bytes()).hexdigest()) for m in (health_module,recovery_module,traits_module)}
wheel=P(os.environ.get('WAKE_ACCEPTANCE_WHEEL','/tmp/codex-wake-503-wheels/candidate-4d22a56/codex_wake-0.22.0.dev2-py3-none-any.whl'))
report['wheel']=dict(path=str(wheel),sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),source_commit=os.environ.get('WAKE_ACCEPTANCE_SOURCE','4d22a56'))
assert report['wheel']['sha256']==os.environ.get('WAKE_ACCEPTANCE_SHA256','6e772f6571caba1d59589336d4546fd5f762aee0a7267d2c931311e5ef88c29d')
assert all(str(P(sys.executable).parent.parent)+'/' in value['path'] for value in report['installed_modules'].values()),'source forcing detected'
try:
 log=(root/'daemon.log').open('wb');daemon=subprocess.Popen([str(binary),'app-server','--listen',endpoint],env=env,cwd=workspace,stdout=log,stderr=subprocess.STDOUT)
 until=time.monotonic()+15
 while not (P(endpoint[7:]).exists() and stat.S_ISSOCK(P(endpoint[7:]).stat().st_mode)):
  assert daemon.poll() is None,'daemon exited';assert time.monotonic()<until,'daemon startup timeout';time.sleep(.05)
 endpoint='unix://'+str(P(endpoint[7:]).resolve(strict=True))
 print('ENDPOINT_QUALIFIED',flush=True)
 control=home/'app-server-control';control.mkdir(mode=0o700,exist_ok=True)
 if not (control/'app-server-control.sock').exists():(control/'app-server-control.sock').symlink_to(P(endpoint[7:]))
 shared=root/'accounts/shared';shared.mkdir(mode=0o700)
 (wake/'controller-accounts.toml').write_text('[profiles]\nstate_root='+json.dumps(str(home.parent))+'\nsource_root='+json.dumps(str(shared))+'\nknown_profiles=["test"]\nshared_links=[]\n[accounts]\nenabled=["codex-test"]\n')
 (wake/'controller-accounts.toml').chmod(0o600)
 (wake/'controller-tabs.json').write_text(json.dumps(dict(schema_version=1,workspaces=dict(fixture=dict(kind='tmux',socket_path=sock,session_id='$0')))));(wake/'controller-tabs.json').chmod(0o600)
 tm('new-session','-d','-s','fixture','-n','notes','-x','140','-y','45','exec sleep 120')
 tm('set-option','-g','automatic-rename','off')
 ids=[]
 for i in range(2):
  selected_cwd=workspace/('z-repository' if i==0 else 'a-repository');selected_cwd.mkdir(exist_ok=True)
  subprocess.run(['git','init','-q',str(selected_cwd)],check=True)
  identifier=str(uuid.uuid4());ids.append(identifier);now=datetime.now(timezone.utc);stamp=now.isoformat().replace('+00:00','Z')
  rollout=home/'sessions'/now.strftime('%Y/%m/%d')/('rollout-'+now.strftime('%Y-%m-%dT%H-%M-%S')+'-'+identifier+'.jsonl');rollout.parent.mkdir(parents=True,exist_ok=True)
  meta=dict(id=identifier,session_id=identifier,timestamp=stamp,cwd=str(selected_cwd),originator='codex_cli_rs',cli_version='0.167.0',source='cli',model_provider='recovery_fixture',base_instructions={'text':'Synthetic provider-free recovery qualification.'})
  rollout.write_text(json.dumps(dict(timestamp=stamp,type='session_meta',payload=meta))+'\n')
  rpc('thread/resume',dict(threadId=identifier));rpc('thread/name/set',dict(threadId=identifier,name='native-'+str(i+1)))
  cmd=shlex.join(['env','CODEX_HOME='+str(home),str(binary),'--remote',endpoint,'resume',identifier,'--no-alt-screen'])
  tm('new-window','-d','-n','native-'+str(i+1),'-c',str(selected_cwd),cmd)
 until=time.monotonic()+20
 while True:
  view=session_rows(wake,socket_path=sock,endpoints=[endpoint],deadline=time.monotonic()+3)
  good=[row for row in view['sessions'] if row['thread_id'] in ids and row.get('attachments')]
  if len(good)==2 and all(observe_row(wake,row,timeout=2)['observation'].get('responsive') for row in good):break
  assert time.monotonic()<until,'native TUI binding readiness timeout';time.sleep(.1)
 print('NATIVE_READY',flush=True)
 installed_cli=str(P(sys.executable).parent/'codex-wake')
 def cli(*args):
  result=subprocess.run([installed_cli,'--wake-root',str(wake),'tabs',*args,'--json'],env=env,text=True,capture_output=True,timeout=30)
  assert result.returncode==0,(result.stdout,result.stderr)
  return json.loads(result.stdout)
 layout_before=tm('list-windows','-F','#{window_id}')
 layout_plan=cli('preview','--workspace','fixture','--group-by','repository','--request-id','layout-preview')['result']['operation']['result']
 report['layout_plan']=layout_plan
 layout_apply=cli('apply','--workspace','fixture','--plan-id',layout_plan['plan']['plan_id'],'--request-id','layout-apply')['result']['operation']['result']
 report['layout_apply']=layout_apply
 assert layout_apply['status']=='applied',layout_apply
 assert tm('list-windows','-F','#{window_id}')!=layout_before,'layout was a no-op rather than actual ordering'
 layout_undo=cli('undo','--workspace','fixture','--receipt-id',layout_apply['receipt']['receipt_id'],'--request-id','layout-undo')['result']['operation']['result']
 assert layout_undo['status']=='undone',layout_undo
 assert tm('list-windows','-F','#{window_id}')==layout_before,'conditional undo failed'
 report['public_actual_layout_and_undo']=True
 captured=cli('recovery-capture','--workspace','fixture','--capture-id','before-outage','--request-id','capture')['result']['operation']['result']
 report['public_cli_capture']=True
 report['captured_kinds']=[row['kind'] for row in captured['snapshot']['rows']]
 report['captured_conversations']=[row.get('identity',{}).get('conversation_id') for row in captured['snapshot']['rows'] if row['kind']=='codex']
 assert sorted(report['captured_conversations'])==sorted(ids),captured
 installed_cli=str(P(sys.executable).parent/'codex-wake')
 status_cli=json.loads(subprocess.check_output([installed_cli,'--wake-root',str(wake),'tabs','recovery-status','--capture-id','before-outage','--json'],env=env,text=True))
 report['installed_cli_status']=dict(status=status_cli.get('status'),passed=True)
 print('CAPTURED',flush=True)
 tm('kill-server');time.sleep(.2)
 tm('new-session','-d','-s','fixture','-n','unrelated','-x','140','-y','45','exec sleep 120');tm('set-option','-g','automatic-rename','off')
 restored_shells=[]
 from codex_wake.process import process_identity
 for index,saved in enumerate(row for row in captured['snapshot']['rows'] if row['kind']=='codex'):
  created=tm('new-window','-d','-P','-F','#{window_id}\t#{pane_id}\t#{pane_pid}',
             '-t','$0:'+str(saved['index']),'-n',saved['name'],'-c',saved['identity']['root'],'bash --noprofile --norc -i')
  wid,pane,pid=created.split('\t');pid=int(pid)
  if index==0:tm('set-option','-w','-t',wid,'@codex-wake-recovery-id',saved['logical_id'])
  draft='SYNTHETIC_UNSENT_RESTORED_'+str(index)
  tm('send-keys','-l','-t',pane,draft)
  restored_shells.append(dict(window=wid,pane=pane,pid=pid,process=process_identity(pid),draft=draft))
 report['restored_shell_slot_count']=len(restored_shells)
 before=tm('list-windows','-F','#{window_id}\t#{window_name}')
 restart=TabRecovery(wake)
 preview=restart.execute('tabs.recovery.preview',dict(workspace='fixture',capture_id='before-outage',restore_layout=True))
 preview_cli=json.loads(subprocess.check_output([installed_cli,'--wake-root',str(wake),'tabs','recovery-preview','--capture-id','before-outage','--workspace','fixture','--restore-layout','--json'],env=env,text=True))
 preview_value=preview_cli.get('result',preview_cli)
 assert all(preview_value.get('target',{}).get(key)==value for key,value in preview['target'].items()),preview_cli
 report['installed_cli_preview']=dict(status=preview_cli.get('status'),passed=True)
 report['preview_statuses']=[row['status'] for row in preview['rows']]
 assert preview['status']=='ready',preview
 applied=cli('recovery-apply','--workspace','fixture','--capture-id','before-outage','--restore-layout','--intent','once','--request-id','apply')['result']['operation']['result']
 report['public_cli_apply']=True
 report['apply']=applied
 final_request='apply'
 if applied['status']=='partial':
  report['initial_partial_apply']=applied
  until=time.monotonic()+15
  while True:
   waiting=cli('recovery-preview','--workspace','fixture','--capture-id','before-outage','--restore-layout')
   if all(row['status'] in ('already_attached','preserved') for row in waiting['rows']):break
   assert time.monotonic()<until,waiting
   time.sleep(.1)
  before_reconcile=tm('list-windows','-F','#{window_id}')
  final_request='apply-reconcile'
  applied=cli('recovery-apply','--workspace','fixture','--capture-id','before-outage','--restore-layout','--intent','once','--request-id',final_request)['result']['operation']['result']
  assert tm('list-windows','-F','#{window_id}')==before_reconcile,'reconciliation relaunched a client'
  report['reconciled_without_new_windows']=True
 report['apply']=applied
 assert applied['status']=='completed',applied
 for shell in restored_shells:
  assert process_identity(shell['pid'])==shell['process'],'preserved shell process changed'
  assert shell['draft'] in tm('capture-pane','-p','-t',shell['pane']),'unsent shell draft lost'
 report['restored_shell_processes_and_drafts_preserved']=True
 after=tm('list-windows','-F','#{window_id}\t#{window_name}')
 assert 'unrelated' in after,'unrelated shell removed'
 repeated=cli('recovery-apply','--workspace','fixture','--capture-id','before-outage','--restore-layout','--intent','once','--request-id',final_request)['result']['operation']['result']
 assert repeated==applied and after==tm('list-windows','-F','#{window_id}\t#{window_name}'),'duplicate attachment'
 final=session_rows(wake,socket_path=sock,endpoints=[endpoint],deadline=time.monotonic()+3)
 report['final_conversations']=[row['thread_id'] for row in final['sessions'] if row.get('attachments')]
 assert sorted(report['final_conversations'])==sorted(ids)
 report['replayed_without_new_windows']=True;report['noncoding_preserved']=True;report['status']='passed'
except BaseException as error:
 report['status']='failed';report['error']=str(error)[:12000];report['traceback']=traceback.format_exc();print('FAILED',str(error)[:300],flush=True)
finally:
 try:tm('kill-server')
 except Exception:pass
 if daemon is not None:
  daemon.terminate()
  try:daemon.wait(timeout=5)
  except subprocess.TimeoutExpired:daemon.kill();daemon.wait(timeout=2)
 if 'log' in globals():log.close()
 trap.shutdown();trap.server_close()
 report['trap_requests']=calls
 report['final_owned_native_processes']=[]
 for proc in P('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:
   if ('CODEX_HOME='+str(home)).encode() in (proc/'environ').read_bytes().split(b'\0'):
    report['final_owned_native_processes'].append(int(proc.name))
  except OSError:pass
 if report['final_owned_native_processes']:report['status']='cleanup_incomplete'

 (root/'receipt.json').write_text(json.dumps(report,indent=2));print('RESULT',report['status'],str(root/'receipt.json'),flush=True)

if report['status']!='passed':raise SystemExit(1)
