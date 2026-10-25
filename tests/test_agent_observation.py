"""Semantic agent state through the public observation seam; runtime evidence is external."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from codex_wake.managed_inventory import ManagedInventory, Observation
from codex_wake.agent_observation import AgentObservation, StateEvidence


class AgentObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.process = dict(pid=123, start_ticks=42, boot_id='boot')
        sample = Observation('codex', 'codex:fixture', 'conversation', str(self.root),
                             'ready', 100, 'native_metadata', self.process, [], {'inspect': 'supported'})
        self.agent = ManagedInventory(self.root, now=lambda: 100).enroll(sample, operator=True)['agent']
        self.evidence = StateEvidence('codex', 'codex:fixture', 'conversation', str(self.root),
            self.process, 100, 'ready', 'native_metadata', 'recipient_idle')

    def test_exact_fresh_runtime_evidence_reports_ready_without_granting_operations(self):
        observer = AgentObservation(self.root, observer=lambda agent, timeout: self.evidence, now=lambda: 100)
        value = observer.observe(self.agent['managed_agent_id'])
        self.assertEqual(value['state'], 'ready')
        self.assertEqual(value['evidence_kind'], 'native_metadata')
        self.assertFalse(value['grants_operations'])

    def test_stale_partial_and_changed_identity_evidence_never_becomes_ready(self):
        variants = [dict(observed_at=69), dict(observed_at=101), dict(complete=False),
                    dict(namespace='other'), dict(conversation_id='other'), dict(root='/other'),
                    dict(process=dict(pid=123, start_ticks=43, boot_id='boot')),
                    dict(state='completed'), dict(source='terminal_text')]
        for change in variants:
            with self.subTest(change=change):
                sample = replace(self.evidence, **change)
                value = AgentObservation(self.root, observer=lambda agent, timeout: sample,
                                         now=lambda: 100).observe(self.agent['managed_agent_id'])
                self.assertEqual(value['state'], 'unknown')
                self.assertFalse(value['fresh'])

    def test_wait_matches_fresh_state_change_and_never_reads_after_deadline(self):
        elapsed = [0.0]
        calls = []
        def read(agent, budget):
            calls.append(budget)
            return replace(self.evidence, observed_at=100 + elapsed[0],
                           state='working' if len(calls) == 1 else 'ready')
        def sleep(seconds):
            elapsed[0] += seconds
        owner = AgentObservation(self.root, observer=read, now=lambda: 100 + elapsed[0],
                                 monotonic=lambda: elapsed[0], sleep=sleep)
        result = owner.wait(self.agent['managed_agent_id'], state='ready', timeout=2, interval=1)
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(calls, [2, 1])
        calls.clear()
        result = owner.wait(self.agent['managed_agent_id'], state='working', timeout=0)
        self.assertEqual(result['status'], 'timeout')
        self.assertEqual(calls, [])
        # Unknown evidence never satisfies a ready predicate, even at timeout.
        owner.observer = lambda agent, budget: replace(self.evidence, observed_at=0)
        result = owner.wait(self.agent['managed_agent_id'], state='ready', timeout=1, interval=1)
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['observation']['state'], 'unknown')

    def test_invalid_wait_and_freshness_limits_are_rejected_before_runtime_read(self):
        def forbidden(agent, timeout):
            self.fail('invalid request reached runtime')
        elapsed = [0.0]
        def advance(seconds):
            elapsed[0] += max(seconds, 1)
        owner = AgentObservation(self.root, observer=forbidden, now=lambda: 100,
                                 monotonic=lambda: elapsed[0], sleep=advance)
        for options in [dict(timeout=-1), dict(timeout=float('nan')), dict(timeout=True),
                        dict(timeout=301), dict(interval=0), dict(freshness=float('inf')),
                        dict(state='completed')]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                owner.wait(self.agent['managed_agent_id'], **dict(dict(state='ready'), **options))
        with self.assertRaises(ValueError):
            owner.observe(self.agent['managed_agent_id'], freshness=0)

    def test_suppressed_agent_is_unknown_without_runtime_access(self):
        ManagedInventory(self.root, now=lambda: 100).set_enrollment(self.agent['managed_agent_id'], enabled=False)
        owner = AgentObservation(self.root, observer=lambda *args: self.fail('suppressed caller read runtime'), now=lambda: 100)
        self.assertEqual(owner.observe(self.agent['managed_agent_id'])['state'], 'unknown')

    def test_native_metadata_adapter_uses_exact_identity_and_supported_status_flags(self):
        import os
        import socket
        from unittest.mock import patch
        from test_shared_app_server import FakeConnection, result
        from codex_wake.a2a_identity import RuntimeIdentity
        from codex_wake.process import process_identity
        from codex_wake.agent_observation import RuntimeStateObserver
        sock = socket.socket(socket.AF_UNIX)
        self.addCleanup(sock.close)
        path = self.root / 'native.sock'
        sock.bind(str(path))
        native = dict(id='conversation', cwd=str(self.root), modelProvider='fixture')
        server = dict(codexHome=str(self.root / 'home'))
        identity = RuntimeIdentity.from_metadata(native, server)
        process = process_identity(os.getpid())
        sample = Observation('codex', identity.namespace, 'conversation', str(self.root), 'ready', 100,
            'native_metadata', dict(pid=os.getpid(), start_ticks=process['start_time_ticks'], boot_id=process['boot_id']),
            [], {'inspect': 'supported'})
        agent = ManagedInventory(self.root, now=lambda: 100).enroll(sample, operator=True)['agent']
        cases = [('idle', [], 'ready'), ('active', [], 'working'),
                 ('active', ['waitingOnApproval'], 'awaiting-human'),
                 ('active', ['waitingOnUserInput'], 'awaiting-human'),
                 ('idle', ['waitingOnApproval'], 'unknown'),
                 ('active', ['newUnknownFlag'], 'unknown'), ('notLoaded', [], 'disconnected')]
        for status, flags, expected in cases:
            with self.subTest(status=status, flags=flags):
                thread = dict(native, status=dict(type=status, activeFlags=flags), turns=['PRIVATE'])
                conn = FakeConnection([result(1, server), result(2, {'thread': thread}), result(3, {'thread': thread})])
                with patch('websockets.sync.client.unix_connect', return_value=conn):
                    owner = AgentObservation(self.root, observer=RuntimeStateObserver(endpoint='unix://' + str(path), now=lambda: 100), now=lambda: 100)
                    value = owner.observe(agent['managed_agent_id'])
                self.assertEqual(value['state'], expected, value)
                self.assertNotIn('PRIVATE', str(value))
                self.assertTrue(all(call['method'] in ('initialize', 'initialized', 'thread/read') for call in conn.sent))

    def test_public_cli_and_mcp_observe_share_unknown_result_without_launching_runtime(self):
        import contextlib
        import io
        import json
        from codex_wake.cli import run
        from codex_wake.mcp_server import CommandRunner
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = run(['--wake-root', str(self.root), 'agents', 'observe',
                        '--managed-agent-id', self.agent['managed_agent_id'],
                        '--app-server', 'unix://' + str(self.root / 'missing.sock'), '--json'])
        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['state'], 'unknown')
        value, failed = CommandRunner(wake_root=self.root, app_server='unix://' + str(self.root / 'missing.sock')).call(
            'wake_agents_observe', dict(managed_agent_id=self.agent['managed_agent_id']))
        self.assertFalse(failed, value)
        self.assertEqual(value['state'], 'unknown')

    def test_grok_qualified_composer_is_ready_but_draft_and_changed_generation_are_unknown(self):
        from test_runtime_a2a import Host, Process, BINDING, SESSION
        from codex_wake.runtime_a2a import GrokMailboxRuntime
        from codex_wake.agent_observation import RuntimeStateObserver
        class Terminal(Host):
            frame = f'Shell version: 1.0.40 [stable]\nSession ID: {SESSION}\nminimal · /help\n❯\nGrok 4.7 (high) · 27K / 256K (11%) · ctrl+o transcript\n'
            def snapshot(self, binding):
                return dict(super().snapshot(binding), frame=self.frame)
        host = Terminal()
        runtime = GrokMailboxRuntime(self.root / 'grok', host=host, process=Process(self.root))
        identity, binding = runtime.resolve(BINDING, 'f' * 64)
        sample = Observation('grok', identity.namespace, SESSION, str(self.root), 'ready', 100,
            'host_bound_runtime', self.process, [], {'inspect': 'supported'})
        agent = ManagedInventory(self.root, now=lambda: 100).enroll(sample, operator=True)['agent']
        owner = AgentObservation(self.root, now=lambda: 100, observer=RuntimeStateObserver(
            now=lambda: 100, grok_source=lambda timeout: (runtime, BINDING, 'f' * 64)))
        self.assertEqual(owner.observe(agent['managed_agent_id'])['state'], 'ready')
        host.frame = host.frame.replace('❯\n', '❯ PRIVATE_DRAFT\n')
        value = owner.observe(agent['managed_agent_id'])
        self.assertEqual(value['state'], 'unknown')
        self.assertNotIn('PRIVATE_DRAFT', str(value))
        host.changed = True
        self.assertEqual(owner.observe(agent['managed_agent_id'])['state'], 'unknown')
