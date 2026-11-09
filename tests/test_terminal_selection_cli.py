"""Ordinary relocation selectors resolve through the real CLI and native inventory."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class SelectionCLITests(unittest.TestCase):
    def test_named_source_tab_flag_freezes_only_that_tab(self):
        with tempfile.TemporaryDirectory(prefix='wake-p211-cli-') as d:
            root=Path(d);sock=str(root/'mux.sock')
            def tmux(*a):return subprocess.check_output(['tmux','-S',sock,*a],text=True).strip()
            tmux('new-session','-d','-s','default','sleep 60');tmux('new-window','-d','-n','other','sleep 60');tmux('new-session','-d','-s','bots','sleep 60')
            try:
                config=root/'controller-tabs.json';config.write_text(json.dumps({'schema_version':1,'workspaces':{name:dict(kind='tmux',socket_path=sock,session_id=sid) for name,sid in [('default','$0'),('bots','$1')]}}));config.chmod(0o600)
                run=subprocess.run([sys.executable,'-m','codex_wake','--wake-root',d,'tabs','relocate','preview','--destination','bots','--tab','default:@0','--json'],capture_output=True,text=True,env=dict(os.environ,PYTHONPATH='src'),timeout=15)
                self.assertEqual(run.returncode,0,run.stderr)
                result=json.loads(run.stdout)['result']['operation']['result']
                self.assertEqual(len(result['outcomes']),1)
                self.assertEqual(result['outcomes'][0]['birth']['window_id'],'@0')
            finally:subprocess.run(['tmux','-S',sock,'kill-server'],capture_output=True)
