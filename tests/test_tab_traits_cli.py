import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class TraitCLITests(unittest.TestCase):
    def test_public_cli_reports_current_error_independent_of_activity_and_health(self):
        if not shutil.which('tmux'):self.skipTest('tmux unavailable')
        from codex_wake.cli import run
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);socket=root/'mux.sock'
            subprocess.run(['tmux','-S',str(socket),'new-session','-d','-s','fixture','-n','error',
                            "printf 'Draft remains untouched\\nError: synthetic connection failure\\n'; sleep 90"],check=True)
            self.addCleanup(subprocess.run,['tmux','-S',str(socket),'kill-server'],capture_output=True)
            config=root/'controller-tabs.json'
            config.write_text(json.dumps(dict(schema_version=1,workspaces={'fixture':dict(kind='tmux',socket_path=str(socket),session_id='$0',evidence_scope='disposable_fixture',privacy='safe')})));config.chmod(0o600)
            # Synchronize by observable screen content rather than an arbitrary sleep.
            import time
            deadline=time.monotonic()+3
            while True:
                before=subprocess.check_output(['tmux','-S',str(socket),'capture-pane','-p','-t','%0'],text=True)
                if 'Error: synthetic' in before:break
                self.assertLess(time.monotonic(),deadline)
            output=io.StringIO()
            with contextlib.redirect_stdout(output):code=run(['--wake-root',directory,'tabs','list','--json'])
            self.assertEqual(code,0,output.getvalue())
            row=json.loads(output.getvalue())['resources'][0]
            traits=row['traits']['panes'][0]['traits']
            self.assertEqual(traits['error']['value'],'present')
            self.assertEqual(traits['activity']['value'],'unknown')
            self.assertEqual(traits['health']['value'],'unknown')
            self.assertEqual(subprocess.check_output(['tmux','-S',str(socket),'capture-pane','-p','-t','%0'],text=True),before)
