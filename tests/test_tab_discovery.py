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


class TabDiscoveryTests(unittest.TestCase):
    def test_no_root_public_list_discovers_current_owned_workspace(self):
        if not shutil.which('tmux'):
            self.skipTest('tmux unavailable')
        from codex_wake.cli import run
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            socket = base / 'tmux.sock'
            subprocess.run(['tmux','-S',str(socket),'new-session','-d','-s','fixture','-n','fixture','sleep 90'],check=True)
            self.addCleanup(subprocess.run,['tmux','-S',str(socket),'kill-server'],capture_output=True)
            output = io.StringIO()
            with patch.dict(os.environ, {'XDG_STATE_HOME': str(base/'state'), 'XDG_CONFIG_HOME':str(base/'config'),
                                         'CODEX_WAKE_ROOT':'', 'TMUX':str(socket)+',1,0'}), contextlib.redirect_stdout(output):
                code = run(['tabs','list','--json'])
            self.assertEqual(code,0,output.getvalue())
            rows = json.loads(output.getvalue())['resources']
            self.assertTrue(any(v['window']['name']=='fixture' for v in rows),'current owned workspace missing')

    def test_invalid_configuration_returns_actionable_public_error(self):
        from codex_wake.cli import run
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);p=base/'controller-tabs.json';p.write_text('{bad');p.chmod(0o600)
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                code=run(['--wake-root',directory,'tabs','list','--json'])
            self.assertEqual(code,2)
            result=json.loads(output.getvalue())
            self.assertEqual(result['error']['code'],'configuration_unavailable')
            self.assertIn('configuration',result['error']['message'])

    def test_unavailable_workspace_does_not_hide_available_peers(self):
        from codex_wake.controller_tabs import ControllerTabs
        from test_controller_tabs import Transport
        class Offline:
            def snapshot(self, deadline):
                raise TimeoutError('offline fixture')
        with tempfile.TemporaryDirectory() as directory:
            owner=ControllerTabs(directory,workspaces={
                'offline':dict(kind='psmux',transport=Offline()),
                'ready':dict(kind='psmux',transport=Transport())},host='h',environment='e')
            value=owner.execute('tabs.list',{})
            self.assertEqual(len(value['resources']),1)
            self.assertEqual(value['unavailable'][0]['workspace'],'offline')
