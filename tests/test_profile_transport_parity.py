"""Profile operations remain available at the public controller/CLI seam."""
import json
from pathlib import Path
import tempfile
import unittest

from codex_wake.account_commands import execute
from codex_wake.controller_accounts import ControllerAccounts
from codex_wake.controller_operations import ControllerOperations


class ProfileTransportParityTests(unittest.TestCase):
    def test_local_public_store_seed_and_sync_need_no_remote_grant(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stock = root / 'stock'
            stock.mkdir(mode=0o700)
            (stock / 'config.toml').write_text('model="original"\n')
            self.assertEqual(execute('accounts.init', {}, root)['status'], 'completed')
            registered = execute('stores.register', dict(selector='stock', home=str(stock)), root)
            self.assertEqual(registered['status'], 'completed', registered)
            created = execute('accounts.create', dict(selector='alice', mode='independent', source='stock'), root)
            self.assertEqual(created['status'], 'completed', created)
            owner = ControllerAccounts(root / 'controller-accounts.toml', host='fixture', environment='test')
            service = ControllerOperations(None, host='fixture', environment='test', accounts=owner)
            self.assertEqual(service.execute('stores.resolve', {'selector': 'stock'})['result']['store']['store_id'], registered['result']['store']['store_id'])
            (stock / 'config.toml').write_text('model="changed"\n')
            arguments = dict(source='stock', destinations=['alice'], categories=['settings'], operation_id='parity', reload=True)
            preview = execute('configuration.sync.preview', arguments, root)
            self.assertEqual(preview['status'], 'completed', preview)
            arguments['expected_snapshot'] = preview['result']['snapshot']
            applied = execute('configuration.sync.apply', arguments, root)
            self.assertEqual(applied['status'], 'completed', applied)
            self.assertIn('unsupported; use next launch', applied['result']['destinations'][0]['reload'])
            self.assertEqual(execute('configuration.sync.apply', arguments, root), applied)
            home = Path(created['result']['account']['home'])
            self.assertIn('changed', (home / 'config.toml').read_text())


    def test_scoped_api_and_native_mcp_agree_and_readiness_cannot_inspect_caller_paths(self):
        import os
        import socket
        import time
        from types import SimpleNamespace
        from codex_wake.controller_auth import Actor, AuthError
        from codex_wake.controller_http import ProtectedOperations, TOOLS
        from codex_wake.managed_inventory import ManagedInventory, InventoryError
        from codex_wake.mcp_server import CommandRunner, SPECS
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stock = root / 'stock'
            stock.mkdir(mode=0o700)
            execute('accounts.init', {}, root)
            registered = execute('stores.register', dict(selector='stock', home=str(stock)), root)['result']['store']
            execute('accounts.create', dict(selector='alice', mode='independent'), root)
            host, environment = socket.gethostname(), os.environ.get('WSL_DISTRO_NAME') or os.name
            accounts = ControllerAccounts(root / 'controller-accounts.toml', host=host, environment=environment)
            target = dict(host=host, environment=environment, **{key: registered[key] for key in ('store_id','home','home_generation')})
            profile = accounts.execute('accounts.resolve', {'selector':'alice'})['account']['target']
            actor = Actor('fixture', 'service', 'fixture', 'grant', 'fixture', 'fixture', frozenset({'account.observe','configuration.observe','control'}), [target, profile], time.time()+60)
            authority = SimpleNamespace(authenticate=lambda token: actor)
            service = ControllerOperations(ManagedInventory(root), host=host, environment=environment, accounts=accounts)
            protected = ProtectedOperations(authority, service)
            observed = protected.execute('token', 'stores.resolve', {'selector':'stock'})
            config = dict(version=1, local_caller=dict(subject=actor.subject, client_id=actor.client_id,
                grant_id=actor.grant_id, issuer=actor.issuer, resource=actor.resource, scopes=sorted(actor.scopes), targets=actor.targets, expires_at=actor.expires_at))
            (root / 'controller-messaging.json').write_text(json.dumps(config))
            native, failed = CommandRunner(wake_root=root).call('wake_controller_store_resolve', {'selector':'stock'})
            self.assertFalse(failed, native)
            self.assertEqual(native['result'], observed['result'])
            self.assertEqual(TOOLS['wake_controller_store_resolve'][1]['properties'], SPECS['wake_controller_store_resolve'][3])
            args = dict(source='stock', destinations=['alice'], categories=['mcp'], operation_id='remote')
            preview = protected.execute('token', 'configuration.sync.preview', args)
            native_preview, failed = CommandRunner(wake_root=root).call('wake_controller_configuration_sync_preview', args)
            self.assertFalse(failed, native_preview)
            self.assertEqual(preview['result'], native_preview['result'])
            with self.assertRaises(InventoryError) as failure:
                protected.execute('token', 'accounts.readiness', {'selector':'alice', 'manifest':'/etc/passwd'})
            self.assertEqual(failure.exception.code, 'invalid_argument')
            # A caller with a profile grant cannot observe stock by guessing its selector.
            actor = Actor('fixture', 'service', 'fixture', 'grant', 'fixture', 'fixture', actor.scopes, [profile], time.time()+60)
            with self.assertRaises(AuthError):
                protected.execute('token', 'stores.resolve', {'selector':'stock'})
            with self.assertRaises(AuthError):
                protected.execute('token', 'configuration.sync.preview', dict(args, operation_id='denied'))
            self.assertEqual(protected.execute('token', 'stores.list', {})['result']['stores'][0]['kind'], 'profile')


    def test_cli_help_completion_and_execution_share_registered_store_selectors(self):
        import contextlib
        import io
        from codex_wake.cli import build_parser
        from codex_wake.account_commands import command
        from codex_wake.completion import candidates
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stock = root / 'stock'
            stock.mkdir(mode=0o700)
            execute('accounts.init', {}, root)
            execute('stores.register', {'selector':'stock','home':str(stock)}, root)
            parser = build_parser()
            args = parser.parse_args(['--wake-root', str(root), 'accounts', 'create', 'alice', '--mode', 'independent', '--source', 'stock', '--json'])
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(command(args, root), 0)
            self.assertTrue(json.loads(output.getvalue())['result']['store']['independent'])
            words = ['--wake-root', str(root), 'configuration', 'sync', 'preview', '--source', 'st']
            self.assertIn('stock', candidates(words, len(words)-1))
            self.assertIn('sync', candidates(['configuration','s'], 1))
            self.assertIn('readiness', candidates(['accounts','r'], 1))


    def test_remote_independent_creation_uses_existing_pinned_registry_operation(self):
        import time
        from types import SimpleNamespace
        from codex_wake.account_management import registry_target
        from codex_wake.controller_auth import Actor
        from codex_wake.controller_http import ProtectedOperations
        from codex_wake.managed_inventory import ManagedInventory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stock = root / 'stock'
            stock.mkdir(mode=0o700)
            execute('accounts.init', {}, root)
            execute('stores.register', dict(selector='stock', home=str(stock)), root)
            accounts = ControllerAccounts(root / 'controller-accounts.toml', host='fixture', environment='test')
            target = registry_target(accounts)
            actor = Actor('fixture','owner','fixture','grant','fixture','fixture',frozenset({'admin'}),[target],time.time()+60)
            service = ControllerOperations(ManagedInventory(root), host='fixture', environment='test', accounts=accounts)
            protected = ProtectedOperations(SimpleNamespace(authenticate=lambda token: actor), service)
            arguments = dict(selector='alice', mode='independent', source='stock',
                _request=dict(operation_id='create',idempotency_key='create',correlation_id='create',binding='fixture',target=target))
            value = protected.execute('token', 'accounts.create', arguments)
            self.assertEqual(value['result']['operation']['execution'], 'completed', value)
            self.assertTrue(accounts.execute('stores.resolve', {'selector':'alice'})['store']['independent'])
            self.assertEqual(protected.execute('token', 'accounts.create', arguments)['result'], value['result'])


if __name__ == '__main__':
    unittest.main()
