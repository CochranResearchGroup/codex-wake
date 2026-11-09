import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from codex_wake.controller_tabs import ControllerTabs
from codex_wake.tab_commands import command
from codex_wake.terminal_session_cli import select_workspace


class SessionCliTests(unittest.TestCase):
    def test_readable_and_json_public_cli(self):
        with tempfile.TemporaryDirectory() as d:
            tabs=ControllerTabs(Path(d),workspaces={},host='test',environment='fixture')
            tabs.execute('tabs.session.create',{'name':'bots'})
            for structured in (False,True):
                out=io.StringIO()
                with contextlib.redirect_stdout(out):
                    status=command(SimpleNamespace(wake_root=d,tab_command='session-list',arguments={},as_json=structured),owner=tabs)
                self.assertEqual(status,0)
                self.assertIn('"sessions"' if structured else 'HEALTH / ACTIVITY',out.getvalue())
                self.assertIn('bots',out.getvalue())

    def test_exact_current_context_and_noninteractive_candidates(self):
        class Owner:
            def execute(self,*unused):
                return {'sessions':[dict(id='a',name='same',server='/tmp/a',backend='tmux',state='running',workspace='one',snapshot={'session_id':'$2'}),dict(id='b',name='same',server='/tmp/b',backend='tmux',state='running',workspace='two',snapshot={'session_id':'$2'})]}
        with patch.dict(os.environ,{'TMUX':'/tmp/b,123,2'}):
            self.assertEqual(select_workspace(Owner()),'two')
        with self.assertRaises(ValueError) as error:
            select_workspace(Owner(),'same',interactive=False)
        self.assertEqual(len(error.exception.candidates),2)
        self.assertEqual(select_workspace(Owner(),'same',server='/tmp/a'),'one')

    def test_generated_parser_exposes_session_alias(self):
        import argparse
        from codex_wake.tab_organization_commands import register_parser
        parser=argparse.ArgumentParser()
        register_parser(parser.add_subparsers(dest='command'))
        args=parser.parse_args(['tabs','show','--session','bots','--server','/tmp/private','--json'])
        self.assertEqual(args.session_selector,'bots')
        self.assertEqual(args.session_server,'/tmp/private')
        self.assertTrue(args.as_json)

    def test_current_context_from_real_private_tmux(self):
        import subprocess
        with tempfile.TemporaryDirectory(prefix='wake-532-context-') as d:
            tabs=ControllerTabs(Path(d),workspaces={},host='test',environment='fixture')
            record=tabs.execute('tabs.session.create',{'name':'current','start':True})['session']
            sock=record['server']
            try:
                tabs.execute('tabs.session.create',{'name':'other','start':True})
                native=record['snapshot']['session_id'].lstrip('$')
                with patch.dict(os.environ,{'TMUX':sock+',123,'+native}):
                    self.assertEqual(select_workspace(tabs),record['workspace'])
            finally:
                subprocess.run(['tmux','-S',sock,'kill-server'],capture_output=True)
