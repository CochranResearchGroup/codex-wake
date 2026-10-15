"""Disposable research only. No Codex/provider calls. Three transient services."""
import json, os, pathlib, signal, subprocess, sys, tempfile, time, uuid

def run(*args):
    return subprocess.run(args,text=True,capture_output=True,timeout=12)

def alive(pid):
    try:
        return pathlib.Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1][0] != 'Z'
    except FileNotFoundError:return False

results=[]
with tempfile.TemporaryDirectory(prefix='cw270-') as tmp:
    sentinel=subprocess.Popen(['sleep','60'])
    try:
        for case in ('deadline','synthetic-token','controller-loss'):
            unit='cw270-'+uuid.uuid4().hex[:12]+'.service'
            info=pathlib.Path(tmp)/case
            # Parent and child ignore TERM to exercise bounded escalation.
            code="import subprocess,signal,time,pathlib,os; signal.signal(signal.SIGTERM,signal.SIG_IGN); p=subprocess.Popen(['sleep','60']); pathlib.Path("+repr(str(info))+").write_text(str(os.getpid())+' '+str(p.pid)); time.sleep(60)"
            props=['Type=exec','RuntimeMaxSec=3s','TimeoutStopSec=1s','KillMode=control-group','SendSIGKILL=yes','Restart=no','MemoryMax=128M','MemorySwapMax=0','CPUQuota=20%','TasksMax=16']
            start=time.monotonic()
            launch=run('systemd-run','--user','--unit='+unit,*['--property='+p for p in props],sys.executable,'-c',code)
            entry=dict(case=case,unit=unit,properties=props,launch_rc=launch.returncode,launch_stderr=launch.stderr)
            try:
                if launch.returncode:
                    results.append(entry);continue
                until=time.monotonic()+2
                while not info.exists() and time.monotonic()<until:time.sleep(.02)
                pids=list(map(int,info.read_text().split()));entry['pids']=pids
                entry['configuration']=run('systemctl','--user','show',unit,'--property=ControlGroup,RuntimeMaxUSec,TimeoutStopUSec,MemoryMax,MemorySwapMax,CPUQuotaPerSecUSec,TasksMax,KillMode').stdout
                cg=next(x.split('=',1)[1] for x in entry['configuration'].splitlines() if x.startswith('ControlGroup='))
                cgpath=pathlib.Path('/sys/fs/cgroup'+cg)
                entry['kernel_limits']={n:(cgpath/n).read_text().strip() for n in ('memory.max','memory.swap.max','cpu.max','pids.max')}
                entry['memberships']={str(p):pathlib.Path(f'/proc/{p}/cgroup').read_text().strip() for p in pids}
                if case=='synthetic-token':
                    # Injected observation, deliberately over cap; not native token telemetry.
                    entry['injected_usage']=dict(cap=100,total=125,overshoot=25)
                    stop=time.monotonic();entry['stop_rc']=run('systemctl','--user','stop',unit).returncode
                    entry['stop_action_seconds']=time.monotonic()-stop
                elif case=='controller-loss':
                    controller=subprocess.Popen(['sleep','60']);controller.kill();controller.wait()
                    entry['dummy_controller_exit']=controller.returncode
                    # No stop request: independent manager runtime must terminate workload.
                until=start+7
                while any(alive(p) for p in pids) and time.monotonic()<until:time.sleep(.02)
                entry['elapsed_to_no_live_owned_seconds']=time.monotonic()-start
                entry['owned_live_after']=[p for p in pids if alive(p)]
                entry['cgroup_populated_after']=(cgpath/'cgroup.events').read_text() if cgpath.exists() else 'removed'
                entry['sentinel_survived']=sentinel.poll() is None
                entry['final']=run('systemctl','--user','show',unit,'--property=ActiveState,SubState,Result,ExecMainStatus').stdout
            finally:
                run('systemctl','--user','stop',unit)
                run('systemctl','--user','reset-failed',unit)
            results.append(entry)
    finally:
        sentinel.terminate();sentinel.wait()
pathlib.Path(__file__).with_name('experiment-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
