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
