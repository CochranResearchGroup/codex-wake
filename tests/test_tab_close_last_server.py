"""An acknowledged final close must verify removal even if tmux exits."""
import subprocess
import unittest
import test_tab_lifecycle as fixture


class LastServerCloseTests(unittest.TestCase):
    setUp=fixture.TabLifecycleTests.setUp
    tmux=fixture.TabLifecycleTests.tmux
    owner=fixture.TabLifecycleTests.owner

    def test_final_owned_window_close_reports_applied_after_server_exits(self):
        self.tmux('kill-session','-t','$1')
        owner=self.owner();before=owner.inspect('source')
        closed=owner.execute('tabs.close',dict(workspace='source',expected_target=before['target'],
            window=before['snapshot']['windows'][0]['window_id'],force=True))
        self.assertEqual(closed['status'],'applied')
        self.assertEqual(closed['workspace_state'],'removed')
        probe=subprocess.run(['tmux','-S',self.socket,'list-sessions'],capture_output=True)
        self.assertNotEqual(probe.returncode,0)
