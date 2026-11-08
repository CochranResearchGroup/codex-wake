import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


class LifecycleCLITests(unittest.TestCase):
    def test_ordinary_local_cli_creates_and_renames_without_grant_files(self):
        if not shutil.which('tmux'):self.skipTest('tmux unavailable')
        from codex_wake.cli import run
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);socket=root/'mux.sock'
            subprocess.run(['tmux','-S',str(socket),'new-session','-d','-s','fixture','-n','source','sleep 90'],check=True)
            self.addCleanup(subprocess.run,['tmux','-S',str(socket),'kill-server'],capture_output=True)
            env={'TMUX':str(socket)+',1,0','CODEX_WAKE_ROOT':str(root/'wake')}
            def cli(*args):
                output=io.StringIO()
                with patch.dict(os.environ,env), contextlib.redirect_stdout(output):code=run(['tabs',*args,'--json'])
                self.assertEqual(code,0,output.getvalue())
                return json.loads(output.getvalue())
            rows=cli('list')['resources'];workspace=next(r['target']['workspace'] for r in rows if r['window']['name']=='source')
            created=cli('create','--workspace',workspace,'--name','created','--cwd',directory)
            op=created['result']['operation'];self.assertEqual(op['execution'],'completed',created)
            window=op['result']['window']['window_id']
            cli('rename','--workspace',workspace,'--window',window,'--name','renamed')
            rows=cli('list')['resources']
            self.assertTrue(any(r['window']['name']=='renamed' for r in rows))
            self.assertFalse((root/'wake/controller-messaging.json').exists())
            from codex_wake.mcp_server import CommandRunner
            target=next(r['target'] for r in rows if r['target']['workspace']==workspace)
            payload=dict(workspace=workspace,window=window,name='native-mcp-renamed',expected_target=target)
            payload['_request']=dict(operation_id='native-rename',idempotency_key='native-rename',correlation_id='native-rename',binding='fixture',target=target)
            with patch.dict(os.environ,env):
                native,failed=CommandRunner(wake_root=root/'wake').call('wake_tabs_rename',payload)
            self.assertFalse(failed,native)
            self.assertEqual(native['result']['operation']['execution'],'completed',native)
