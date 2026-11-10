"""Native process budget protects formatting throughput on ordinary large sessions."""
import subprocess
from unittest.mock import patch
from test_tab_formatting import FormattingTests


class FormattingProcessBudgetTests(FormattingTests):
    def test_format_and_rollback_avoid_per_option_native_processes(self):
        for i in range(5):self.tmux('new-window','-d','-t','fixture:','sleep 120')
        self.tmux('set-option','-w','-t','@0','window-status-format','line one\nline two; literal #W')
        before=self.tmux('show-options','-w','-t','@0')
        original=subprocess.run;commands=[]
        from codex_wake.tab_formatting import TabFormatting
        saved=TabFormatting.save;save_count=[]
        def persist(owner,state):save_count.append(1);return saved(owner,state)
        def counted(*a,**k):commands.append(a[0]);return original(*a,**k)
        with patch('subprocess.run',side_effect=counted), patch.object(TabFormatting,'save',persist):
            self.assertEqual(self.call('enable')['status'],'applied')
            self.assertEqual(self.call('rollback')['status'],'rolled_back')
        self.assertLess(len(commands),110)
        self.assertLessEqual(len(save_count),9)
        self.assertEqual(self.tmux('show-options','-w','-t','@0'),before)

    def test_recreated_monitor_owner_renews_with_bounded_native_and_durable_io(self):
        import os
        from codex_wake.tab_format_monitor import refresh_formatting
        observed=self.tabs.execute('tabs.list',{})
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        from codex_wake.controller_tabs import ControllerTabs
        restored=ControllerTabs(self.root,workspaces=self.tabs.workspaces,host=self.tabs.host,environment=self.tabs.environment)
        commands=[];flushes=[]
        original_run=subprocess.run;original_sync=os.fsync
        def counted(*args,**kwargs):
            commands.append(args[0]);return original_run(*args,**kwargs)
        def synced(fd):
            flushes.append(fd);return original_sync(fd)
        with patch('subprocess.run',side_effect=counted),patch('os.fsync',side_effect=synced):
            result=refresh_formatting(self.root,observed,tabs=restored)
        self.assertEqual(result['status'],'completed')
        self.assertLessEqual(len(commands),6)
        self.assertLessEqual(len(flushes),1)
        self.assertFalse(any('set-option' in command and '-w' in command for command in commands))

    def test_two_dirty_windows_share_native_batches_and_keep_current_lease(self):
        from pathlib import Path
        from types import SimpleNamespace
        import time
        from codex_wake.tab_format_monitor import refresh_formatting
        for _ in range(3):self.tmux('new-window','-d','-t','fixture:','exec sleep 90')
        observed=dict(self.tabs.execute('tabs.list',{}),origin='daemon',projection_revision='first')
        wall=time.time()
        def trait(value):return dict(value=value,status='observed',observed_at=wall,source_available=True)
        for resource in observed['resources']:
            resource.update(projection_revision=resource['window']['window_id']+'-idle',evidence_revision='initial')
            resource['traits']=dict(panes=[dict(pane_id=resource['window']['panes'][0]['pane_id'],traits=dict(
                harness=trait('codex'),build=trait('stock'),activity=trait('idle')))])
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        lease=self.tmux('show-options','-v','-t','$0','@wake-format-clock')
        changed=dict(observed,projection_revision='second')
        for resource in changed['resources'][:2]:
            resource['projection_revision']=resource['window']['window_id']+'-running'
            resource['traits']['panes'][0]['traits']['activity']=trait('running')
        import os
        commands=[];stat_pids=[];flushes=[];run=subprocess.run;read_text=Path.read_text;sync=os.fsync
        def synced(fd):flushes.append(fd);return sync(fd)
        def counted(*args,**kwargs):commands.append(args[0]);return run(*args,**kwargs)
        def read(path,*args,**kwargs):
            if path.parent.parent==Path('/proc') and path.name=='stat':stat_pids.append(int(path.parent.name))
            return read_text(path,*args,**kwargs)
        clock=SimpleNamespace(time=lambda:wall+2,monotonic=time.monotonic,sleep=time.sleep)
        with patch('subprocess.run',side_effect=counted),patch.object(Path,'read_text',read),patch('codex_wake.tab_formatting.time',clock),patch('os.fsync',side_effect=synced):
            report=refresh_formatting(self.root,changed,tabs=self.tabs)
        self.assertEqual(report['status'],'completed')
        self.assertLessEqual(len(flushes),1,'Existing durable originals need only the final checkpoint.')
        native_reads_and_writes=[c for c in commands if any(v in c for v in ('show-options','set-option'))]
        self.assertLessEqual(len(native_reads_and_writes),2,'Session custody and dirty window reads share one native client.')
        self.assertLessEqual(len(commands),5)
        self.assertEqual(set(stat_pids),{r['window']['panes'][0]['pid'] for r in changed['resources'][:2]})
        self.assertEqual(self.tmux('show-options','-v','-t','$0','@wake-format-clock'),lease)
        for resource in changed['resources'][:2]:
            rendered=self.tmux('display-message','-p','-t',resource['window']['window_id'],'#{E:window-status-format}')
            self.assertIn('RUN',rendered)
        self.assertEqual(self.call('rollback')['status'],'rolled_back')
