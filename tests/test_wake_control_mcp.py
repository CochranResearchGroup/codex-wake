import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from codex_wake.mcp_server import CommandRunner, SPECS

CALLER = '12345678-1234-1234-1234-123456789abc'

class WakeControlMCPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'wakes'
        self.root.mkdir()
        self.config = Path(self.temp.name) / 'grant.json'
        self.config.write_text(json.dumps({'version': 1, 'callers': {CALLER: {'roots': [str(self.root)], 'actions': ['list', 'cancel', 'pause', 'resume', 'pause-status', 'interrupt']}}}))

    def runner(self):
        return CommandRunner(cli='wake', wake_root=self.root, wake_control_config=self.config)

    @patch('codex_wake.mcp_server.subprocess.run')
    def test_denied_without_host_grant(self, run):
        value, failed = CommandRunner(wake_root=self.root).call('wake_pause', {'caller_thread_id': CALLER})
        self.assertTrue(failed)
        self.assertEqual(value['error']['code'], 'policy_denied')
        run.assert_not_called()

    @patch('codex_wake.mcp_server.subprocess.run')
    def test_bound_commands(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, '{"ok":true}')
        for tool, verb in [('wake_list','list'), ('wake_cancel','cancel'), ('wake_pause','pause'), ('wake_resume','resume'), ('wake_pause_status','pause-status'), ('wake_interrupt','interrupt')]:
            args = {'caller_thread_id': CALLER}
            if verb == 'cancel': args['all'] = True
            value, failed = self.runner().call(tool, args)
            self.assertFalse(failed)
            command = run.call_args.args[0]
            self.assertEqual(command[:4], ['wake','--wake-root',str(self.root),verb])
            self.assertEqual(command[command.index('--authorized-root') + 1], str(self.root))
            self.assertNotIn('--app-server', command)
            self.assertNotIn('--caller-thread-id', command)
            self.assertEqual(run.call_args.kwargs['env']['CODEX_THREAD_ID'], CALLER)

    @patch('codex_wake.mcp_server.subprocess.run')
    def test_denies_malformed_grants_and_path_override(self, run):
        self.config.write_text('{"version":true,"callers":{}}')
        self.assertTrue(self.runner().call('wake_pause', {'caller_thread_id':CALLER})[1])
        self.assertTrue(self.runner().call('wake_list', {'caller_thread_id':CALLER,'wake_root':'/else'})[1])
        run.assert_not_called()

    @patch('codex_wake.mcp_server.subprocess.run', side_effect=subprocess.TimeoutExpired('wake', 1))
    def test_timeout_effect_uncertainty(self, run):
        self.assertEqual(self.runner().call('wake_pause', {'caller_thread_id':CALLER})[0]['error']['code'], 'effect_uncertain')
        self.assertEqual(self.runner().call('wake_list', {'caller_thread_id':CALLER})[0]['error']['code'], 'operation_timeout')

    def test_schema(self):
        for name in ('wake_list','wake_cancel','wake_pause','wake_resume','wake_pause_status','wake_interrupt'):
            self.assertIn('caller_thread_id', SPECS[name][4])
            self.assertNotIn('registry_dir', SPECS[name][3])

    @patch('codex_wake.mcp_server.subprocess.run')
    def test_all_registered_roots_require_complete_grant(self, run):
        other = Path(self.temp.name) / 'other'
        registry = Path(self.temp.name) / 'registry'
        resolver = unittest.mock.Mock(return_value=[self.root, other])
        with patch.dict('sys.modules', {'codex_wake.wake_control': SimpleNamespace(select_roots=resolver)}):
            runner = self.runner()
            runner.wake_registry = registry
            value, failed = runner.call('wake_pause', {'caller_thread_id': CALLER, 'all_roots': True})
            self.assertTrue(failed)
            self.assertEqual(value['error']['code'], 'policy_denied')
            run.assert_not_called()
            resolver.assert_called_once_with(self.root, all_roots=True, registry_dir=registry)

    @patch('codex_wake.mcp_server.subprocess.run')
    def test_duplicate_config_keys_and_missing_identity_are_denied(self, run):
        self.config.write_text('{"version":1,"version":1,"callers":{}}')
        self.assertTrue(self.runner().call('wake_list', {'caller_thread_id':CALLER})[1])
        self.assertEqual(self.runner().call('wake_list', {})[0]['error']['code'], 'invalid_argument')
        run.assert_not_called()

    @patch('codex_wake.mcp_server.subprocess.run')
    def test_action_and_single_root_grants_are_enforced(self, run):
        self.config.write_text(json.dumps({'version':1,'callers':{CALLER:{'roots':[str(self.root)],'actions':['list']}}}))
        self.assertTrue(self.runner().call('wake_interrupt', {'caller_thread_id':CALLER})[1])
        runner = self.runner()
        runner.wake_root = self.root.parent
        self.assertTrue(runner.call('wake_list', {'caller_thread_id':CALLER})[1])
        run.assert_not_called()

    @patch('codex_wake.mcp_server.subprocess.run')
    def test_all_roots_freezes_selected_scope_for_cli_race_check(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, '{"ok":true}')
        other = Path(self.temp.name) / 'other'
        extra = Path(self.temp.name) / 'granted-but-not-registered'
        registry = Path(self.temp.name) / 'registry'
        self.config.write_text(json.dumps({'version':1,'callers':{CALLER:{'roots':[str(self.root),str(other),str(extra)],'actions':['pause']}}}))
        resolver = unittest.mock.Mock(return_value=[self.root,other])
        with patch.dict('sys.modules', {'codex_wake.wake_control': SimpleNamespace(select_roots=resolver)}):
            runner = self.runner()
            runner.wake_registry = registry
            self.assertFalse(runner.call('wake_pause', {'caller_thread_id':CALLER,'all_roots':True})[1])
        command = run.call_args.args[0]
        bound = [command[i + 1] for i, item in enumerate(command) if item == '--authorized-root']
        self.assertEqual(bound, [str(self.root),str(other)])
        self.assertNotIn(str(extra), command)
        self.assertIn('--all-roots', command)
        self.assertEqual(command[command.index('--registry-dir')+1], str(registry))
