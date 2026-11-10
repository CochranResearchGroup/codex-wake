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
        before=physical();start=time.monotonic();cpu0=time.process_time();peak=0;counts=[]
        try:
            while time.monotonic()-start<args.seconds:
                value=observer.tick();counts.append(len(value['resources']))
                status=observer.status();updates=status['costs']['native_events']
                for source in status['sources']:
                    if source.get('owned_pid'):controls.add(source['owned_pid'])
                for row in value['resources']:
                    for pane in row['traits']['panes']:
                        if pane.get('binding'):observed.add(hashlib.sha256(str(pane['binding'].get('conversation_id')).encode()).hexdigest())
                        for process in pane.get('processes',[]):births[str(process['pid'])]=(str(process.get('start_ticks')),process.get('boot_id'))
                peak=max(peak,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
                time.sleep(.5)
            report.update(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu0,
                observed_tab_count=max(counts,default=0),min_observed_tab_count=min(counts,default=0),
                bound_conversation_count=len(observed),native_events_including_baselines=updates,
                native_status_transitions=transitions[0],
                native_source_count=len(observer.native),peak_owner_rss_bytes=peak,
                exact_pane_layout_unchanged=before==physical())
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
