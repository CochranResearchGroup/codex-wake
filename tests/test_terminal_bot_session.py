"""Dedicated launch qualification uses only an owned inert sleep process."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_tabs import ControllerTabs
from codex_wake.tab_commands import operator_execute
from codex_wake.terminal_bot_session import ensure_bot_session


class BotSessionTests(unittest.TestCase):
    def test_public_ensure_reuses_process_and_preserves_default(self):
        with tempfile.TemporaryDirectory(prefix='wake-532-') as d:
            root=Path(d)
            tabs=ControllerTabs(root,workspaces={},host='test',environment='fixture')
            default=tabs.execute('tabs.session.create',{'name':'default','start':True})['session']
            sock=default['server']
            def panes():
                return subprocess.check_output(['tmux','-S',sock,'list-panes','-a','-F','#{session_name}:#{pane_id}:#{pane_pid}'],text=True)
            before=panes()
            def execute(op,args):return operator_execute(op,args,root,owner=tabs)
            try:
                first=ensure_bot_session(execute,argv=['/bin/sleep','300'],server=sock)
                birth=panes()
                second=ensure_bot_session(execute,argv=['/bin/false'],server=sock)
                self.assertEqual(panes(),birth)
                self.assertIn(before.strip(),birth)
                self.assertEqual(len(tabs.execute('tabs.session.list',{})['sessions']),2)
                self.assertEqual(first['status'],second['status'])
            finally:
                subprocess.run(['tmux','-S',sock,'kill-server'],capture_output=True)
