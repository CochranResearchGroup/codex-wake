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
        self.assertLessEqual(len(commands),6,commands)
        self.assertLessEqual(len(flushes),1)
        self.assertFalse(any('set-option' in command and '-w' in command for command in commands))
