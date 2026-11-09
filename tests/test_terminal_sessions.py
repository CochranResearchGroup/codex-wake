"""Named terminal sessions through the public controller operation seam."""
import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_tabs import ControllerTabs


class TerminalSessionTests(unittest.TestCase):
    def test_empty_session_rename_retains_identity_and_retired_name_is_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            tabs=ControllerTabs(Path(d),workspaces={},host='test',environment='fixture')
            created=tabs.execute('tabs.session.create',{'name':'bots'})['session']
            self.assertEqual(created['state'],'empty')
            changed=tabs.execute('tabs.session.update',{'session':created['id'],'changes':{'name':'workers','labels':['automation']}})['session']
            self.assertEqual(changed['id'],created['id'])
            self.assertEqual(changed['name'],'workers')
            self.assertEqual(tabs.execute('tabs.session.list',{})['sessions'][0]['labels'],['automation'])
            tabs.execute('tabs.session.delete',{'session':created['id']})
            replacement=tabs.execute('tabs.session.create',{'name':'workers'})['session']
            self.assertNotEqual(replacement['id'],created['id'])

    def test_native_session_survives_owner_reopen_and_defaults_do_not_restart_tabs(self):
        import subprocess
        with tempfile.TemporaryDirectory(prefix='wake-p211-') as d:
            root=Path(d);tabs=ControllerTabs(root,workspaces={},host='test',environment='fixture')
            session=tabs.execute('tabs.session.create',{'name':'bots','start':True})['session']
            sock=str(root/'terminal-sessions/tmux.sock')
            def tmux(*a):return subprocess.check_output(['tmux','-S',sock,*a],text=True).strip()
            try:
                birth=tmux('list-panes','-a','-F','#{pane_id}:#{pane_pid}')
                changed=tabs.execute('tabs.session.update',{'session':session['id'],'changes':{'name':'workers','defaults':{'argv':['/bin/false']}}})['session']
                self.assertEqual(changed['name'],'workers')
                reopened=ControllerTabs(root,workspaces={},host='test',environment='fixture')
                actual=reopened.execute('tabs.session.show',{'session':'workers'})['session']
                self.assertEqual(actual['state'],'running')
                self.assertEqual(actual['id'],session['id'])
                self.assertEqual(tmux('list-panes','-a','-F','#{pane_id}:#{pane_pid}'),birth)
                with self.assertRaisesRegex(ValueError,'explicit drain'):
                    reopened.execute('tabs.session.delete',{'session':'workers'})
                tmux('kill-session','-t','workers')
                self.assertEqual(reopened.execute('tabs.session.show',{'session':'workers'})['session']['state'],'empty')
            finally:
                subprocess.run(['tmux','-S',sock,'kill-server'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

    def test_public_cli_journal_reuses_intent_without_duplicate_creation(self):
        from codex_wake.tab_commands import operator_execute
        with tempfile.TemporaryDirectory() as d:
            tabs=ControllerTabs(Path(d),workspaces={},host='test',environment='fixture')
            first=operator_execute('tabs.session.create',{'name':'bots'},d,owner=tabs,request_id='session-1')
            second=operator_execute('tabs.session.create',{'name':'bots'},d,owner=tabs,request_id='session-1')
            self.assertEqual(first['result']['operation']['result']['session']['id'],second['result']['operation']['result']['session']['id'])
            self.assertEqual(len(tabs.execute('tabs.session.list',{})['sessions']),1)

    def test_ensure_reuses_running_named_session_without_restarting_command(self):
        import subprocess
        with tempfile.TemporaryDirectory(prefix='wake-p211-') as d:
            tabs=ControllerTabs(Path(d),workspaces={},host='test',environment='fixture')
            first=tabs.execute('tabs.session.ensure',{'name':'bots','defaults':{'argv':['/bin/sh']}})
            sock=str(Path(d)/'terminal-sessions/tmux.sock')
            try:
                second=tabs.execute('tabs.session.ensure',{'name':'bots','defaults':{'argv':['/bin/false']}})
                self.assertTrue(second['reused'])
                self.assertEqual(first['session']['snapshot']['windows'],second['session']['snapshot']['windows'])
            finally:subprocess.run(['tmux','-S',sock,'kill-server'],capture_output=True)

    def test_unknown_native_launch_is_not_empty_or_deletable(self):
        import subprocess
        from unittest.mock import patch
        real_run=subprocess.run
        with tempfile.TemporaryDirectory(prefix='wake-p211-') as d:
            tabs=ControllerTabs(Path(d),workspaces={},host='test',environment='fixture')
            sock=str(Path(d)/'terminal-sessions/tmux.sock')
            def lost_reply(command,*a,**kw):
                value=real_run(command,*a,**kw)
                if 'new-session' in command:raise subprocess.TimeoutExpired(command,10)
                return value
            try:
                with patch('subprocess.run',side_effect=lost_reply):
                    with self.assertRaises(subprocess.TimeoutExpired):tabs.execute('tabs.session.create',{'name':'bots','start':True})
                session=tabs.execute('tabs.session.show',{'session':'bots'})['session']
                self.assertEqual(session['state'],'unavailable')
                with self.assertRaises(ValueError):tabs.execute('tabs.session.delete',{'session':'bots'})
            finally:real_run(['tmux','-S',sock,'kill-server'],capture_output=True)
