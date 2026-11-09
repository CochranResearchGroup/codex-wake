import json,os,shutil,subprocess,tempfile,time,uuid,hashlib
from pathlib import Path
from codex_wake.controller_tabs import ControllerTabs
from codex_wake.controller_tab_adapters import ConfiguredBridge,PsmuxAttachmentTransport
from codex_wake import tab_psmux_bridge
py='/mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts/python.exe'
ns='wake529-'+uuid.uuid4().hex[:12];directory=Path('/mnt/c/Users/ecoch/AppData/Local/codex-wake-test')/ns;directory.mkdir()
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
  changed=tabs.execute('tabs.session.update',dict(session=created['id'],changes={'name':'workers','labels':['automation']}))['session'];assert changed['id']==created['id'] and changed['name']=='workers';checks.append('rename-preserves-identity')
  assert [(p['pid'],p['windows_creation_filetime']) for w in changed['snapshot']['windows'] for p in w['panes']]==birth
  reopened=ControllerTabs(Path(root),workspaces={},host='test',environment='fixture');running=reopened.execute('tabs.session.show',dict(session='workers'))['session'];assert running['state']=='running';checks.append('restart-restores-exact-generation')
  try:reopened.execute('tabs.session.delete',dict(session='workers'));raise AssertionError('populated deleted')
  except ValueError:checks.append('populated-delete-refused')
  cfg=reopened.workspaces[created['id']];snapshot=cfg['transport'].snapshot(time.monotonic()+10);cfg['transport'].lifecycle('close',dict(window=snapshot['windows'][0]['window_id']),time.monotonic()+10)
  assert reopened.execute('tabs.session.show',dict(session='workers'))['session']['state']=='empty';checks.append('last-tab-close-retains-empty')
  reopened.execute('tabs.session.delete',dict(session='workers'));assert not reopened.execute('tabs.session.list',{})['sessions'];checks.append('empty-delete')
  final=transport.snapshot(time.monotonic()+10);assert original['windows']==final['windows'];checks.append('peer-server-unchanged')
 result=dict(status='passed',checks=checks,namespace=ns,identity=ident,bridge_sha256=hashlib.sha256(bridge.read_bytes()).hexdigest(),windows_python=py,provider_calls=0,production_touched=False)
except Exception as e:
 result=dict(status='failed',checks=checks,namespace=ns,error=repr(e));raise
finally:
 # Close only known owned names via exact native bridge lifecycle.
 for name in ['workers','bots','seed']:
  try:
   if bootstrap(name,'session_probe')['present']:
    d=json.loads(subprocess.check_output(base+['--session',name,'--describe'],text=True,timeout=15));t=PsmuxAttachmentTransport(ConfiguredBridge(base+['--session',name,'--server-pid',str(d['identity']['pid']),'--server-birth',str(d['identity']['creation_filetime'])]),generation=d['generation'])
    for w in t.snapshot(time.monotonic()+10)['windows']:t.lifecycle('close',dict(window=w['window_id']),time.monotonic()+10)
  except Exception as e:result['cleanup_error']=repr(e)
 result['final_presence']={name:bootstrap(name,'session_probe') for name in ['workers','bots','seed']}
 Path('/tmp/qualification529.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));shutil.rmtree(directory)
