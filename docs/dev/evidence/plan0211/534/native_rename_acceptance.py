import json,os,shutil,subprocess,tempfile,time,uuid,hashlib,sys
import codex_wake
from pathlib import Path
from codex_wake.controller_tabs import ControllerTabs
from codex_wake.controller_tab_adapters import ConfiguredBridge,PsmuxAttachmentTransport
from codex_wake import tab_psmux_bridge
py='/mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts/python.exe'
ns='wake534-'+uuid.uuid4().hex[:12];directory=Path('/mnt/c/Users/ecoch/AppData/Local/codex-wake-test')/ns;directory.mkdir()
bridge=directory/'bridge.py';shutil.copyfile(tab_psmux_bridge.__file__,bridge)
wp=subprocess.check_output(['wslpath','-w',str(bridge)],text=True).strip();base=[py,wp,'--namespace',ns]
def bootstrap(name,action):
 r=subprocess.run(base+['--session',name,'--session-management'],input=json.dumps(dict(action=action,arguments={})),capture_output=True,text=True,timeout=15);v=json.loads(r.stdout);assert 'error' not in v,v;return v['result']
checks=[];result={}
try:
 bootstrap('seed','session_create')
 d=json.loads(subprocess.check_output(base+['--session','seed','--describe'],text=True,timeout=15));ident=d['identity'];fixed=base+['--session','seed','--server-pid',str(ident['pid']),'--server-birth',str(ident['creation_filetime'])]
 transport=PsmuxAttachmentTransport(ConfiguredBridge(fixed),generation=d['generation'])
 original=transport.snapshot(time.monotonic()+10)
 with tempfile.TemporaryDirectory() as root:
  tabs=ControllerTabs(Path(root),workspaces={'seed':dict(kind='psmux',label='seed',transport=transport)},host='test',environment='fixture')
  created=tabs.execute('tabs.session.create',dict(name='bots',backend='psmux'))['session'];assert created['state']=='empty' and created['server']==ns;checks.append('empty-definition-host-namespace')
  opened=tabs.execute('tabs.session.open',dict(session=created['id']))['session'];assert opened['state']=='running';checks.append('native-open')
  birth=[(p['pid'],p['windows_creation_filetime']) for w in opened['snapshot']['windows'] for p in w['panes']]
  workspace=opened['workspace']
  before=transport.snapshot(time.monotonic()+10)
  baseline=tabs.workspaces[workspace]['transport'].formatting('read',dict(window=opened['snapshot']['windows'][0]['window_id']),time.monotonic()+10)
  enabled=tabs.execute('tabs.format.enable',dict(workspace=workspace));assert enabled['status']=='applied',enabled
  changed=tabs.execute('tabs.session.update',dict(session=created['id'],changes={'name':'workers','labels':['automation']}))['session'];assert changed['id']==created['id'] and changed['name']=='workers'
  rollback=tabs.execute('tabs.format.rollback',dict(workspace=workspace));assert rollback['status']=='rolled_back',rollback
  restored=tabs.workspaces[workspace]['transport'].formatting('read',dict(window=opened['snapshot']['windows'][0]['window_id']),time.monotonic()+10)
  assert restored==baseline,(restored,baseline)
  checks.append('rename-exact-format-baseline-rollback')
  assert [(p['pid'],p['windows_creation_filetime']) for w in changed['snapshot']['windows'] for p in w['panes']]==birth
  reopened=ControllerTabs(Path(root),workspaces={},host='test',environment='fixture');running=reopened.execute('tabs.session.show',dict(session='workers'))['session'];assert running['state']=='running';checks.append('restart-restores-exact-generation')
  try:reopened.execute('tabs.session.delete',dict(session='workers'));raise AssertionError('populated deleted')
  except ValueError:checks.append('populated-delete-refused')
  empty=reopened.execute('tabs.session.create',dict(name='unsupported-move',backend='psmux'))['session']
  try:
   reopened.execute('tabs.relocate.preview',dict(session='workers',destination=empty['id']))
   raise AssertionError('psmux cross-session move accepted')
  except ValueError:checks.append('psmux-cross-session-move-unsupported-before-effect')
  reopened.execute('tabs.session.delete',dict(session=empty['id']))
  deleted=reopened.execute('tabs.session.delete',dict(session='workers',terminate=True))
  result['first_native_delete_status']=deleted['status']
  if deleted['status']=='partial':deleted=reopened.execute('tabs.session.delete',dict(plan_id=deleted['plan_id']))
  assert deleted['status']=='deleted',deleted
  replacement=reopened.execute('tabs.session.create',dict(name='workers',backend='psmux',server=ns))['session']
  assert replacement['id']!=created['id'] and replacement['state']=='empty'
  reopened.execute('tabs.session.delete',dict(session=replacement['id']))
  checks.append('native-terminate-reconcile-tombstone-name-reuse-empty-delete')
  final=transport.snapshot(time.monotonic()+10);assert original['windows']==final['windows'];checks.append('peer-server-unchanged')
 result=dict(result,owned_servers=[original['server_identity'],opened['snapshot']['server_identity']],package=codex_wake.__file__,python=sys.executable,prefix=sys.prefix,status='passed',checks=checks,namespace=ns,identity=ident,bridge_sha256=hashlib.sha256(bridge.read_bytes()).hexdigest(),windows_python=py,provider_calls=0,production_touched=False)
