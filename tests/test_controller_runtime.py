import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_auth import Actor, AuthError
from codex_wake.managed_inventory import InventoryError


class RuntimeTests(unittest.TestCase):
    def actor(self):
        return Actor('caller', 'service', 'client', 'grant', 'https://wake.test', 'https://wake.test/controller', frozenset({'observe', 'control'}), [{'host': 'fixture', 'environment': 'linux', 'runtime': 'codex', 'namespace': 'account:alice', 'conversation_id': 'recipient', 'process': {'pid': 1}}], 1000)

    def test_intent_precedes_effect_and_uncertain_dispatch_is_never_replayed(self):
        from codex_wake.controller_runtime import ControllerRuntime
        with tempfile.TemporaryDirectory() as directory:
            runtime = ControllerRuntime(Path(directory), now=lambda: 100)
            actor = self.actor()
            meta = dict(operation_id='operation-one', idempotency_key='intent-one', correlation_id='correlation-one', binding='opaque-binding', target=actor.targets[0])
            arguments = dict(expected_target=actor.targets[0], value='original', _request=meta)
            effect = Path(directory) / 'effect'
            def dispatch(operation, args):
                self.assertNotIn('_request', args)
                admitted = runtime.operation(actor, 'operations.result', {'operation_id': 'operation-one'}, authorize=lambda: actor)
                self.assertEqual(admitted['result']['operation']['execution'], 'unknown')
                effect.write_text('one effect')
                raise RuntimeError('synthetic response lost after effect')
            first = runtime.execute(actor, 'fixture.effect', arguments, authorize=lambda: actor, dispatch=dispatch)
            self.assertEqual(first['result']['operation']['execution'], 'unknown')
            self.assertEqual(first['result']['operation']['delivery'], 'uncertain')
            def forbidden(*args): self.fail('uncertain dispatch replayed')
            again = ControllerRuntime(Path(directory), now=lambda: 100).execute(actor, 'fixture.effect', arguments, authorize=lambda: actor, dispatch=forbidden)
            self.assertEqual(first, again)
            with self.assertRaises(InventoryError): runtime.execute(actor, 'fixture.effect', dict(arguments, value='changed'), authorize=lambda: actor, dispatch=forbidden)
            with self.assertRaises(AuthError): runtime.operation(Actor('other', *tuple(actor.__dict__.values())[1:]), 'operations.result', {'operation_id': 'operation-one'}, authorize=lambda: actor)
            self.assertEqual(effect.read_text(), 'one effect')
