#!/usr/bin/env python3
"""Bounded existing-host metadata-only observation; never starts live monitor."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import tempfile
import time


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',required=True);parser.add_argument('--seconds',type=float,default=20);args=parser.parse_args()
    assert not Path(args.receipt).exists(),'use a unique receipt path'
    import codex_wake
    from codex_wake.shortcut_store import default_root
    from codex_wake.tab_observer import TabObserver
    assert 'site-packages' in codex_wake.__file__
    existing=default_root();controls=set();births={};observed=set();updates=0;transitions=[0]
    report=dict(package=codex_wake.__file__,uid=os.geteuid(),scope='existing host metadata and passive native status only',
        health_requests=False,screen_captures=False,provider_requests=False,live_monitor_activation=False,
        production_configuration_changes=False,qualification_limit='read-only live tiers differ from default because live health/capture forbidden')
    with tempfile.TemporaryDirectory(prefix='wake547-live-') as directory:
        root=Path(directory)
        for name in ('controller-tabs.json','controller-accounts.toml'):
            if (existing/name).is_file():shutil.copyfile(existing/name,root/name);(root/name).chmod(0o600)
        from codex_wake.tab_native_feed import NativeStatusFeed
        class CountedFeed(NativeStatusFeed):
            def poll(self,timeout=0.0):
                events=super().poll(timeout)
                transitions[0]+=sum(event['kind']=='update' for event in events)
                return events
        observer=TabObserver(root,settings=dict(health=False,errors=False),native_feed_factory=CountedFeed)
        def physical():
            values=[]
            for config in observer.owner.workspaces.values():
                if config['kind'] in ('tmux','byobu'):
                    result=subprocess.check_output(['tmux','-S',config['socket_path'],'list-panes','-s','-t',config['session_id'],
                        '-F','#{session_id}\t#{window_id}\t#{pane_id}\t#{pane_pid}\t#{window_layout}'],text=True)
                    values.append(result)
            return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()
        def sample_owned_tree():
            stack=[os.getpid()];seen=set();cpu=0.;rss=0
            while stack:
                pid=stack.pop()
                if pid in seen:continue
                seen.add(pid)
                try:
                    fields=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
                    cpu+=sum(int(fields[i]) for i in (11,12,13,14))/os.sysconf('SC_CLK_TCK')
                    rss+=int(fields[21])*os.sysconf('SC_PAGE_SIZE')
                    for task in Path('/proc',str(pid),'task').iterdir():
                        try:stack.extend(int(child) for child in (task/'children').read_text().split())
                        except OSError:pass
                except (OSError,ValueError):pass
            return cpu,rss
        before=physical();start=time.monotonic();cpu0=time.process_time();tree_cpu0,_=sample_owned_tree();peak=0;tree_peak=0;counts=[];formatting_read_done=False
        report['formatting_read_probe']=dict(workspaces=0,windows_attempted=0,windows_read=0,failures=[])
        def track_controls(status):
            for source in [*status.get('sources',[]),*status.get('formatting_reads',[])]:
                if source.get('owned_pid'):controls.add(source['owned_pid'])
        try:
            while time.monotonic()-start<args.seconds:
                value=observer.tick();counts.append(len(value['resources']))
                if not formatting_read_done:
                    probe=report['formatting_read_probe']
                    for name,config in observer.owner.workspaces.items():
                        if config['kind'] not in ('tmux','byobu'):continue
                        windows=list(dict.fromkeys(row['window']['window_id'] for row in value['resources']
                            if row['target']['workspace']==name))[:2]
                        if not windows:continue
                        probe['workspaces']+=1
                        for window in windows:
                            probe['windows_attempted']+=1
                            try:
                                config['transport'].formatting('read',{'window':window},time.monotonic()+2)
                                probe['windows_read']+=1
                            except Exception as error:
                                probe['failures'].append(dict(code=getattr(error,'code','formatting_read_failed')))
                    formatting_read_done=True
                status=observer.status();updates=status['costs']['native_events'];track_controls(status)
                for row in value['resources']:
                    for pane in row['traits']['panes']:
                        if pane.get('binding'):observed.add(hashlib.sha256(str(pane['binding'].get('conversation_id')).encode()).hexdigest())
                        for process in pane.get('processes',[]):births[str(process['pid'])]=(str(process.get('start_ticks')),process.get('boot_id'))
                peak=max(peak,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
                _,tree_rss=sample_owned_tree();tree_peak=max(tree_peak,tree_rss)
                time.sleep(.5)
            tree_cpu1,_=sample_owned_tree()
            report.update(aggregate_owned_cpu_seconds=tree_cpu1-tree_cpu0,peak_aggregate_owned_rss_bytes=tree_peak,
                measurement='owner and recursive owned children across all threads, including reaped child CPU; shared WSL kernel',
                wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu0,
                observed_tab_count=max(counts,default=0),min_observed_tab_count=min(counts,default=0),
                bound_conversation_count=len(observed),native_events_including_baselines=updates,
                native_status_transitions=transitions[0],
                native_source_count=len(observer.native),peak_owner_rss_bytes=peak,
                exact_pane_layout_unchanged=before==physical())
            report['formatting_read_states']=[{key:row.get(key) for key in ('state','owned_pid','requests','failures','read_only')}
                for row in observer.status().get('formatting_reads',[])]
            probe=report['formatting_read_probe'];readers=[row for row in report['formatting_read_states'] if row.get('requests',0)]
            probe['qualified']=bool(probe['windows_attempted'] and not probe['failures'] and
                probe['windows_attempted']==probe['windows_read'] and len(readers)==probe['workspaces'] and
                sum(row.get('requests',0) for row in readers)>=probe['windows_read'] and
                all(row.get('read_only') and row.get('state')=='connected' and row.get('owned_pid') for row in readers))
            report['owned_control_pids']=sorted(controls)
            report['source_states']=[dict(kind=s.get('source_kind'),state=s.get('state'),reason=s.get('reason')) for s in observer.status()['sources']]
        finally:observer.close()
        report['owned_controls_remaining']=sum(Path('/proc',str(pid)).exists() for pid in controls)
        unchanged=0;gone=0
        from codex_wake.process import process_identity
        for pid,birth in births.items():
            value=process_identity(int(pid))
            if value is None:gone+=1
            elif (str(value['start_time_ticks']),value.get('boot_id'))==birth:unchanged+=1
        report['observed_process_births_unchanged']=unchanged;report['observed_processes_gone']=gone
    Path(args.receipt).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main()
