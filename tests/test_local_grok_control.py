"""Shared local Grok behavior at the actual ACP boundary (fixture, no provider)."""
import tempfile
import unittest
from pathlib import Path
import test_controller_grok
from codex_wake.managed_inventory import InventoryError


class LocalGrokTests(unittest.TestCase):
    def fixture(self, root):
        owner, actor, target, args, calls, profile = test_controller_grok.GrokControllerTests().fixture(root)
        Path(target['home']).mkdir()
        original = owner.request
        def request(profile, method, params, identifier, guard):
            if method == 'session/load':
                guard(); return {'models': {'currentModelId': 'grok-fixture', 'availableModels': [{'modelId': 'grok-fixture', 'name': 'Fixture'}]}, '_meta': {'x.ai/sessionDetail': {'sessionId': params['sessionId'], 'cwd': str(root), 'currentModelId': 'grok-fixture'}}}
            if method == 'session/set_model':
                guard(); calls.append((method, params, identifier)); return {'_meta': {'model': {'Ok': params['modelId']}}}
            if method == 'session/list':
                guard(); return {'sessions': [{'sessionId': 'conversation', 'cwd': str(root), 'title': 'Owned'}]}
            return original(profile, method, params, identifier, guard)
        from codex_wake.local_grok_control import LocalGrokControl
        return LocalGrokControl(root, request=request), calls

    def test_same_interface_discovers_headless_session_and_refuses_changed_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            owner, calls = self.fixture(Path(directory))
            view = owner.discover()
            self.assertEqual(view['status'], 'complete')
            row = owner.resolve('grok:conversation')
            self.assertEqual(row['target']['provider'], 'grok')
            self.assertEqual(row['presentation'], 'headless_acp')
            self.assertEqual(row['profile'], 'selected')
            with self.assertRaises(InventoryError):
                owner.resolve('grok:conversation', expected_target=dict(row['target'], connection_generation='old'))
            with self.assertRaises(InventoryError):
                owner.resolve('conversation')

    def test_prompt_retains_original_answer_and_output_without_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            owner, calls = self.fixture(Path(directory))
            first = owner.prompt('grok:conversation', 'Literal Ω\nsecond line', key='same')
            identifier = first['result']['operation']['operation_id']
            again = owner.prompt('grok:conversation', 'Literal Ω\nsecond line', key='same')
            self.assertEqual(again['result']['operation']['operation_id'], identifier)
            self.assertEqual(owner.output(identifier, mode='final')['text'], 'fixture answer')
            self.assertEqual(owner.output(identifier, mode='transcript')['events'][0]['source'], 'original_grok_acp_reply')
            self.assertEqual(sum(method == 'session/prompt' for method, _, _ in calls), 1)
            self.assertEqual(owner.cancel(identifier)['result']['operation']['execution'], 'completed')

    def test_model_interaction_is_retained_cancel_safe_and_uses_native_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            owner, calls = self.fixture(Path(directory))
            status = owner.slash('run', dict(selector='grok:conversation', command='/status', idempotency_key='status'))
            self.assertTrue(status['result']['operation']['result']['completed'])
            pending = owner.slash('run', dict(selector='grok:conversation', command='/model', idempotency_key='choose'))
            record = pending['result']['operation']; handle = record['result']
            self.assertEqual(handle['interaction_id'], record['operation_id'])
            self.assertEqual(handle['presentation'], 'controller_interaction')
            self.assertFalse(handle['native_popup'])
            owner.slash('cancel', dict(interaction_id=handle['interaction_id']))
            self.assertFalse(any(method == 'session/set_model' for method, _, _ in calls))
            pending = owner.slash('run', dict(selector='grok:conversation', command='/model', idempotency_key='choose2'))
            identifier = pending['result']['operation']['operation_id']
            result = owner.slash('respond', dict(interaction_id=identifier, value='grok-fixture', idempotency_key='selection'))
            self.assertEqual(result['result']['operation']['execution'], 'completed')
            owner.slash('respond', dict(interaction_id=identifier, value='grok-fixture', idempotency_key='selection'))
            self.assertEqual(sum(method == 'session/set_model' for method, _, _ in calls), 1)
            with self.assertRaises(InventoryError):
                owner.slash('run', dict(selector='grok:conversation', command='/goal', idempotency_key='unsafe'))
            self.assertFalse(any(method == 'session/prompt' for method, _, _ in calls))

    def test_lost_model_response_reconciles_exact_readback_without_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            owner, calls = self.fixture(Path(directory))
            pending = owner.slash('run', dict(selector='grok:conversation', command='/model', idempotency_key='lost-choice'))
            identifier = pending['result']['operation']['operation_id']
            original = owner.owner.request
            def lost(profile, method, params, key, guard):
                value = original(profile, method, params, key, guard)
                if method == 'session/set_model':
                    raise TimeoutError('response lost after native effect')
                return value
            owner.owner.request = lost
            owner.slash('respond', dict(interaction_id=identifier, value='grok-fixture', idempotency_key='lost-selection'))
            retained = owner.result(identifier)['result']['operation']
            self.assertEqual(retained['execution'], 'completed')
            self.assertEqual(retained['result']['reconciliation'], 'native_model_observed_without_replay')
            self.assertEqual(sum(method == 'session/set_model' for method, _, _ in calls), 1)

    def test_create_is_usable_without_target_json_and_retry_preserves_original_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            owner, calls = self.fixture(Path(directory))
            created = owner.create(profile='selected', key='create-once')
            self.assertEqual(created['result']['operation']['result']['session_id'], 'new-conversation')
            (Path(directory) / 'controller-grok.json').unlink()
            retry = owner.create(profile='selected', key='create-once')
            self.assertEqual(retry['result']['operation']['operation_id'], created['result']['operation']['operation_id'])
            self.assertEqual(sum(method == 'session/new' for method, _, _ in calls), 1)
            with self.assertRaises(InventoryError):
                owner.create(profile='different', key='create-once')

    def test_prompt_retry_uses_original_custody_after_profile_disappears(self):
        with tempfile.TemporaryDirectory() as directory:
            owner, calls = self.fixture(Path(directory))
            first = owner.prompt('grok:conversation', 'same', key='original')
            (Path(directory) / 'controller-grok.json').unlink()
            retry = owner.prompt('grok:conversation', 'same', key='original')
            self.assertEqual(retry['result']['operation']['operation_id'], first['result']['operation']['operation_id'])
            with self.assertRaises(InventoryError):owner.prompt('grok:other', 'same', key='original')
            with self.assertRaises(InventoryError):owner.prompt('grok:conversation', 'different', key='original')
            with self.assertRaises(InventoryError):owner.prompt('grok:conversation', 'same', key='original', profile='other')

    def test_model_response_refuses_replaced_agent_generation_before_effect(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); owner, calls = self.fixture(root)
            pending = owner.slash('run', dict(selector='grok:conversation', command='/model', idempotency_key='old-agent'))
            identifier = pending['result']['operation']['operation_id']
            path = root / 'controller-grok.json'; registry = json.loads(path.read_text())
            registry['profiles']['selected']['target']['connection_generation'] = 'replacement'
            path.write_text(json.dumps(registry))
            with self.assertRaises(InventoryError):
                owner.slash('respond', dict(interaction_id=identifier, value='grok-fixture', idempotency_key='refused'))
            self.assertFalse(any(method == 'session/set_model' for method, _, _ in calls))
