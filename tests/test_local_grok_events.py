"""Qualified collector custody deadlines gate the public ACP collector."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.controller_runtime import ControllerRuntime
from codex_wake.daemon_commands import local_operator
from codex_wake.local_grok_events import collect
from codex_wake.local_session_events import TurnEvents
from codex_wake.process import process_identity
from test_measurements import observation


class GrokEventWaitTests(unittest.TestCase):
    def seed(self, root):
        home = root / 'home'
        home.mkdir()
        birth = process_identity(os.getpid())
        target = dict(host='fixture', environment='linux', runtime='grok', provider='grok',
            account='fixture', home=str(home), namespace='grok:fixture',
            build_sha256=hashlib.sha256(Path('/proc/self/exe').resolve().read_bytes()).hexdigest(),
            configuration_revision='fixture-v1', backend_id='agent-one', channel='acp-websocket',
            connection_generation='instance-one', process_pid=str(os.getpid()),
            process_start_ticks=str(birth['start_time_ticks']), process_boot_id=birth['boot_id'])
        secret = root / 'transport.secret'
        secret.write_text('synthetic-unused-secret')
        secret.chmod(0o600)
        profile = dict(target=target, endpoint='ws://127.0.0.1:23456/ws', secret_file=str(secret),
            cwd=str(root), agent_version='1.0.70', timeout=2)
        registry = root / 'controller-grok.json'
        registry.write_text(json.dumps(dict(version=1, profiles={'selected': profile})))
        registry.chmod(0o600)
        selected = dict(target, conversation_id='conversation')
        actor = local_operator(selected)
        runtime = ControllerRuntime(root)
        identifier = 'fixture-grok-event-wait'
        arguments = dict(profile='selected', prompt='synthetic prompt', expected_target=selected,
            _request=dict(operation_id=identifier, idempotency_key=identifier,
                correlation_id=identifier, binding='fixture', target=selected))
        runtime.execute(actor, 'grok.prompt', arguments, authorize=lambda: actor,
            dispatch=lambda _operation, _payload: dict(_pending=True,
                handle=dict(kind='grok_acp_collecting', native_request_id=identifier)))
        return runtime, actor, identifier

    def test_expired_custody_deadline_holds_even_when_waiting_is_already_published(self):
        with tempfile.TemporaryDirectory() as directory, patch(
                'codex_wake.measurements.utc_bounds', return_value=(1000, 1000.001)):
            root = Path(directory)
            runtime, actor, identifier = self.seed(root)
            with patch('codex_wake.measurements.snapshot', side_effect=[
                    observation(1000), observation(1001), observation(12000)]), patch(
                    'codex_wake.grok_acp.GrokACPConnection', side_effect=AssertionError('ACP must not open')) as connection:
                collect(root, identifier)
            self.assertEqual(connection.call_count, 0)
            result = runtime.operation(actor, 'operations.result', dict(operation_id=identifier),
                authorize=lambda: actor)['result']['operation']
            self.assertEqual(result['phase'], 'uncertain')
            self.assertEqual(result['execution'], 'unknown')
            self.assertEqual(TurnEvents(root).state(identifier)['status'], 'uncertain')

    def test_missing_or_lost_counter_holds_original_intent_without_reopening_collector(self):
        from codex_wake import measurements
        for samples in ([measurements.TimeUnavailable('missing')],
                        [observation(1000), observation(1001), measurements.TimeUnavailable('lost')]):
            with self.subTest(samples=len(samples)), tempfile.TemporaryDirectory() as directory, patch(
                    'codex_wake.measurements.utc_bounds', return_value=(1000, 1000.001)):
                root = Path(directory)
                runtime, actor, identifier = self.seed(root)
                with patch('codex_wake.measurements.snapshot', side_effect=samples), patch(
                        'codex_wake.grok_acp.GrokACPConnection', side_effect=AssertionError('ACP must not open')) as connection:
                    collect(root, identifier)
                    collect(root, identifier)
                self.assertEqual(connection.call_count, 0)
                result = runtime.operation(actor, 'operations.result', dict(operation_id=identifier),
                    authorize=lambda: actor)['result']['operation']
                self.assertEqual(result['operation_id'], identifier)
                self.assertEqual(result['phase'], 'uncertain')
                self.assertFalse(TurnEvents(root).state(identifier).get('transmitted', False))

    def connection(self, calls):
        class Connection:
            def __init__(self, profile, *, guard, on_update=None):
                self.profile, self.guard = profile, guard
                calls.append('open')
            def __enter__(self):
                self.guard()
                return self
            def __exit__(self, *_args):
                pass
            def call(self, method, params, identifier):
                self.guard()
                calls.append(method)
                if method == 'initialize':
                    return dict(protocolVersion=1, agentCapabilities=dict(sessionCapabilities=dict(list={})),
                        _meta=dict(agentVersion='1.0.70', agentId='agent-one', agentInstanceId='instance-one',
                                   currentWorkingDirectory=self.profile['cwd']))
                if method == 'session/list':
                    return dict(sessions=[dict(sessionId='conversation', cwd=self.profile['cwd'])])
                if method == 'session/prompt':
                    return dict(stopReason='end_turn')
                raise AssertionError(method)
        return Connection

    def test_clock_loss_after_discovery_holds_before_prompt_connection(self):
        from codex_wake import measurements
        with tempfile.TemporaryDirectory() as directory, patch(
                'codex_wake.measurements.utc_bounds', return_value=(1000, 1000.001)):
            root = Path(directory)
            runtime, actor, identifier = self.seed(root)
            calls = []
            with patch('codex_wake.measurements.snapshot', side_effect=[observation(1000),
                    observation(1001), observation(1002), measurements.TimeUnavailable('lost')]), patch(
                    'codex_wake.grok_acp.GrokACPConnection', self.connection(calls)):
                collect(root, identifier)
            self.assertEqual(calls, ['open', 'initialize', 'session/list'])
            result = runtime.operation(actor, 'operations.result', dict(operation_id=identifier),
                authorize=lambda: actor)['result']['operation']
            self.assertEqual(result['phase'], 'uncertain')
            self.assertFalse(TurnEvents(root).state(identifier).get('transmitted', False))

    def test_qualified_custody_wait_preserves_single_original_prompt(self):
        with tempfile.TemporaryDirectory() as directory, patch(
                'codex_wake.measurements.utc_bounds', return_value=(1000, 1000.001)):
            root = Path(directory)
            runtime, actor, identifier = self.seed(root)
            calls = []
            with patch('codex_wake.measurements.snapshot', return_value=observation(1000)), patch(
                    'codex_wake.grok_acp.GrokACPConnection', self.connection(calls)):
                collect(root, identifier)
                collect(root, identifier)
            self.assertEqual(calls.count('session/prompt'), 1)
            result = runtime.operation(actor, 'operations.result', dict(operation_id=identifier),
                authorize=lambda: actor)['result']['operation']
            self.assertEqual(result['phase'], 'terminal')
            self.assertEqual(result['execution'], 'completed')
            self.assertEqual(result['result']['native_request_id'], identifier)
            self.assertEqual(TurnEvents(root).state(identifier)['status'], 'completed')
