import tempfile
import unittest
from pathlib import Path

from codex_wake.managed_inventory import InventoryError


class HostTests(unittest.TestCase):
    def test_host_and_wsl_environment_identity_freshness_and_authority_are_independent(self):
        from codex_wake.controller_hosts import HostRegistry
        with tempfile.TemporaryDirectory() as directory:
            clock = [100]
            registry = HostRegistry(Path(directory) / 'hosts.sqlite', now=lambda: clock[0])
            windows = registry.register('host-one', 'windows', kind='windows', authority='authority-windows', destination='windows-fixture', operator=True)
            wsl = registry.register('host-one', 'wsl-ubuntu', kind='wsl', authority='authority-ubuntu', destination='ubuntu-fixture', operator=True)
            self.assertEqual(windows['target']['host'], wsl['target']['host'])
            self.assertNotEqual(windows['target']['environment'], wsl['target']['environment'])
            self.assertNotEqual(windows['target']['authority'], wsl['target']['authority'])
            registry.observe(windows['target'], online=False, operator=True)
            clock[0] = 131
            rows = registry.list()
            self.assertEqual(len(rows), 2)
            self.assertEqual({r['observation']['freshness'] for r in rows}, {'stale'})
            self.assertFalse(next(r for r in rows if r['target']['environment'] == 'windows')['observation']['online'])
            with self.assertRaises(InventoryError) as error:
                registry.register('host-one', 'windows', kind='windows', authority='new-authority', destination='different', operator=True)
            self.assertEqual(error.exception.code, 'authority_conflict')
            with self.assertRaises(InventoryError): registry.register('unauthorized', 'linux', kind='remote', authority='other', destination='other')

    def test_registered_ssh_principal_uses_common_read_admission_without_owner_privilege(self):
        from codex_wake.controller_hosts import HostRegistry, SSHReceiver
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import ManagedInventory, Observation
        with tempfile.TemporaryDirectory() as directory:
            registry = HostRegistry(Path(directory) / 'hosts.sqlite', now=lambda: 100)
            row = registry.register('host', 'wsl', kind='wsl', authority='authority', destination='fixture', operator=True)
            inventory = ManagedInventory(Path(directory) / 'wake', now=lambda: 100)
            for account in ('alice', 'bob'):
                inventory.enroll(Observation('codex', 'account:' + account, account, '/fixture', 'ready', 100, 'native_metadata', {'pid': 123, 'start_ticks': 42, 'boot_id': 'fixture'}, [], {}), operator=True)
            registry.map_principal('bot-key', subject='service:bot', scopes=['observe'], targets=[{'host': 'host', 'environment': 'wsl', 'namespace': 'account:alice'}], expires_at=200, operator=True)
            receiver = SSHReceiver(registry, ControllerOperations(inventory, host='host', environment='wsl'), principal_id='bot-key', target=row['target'])
            request = dict(target=row['target'], operation='inventory.list', arguments={}, constraints={'scopes': ['observe'], 'targets': [{'host': 'host', 'environment': 'wsl'}]})
            result = receiver.execute(request)
            self.assertEqual(result['actor']['subject'], 'service:bot')
            self.assertEqual([r['target']['namespace'] for r in result['result']['resources']], ['account:alice'])
            with self.assertRaises(InventoryError): receiver.execute(dict(request, principal_id='owner'))
            registry.revoke_principal('bot-key', operator=True)
            from codex_wake.controller_auth import AuthError
            with self.assertRaises(AuthError): receiver.execute(request)

    def test_route_is_pinned_authorized_and_never_replayed_after_uncertain_disconnect(self):
        from codex_wake.controller_hosts import HostRegistry, HostOperations, TransportFailure
        from codex_wake.controller_auth import Actor
        with tempfile.TemporaryDirectory() as directory:
            registry = HostRegistry(Path(directory) / 'hosts.sqlite', now=lambda: 100)
            row = registry.register('host', 'remote', kind='remote', authority='one-authority', destination='fixture', operator=True)
            calls = []
            class DisconnectedTransport:
                def send(self, registered, request):
                    calls.append(request)
                    raise TransportFailure('synthetic_disconnect_after_submission', submitted=True)
            operations = HostOperations(registry, transport=DisconnectedTransport())
            actor = Actor('caller', 'service', 'client', 'grant', 'https://wake.test', 'https://wake.test/controller', frozenset({'observe'}), [dict(row['target'])], 200)
            args = dict(target=row['target'], operation='inventory.list', arguments={}, operation_id='operation-one', idempotency_key='request-one')
            with self.assertRaises(InventoryError): operations.execute('hosts.route', args)
            first = operations.execute('hosts.route', args, actor=actor)['route']
            self.assertEqual((first['execution'], first['delivery'], first['effect']), ('unknown', 'uncertain', 'none_read_only'))
            replay = HostOperations(HostRegistry(registry.path, now=lambda: 100), transport=DisconnectedTransport()).execute('hosts.route', args, actor=actor)['route']
            self.assertEqual(first, replay)
            self.assertEqual(len(calls), 1)
            with self.assertRaises(InventoryError) as error:
                operations.execute('hosts.route', dict(args, arguments={'query': 'changed'}), actor=actor)
            self.assertEqual(error.exception.code, 'idempotency_conflict')
            with self.assertRaises(InventoryError) as error:
                operations.execute('hosts.route', dict(args, operation='runtime.input', idempotency_key='mutation'), actor=actor)
            self.assertEqual(error.exception.code, 'unsupported_operation')
            registry.observe(row['target'], online=False, operator=True)
            with self.assertRaises(InventoryError) as error:
                operations.execute('hosts.route', dict(args, operation_id='operation-two', idempotency_key='request-two'), actor=actor)
            self.assertEqual(error.exception.code, 'offline_target')
            self.assertEqual(len(calls), 1)

    def test_exact_pin_and_final_authorization_callback_block_submission(self):
        from dataclasses import replace
        from codex_wake.controller_hosts import HostRegistry, HostOperations
        from codex_wake.controller_auth import Actor, AuthError
        with tempfile.TemporaryDirectory() as directory:
            registry = HostRegistry(Path(directory) / 'hosts.sqlite', now=lambda: 100)
            row = registry.register('host', 'remote', kind='remote', authority='authority', destination='fixture', operator=True)
            calls = []
            class ForbiddenTransport:
                def send(self, *args):
                    calls.append(args)
                    raise AssertionError('unauthorized input reached SSH')
            operations = HostOperations(registry, transport=ForbiddenTransport())
            actor = Actor('caller', 'service', 'client', 'grant', 'https://wake.test', 'https://wake.test/controller', frozenset({'observe'}), [dict(row['target'])], 200)
            args = dict(target=row['target'], operation='inventory.list', arguments={}, operation_id='revoked-operation', idempotency_key='revoked-key')
            for scopes in ([{'host': 'host', 'environment': 'remote'}], [dict(row['target'], authority='other')]):
                with self.assertRaises(InventoryError) as error:
                    operations.execute('hosts.route', args, actor=replace(actor, targets=scopes))
                self.assertEqual(error.exception.code, 'unauthorized_target')
            def revoked(): raise AuthError()
            result = operations.execute('hosts.route', args, actor=actor, authorize=revoked)['route']
            self.assertEqual((result['execution'], result['delivery'], result['reason']), ('not_started', 'not_submitted', 'invalid_token'))
            later = operations.execute('hosts.route', args, actor=actor, authorize=lambda: actor)['route']
            self.assertEqual(result, later)
            registry.now = lambda: 131
            with self.assertRaises(InventoryError) as error:
                operations.execute('hosts.route', dict(args, operation_id='expired-observation', idempotency_key='expired-observation'), actor=actor)
            self.assertEqual(error.exception.code, 'stale_target')
            self.assertEqual(calls, [])
