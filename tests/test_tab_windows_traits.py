import os
import tempfile
import time
import unittest
from codex_wake.tab_traits import TabTraits


class WindowsTraitTests(unittest.TestCase):
    def test_windows_pid_is_never_interpreted_as_linux_process(self):
        with tempfile.TemporaryDirectory() as root:
            def linux_probe(pid,deadline):
                raise AssertionError('Windows PID crossed into Linux /proc')
            owner=TabTraits(root,process_probe=linux_probe)
            pane=dict(pane_id='%1',pid=os.getpid(),platform='windows',windows_creation_filetime=123,
                      windows_processes=[dict(pid=os.getpid(),creation_filetime=123,executable='C:\\bin\\codex.exe')],windows_processes_complete=True)
            result=owner.observe_window(dict(panes=[pane]),deadline=time.monotonic()+2)
            traits=result['panes'][0]['traits']
            self.assertEqual(traits['harness']['value'],'codex')
            self.assertEqual(traits['health']['value'],'unknown')
            self.assertEqual(traits['activity']['value'],'unknown')

    def test_wsl_relay_is_unknown_not_absent_coding_session(self):
        with tempfile.TemporaryDirectory() as root:
            row=dict(panes=[dict(pane_id='%1',pid=1,platform='windows',windows_processes_complete=True,
                                windows_processes=[dict(pid=1,creation_filetime=10,executable='C:\\Windows\\System32\\wsl.exe')])])
            traits=TabTraits(root).observe_window(row)['panes'][0]['traits']
            self.assertEqual(traits['session_presence']['value'],'unknown')
            self.assertEqual(traits['session_presence']['reason'],'remote_runtime_unverified')
