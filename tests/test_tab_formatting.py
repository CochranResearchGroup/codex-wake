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

    def test_enable_after_server_restart_preserves_old_baseline_and_new_rollback(self):
        self.tmux('set-option','-w','-t','@0','window-status-format','before reboot #W')
        self.call('enable')
        old=self.call('status')['record']
        self.tmux('kill-server')
        self.socket=str(self.root/'restarted.sock')
        self.tmux('new-session','-d','-s','fixture','-n','after reboot','sleep 120')
        self.transport=TmuxAttachmentTransport(self.socket,'$0')
        self.tabs.workspaces['work']['transport']=self.transport
        self.tmux('set-option','-w','-t','@0','window-status-format','after reboot #W')
        before=self.tmux('show-options','-w','-t','@0')
        panes=self.tmux('list-panes','-F','#{pane_id}:#{pane_pid}')
        self.assertEqual(self.call('enable')['status'],'applied')
        self.assertIn('SH',self.tmux('show-options','-w','-v','-t','@0','window-status-format'))
        state=json.loads((self.root/'tab-formatting'/'state.json').read_text())
        self.assertEqual(state['retired_workspaces']['work'][old['identity']],old)
        self.assertEqual(self.call('rollback')['status'],'rolled_back')
        self.assertEqual(self.tmux('show-options','-w','-t','@0'),before)
        self.assertEqual(self.tmux('list-panes','-F','#{pane_id}:#{pane_pid}'),panes)

    def test_changed_namespace_is_inspectable_but_refresh_and_old_intent_are_fenced(self):
        from codex_wake.managed_inventory import InventoryError
        from codex_wake.tab_format_monitor import refresh_formatting
        self.call('enable')
        pin=self.tabs.format_target(workspace='work')
        path=self.root/'tab-formatting'/'state.json'
        original=path.read_bytes()
        self.tmux('new-session','-d','-s','replacement','sleep 120')
        self.tabs.workspaces['work']['transport']=TmuxAttachmentTransport(self.socket,'$1')
        for verb in ('status','inspect'):
            inspected=self.call(verb)
            self.assertEqual(inspected['status'],'stale_target')
            self.assertFalse(inspected['namespace_matches'])
        for verb in ('rollback','resume','reenable','reset','pause'):
            with self.assertRaises(InventoryError) as error:self.call(verb)
            self.assertEqual(error.exception.code,'stale_target')
        result=refresh_formatting(self.root,self.tabs.execute('tabs.list',{}),tabs=self.tabs)
        self.assertEqual(result['workspaces'][0]['code'],'stale_target')
        with self.assertRaises(InventoryError) as error:self.call('enable',expected_target=pin)
        self.assertEqual(error.exception.code,'stale_target')
        self.assertEqual(path.read_bytes(),original)
        self.assertEqual(self.tmux('show-options','-w','-v','-t','@1','window-status-format'),'')

    def test_returning_namespace_reuses_originals_and_retired_alias_is_fenced(self):
        from codex_wake.managed_inventory import InventoryError
        self.tmux('set-option','-w','-t','@0','window-status-format','original namespace #W')
        before=self.tmux('show-options','-w','-t','@0')
        self.call('enable')
        old_transport=self.transport
        self.tmux('new-session','-d','-s','replacement','sleep 120')
        self.tabs.workspaces['work']['transport']=TmuxAttachmentTransport(self.socket,'$1')
        self.call('enable')
        self.tabs.workspaces['alias']=dict(kind='tmux',transport=old_transport)
        with self.assertRaises(InventoryError) as error:
            self.tabs.execute('tabs.format.enable',dict(workspace='alias'))
        self.assertEqual(error.exception.code,'formatting_custody_conflict')
        del self.tabs.workspaces['alias']
        self.tabs.workspaces['work']['transport']=old_transport
        self.assertEqual(self.call('enable')['status'],'applied')
        self.assertEqual(self.call('rollback')['status'],'rolled_back')
        self.assertEqual(self.tmux('show-options','-w','-t','@0'),before)

    def test_public_cli_and_mcp_contract_share_reversible_operations(self):
        from codex_wake.tab_contract import tool_specs
        from codex_wake.controller_http import TOOLS
        from codex_wake.mcp_server import SPECS
        config=self.root/'controller-tabs.json'
        config.write_text(json.dumps(dict(schema_version=1,workspaces={'work':dict(kind='tmux',socket_path=self.socket,session_id='$0')})))
        config.chmod(0o600)
        import sys
        from codex_wake.tab_monitor import TabMonitor
        self.addCleanup(lambda:TabMonitor(self.root).execute('tabs.monitor.stop',{}))
        for verb in ('enable','rollback','reenable'):
            tool='wake_tabs_format_'+verb
            self.assertIn(tool,tool_specs());self.assertIn(tool,TOOLS);self.assertIn(tool,SPECS)
            result=subprocess.run([sys.executable,'-m','codex_wake.entrypoint','--wake-root',str(self.root),'tabs','format',verb,'--workspace','work','--json'],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout)['result']['operation']['result']['status'],'rolled_back' if verb=='rollback' else 'applied')

    def test_changing_pane_titles_do_not_block_journaled_formatting_but_birth_changes_do(self):
        from codex_wake.tab_commands import operator_execute
        from codex_wake.managed_inventory import InventoryError
        class LiveTitles(TmuxAttachmentTransport):
            counter = 0
            def snapshot(self, deadline):
                self.counter += 1
                self.command(deadline, 'select-pane', '-t', '%0', '-T', 'turn '+str(self.counter))
                return super().snapshot(deadline)
        self.tabs.workspaces['work']['transport'] = LiveTitles(self.socket, '$0')
        for verb, wanted in [('enable','applied'), ('rollback','rolled_back'), ('reenable','applied')]:
            value = operator_execute('tabs.format.'+verb, dict(workspace='work'), self.root, owner=self.tabs)
            operation = value['result']['operation']
            self.assertEqual(operation['execution'], 'completed', operation)
            self.assertEqual(operation['result']['status'], wanted)
        pinned = self.tabs.format_target(workspace='work')
        self.tmux('respawn-pane', '-k', '-t', '%0', 'sleep 120')
        with self.assertRaises(InventoryError) as error:
            self.call('rollback', expected_target=pinned)
        self.assertEqual(error.exception.code, 'stale_target')
        self.assertTrue(self.call('status')['record']['enabled'])

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
