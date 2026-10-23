"""Provider-free readiness regression for the opt-in MR06 launcher."""
import subprocess
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from scripts.multiruntime_live_qualification import prepare_tmux

@unittest.skipUnless(shutil.which("tmux"), "tmux required for terminal startup evidence")
class StartupEvidenceTests(unittest.TestCase):
    def test_immediate_tui_exit_keeps_pane_and_original_error_without_model_calls(self):
        with tempfile.TemporaryDirectory(prefix='cw-mr06-harness-') as tmp:
            root=Path(tmp);socket=root/'tmux.sock'
            def tmux(*args):
                return subprocess.run(['tmux','-S',str(socket),*map(str,args)],capture_output=True,
                                      text=True,check=True,timeout=3).stdout
            try:
                pane=prepare_tmux(tmux,root,['sh','-c','echo CW_STARTUP_FAILURE; exit 7'])
                deadline=time.monotonic()+3
                while tmux('display-message','-p','-t',pane,'#{pane_dead}').strip()!='1':
                    if time.monotonic()>deadline:self.fail('fixture command did not exit')
                    time.sleep(.02)
                while True:
                    captured=tmux('capture-pane','-p','-S','-2000','-t',pane)
                    if 'CW_STARTUP_FAILURE' in captured:break
                    if time.monotonic()>deadline:self.fail('startup error was not retained: '+captured)
                    time.sleep(.02)
                self.assertIn('CW_STARTUP_FAILURE',captured)
                self.assertEqual(tmux('display-message','-p','-t',pane,'#{pane_dead_status}').strip(),'7')
            finally:
                subprocess.run(['tmux','-S',str(socket),'kill-server'],capture_output=True,timeout=3)
