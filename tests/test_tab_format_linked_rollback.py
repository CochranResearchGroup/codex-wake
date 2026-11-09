"""Rollback must not restore a window currently shared with another workspace."""
from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
from codex_wake.controller_tabs import ControllerTabs


@unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
class LinkedFormattingRollbackTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.socket=str(self.root/'owned.sock')
        self.tmux('new-session','-d','-s','a','-n','source','sleep 90')
        self.addCleanup(lambda:self.tmux('kill-server',check=False))
        self.tmux('new-window','-d','-t','a:','-n','ordinary','sleep 90')
        self.tmux('new-session','-d','-s','b','-n','anchor','sleep 90')
        self.transport=TmuxAttachmentTransport(self.socket,'$0')
        self.tabs=ControllerTabs(self.root,workspaces={'a':dict(kind='tmux',transport=self.transport)},
                                 host='fixture',environment='local')

    def tmux(self,*arguments,check=True):
        return subprocess.run(['tmux','-S',self.socket,*arguments],capture_output=True,
                              text=True,check=check,timeout=5).stdout

    def call(self,verb):
        return self.tabs.execute('tabs.format.'+verb,dict(workspace='a'))

    def verify_linked_hold_and_retry(self,verb):
        self.tmux('set-option','-w','-t','a:0','window-status-format','source original #W')
        self.tmux('set-option','-w','-t','a:1','window-status-format','ordinary original #W')
        originals={wid:self.tmux('show-options','-w','-t',wid) for wid in ('@0','@1')}
        session_original=self.tmux('show-options','-t','a')
        anchor=self.tmux('list-panes','-t','b:0','-F','#{window_id}:#{window_name}:#{pane_pid}')
        self.assertEqual(self.call('enable')['status'],'applied')
        baseline=deepcopy(self.call('status')['record']['windows']['@0']['original'])
        self.tmux('link-window','-s','a:0','-t','b:1')
        linked_before=self.tmux('show-options','-w','-t','b:1')
        linked_identity=self.tmux('list-panes','-t','b:1','-F','#{window_id}:#{window_name}:#{pane_pid}')

        result=self.call(verb)
        self.assertEqual(result['status'],'partial')
        self.assertIn(dict(window='@0',code='linked_window'),result['failures'])
        self.assertEqual(self.tmux('show-options','-w','-t','b:1'),linked_before)
        self.assertEqual(self.tmux('list-panes','-t','b:1','-F','#{window_id}:#{window_name}:#{pane_pid}'),linked_identity)
        self.assertEqual(self.tmux('list-panes','-t','b:0','-F','#{window_id}:#{window_name}:#{pane_pid}'),anchor)
        self.assertEqual(self.tmux('show-options','-w','-t','a:1'),originals['@1'])
        self.assertEqual(self.tmux('show-options','-t','a'),session_original)
        held=self.call('status')['record']
        self.assertFalse(held['enabled'])
        self.assertFalse(held['windows']['@0']['restored'])
        self.assertEqual(held['windows']['@0']['original'],baseline)

        self.tmux('unlink-window','-t','b:1')
        retried=self.call(verb)
        self.assertEqual(retried['status'],'reset' if verb=='reset' else 'rolled_back')
        self.assertEqual(retried['failures'],[])
        for wid,options in originals.items():self.assertEqual(self.tmux('show-options','-w','-t',wid),options)
        self.assertEqual(self.tmux('list-panes','-t','a:0','-F','#{window_id}:#{window_name}:#{pane_pid}'),linked_identity)
        self.assertEqual(self.tmux('list-panes','-t','b:0','-F','#{window_id}:#{window_name}:#{pane_pid}'),anchor)
        self.assertEqual(self.call('status')['record']['windows']['@0']['original'],baseline)

    def test_rollback_holds_currently_linked_window_and_retries_after_unlink(self):
        self.verify_linked_hold_and_retry('rollback')

    def test_reset_holds_currently_linked_window_and_retries_after_unlink(self):
        self.verify_linked_hold_and_retry('reset')
