#!/usr/bin/env python3
"""Installed-only 100-tab resource qualification; no provider or production effects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--receipt',required=True)
    parser.add_argument('--source-commit',required=True)
    parser.add_argument('--seconds',type=float,default=60)
    parser.add_argument('--diagnostic-profile')
    parser.add_argument('--monitor',action='store_true')
    parser.add_argument('--diagnostic-source')
    parser.add_argument('--monitor-profile')
    parser.add_argument('--steady-profile-prefix')
    parser.add_argument('--poll-interval',type=float,default=.1)
    parser.add_argument('--tick-interval',type=float,default=1.0)
    args=parser.parse_args()
    assert args.seconds>=60 or args.diagnostic_profile,'short windows require explicitly labeled diagnostic profile'
    assert not Path(args.receipt).exists(),'use a unique receipt path; failed attempts must remain retained'
    profile_paths=[]
    if args.monitor_profile:profile_paths.append(Path(args.monitor_profile))
    if args.diagnostic_profile and args.diagnostic_profile!='none':profile_paths.append(Path(args.diagnostic_profile))
    if args.steady_profile_prefix:
        profile_paths.extend(Path(args.steady_profile_prefix+'.'+phase+'.'+suffix)
                             for phase in ('idle','active') for suffix in ('started','prof'))
    assert not any(path.exists() for path in profile_paths),'use unique profile paths; prior runs are immutable'
    if args.diagnostic_source:
        assert args.diagnostic_profile,'source overrides are diagnostics only'
        os.environ['PYTHONPATH']=args.diagnostic_source;sys.path.insert(0,args.diagnostic_source)
    import codex_wake
    from codex_wake.tab_observer import TabObserver
    from websockets.sync.server import unix_serve
    assert args.diagnostic_source or 'site-packages' in codex_wake.__file__, 'source shadow is prohibited'
    receipt=dict(source_commit=args.source_commit,python=sys.version,package=codex_wake.__file__,uid=os.geteuid(),
        tabs=100,initial_idle_active_turns=0,active_conversations=10,windows_seconds=args.seconds,tiers=dict(activity=True,health=True,errors=True),
        cpu_denominator='one core',measurement='Python observer plus fixture server and driver (conservative upper bound), live owned children plus reaped child CPU; excludes disposable pane workload and tmux server',
        fixture_limit='metadata-only Unix WebSocket fixture; no provider turns or proof of real native broadcasts',
        latency_measure='fixture send to public projection, upper bound on receive-to-projection',production_effects=False,tick_interval_seconds=args.tick_interval,public_status_poll_seconds=args.poll_interval if args.monitor else args.tick_interval,source_override=bool(args.diagnostic_source))
    with tempfile.TemporaryDirectory(prefix='wake547-') as directory:
        root=Path(directory); home=root/'home';home.mkdir();(home/'app-server-control').mkdir()
        binary=root/'codex';shutil.copyfile('/bin/sleep',binary);binary.chmod(0o700)
        tmux=['tmux','-S',str(root/'tmux.sock')]
        def command(*parts):
            return subprocess.check_output([*tmux,*parts],text=True).strip()
        start=time.monotonic()
        command('new-session','-d','-s','fixture','-c',str(root),str(binary)+' 900')
        for i in range(1,100):
            command('new-window','-d','-t','fixture','-c',str(root),str(binary)+' 900')
        pane_ids=command('list-panes','-a','-F','#{pane_id}').splitlines()
        assert len(pane_ids)==100
        for i,pane in enumerate(pane_ids): command('select-pane','-t',pane,'-T','fixture-thread-'+str(i))
        from codex_wake.process import process_identity
        fixture_tmux_pid=int(command('display-message','-p','#{pid}'))
        fixture_tmux_birth=process_identity(fixture_tmux_pid)
        assert fixture_tmux_birth and Path('/proc',str(fixture_tmux_pid)).stat().st_uid==os.geteuid()
        receipt['fixture_tmux_identity']=dict(pid=fixture_tmux_pid,start_ticks=fixture_tmux_birth['start_time_ticks'],boot_id=fixture_tmux_birth['boot_id'])
        def fixture_tmux_sample():
            try:
                info=Path('/proc',str(fixture_tmux_pid)).stat()
                fields=Path('/proc',str(fixture_tmux_pid),'stat').read_text().rsplit(')',1)[1].split()
                if info.st_uid!=os.geteuid() or str(fields[19])!=str(fixture_tmux_birth['start_time_ticks']):
                    return dict(status='identity_changed')
                return dict(status='qualified',cpu_seconds=sum(int(fields[i]) for i in (11,12))/os.sysconf('SC_CLK_TCK'),
                    rss_bytes=int(fields[21])*os.sysconf('SC_PAGE_SIZE'))
            except (OSError,ValueError):return dict(status='unavailable')
        path=root/'controller-tabs.json';path.write_text(json.dumps(dict(schema_version=1,workspaces=dict(fixture=dict(
            kind='tmux',socket_path=str(root/'tmux.sock'),session_id='$0')))));path.chmod(0o600)
        connections=[];lock=threading.Lock(); methods={}
        states={f't{i}':dict(type='idle',activeFlags=[]) for i in range(100)}
        def handler(connection):
            with lock:connections.append(connection)
            try:
                for raw in connection:
                    value=json.loads(raw);method=value.get('method');methods[method]=methods.get(method,0)+1
                    if method=='initialized':continue
                    if method=='initialize':result=dict(codexHome=str(home),userAgent='qualification-metadata-fixture')
                    elif method=='thread/loaded/list':result=dict(data=list(states),nextCursor=None)
                    elif method=='thread/read':
                        thread_id=value['params']['threadId'];i=int(thread_id[1:])
                        result=dict(thread=dict(id=thread_id,name='fixture-thread-'+str(i),cwd=str(root),status=states[thread_id]))
                    else:
                        connection.send(json.dumps(dict(id=value.get('id'),error=dict(code=-32601,message='unsupported qualification method'))));continue
                    connection.send(json.dumps(dict(id=value['id'],result=result)))
            except Exception:pass
        native_path=home/'app-server-control/app-server-control.sock'
        endpoint='unix://'+str(native_path)
        receipt['fixture_setup_seconds']=time.monotonic()-start
        control_pids=set();latencies=[];monitor_pid=None
        components={}
        def sample():
            own=resource.getrusage(resource.RUSAGE_SELF);exited=resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu=0.0 if args.monitor else own.ru_utime+own.ru_stime+exited.ru_utime+exited.ru_stime
            components.clear();components.update(owner=0.,live=0.,reaped=0.)
            rss=0;stack=[monitor_pid if args.monitor else os.getpid()];seen=set()
            while stack:
                pid=stack.pop()
                if pid in seen:continue
                seen.add(pid)
                try:
                    fields=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
                    rss+=int(fields[21])*os.sysconf('SC_PAGE_SIZE')
                    if args.monitor:
                        components['owner' if pid==monitor_pid else 'live']+=sum(int(fields[i]) for i in (11,12))/os.sysconf('SC_CLK_TCK')
                        components['reaped']+=sum(int(fields[i]) for i in (13,14))/os.sysconf('SC_CLK_TCK')
                        cpu+=sum(int(fields[i]) for i in (11,12,13,14))/os.sysconf('SC_CLK_TCK')
                    elif pid!=os.getpid():cpu+=(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')
                    for task in Path('/proc',str(pid),'task').iterdir():
                        try:stack.extend(int(p) for p in (task/'children').read_text().split())
                        except OSError:pass
                except (OSError,ValueError):pass
            return cpu,rss
        def activity(value,thread_id):
            for row in value['resources']:
                for pane in row['traits']['panes']:
                    if (pane.get('binding') or {}).get('conversation_id')==thread_id:
                        return pane['traits']['activity']['value']
            return None
        server=None;observer=None;monitor=None;profile_process=None
        def cli(*parts):
            env=dict(os.environ,CODEX_HOME=str(home))
            if not args.diagnostic_source:env.pop('PYTHONPATH',None)
            result=subprocess.run([str(Path(sys.executable).parent/'codex-wake'),'--wake-root',str(root),*parts],env=env,cwd=root,text=True,capture_output=True,timeout=60)
            assert result.returncode==0,(parts,result.returncode,result.stdout,result.stderr)
            return result.stdout
        def track_controls(status):
            for row in [*status.get('sources',[]),*status.get('formatting_reads',[])]:
                if row.get('owned_pid'):control_pids.add(row['owned_pid'])
        def tick(**kwargs):
            if monitor:
                value=monitor.execute('tabs.monitor.status',{}).get('snapshot') or dict(resources=[])
                track_controls(value.get('observer',{}))
                return value
            value=observer.tick(**kwargs);track_controls(observer.status());return value
        def active_count(value):
            return sum(pane['traits']['activity']['value'] in ('running','waiting-for-input')
                       for row in value['resources'] for pane in row['traits']['panes'])
        def barrier(since_wall,required_active):
            until=time.monotonic()+30;qualified_at=None
            while True:
                report=monitor.execute('tabs.monitor.status',{})
                value=report.get('snapshot') or dict(resources=[])
                sources=value.get('observer',{}).get('sources',[])
                formatting=report['monitor'].get('last_formatting') or {}
                workspace=next((row for row in formatting.get('workspaces',[]) if row.get('workspace')=='fixture'),{})
                bound=sum(bool(p.get('binding')) for r in value['resources'] for p in r['traits']['panes'])
                qualified=(len(value['resources'])==100 and bound==100 and sources and
                    {'tmux','native'}<={row.get('source_kind') for row in sources} and
                    all(row.get('state')=={'tmux':'available','native':'connected'}.get(row.get('source_kind')) for row in sources) and
                    formatting.get('status')=='completed' and workspace.get('status')=='applied' and
                    not workspace.get('failures') and value.get('observed_at',0)>since_wall and active_count(value)==required_active)
                if qualified:
                    if qualified_at is not None and value['observed_at']>qualified_at:
                        return value,dict(boundary_at=since_wall,first_qualified_snapshot_at=qualified_at,
                            subsequent_snapshot_at=value['observed_at'],bound_panes=bound,active_turns=active_count(value),
                            formatting_status=workspace['status'],failures=workspace.get('failures',[]),
                            source_states=[dict(kind=row['source_kind'],state=row['state']) for row in sources])
                    qualified_at=value['observed_at'] if qualified_at is None else qualified_at
                assert time.monotonic()<until,('deterministic barrier failed',len(value['resources']),bound,
                    active_count(value),required_active,[dict(kind=row.get('source_kind'),state=row.get('state')) for row in sources],formatting)
                time.sleep(.05)
        try:
            with unix_serve(handler,path=str(native_path)) as server:
                worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
                owner_start=time.monotonic()
                if args.monitor:
                    from codex_wake.tab_monitor import TabMonitor
                    monitor=TabMonitor(root)
                    cli('tabs','monitor-start')
                    if args.monitor_profile or args.steady_profile_prefix:
                        assert args.diagnostic_profile,'profiling is diagnostics only'
                        monitor.execute('tabs.monitor.stop',dict(timeout=5))
                        env=dict(os.environ,CODEX_HOME=str(home))
                        if args.steady_profile_prefix:
                            wrapper="""import cProfile,signal,sys
