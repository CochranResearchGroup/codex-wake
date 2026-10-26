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

    def test_agent_can_inspect_due_time_and_cancel_its_future_wake_with_host_scope(self):
        import sys
        runner = CommandRunner(wake_root=self.root, wake_control_config=self.config)
        context = dict(threadId=CALLER, sessionId=CALLER, callId='fixture-native',
            **{'x-codex-turn-metadata':dict(thread_id=CALLER, session_id=CALLER, turn_id='fixture-turn')})
        clock = dict(utc=dict(status='network', sources=['a', 'b'], lower=1893456000, upper=1893456000.2), counter=None)
        with patch('codex_wake.app_server.resolve_codex_cmd', return_value=sys.executable), patch(
                'codex_wake.native_clock.snapshot', return_value=clock):
            made, failed = runner.call('wake_native_after', dict(caller_thread_id=CALLER,
                trigger='3650d', ttl='24h', prompt='Read-only review', idempotency_key='inspect-future',
                wake_lifetime='persistent'), native_context=context)
        self.assertFalse(failed, made)
        listed, failed = runner.call('wake_list', dict(caller_thread_id=CALLER))
        self.assertFalse(failed, listed)
        wake, = listed['roots'][0]['wakes']
        self.assertEqual(wake.get('due_at'), made['due_at'])
        self.assertEqual(wake['expires_at'], made['expires_at'])
        cancelled, failed = runner.call('wake_cancel', dict(caller_thread_id=CALLER, wake_id=made['id']))
        self.assertFalse(failed, cancelled)
        self.assertEqual(cancelled['roots'][0]['results'], [dict(wake_id=made['id'], state='cancelled')])

    def test_verified_self_controls_do_not_need_per_thread_grants_or_reach_peer_wakes(self):
        import sys
        from codex_wake.records import find_record
        peer = '22345678-1234-1234-1234-123456789abc'
        from codex_wake.session_permissions import PermissionStore, Principal
        self.root.chmod(0o700)
        PermissionStore(self.root).configure({'version': 1}, Principal('fixture-operator', 'operator'), expected_revision=0)
        runner = CommandRunner(wake_root=self.root, wake_control_config=self.config)
        self.config.write_text(json.dumps(dict(version=2, callers={}, native_self=dict(
            roots=[str(self.root)], actions=['list', 'cancel']))))
        self.config.chmod(0o600)
        clock = dict(utc=dict(status='network', sources=['a', 'b'], lower=1893456000, upper=1893456000.2), counter=None)
        def context(caller):
            return dict(threadId=caller, sessionId=caller, callId='fixture-native',
                **{'x-codex-turn-metadata':dict(thread_id=caller, session_id=caller, turn_id='fixture-turn')})
        made = {}
        with patch('codex_wake.app_server.resolve_codex_cmd', return_value=sys.executable), patch(
                'codex_wake.native_clock.snapshot', return_value=clock):
            for caller in (CALLER, peer):
                value, failed = runner.call('wake_native_after', dict(caller_thread_id=caller,
                    trigger='24h', prompt='Read-only review', idempotency_key='owned-' + caller,
                    wake_lifetime='persistent'), native_context=context(caller))
                self.assertFalse(failed, value)
                made[caller] = value['id']
        listed, failed = runner.call('wake_list', dict(caller_thread_id=CALLER), native_context=context(CALLER))
        self.assertFalse(failed, listed)
        self.assertEqual([w['wake_id'] for w in listed['roots'][0]['wakes']], [made[CALLER]])
        self.assertTrue(runner.call('wake_list', dict(caller_thread_id=CALLER))[1])
        self.assertTrue(runner.call('wake_pause', dict(caller_thread_id=CALLER), native_context=context(CALLER))[1])
        self.assertTrue(runner.call('wake_list', dict(caller_thread_id=peer), native_context=context(CALLER))[1])
        self.assertTrue(runner.call('wake_list', dict(caller_thread_id=CALLER, all_roots=True), native_context=context(CALLER))[1])
        self.assertTrue(runner.call('wake_cancel', dict(caller_thread_id=CALLER, wake_id=made[peer]), native_context=context(CALLER))[1])
        self.assertEqual(find_record(self.root, made[peer]).record['status'], 'pending')
        cancelled, failed = runner.call('wake_cancel', dict(caller_thread_id=CALLER, all=True), native_context=context(CALLER))
        self.assertFalse(failed, cancelled)
        self.assertEqual(find_record(self.root, made[CALLER]).record['status'], 'cancelled')
