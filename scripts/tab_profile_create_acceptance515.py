#!/usr/bin/env python3
"""Installed disposable native selected-profile creation; no provider/model turns.

Uses the previously qualified immutable #368 native package and public synthetic
model metadata. Owns only its fresh tmux socket, private home and descendant PIDs.
"""
import hashlib
import http.server
import json
import os
from pathlib import Path
import socket
import sys
import subprocess
import tempfile
import threading
import time
import traceback

from codex_wake.process import process_identity

assert os.getuid()==1017
root=Path(tempfile.mkdtemp(prefix='wake-profile515-native-'));root.chmod(0o700)
print('STATE_ROOT',root,flush=True)
wake=root/'wake';wake.mkdir(mode=0o700)
workspace=root/'workspace';workspace.mkdir(mode=0o700)
home=root/'accounts/codex-fixture';home.mkdir(parents=True,mode=0o700)
binary=Path('/tmp/recovery368-native-package/bin/codex')
model=json.loads(Path('/tmp/recovery368-models.json').read_text())['models'][0]
(home/'models.json').write_text(json.dumps({'models':[model]}))
calls=[]
class Trap(http.server.BaseHTTPRequestHandler):
 def do_GET(self):calls.append(('GET',self.path));self.send_response(503);self.end_headers()
 def do_POST(self):calls.append(('POST',self.path));self.send_response(503);self.end_headers()
 def log_message(self,*args):pass
trap=http.server.ThreadingHTTPServer(('127.0.0.1',0),Trap);threading.Thread(target=trap.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(trap.server_port)
(home/'config.toml').write_text('model='+json.dumps(model['slug'])+'\nmodel_provider="profile_fixture"\nmodel_catalog_json='+json.dumps(str(home/'models.json'))+'\ncheck_for_update_on_startup=false\n[analytics]\nenabled=false\n[model_providers.profile_fixture]\nname="No provider turns"\nbase_url='+json.dumps(url+'/never-query')+'\nwire_api="responses"\nrequires_openai_auth=false\n[projects.'+json.dumps(str(workspace))+']\ntrust_level="trusted"\n')
sha=hashlib.sha256(binary.read_bytes()).hexdigest()
manifest=root/'builds.json';manifest.write_text(json.dumps({'schema_version':1,'builds':{'modded':{
 'executable':str(binary),'sha256':sha,'upstream_version':'0.167.0','revision':'qualified368','source':'qualified-provider-free-fixture','read_schemas':[5]}}}))
(wake/'controller-accounts.toml').write_text('[profiles]\nstate_root='+json.dumps(str(home.parent))+'\nselection_mode="launcher"\nknown_profiles=["fixture"]\nshared_links=[]\n[builds]\nmanifest='+json.dumps(str(manifest))+'\n')
(wake/'controller-accounts.toml').chmod(0o600)
sock=str(root/'tmux.sock')
env={k:os.environ[k] for k in ('PATH','LANG','PYTHONPATH') if k in os.environ}
env.update(HOME=str(root/'house'),TERM='xterm-256color',HTTP_PROXY=url,HTTPS_PROXY=url,ALL_PROXY=url,NO_PROXY='localhost,127.0.0.1',CODEX_BUILD_UPDATE_CHECK='0')
def tm(*args):return subprocess.check_output(['tmux','-S',sock,*args],text=True,env=env).strip()
report=dict(status='running',native_sha256=sha,provider_calls=[],model_turns=0,uid=os.getuid())
child=None;unrelated=None
try:
 tm('new-session','-d','-s','fixture','-n','anchor','sleep 120')
 tm('set-option','-g','automatic-rename','off')
 # An unrelated local process is deliberately outside the disposable socket.
 unrelated=subprocess.Popen(['sleep','120'])
 config=wake/'controller-tabs.json'
 config.write_text(json.dumps(dict(schema_version=1,workspaces={'fixture':dict(kind='tmux',socket_path=sock,session_id='$0')})));config.chmod(0o600)
 argv=[str(Path(sys.executable).parent/'codex-wake'),'--wake-root',str(wake),'tabs','create',
       '--workspace','fixture','--profile','fixture','--name','selected','--cwd',str(workspace),'--request-id','native-profile515']
 def create():
  completed=subprocess.run(argv,env=env,cwd=workspace,text=True,capture_output=True,timeout=20)
  assert completed.returncode==0,(completed.stdout,completed.stderr)
  return json.loads(completed.stdout)
 result=create()
 report['public_cli']=True
 report['operation']=result
 # The public journal retains the exact effect owner's response.
 record=result['result']['operation'];effect=record['result']
 assert effect['status']=='applied',effect
 child=effect['process'];report['owned_child']=child
 foreground=effect['foreground']
 assert foreground['role']=='foreground_tui_client'
 assert foreground['source']=='exact_run_build_direct_child_invocation'
 wrapper=foreground['wrapper_process']
 assert process_identity(wrapper['pid'])=={k:v for k,v in wrapper.items() if k!='pid'}
 status=Path('/proc',str(child['pid']),'status').read_text()
 assert int(next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:')))==wrapper['pid']
 argv_native=Path('/proc',str(child['pid']),'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
 assert argv_native[1]==b'--no-daemon' and b'app-server' not in argv_native
 report['exact_foreground_client_role']=foreground
 assert effect['profile_target']['home']==str(home)
 assert effect['profile_target']['build_sha256']==sha
 assert effect['profile_target']['build_channel']=='modded'
 before=tm('list-windows','-F','#{window_id}')
 repeated=create()
 assert repeated==result and before==tm('list-windows','-F','#{window_id}')
 report['same_key_replay_without_duplicate']=True
 assert process_identity(child['pid'])=={k:v for k,v in child.items() if k!='pid'}
 assert unrelated.poll() is None
 assert not calls,calls
 report.update(status='passed',exact_selected_build_home_process=True,provider_calls=list(calls))
except Exception as error:
 report.update(status='failed',error_type=type(error).__name__,error=str(error));traceback.print_exc()
finally:
 try:tm('kill-server')
 except Exception:pass
 deadline=time.monotonic()+5
 while child and process_identity(child['pid']) is not None and time.monotonic()<deadline:time.sleep(.05)
 report['final_owned_native_processes']=[child] if child and process_identity(child['pid']) is not None else []
 report['unrelated_process_preserved']=unrelated is not None and unrelated.poll() is None
 if unrelated is not None:
  unrelated.terminate();unrelated.wait(timeout=5)
 trap.shutdown()
 (root/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],receipt=str(root/'receipt.json'))),flush=True)
 if report['status']!='passed':raise SystemExit(1)