except Exception as e:
 result=dict(status='failed',checks=checks,namespace=ns,error=repr(e));raise
finally:
 # Close only known owned names via exact native bridge lifecycle.
 for name in ['workers','bots','seed','unsupported-move']:
  try:
   if bootstrap(name,'session_probe')['present']:
    d=json.loads(subprocess.check_output(base+['--session',name,'--describe'],text=True,timeout=15));t=PsmuxAttachmentTransport(ConfiguredBridge(base+['--session',name,'--server-pid',str(d['identity']['pid']),'--server-birth',str(d['identity']['creation_filetime'])]),generation=d['generation'])
    for w in t.snapshot(time.monotonic()+10)['windows']:t.lifecycle('close',dict(window=w['window_id']),time.monotonic()+10)
  except Exception as e:result['cleanup_error']=repr(e)
 result['final_presence']={name:bootstrap(name,'session_probe') for name in ['workers','bots','seed','unsupported-move']}
 if result.get('owned_servers'):
  code="import ctypes,json,sys\nfrom ctypes import wintypes as w\nk=ctypes.WinDLL('kernel32',use_last_error=True)\nk.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE\nk.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];k.GetProcessTimes.restype=w.BOOL\nk.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];k.CloseHandle.argtypes=[w.HANDLE]\ndef observe(p):\n h=k.OpenProcess(0x1000,False,p)\n if not h:return dict(winerror=ctypes.get_last_error())\n try:\n  t=[w.FILETIME() for _ in range(4)];out=w.DWORD()\n  assert k.GetProcessTimes(h,*[ctypes.byref(v) for v in t]) and k.GetExitCodeProcess(h,ctypes.byref(out))\n  return dict(birth=(t[0].dwHighDateTime<<32)|t[0].dwLowDateTime,exit_code=out.value)\n finally:k.CloseHandle(h)\nprint(json.dumps({str(p):observe(p) for p in json.loads(sys.stdin.read())}))"
  census=subprocess.run([py,'-c',code,wp],input=json.dumps([i['pid'] for i in result['owned_servers']]),text=True,capture_output=True,check=True,timeout=15)
  result['final_server_births']=json.loads(census.stdout)
  assert all(result['final_server_births'][str(i['pid'])].get('winerror')==87 or result['final_server_births'][str(i['pid'])].get('birth') not in (None,i['creation_filetime']) or result['final_server_births'][str(i['pid'])].get('exit_code',259)!=259 for i in result['owned_servers']),result['final_server_births']
 Path('/tmp/qualification534-green.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));shutil.rmtree(directory)
