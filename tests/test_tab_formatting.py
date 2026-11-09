"""Formatting acceptance through the public controller on a disposable tmux."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
from codex_wake.controller_tabs import ControllerTabs


@unittest.skipUnless(shutil.which('tmux'), 'tmux unavailable')
class FormattingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.socket=str(self.root/'tmux.sock')
        self.tmux('new-session','-d','-s','fixture','-n','original name','sleep 120')
        self.addCleanup(lambda:self.tmux('kill-server',check=False))
        self.transport=TmuxAttachmentTransport(self.socket,'$0')
        self.tabs=ControllerTabs(self.root,workspaces={'work':dict(kind='tmux',transport=self.transport)},host='test',environment='local')

    def tmux(self,*args,check=True):
        return subprocess.run(['tmux','-S',self.socket,*args],capture_output=True,text=True,check=check,timeout=5).stdout

    def call(self,verb,**arguments):
        return self.tabs.execute('tabs.format.'+verb,dict(workspace='work',**arguments))

    def test_rollback_restores_explicit_and_inherited_originals_and_reenable_keeps_baseline(self):
        self.tmux('set-option','-w','-t','@0','window-status-format','original #W')
        self.tmux('set-option','-g','window-status-current-style','fg=yellow,bg=black')
        before=self.tmux('show-options','-w','-t','@0')
        self.assertEqual(self.call('enable')['status'],'applied')
        self.assertIn('SH',self.tmux('show-options','-w','-v','-t','@0','window-status-format'))
        self.assertEqual(self.call('rollback')['status'],'rolled_back')
        self.assertEqual(self.tmux('show-options','-w','-t','@0'),before)
        self.tmux('set-option','-w','-t','@0','window-status-format','intervening manual')
        self.call('reenable');self.call('rollback');self.call('rollback')
        self.assertEqual(self.tmux('show-options','-w','-t','@0'),before)
        self.assertEqual(self.tmux('display-message','-p','-t','@0','#{window_name}').strip(),'original name')

    def test_public_cli_and_mcp_contract_share_reversible_operations(self):
        from codex_wake.tab_contract import tool_specs
        from codex_wake.controller_http import TOOLS
        from codex_wake.mcp_server import SPECS
        config=self.root/'controller-tabs.json'
        config.write_text(json.dumps(dict(schema_version=1,workspaces={'work':dict(kind='tmux',socket_path=self.socket,session_id='$0')})))
        config.chmod(0o600)
        import sys
        for verb in ('enable','rollback','reenable'):
            tool='wake_tabs_format_'+verb
            self.assertIn(tool,tool_specs());self.assertIn(tool,TOOLS);self.assertIn(tool,SPECS)
            result=subprocess.run([sys.executable,'-m','codex_wake.entrypoint','--wake-root',str(self.root),'tabs','format',verb,'--workspace','work'],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout)['result']['operation']['result']['status'],'rolled_back' if verb=='rollback' else 'applied')

    def test_missing_baseline_and_failed_restoration_are_not_success(self):
        from codex_wake.managed_inventory import InventoryError
        with self.assertRaises(InventoryError) as error:self.call('rollback')
        self.assertEqual(error.exception.code,'baseline_missing')
        self.call('enable')
        original=self.transport.formatting
        def unavailable(action,arguments,deadline):
            if action=='write':raise OSError('terminal unavailable')
            return original(action,arguments,deadline)
        self.transport.formatting=unavailable
        self.assertEqual(self.call('rollback')['status'],'partial')
        self.transport.formatting=original
        self.assertEqual(self.call('rollback')['status'],'rolled_back')
        self.assertFalse(self.call('status')['record']['enabled'])
