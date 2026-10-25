"""Disposable top-level attention CLI and native MCP integration."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from codex_wake.a2a_bus import BusStore
from codex_wake.cli import run
from codex_wake.mcp_server import CommandRunner, SPECS


class FrontierAttentionCallersTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        env = patch.dict(os.environ, {
            'XDG_STATE_HOME': str(self.root / 'state-home'),
            'XDG_CONFIG_HOME': str(self.root / 'config-home'),
            'XDG_CACHE_HOME': str(self.root / 'cache-home'),
            'XDG_RUNTIME_DIR': str(self.root / 'runtime'),
        })
        env.start()
        self.addCleanup(env.stop)
        self.wake = self.root / 'wake'
        self.caller = '00000000-0000-7000-8000-000000000339'

    def packet(self, owner):
        return dict(key='attention-integration', kind='decision', question='Continue exact operation?',
            options=['accept', 'decline'], evidence=['receipt:integration'], priority='normal',
            expires_at=time.time() + 300, permission_decision=False,
            context=dict(owner=owner, operation_id='integration-operation', attempt=1,
                task_id='integration-task', allocation_id='original-allocation', runtime='codex',
                conversation_id=owner, account='account-one', target=owner, action='refresh.self',
                effect_scope='connection', policy_root=str(self.wake), policy_revision=1,
                operation_state='blocked'))

    def native(self, caller=None):
        caller = caller or self.caller
        return dict(threadId=caller, sessionId=caller, callId='integration-call', **{
            'x-codex-turn-metadata': dict(thread_id=caller, session_id=caller, turn_id='integration-turn')})

    def test_top_level_cli_operator_request_inspect_response_and_no_unvalidated_consumption(self):
        bus, capability = BusStore.configure(self.root / 'bus')
        packet = self.root / 'request.json'
        packet.write_text(json.dumps(self.packet('local-operator')))
        auth = ['--bus-root', str(bus.root), '--operator-capability', str(capability)]

        def cli(words, expected=0):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = run(['--wake-root', str(self.wake), 'attention'] + words + auth)
            self.assertEqual(code, expected, output.getvalue())
            return json.loads(output.getvalue())

        row = cli(['request', '--file', str(packet)])
        self.assertEqual(row['status'], 'open')
        self.assertEqual(cli(['list'])['requests'][0]['request_id'], row['request_id'])
        response_args = ['respond', '--request-id', row['request_id'], '--choice', 'accept',
            '--expected-revision', '1', '--fingerprint', row['fingerprint']]
        self.assertEqual(cli(response_args)['status'], 'responded')
        duplicate = cli(response_args, expected=2)
        self.assertEqual(duplicate['error']['code'], 'attention_revision_conflict')
        held = cli(['consume', '--request-id', row['request_id'], '--expected-revision', '2',
            '--fingerprint', row['fingerprint']], expected=2)
        self.assertEqual(held['error']['code'], 'context_unavailable')
        shown = cli(['show', '--request-id', row['request_id']])
        self.assertEqual(shown['status'], 'responded')
        self.assertEqual(len(shown['history']), 2)

    def test_native_mcp_request_list_show_exact_owner_and_no_model_mutators(self):
        policy = self.root / 'controllers.json'
        policy.write_text(json.dumps(dict(version=1, controllers={self.caller: ['integration-task']})))
        policy.chmod(0o600)
        runner = CommandRunner(wake_root=self.wake, harness_policy=policy)
        arguments = dict(caller_thread_id=self.caller, request=self.packet(self.caller))
        row, failed = runner.call('wake_attention_request', arguments, native_context=self.native())
        self.assertFalse(failed, row)
        listed, failed = runner.call('wake_attention_list', dict(caller_thread_id=self.caller),
            native_context=self.native())
        self.assertFalse(failed, listed)
        self.assertEqual(listed['requests'][0]['request_id'], row['request_id'])
        shown, failed = runner.call('wake_attention_show', dict(caller_thread_id=self.caller,
            request_id=row['request_id']), native_context=self.native())
        self.assertFalse(failed, shown)
        self.assertEqual(shown['fingerprint'], row['fingerprint'])
        peer = '00000000-0000-7000-8000-000000000340'
        denied, failed = runner.call('wake_attention_show', dict(caller_thread_id=peer,
            request_id=row['request_id']), native_context=self.native(peer))
        self.assertTrue(failed, denied)
        denied, failed = runner.call('wake_attention_list', dict(caller_thread_id=self.caller),
            native_context=self.native(peer))
        self.assertTrue(failed, denied)
        attention_tools = {name for name in SPECS if name.startswith('wake_attention_')}
        self.assertEqual(attention_tools, {'wake_attention_request', 'wake_attention_list', 'wake_attention_show'})
        self.assertIn('wake_agents_overview', SPECS)