from pathlib import Path
prefix=sys.argv[1]; phase=[0]; profiler=[None]
def begin(signum,frame):
    phase[0]+=1; profiler[0]=cProfile.Profile(); profiler[0].enable()
    Path(prefix+'.'+('idle' if phase[0]==1 else 'active')+'.started').write_text('started')
def end(signum,frame):
    profiler[0].disable()
    profiler[0].dump_stats(prefix+'.'+('idle' if phase[0]==1 else 'active')+'.prof')
signal.signal(signal.SIGUSR1,begin);signal.signal(signal.SIGUSR2,end)
from codex_wake.tab_monitor import main
main(['--serve',sys.argv[-1]])
"""
                            argv=[sys.executable,'-c',wrapper,args.steady_profile_prefix,'codex_wake.tab_monitor','--serve',str(root)]
                        else:
                            argv=[sys.executable,'-m','cProfile','-o',args.monitor_profile,'-m','codex_wake.tab_monitor','--serve',str(root)]
                        profile_process=subprocess.Popen(argv,env=env,cwd=root,stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                        until=time.monotonic()+5
                        while monitor.execute('tabs.monitor.status',{})['monitor']['status']!='running':
                            assert time.monotonic()<until;time.sleep(.05)
                    cli('tabs','format','configure','--workspace','fixture','--preset','slate')
                    cli('tabs','format','enable','--workspace','fixture')
                    enabled_at=time.time()
                    monitor_pid=monitor.execute('tabs.monitor.status',{})['monitor']['process']['pid']
                    value,receipt['startup_barrier']=barrier(enabled_at,0)
                    receipt['startup_barrier']['enable_returned_at']=enabled_at
                    receipt['measurement']='actual installed TabMonitor owner plus all current owned descendants and reaped child CPU via proc cutime/cstime; fixture/driver/workload processes excluded'
                    receipt['formatting_enabled']='slate100tabs; configured through installed CLI'
                else:
                    observer=TabObserver(root,native_endpoints=[endpoint])
                    value=tick(deadline=time.monotonic()+10)
                assert len(value['resources'])==100,len(value['resources'])
                bound=sum(bool(p.get('binding')) for r in value['resources'] for p in r['traits']['panes'])
                assert bound==100,('native bindings',bound)
                receipt['cold_start_seconds']=time.monotonic()-start
                receipt['owner_cold_start_seconds']=time.monotonic()-owner_start
                receipt['native_bound_panes']=bound
                track_controls(value.get('observer',{}) if monitor else observer.status())
                if monitor_pid:control_pids.add(monitor_pid)
                if args.diagnostic_profile:
                    if args.diagnostic_profile!='none':
                        import cProfile
                        profiler=cProfile.Profile();profiler.enable()
                    receipt['mode']='short diagnostic profile, not acceptance'
                for phase in ('idle','active'):
                    if phase=='active':
                        activation_start=time.monotonic();activation_cpu0,_=sample();activation_wall=time.time()
                        with lock:
                            for index in range(10):
                                thread_id='t'+str(index);states[thread_id]=dict(type='active',activeFlags=[])
                                message=json.dumps(dict(method='thread/status/changed',params=dict(threadId=thread_id,status=states[thread_id])))
                                for connection in list(connections):
                                    try:connection.send(message)
                                    except Exception:connections.remove(connection)
                        burst_sent=time.monotonic()
                        if monitor:
                            value,activation_barrier=barrier(activation_wall,10)
                        else:
                            until=time.monotonic()+3
                            while True:
                                value=tick()
                                if active_count(value)==10:break
                                assert time.monotonic()<until;time.sleep(.01)
                            activation_barrier=dict(active_turns=10)
                        activation_cpu1,_=sample()
                        receipt['active_activation']=dict(events=10,burst_send_seconds=burst_sent-activation_start,
                            total_wall_seconds=time.monotonic()-activation_start,cpu_seconds=activation_cpu1-activation_cpu0,
                            barrier=activation_barrier,excluded_from_ordinary_window=True)
                    if args.steady_profile_prefix:
                        import signal
                        from codex_wake.process import process_identity
                        expected=monitor.execute('tabs.monitor.status',{})['monitor']['process']
                        birth=process_identity(monitor_pid)
                        assert Path('/proc',str(monitor_pid)).stat().st_uid==os.geteuid()
                        assert birth and str(birth['start_time_ticks'])==str(expected['start_ticks']) and birth['boot_id']==expected['boot_id']
                        os.kill(monitor_pid,signal.SIGUSR1)
                        marker=Path(args.steady_profile_prefix+'.'+phase+'.started')
                        until=time.monotonic()+2
                        while not marker.exists():
                            assert time.monotonic()<until;time.sleep(.01)
                    fixture_tmux0=fixture_tmux_sample()
                    begin=time.monotonic();cpu0,_=sample();components0=dict(components);state_versions=set();state_max_bytes=0;observer_costs0=dict(value.get('observer',{}).get('costs',{}));self0=resource.getrusage(resource.RUSAGE_SELF);child0=resource.getrusage(resource.RUSAGE_CHILDREN);thread0=time.thread_time();maxrss=0;sequence=[0];pending={}
                    stopping=threading.Event()
                    def produce():
                        next_event=begin
                        while not stopping.is_set() and next_event<begin+args.seconds:
                            if stopping.wait(max(0,next_event-time.monotonic())):break
                            index=sequence[0]%10;thread_id='t'+str(index)
                            flags=[] if (sequence[0]//10)%2 else ['waitingOnUserInput']
                            status=dict(type='active',activeFlags=flags);states[thread_id]=status
                            message=json.dumps(dict(method='thread/status/changed',params=dict(threadId=thread_id,status=status)))
                            with lock:
                                for connection in list(connections):
                                    try:connection.send(message)
                                    except Exception:connections.remove(connection)
                                pending[thread_id]=(time.monotonic(),'waiting-for-input' if flags else 'running')
                            sequence[0]+=1;next_event+=.5
                    producer=threading.Thread(target=produce,daemon=True) if phase=='active' else None
                    if producer:producer.start()
                    def project_pending(value):
                        with lock:items=list(pending.items())
                        for thread_id,(sent,expected) in items:
                            if activity(value,thread_id)==expected:
                                latencies.append(time.monotonic()-sent)
                                with lock:
                                    if pending.get(thread_id)==(sent,expected):pending.pop(thread_id)
                    while time.monotonic()-begin<args.seconds:
                        current=time.monotonic()
                        value=tick()
                        assert len(value['resources'])==100
                        project_pending(value)
                        _,rss=sample();maxrss=max(maxrss,rss)
                        try:
                            info=(root/'tab-formatting/state.json').stat()
                            state_versions.add((info.st_ino,info.st_mtime_ns));state_max_bytes=max(state_max_bytes,info.st_size)
                        except OSError:pass
                        time.sleep(max(0,(args.poll_interval if monitor else args.tick_interval)-(time.monotonic()-current)))
                    stopping.set()
                    if producer:producer.join(2)
                    project_pending(tick())
                    cpu1,_=sample();components1=dict(components);wall=time.monotonic()-begin
                    self1=resource.getrusage(resource.RUSAGE_SELF);child1=resource.getrusage(resource.RUSAGE_CHILDREN)
                    own_delta=self1.ru_utime+self1.ru_stime-self0.ru_utime-self0.ru_stime
                    fixture_tmux1=fixture_tmux_sample()
                    main_delta=time.thread_time()-thread0
                    reaped_delta=child1.ru_utime+child1.ru_stime-child0.ru_utime-child0.ru_stime
                    receipt[phase]=dict(wall_seconds=wall,cpu_seconds=cpu1-cpu0,cpu_percent_one_core=100*(cpu1-cpu0)/wall,
                        max_aggregate_rss_bytes=maxrss,status_changes=sequence[0],unprojected_events=len(pending),
                        owner_cpu_seconds=components1['owner']-components0['owner'] if args.monitor else own_delta,main_thread_cpu_seconds=main_delta if not args.monitor else None,
                        non_main_threads_cpu_seconds=own_delta-main_delta if not args.monitor else None,
                        fixture_driver_cpu_seconds=own_delta if args.monitor else None,
                        fixture_driver_main_thread_cpu_seconds=main_delta if args.monitor else None,
                        fixture_native_and_driver_other_threads_cpu_seconds=own_delta-main_delta if args.monitor else None,
                        fixture_cpu_attribution_limit='native protocol server and producer share driver process; other-thread CPU cannot isolate server from workload producer',
                        fixture_tmux_server=dict(before=fixture_tmux0,after=fixture_tmux1,
                            cpu_seconds=fixture_tmux1['cpu_seconds']-fixture_tmux0['cpu_seconds']
                                if fixture_tmux0['status']==fixture_tmux1['status']=='qualified' else None,
                            excluded_from_observer_gate=True,
                            attribution='private tmux server own CPU; workload panes excluded; formatting/shared terminal service work not separable by client'),
                        reaped_child_cpu_seconds=components1['reaped']-components0['reaped'] if args.monitor else reaped_delta,
                        live_child_cpu_seconds=components1['live']-components0['live'] if args.monitor else (cpu1-cpu0)-own_delta-reaped_delta)
                    if args.steady_profile_prefix:
                        birth=process_identity(monitor_pid)
                        assert birth and str(birth['start_time_ticks'])==str(expected['start_ticks']) and birth['boot_id']==expected['boot_id']
                        os.kill(monitor_pid,signal.SIGUSR2)
                        result_path=Path(args.steady_profile_prefix+'.'+phase+'.prof')
                        until=time.monotonic()+2
                        while not result_path.exists():
                            assert time.monotonic()<until;time.sleep(.01)
                    until=time.monotonic()+2
                    while pending and time.monotonic()<until:
                        time.sleep(.05);project_pending(tick())
                    receipt[phase]['unprojected_events']=len(pending)
                    receipt[phase]['format_state_max_bytes']=state_max_bytes
                    receipt[phase]['format_state_versions_observed']=len(state_versions)
                    receipt[phase]['observer_costs_start']=observer_costs0
                    receipt[phase]['observer_costs_end']=dict(value.get('observer',{}).get('costs',{}))
                    receipt[phase]['counter_limit']='observer counters are last published values; state inode sampling is a lower bound on writes'
                    Path(args.receipt).write_text(json.dumps(receipt,indent=2)+'\n')
                if args.diagnostic_profile and args.diagnostic_profile!='none':
                    profiler.disable();profiler.dump_stats(args.diagnostic_profile)
                receipt['p95_send_to_projection_seconds']=sorted(latencies)[int(.95*(len(latencies)-1))] if latencies else None
                receipt['latency_samples']=len(latencies)
                receipt['checks']=(tick().get('observer',{}).get('checks',{}) if monitor else observer.status()['checks'])
                receipt['native_methods']=methods
                receipt['all_ordinary_events_projected']=len(latencies)==receipt['active']['status_changes'] and receipt['active']['unprojected_events']==0
                receipt['thresholds_pass']=not args.diagnostic_profile and receipt['all_ordinary_events_projected'] and receipt['idle']['cpu_percent_one_core']<=1 and receipt['active']['cpu_percent_one_core']<=5 and max(receipt[p]['max_aggregate_rss_bytes'] for p in ('idle','active'))<=256*1024*1024 and receipt['p95_send_to_projection_seconds'] is not None and receipt['p95_send_to_projection_seconds']<=2
                if observer:
                    observer.close();observer=None
                if monitor:
                    cli('tabs','monitor-stop')
                    cli('tabs','format','rollback','--workspace','fixture')
                    monitor=None
                if profile_process:profile_process.wait(timeout=5)
                server.shutdown();worker.join(2)
        finally:
            try:
                if observer:observer.close()
                if monitor:
                    try:cli('tabs','monitor-stop')
                    except Exception:
                        # Cleanup must survive a product CLI rendering failure.
                        monitor.execute('tabs.monitor.stop',dict(timeout=5))
                    monitor=None
                if profile_process:profile_process.wait(timeout=5)
            finally:
                subprocess.run([*tmux,'kill-server'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                receipt['owned_control_processes_remaining']=sum(Path('/proc',str(pid)).exists() for pid in control_pids)
                Path(args.receipt).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt.get(k) for k in ('source_commit','uid','tabs','cold_start_seconds','idle','active','p95_send_to_projection_seconds','thresholds_pass','owned_control_processes_remaining')},sort_keys=True))
    return 0 if receipt.get('thresholds_pass') and not receipt['owned_control_processes_remaining'] else 1


if __name__=='__main__':sys.exit(main())
