#!/usr/bin/env python3
# Native fixture setup adapted with attribution from /root/traits505 #368.
# Actual UID1017, exact immutable Codex167 and native Windows psmux; no turns.
import os,sys,json,pathlib,subprocess,shlex,time,threading,http.server,shutil,uuid,hashlib,traceback,stat,socket
from codex_wake.process import process_identity
from datetime import datetime,timezone
from codex_wake.native_protocol import native_request
from codex_wake.tab_traits import session_rows
from codex_wake.local_health import observe_row
from codex_wake.tab_reattach import TabReattach
P=pathlib.Path
assert os.getuid()==1017
import tempfile
root=P(tempfile.mkdtemp(prefix='wake-reattach510-native-'))
print('STATE_ROOT',root,flush=True)
workspace=root/'workspace';workspace.mkdir(mode=0o700)
home=root/'accounts/codex-test';home.mkdir(mode=0o700,parents=True)
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
endpoint='unix://'+str(root/'native.sock');sock=str(root/'tmux.sock')
env={k:os.environ[k] for k in ('PATH','LANG','PYTHONPATH') if k in os.environ}
env.update(HOME=str(root/'house'),CODEX_HOME=str(home),TERM='xterm-256color',HTTP_PROXY=url,HTTPS_PROXY=url,ALL_PROXY=url,NO_PROXY='localhost,127.0.0.1',CODEX_BUILD_UPDATE_CHECK='0')
log=(root/'daemon.log').open('wb');daemon=subprocess.Popen([str(binary),'app-server','--listen',endpoint],env=env,cwd=workspace,stdout=log,stderr=subprocess.STDOUT)
def tm(*args):return subprocess.check_output(['tmux','-S',sock,*args],text=True,env=env).strip()
def rpc(method,params):return native_request(endpoint,str(binary),method,params,5)
report=dict(uid=os.getuid(),native_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),external_provider_calls=0,model_turns=0,status='running')
try:
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
 for i in range(1):
  identifier=str(uuid.uuid4());ids.append(identifier);now=datetime.now(timezone.utc);stamp=now.isoformat().replace('+00:00','Z')
  rollout=home/'sessions'/now.strftime('%Y/%m/%d')/('rollout-'+now.strftime('%Y-%m-%dT%H-%M-%S')+'-'+identifier+'.jsonl');rollout.parent.mkdir(parents=True,exist_ok=True)
  meta=dict(id=identifier,session_id=identifier,timestamp=stamp,cwd=str(workspace),originator='codex_cli_rs',cli_version='0.167.0',source='cli',model_provider='recovery_fixture',base_instructions={'text':'Synthetic provider-free recovery qualification.'})
  rollout.write_text(json.dumps(dict(timestamp=stamp,type='session_meta',payload=meta))+'\n')
  rpc('thread/resume',dict(threadId=identifier));rpc('thread/name/set',dict(threadId=identifier,name='native-'+str(i+1)))
  cmd=shlex.join(['env','CODEX_HOME='+str(home),str(binary),'--remote',endpoint,'resume',identifier,'--no-alt-screen'])
  tm('new-window','-d','-n','native-'+str(i+1),'-c',str(workspace),cmd)
 until=time.monotonic()+20
 while True:
  view=session_rows(wake,socket_path=sock,endpoints=[endpoint],deadline=time.monotonic()+3)
  good=[row for row in view['sessions'] if row['thread_id'] in ids and row.get('attachments')]
  if len(good)==1 and all(observe_row(wake,row,timeout=2)['observation'].get('responsive') for row in good):break
  assert time.monotonic()<until,'native TUI binding readiness timeout';time.sleep(.1)
 print('NATIVE_READY',flush=True)

 from codex_wake.controller_tab_adapters import TmuxAttachmentTransport,PsmuxAttachmentTransport,ConfiguredBridge
 from codex_wake import tab_psmux_bridge
 winpython='/mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts/python.exe'
 namespace='wake510-'+uuid.uuid4().hex[:12]
 report['windows_namespace']=namespace
 created=False
 def win(code,*args):
  return subprocess.check_output([winpython,'-c',code,*args],text=True,timeout=20).strip()
 binary_code="import subprocess,os,sys;from pathlib import Path;p=str(Path(os.environ['LOCALAPPDATA'])/'Microsoft/WinGet/Links/psmux.exe');"
 try:
  bridge_script=subprocess.check_output(['wslpath','-w',str(P(tab_psmux_bridge.__file__).resolve())],text=True).strip()
  creation=binary_code+"import importlib.util;spec=importlib.util.spec_from_file_location('bridge',sys.argv[2]);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);d=Path(os.environ['LOCALAPPDATA'])/'codex-wake-test'/sys.argv[1];d.mkdir(parents=True);subprocess.run(['icacls',str(d),'/inheritance:r','/grant:r','*'+b.current_sid()+':(OI)(CI)F'],check=True,capture_output=True,timeout=5);print(d);subprocess.run([p,'-L',sys.argv[1],'new-session','-d','-s','destination','-n','anchor','--','cmd.exe','/d','/k'],capture_output=True,check=True,timeout=5)"
  windows_directory=win(creation,namespace,bridge_script);created=True
  bridge_script=subprocess.check_output(['wslpath','-w',str(P(tab_psmux_bridge.__file__).resolve())],text=True).strip()
  command=[winpython,bridge_script,'--namespace',namespace,'--session','destination','--attach-directory',windows_directory]
  description=json.loads(subprocess.check_output(command+['--describe'],text=True,timeout=15))
  command+=['--server-pid',str(description['identity']['pid']),'--server-birth',str(description['identity']['creation_filetime'])]
  # The wrapper only selects the installed fixture package/dependencies; native
  # launch fields remain in the private hashed manifest, never caller argv.
  python_wrapper=root/'wake-python'
  python_wrapper.write_text('#!/bin/sh\nexport PYTHONPATH='+shlex.quote(os.environ['PYTHONPATH'])+'\nexport HOME='+shlex.quote(str(root/'house'))+'\nexport WSL_DISTRO_NAME='+shlex.quote(os.environ['WSL_DISTRO_NAME'])+'\nexec /usr/bin/python3 "$@"\n')
  python_wrapper.chmod(0o700)
  workspaces=dict(source=dict(kind='byobu',transport=TmuxAttachmentTransport(sock,'$0'),app_server=endpoint,wake_python=str(python_wrapper)),
                  destination=dict(kind='psmux',transport=PsmuxAttachmentTransport(ConfiguredBridge(command),generation=description['generation'])))
  owner=TabReattach(wake,workspaces=workspaces,host=socket.gethostname(),environment=os.environ['WSL_DISTRO_NAME'])
  view=session_rows(wake,socket_path=sock,endpoints=[endpoint],deadline=time.monotonic()+3)
  row=next(r for r in view['sessions'] if r['thread_id']==ids[0])
  attachment=row['attachments'][0]
  profile=owner.runtime.capture('source',next(w for w in owner.lifecycle.inspect('source')['snapshot']['windows'] if w['window_id']==attachment['window_id']))
  report['source_process']=profile['process']
  resources=wake/'objective-ledgers';resources.mkdir(mode=0o700)
  cumulative=resources/'synthetic.json';cumulative.write_text('{"used":93,"window":7,"deadline":1800000010}')
  before_cumulative=cumulative.read_bytes();before_inode=cumulative.stat().st_ino
  request=dict(workspace='source',expected_target=owner.lifecycle.inspect('source')['target'],window=attachment['window_id'],
               destination='destination',expected_destination=owner.lifecycle.inspect('destination')['target'],force=True)
  # Native health does not prove the unsent composer is empty.
  draft='synthetic-unsent-510'
  tm('send-keys','-t',attachment['pane_id'],'-l',draft)
  time.sleep(.3)
  held=owner.execute('tabs.reattach-preview',dict(request,retire_source=True))
  assert held['status']=='held' and held['reason']=='source_input_custody_unknown_or_nonempty',held
  assert draft in tm('capture-pane','-p','-t',attachment['pane_id'])
  report['draft_retirement_held']=True
  preview=owner.execute('tabs.reattach-preview',request);report['preview']=preview
  assert preview['status']=='ready',preview
  report['source_alive_before_apply']=process_identity(profile['process']['pid']) is not None
  result=owner.execute('tabs.reattach-apply',dict(plan_id=preview['plan_id']));report['apply']=result
  if result['status']!='applied':
   try:
    observed=workspaces['destination']['transport'].snapshot(time.monotonic()+5)
    report['destination_screens']=[workspaces['destination']['transport'].visible_screen(w['panes'][0]['pane_id'],time.monotonic()+5)
      for w in observed['windows'] if w['name'].startswith('reattach-')]
   except Exception as diagnostic:report['destination_diagnostic_error']=str(diagnostic)
  assert result['status']=='applied',result
  assert result['identity']['conversation_id']==ids[0]
  assert result['destination']['health']['evidence']=='tui_main_loop_ack'
  assert result['destination']['process']['pid']!=profile['process']['pid']
  assert cumulative.read_bytes()==before_cumulative and cumulative.stat().st_ino==before_inode
  current=workspaces['destination']['transport'].snapshot(time.monotonic()+5)
  before_windows=[w['window_id'] for w in current['windows']]
  repeated=owner.execute('tabs.reattach-apply',dict(plan_id=preview['plan_id']))
  assert repeated['replayed']
  assert [w['window_id'] for w in workspaces['destination']['transport'].snapshot(time.monotonic()+5)['windows']]==before_windows
  assert result['source_preserved'] is True and result['source_retired'] is False
  assert attachment['window_id'] in tm('list-windows','-F','#{window_id}')
  assert draft in tm('capture-pane','-p','-t',attachment['pane_id'])
  destination_window=next(w for w in current['windows'] if w['window_id']==result['destination']['window']['window_id'])
  projection=owner.binding_for('destination',destination_window)
  assert projection and projection['identity']==result['identity'],projection
  report['managed_destination_projection_verified']=True
  report.update(status='passed',same_account_conversation_execution_owner=True,destination_verified_source_draft_retained=True,
                cumulative_state_preserved=True,replay_without_duplicate_client=True,windows_identity=description['identity'],
                bridge_sha256=hashlib.sha256(P(tab_psmux_bridge.__file__).read_bytes()).hexdigest(),trap_requests=list(calls))
  assert not calls,calls
 finally:
  if created:
   win(binary_code+"subprocess.run([p,'-L',sys.argv[1],'kill-server'],capture_output=True,timeout=5);r=subprocess.run([p,'-L',sys.argv[1],'list-sessions'],capture_output=True,text=True,timeout=5);print(r.returncode,r.stdout)",namespace)
except Exception as error:
 report.update(status='failed',error_type=type(error).__name__,error=str(error));traceback.print_exc()
finally:
 try:tm('kill-server')
 except Exception:pass
 daemon.terminate()
 try:daemon.wait(timeout=5)
 except subprocess.TimeoutExpired:daemon.kill();daemon.wait(timeout=2)
 trap.shutdown();trap.server_close();log.close()
 report['trap_requests']=list(calls)
 # Retain only owned fixture process observations, not a host-wide process dump.
 pids=[report.get('source_process',{}).get('pid'),(report.get('apply',{}).get('destination') or {}).get('process',{}).get('pid')]
 until=time.monotonic()+5
 while time.monotonic()<until and any(pid and process_identity(pid) is not None for pid in pids):time.sleep(.05)
 report['final_owned_native_processes']=[pid for pid in pids if pid and process_identity(pid) is not None]
 if report['final_owned_native_processes'] and report['status']=='passed':report['status']='cleanup_incomplete'
 (root/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],receipt=str(root/'receipt.json'))),flush=True)
 if report['status']!='passed':raise SystemExit(1)
