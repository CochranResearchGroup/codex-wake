"""One disposable public stop recovery proof; generic sleep/injected time, no Codex/provider."""
import json,os,sys,tempfile,time,subprocess,uuid
from pathlib import Path
from codex_wake.host_execution import SystemdExecution
from codex_wake.strict_runtime import location
from codex_wake.lifecycle_configuration import effective_configuration
from codex_wake.objective_ledger import ObjectiveLedger
from codex_wake.process import process_identity,boot_id_value
out=Path(sys.argv[1]); source=Path.cwd(); result={'qualification':'real systemd/public operator CLI; injected time/ledger and generic sleep, no native Codex/provider'}
with tempfile.TemporaryDirectory(prefix='cw166-launch-recovery-') as tmp:
 root=Path(tmp);directory=location(root,'proof');home=directory/'home';home.mkdir(parents=True,mode=0o700);directory.chmod(0o700)
 instruction=root/'review.md';instruction.write_text('Fixture only.')
 limits=dict(memory_max_bytes=134217728,memory_swap_max_bytes=0,cpu_quota_percent=50,tasks_max=32,stop_grace_seconds=1,checkpoint_grace_seconds=1,poll_seconds=.2,accounting_max_age_seconds=10)
 selection=dict(name='fixture',path=str(instruction))
 profiles=dict(profiles={'fixture':dict(cwd=tmp,codex_home=str(home),app_server='unix://'+str(directory/'app-server.sock'),strict_execution=limits)},lifecycle_defaults=dict(session_token_limit=100,objective_token_limit=200,session_time_limit_seconds=20,objective_time_limit_seconds=30,max_correction_cycles=0,handoff_writer=selection,preflight_reviewer=selection),continuations={'bootstrap':dict(objective_id='proof',objective='Fixture only',approval='operator fixture',started_at='1970-01-01T00:01:40Z')})
 profiles_path=root/'profiles.json';profiles_path.write_text(json.dumps(profiles));cfg=effective_configuration(profiles,'bootstrap','fixture')
 ledger=ObjectiveLedger(root,'proof');ledger.configure({k:v for k,v in cfg.items() if k not in ('source_thread_id','profile')},'operator fixture',now=100)
 lifecycle=root/'lifecycle';lifecycle.mkdir();heartbeat=lifecycle/'supervision.json';heartbeat.write_text(json.dumps(dict(active=True,pid=os.getpid(),identity=process_identity(os.getpid()),observed_at=100,observed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME),boot_id=boot_id_value(),interval=1)));heartbeat.chmod(0o600)
 generation=uuid.uuid4().hex;unit='codex-wake-objective-'+generation+'.service';binding=directory/'binding.json'
 binding.write_text(json.dumps(dict(state='uncertain',objective_id='proof',generation=generation,unit=unit,identity=None,configuration_revision=cfg['revision'],reason='executor_launch_unverified')));binding.chmod(0o600)
 status=directory/'status.json';config=directory/'guard.json';config.write_text(json.dumps(dict(wake_root=tmp,objective_id='proof',endpoint='unix://'+str(directory/'app-server.sock'),codex_home=str(home),argv=['/bin/sleep','30'],cwd=tmp,configuration=cfg,started_upper=100,started_boottime=time.clock_gettime(time.CLOCK_BOOTTIME),boot_id=boot_id_value(),deadline=130,status_path=str(status),generation=generation)));config.chmod(0o600)
 sentinel=subprocess.Popen(['/bin/sleep','30']);identity=None
 try:
  def lost_response(argv,**kwargs):
   value=subprocess.run(argv,**kwargs)
   if argv[0]=='systemd-run':raise subprocess.TimeoutExpired(argv,15)
   return value
  try:SystemdExecution(runner=lost_response).launch(unit,[sys.executable,'-m','codex_wake.strict_executor',str(config)],cwd=tmp,environment={'PYTHONPATH':str(source/'src')},limits={k:limits[k] for k in ('memory_max_bytes','memory_swap_max_bytes','cpu_quota_percent','tasks_max','stop_grace_seconds')},runtime_seconds=15)
  except RuntimeError as exc:
   assert str(exc).startswith('ambiguous launch');result['launch_response']='intentionally lost after actual systemd-run response'
  until=time.monotonic()+5
  while not status.exists() and time.monotonic()<until:time.sleep(.025)
  guard=json.loads(status.read_text());identity=guard['service_identity'];result['guard_identity']=identity
  assert guard['generation']==generation and identity['unit']==unit
  before=SystemdExecution().inspect(identity);assert guard['pid'] in before['members'];result['before']=before
  env=dict(os.environ,PYTHONPATH=str(source/'src'))
  stopped=subprocess.run([sys.executable,'-m','codex_wake','--wake-root',tmp,'sessions','execution','--profiles',str(profiles_path),'--profile','fixture','--thread-id','bootstrap','--stop','--json'],env=env,capture_output=True,text=True,timeout=10)
  result['public_stop_code']=stopped.returncode;result['public_stop']=json.loads(stopped.stdout);assert stopped.returncode==0
  saved=json.loads(binding.read_text());result['binding']=saved;assert saved['identity']==identity and saved['state']=='stopped'
  after=SystemdExecution().inspect(identity);result['after']=after;assert not after['populated'] and not after['members']
  result['sentinel_survived']=sentinel.poll() is None;assert result['sentinel_survived'];result['state']='passed'
 finally:
  if identity:
   try:SystemdExecution().stop(identity)
   except RuntimeError:pass
  sentinel.terminate();sentinel.wait(timeout=3)
  out.write_text(json.dumps(result,indent=2)+'\n')
print(result['state'])
