import os,json,time,subprocess,pathlib,signal,shlex,threading,http.server,traceback,ctypes
from codex_wake.native_protocol import native_request
from codex_wake.local_health import observe_row
from codex_wake.tab_traits import session_rows
from codex_wake.process import process_identity
P=pathlib.Path;assert os.geteuid()==1017
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--state',type=P,required=True);root=parser.parse_args().state
old=json.loads((root/'receipt.json').read_text())
home=root/'accounts/codex-test';os.environ['CODEX_HOME']=str(home)
binary='/tmp/recovery368-native-package/bin/codex';identifier=old['captured_conversations'][0];sock=str(root/'tmux.sock')
requests=[]
class Trap(http.server.BaseHTTPRequestHandler):
 def do_GET(self):requests.append(('GET',self.path));self.send_response(503);self.end_headers()
 def do_POST(self):requests.append(('POST',self.path));self.send_response(503);self.end_headers()
 def log_message(self,*args):pass
trap=http.server.ThreadingHTTPServer(('127.0.0.1',0),Trap);threading.Thread(target=trap.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(trap.server_port)
config=(home/'config.toml').read_text();config='\n'.join('base_url='+json.dumps(url+'/never-query') if line.startswith('base_url=') else line for line in config.splitlines())+'\n';(home/'config.toml').write_text(config)
env=dict(PATH=os.environ['PATH'],HOME=str(root/'house'),CODEX_HOME=str(home),TERM='xterm-256color',HTTP_PROXY=url,HTTPS_PROXY=url,ALL_PROXY=url,NO_PROXY='127.0.0.1,localhost')
endpoint='unix://'+str(root/'native.sock');log=(root/'health-stop-daemon.log').open('wb')
daemon=subprocess.Popen([binary,'app-server','--listen',endpoint],env=env,cwd=root/'workspace',stdout=log,stderr=subprocess.STDOUT)
def tm(*args):return subprocess.check_output(['tmux','-S',sock,*args],env=env,text=True).strip()
source_pid=None;source_birth=None;stopped_tid=None;tmux_server=None;tmux_log=None;report=dict(status='running',root=str(root),identifier=identifier)
def states():return {p.name:(p/'stat').read_text().rsplit(')',1)[1].split()[0] for p in P('/proc',str(source_pid),'task').iterdir()}
def pending():return {line.split(':')[0]:line.split(':')[1].strip() for line in P('/proc',str(source_pid),'status').read_text().splitlines() if line.startswith(('SigPnd:','ShdPnd:'))}
try:
 until=time.monotonic()+15
 while not P(endpoint[7:]).exists():assert time.monotonic()<until;time.sleep(.02)
 endpoint='unix://'+str(P(endpoint[7:]).resolve())
 if P(sock).exists():P(sock).unlink()
 tmux_log=(root/'ptrace-tmux.log').open('wb')
 tmux_server=subprocess.Popen(['tmux','-D','-S',sock],stdin=subprocess.DEVNULL,stdout=tmux_log,stderr=subprocess.STDOUT,env=env)
 until=time.monotonic()+3
 while not P(sock).exists():assert time.monotonic()<until;time.sleep(.02)
 tm('new-session','-d','-s','fixture','-n','shell','-x','140','-y','45','exec sleep 120');tm('set-option','-g','automatic-rename','off')
 created=[]
 for name in ('view-a','view-b'):
  created.append(tm('new-window','-d','-P','-F','#{pane_pid}|#{pane_id}','-n',name,shlex.join(['env','CODEX_HOME='+str(home),binary,'--remote',endpoint,'resume',identifier,'--no-alt-screen'])).split('|'))
 source_pid,peer_pid=[int(v[0]) for v in created]
 source_birth=process_identity(source_pid);peer_birth=process_identity(peer_pid)
 source_exact=dict(pid=source_pid,start_ticks=source_birth['start_time_ticks'],boot_id=source_birth['boot_id'])
 peer_exact=dict(pid=peer_pid,start_ticks=peer_birth['start_time_ticks'],boot_id=peer_birth['boot_id'])
 row=dict(target=dict(host='cooper',environment='posix',provider='codex',home=str(home),executable=binary,
  build_sha256=old['native_sha256'],conversation_id=identifier,process=dict(pid=daemon.pid)),endpoint=endpoint,codex_cmd=[binary],model_provider='recovery_fixture')
 until=time.monotonic()+20
 while True:
  first=observe_row(root/'wake',row,timeout=1,client_process=source_exact);peer=observe_row(root/'wake',row,timeout=1,client_process=peer_exact)
  if first['observation'].get('responsive') and peer['observation'].get('responsive'):break
  assert time.monotonic()<until,'dualview readiness timeout';time.sleep(.05)
 report.update(source_pid=source_pid,peer_pid=peer_pid,birth=source_birth,healthy_source=first,healthy_peer=peer,task_states_healthy=states())
 assert process_identity(source_pid)==source_birth
 tid=first['observation']['loop_tid'];assert (P('/proc',str(source_pid),'task',str(tid),'comm')).read_text().strip()=='codex-main'
 libc=ctypes.CDLL(None,use_errno=True)
 def ptrace(request):
  result=libc.ptrace(request,tid,None,None)
  if result==-1:raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
 ptrace(0x4206);ptrace(0x4207);stopped_tid=tid
 until=time.monotonic()+3
 while True:
  waited,status=os.waitpid(tid,os.WNOHANG|0x40000000)
  if waited:assert os.WIFSTOPPED(status);break
  assert time.monotonic()<until,'exact loop did not stop';time.sleep(.01)
 report['task_states_before']=states();report['pending_before']=pending()
 assert report['task_states_before'][str(tid)] in ('T','t')
 selected=observe_row(root/'wake',row,timeout=.25,client_process=source_exact)
 report['selected']=selected;report['task_states_after']=states();report['pending_after']=pending()
 report['peer_after']=observe_row(root/'wake',row,timeout=1,client_process=peer_exact)
 before=report['task_states_before'][str(tid)] in ('T','t');after=report['task_states_after'][str(tid)] in ('T','t')
 assert not selected['observation'].get('responsive'),'stopped exact loop falsely acknowledged'
 assert report['peer_after']['observation'].get('responsive'),'healthy peer lost'
 import sys
 completed=subprocess.run([str(P(sys.executable).parent/'codex-wake'),'--wake-root',str(root/'wake'),'tabs','recovery-capture','--workspace','fixture','--capture-id','ptrace-negative','--request-id','ptrace-negative'],env=env,text=True,capture_output=True,timeout=30)
 assert completed.returncode==0,(completed.stdout,completed.stderr)
 captured=json.loads(completed.stdout)['result']['operation']['result']
 report['public_cli_capture']=True
 captured_source=next(value for value in captured['snapshot']['rows'] if created[0][1] in value['original_panes'])
 assert captured_source['kind']=='unsupported','capture borrowed peer for stopped exact UIloop'
 report['capture_stopped_source_kind']=captured_source['kind']
 report['hypothesis']='H3_stopped_source_ack' if before and after and selected['observation'].get('responsive') else 'H2_source_resumed' if before and not after else 'H1_group_stop_incomplete' if not before else 'negative_pass'
 report['status']='observed';print(json.dumps(dict(hypothesis=report['hypothesis'],selected_responsive=selected['observation'].get('responsive'),loop_tid=first['observation'].get('loop_tid'))),flush=True)
except Exception as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());print('FAILED',str(e),flush=True)
finally:
 if stopped_tid is not None:
  try:ptrace(17)
  except Exception:pass
 if source_pid and process_identity(source_pid)==source_birth:os.kill(source_pid,signal.SIGCONT)
 try:tm('kill-server')
 except Exception:pass
 daemon.terminate()
 try:daemon.wait(timeout=5)
 except subprocess.TimeoutExpired:daemon.kill();daemon.wait(timeout=2)
 if tmux_server is not None:
  try:tmux_server.wait(timeout=2)
  except subprocess.TimeoutExpired:tmux_server.terminate();tmux_server.wait(timeout=2)
 if tmux_log:tmux_log.close()
 log.close();trap.shutdown();trap.server_close();report['trap_requests']=requests
 (root/'health-ptrace-diagnosis.json').write_text(json.dumps(report,indent=2));print('RECEIPT',root/'health-ptrace-diagnosis.json',flush=True)
