#!/usr/bin/env python3
"""Opt-in installed tmux clock/daemon-loss qualification in an owned namespace."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

from codex_wake.tab_monitor import TabMonitor


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='wake-format520-') as directory:
        root=Path(directory);socket=str(root/'tmux.sock')
        def tmux(*argv,check=True):
            return subprocess.run(['tmux','-S',socket,*argv],capture_output=True,text=True,check=check,timeout=5).stdout
        tmux('new-session','-d','-s','expiry','-n','preserved','exec sleep 90')
        monitor=TabMonitor(root);started=None
        try:
            config=root/'controller-tabs.json';config.write_text(json.dumps(dict(schema_version=1,workspaces=dict(work=dict(kind='tmux',socket_path=socket,session_id='$0')))));config.chmod(0o600)
            before=tmux('list-panes','-F','#{pane_id}:#{pane_pid}')
            started=monitor.execute('tabs.monitor.start',dict(interval=.5,probe_timeout=.8,cycle_timeout=2,stale_after=20))
            until=time.monotonic()+5
            while not tmux('show-options','-w','-v','-t','@0','window-status-format'):
                if time.monotonic()>=until:raise RuntimeError('automatic formatting unavailable')
                time.sleep(.02)
            pid=started['monitor']['process']['pid'];os.kill(pid,signal.SIGKILL)
            # Reap our owned monitor, then prove the backend's own clock still
            # changes the retained format. No Wake publisher or expiry job runs.
            os.waitpid(pid,0);began=time.monotonic()
            live=tmux('display-message','-p','-t','@0','#{E:window-status-format}')
            if 'STALE' in live:raise RuntimeError('initial display unexpectedly stale')
            until=began+25
            while True:
                rendered=tmux('display-message','-p','-t','@0','#{E:window-status-format}')
                if 'STALE' in rendered:break
                if time.monotonic()>=until:raise RuntimeError('native expiry failed after publisher loss')
                time.sleep(.1)
            elapsed=time.monotonic()-began
            assert 'colour238' in rendered and 'preserved' in rendered,rendered
            assert before==tmux('list-panes','-F','#{pane_id}:#{pane_pid}')
            from codex_wake.controller_tabs import controller_tabs_from_root
            rollback=controller_tabs_from_root(root).execute('tabs.format.rollback',dict(workspace='work'))
            assert rollback['status']=='rolled_back',rollback
            report=dict(status='PASS',tmux_version=subprocess.check_output(['tmux','-V'],text=True).strip(),
                monitor_pid=pid,monitor_dead=True,native_clock_expiry=True,stale_after_seconds=20,
                observed_expiry_after_monitor_death_seconds=round(elapsed,3),pane_process_preserved=True,
                original_options_restored=True,production_touched=False,external_inference=False,
                seam='native format expansion and option readback; attached screen rendering qualified separately')
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
        finally:
            if started:monitor.execute('tabs.monitor.stop',{})
            tmux('kill-server',check=False)


if __name__=='__main__':main()
