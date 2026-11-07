import tempfile
from pathlib import Path
import unittest

from codex_wake.controller_accounts import ControllerAccounts
from codex_wake.configuration_sync import execute


class ConfigurationSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.stock = self.root / 'stock'
        self.stock.mkdir(mode=0o700)
        (self.stock / 'config.toml').write_text('model="old"\n[hooks.demo]\ncommand="old"\n[mcp_servers.demo]\nurl="https://old.invalid"\n')
        self.owner = ControllerAccounts(self.root / 'accounts.toml', host='test', environment='wsl')
        self.owner.execute('accounts.init', {})
        self.owner.execute('stores.register', {'selector':'stock', 'home':str(self.stock)})
        self.owner.execute('accounts.create', {'selector':'alice', 'mode':'independent'})
        self.alice = Path(self.owner.execute('stores.resolve', {'selector':'alice'})['store']['home'])

    def request(self, **extra):
        return dict(source='stock', destinations=['alice'], categories=['settings'], operation_id='test', **extra)

    def test_seed_baseline_preserves_destination_edit_and_applies_safe_entry(self):
        (self.alice / 'config.toml').write_text('model="alice"\n[hooks.demo]\ncommand="old"\n[mcp_servers.demo]\nurl="https://old.invalid"\n')
        (self.stock / 'config.toml').write_text('model="old"\nreasoning="high"\n')
        preview = execute(self.owner, 'configuration.sync.preview', self.request())
        result = execute(self.owner, 'configuration.sync.apply', self.request(expected_snapshot=preview['snapshot']))
        import tomllib
        actual = tomllib.loads((self.alice / 'config.toml').read_text())
        self.assertEqual(actual['model'], 'alice')
        self.assertEqual(actual['reasoning'], 'high')
        self.assertEqual(result['activation'], 'next_launch')
        self.assertEqual(result, execute(self.owner, 'configuration.sync.apply', self.request(expected_snapshot=preview['snapshot'])))

    def test_partial_conflicts_deletions_and_changed_inputs(self):
        from codex_wake.managed_inventory import InventoryError
        (self.alice / 'config.toml').write_text('model="alice"\n[hooks.demo]\ncommand="old"\n[mcp_servers.demo]\nurl="https://old.invalid"\n')
        (self.stock / 'config.toml').write_text('model="new"\n[hooks.demo]\ncommand="new"\n[mcp_servers.demo]\nurl="https://new.invalid"\n')
        args = dict(source='stock', destinations=['alice'], categories=['settings','hooks','mcp'], operation_id='partial')
        preview = execute(self.owner, 'configuration.sync.preview', args)
        self.assertEqual(sum(e['status']=='conflict' for e in preview['destinations'][0]['entries']), 1)
        execute(self.owner, 'configuration.sync.apply', dict(args, expected_snapshot=preview['snapshot']))
        import tomllib
        actual = tomllib.loads((self.alice/'config.toml').read_text())
        self.assertEqual(actual['model'], 'alice')
        self.assertEqual(actual['hooks']['demo']['command'], 'new')
        (self.stock/'config.toml').write_text('model="new"\n')
        delete = dict(args, operation_id='delete', categories=['hooks'])
        preview = execute(self.owner, 'configuration.sync.preview', delete)
        self.assertIn('deletion_preserved', [e['status'] for e in preview['destinations'][0]['entries']])
        delete['propagate_deletions'] = True
        preview = execute(self.owner, 'configuration.sync.preview', delete)
        (self.alice/'config.toml').write_text((self.alice/'config.toml').read_text()+'\n# comment\n')
        # Byte changes also invalidate approval, even when TOML meaning is stable.
        with self.assertRaises(InventoryError):
            execute(self.owner, 'configuration.sync.apply', dict(delete, expected_snapshot=preview['snapshot']))
        preview = execute(self.owner, 'configuration.sync.preview', delete)
        execute(self.owner, 'configuration.sync.apply', dict(delete, expected_snapshot=preview['snapshot']))
        self.assertNotIn('command', tomllib.loads((self.alice/'config.toml').read_text())['hooks']['demo'])

    def test_hooks_entry_merge_assets_redaction_and_scoped_reload(self):
        import json
        (self.stock/'bin').mkdir()
        (self.stock/'bin'/'hook.sh').write_text('echo '+str(self.stock))
        (self.stock/'hooks.json').write_text(json.dumps({'first':str(self.stock/'bin'/'hook.sh'), 'second':'original'}))
        self.owner.execute('accounts.create', {'selector':'bob', 'mode':'independent'})
        bob = Path(self.owner.execute('stores.resolve', {'selector':'bob'})['store']['home'])
        (bob/'hooks.json').write_text(json.dumps({'first':str(bob/'bin'/'hook.sh'), 'second':'bob-local'}))
        (self.stock/'hooks.json').write_text(json.dumps({'first':str(self.stock/'bin'/'hook.sh'), 'second':'original','third':'sensitive-example-value'}))
        (self.stock/'bin'/'hook.sh').write_text('echo updated '+str(self.stock))
        args = dict(source='stock', destinations=['bob'], categories=['hooks'], operation_id='assets', reload=True)
        preview = execute(self.owner, 'configuration.sync.preview', args)
        self.assertNotIn('sensitive-example-value', json.dumps(preview))
        reloaded = []
        result = execute(self.owner, 'configuration.sync.apply', dict(args, expected_snapshot=preview['snapshot']), reload_executor=lambda store:reloaded.append(store['selector']))
        actual = json.loads((bob/'hooks.json').read_text())
        self.assertEqual(actual['second'], 'bob-local')
        self.assertEqual(actual['third'], 'sensitive-example-value')
        self.assertEqual((bob/'bin'/'hook.sh').read_text(), 'echo updated '+str(bob))
        self.assertEqual(reloaded, ['bob'])
        self.assertNotIn('sensitive-example-value', json.dumps(result))

    def test_failed_reload_does_not_repeat_an_uncertain_effect(self):
        from codex_wake.managed_inventory import InventoryError
        (self.stock/'config.toml').write_text('model="new"\n')
        args = self.request(reload=True)
        preview = execute(self.owner, 'configuration.sync.preview', args)
        calls = []
        def failing_reload(store):
            calls.append(store['selector'])
            raise RuntimeError('lost native reply')
        with self.assertRaises(RuntimeError):
            execute(self.owner, 'configuration.sync.apply', dict(args, expected_snapshot=preview['snapshot']), reload_executor=failing_reload)
        with self.assertRaises(InventoryError) as failure:
            execute(self.owner, 'configuration.sync.apply', dict(args, expected_snapshot=preview['snapshot']), reload_executor=failing_reload)
        self.assertEqual(failure.exception.code, 'outcome_unknown')
        self.assertEqual(calls, ['alice'])

    def test_profile_to_stock_and_sibling_use_seed_ancestry_without_copying_auth(self):
        import tomllib
        self.owner.execute('accounts.create', {'selector':'bob', 'mode':'independent'})
        (self.stock/'auth.json').write_text('stock-auth')
        (self.alice/'auth.json').write_text('alice-auth')
        (self.alice/'config.toml').write_text('model="alice-new"\ncli_auth_credentials_store="file"\n')
        args = dict(source='alice', destinations=['stock','bob'], categories=['settings'], operation_id='reverse')
        preview = execute(self.owner, 'configuration.sync.preview', args)
        execute(self.owner, 'configuration.sync.apply', dict(args, expected_snapshot=preview['snapshot']))
        bob = Path(self.owner.execute('stores.resolve', {'selector':'bob'})['store']['home'])
        self.assertEqual(tomllib.loads((self.stock/'config.toml').read_text())['model'], 'alice-new')
        self.assertEqual(tomllib.loads((bob/'config.toml').read_text())['model'], 'alice-new')
        self.assertEqual((self.stock/'auth.json').read_text(), 'stock-auth')
        self.assertEqual((self.alice/'auth.json').read_text(), 'alice-auth')
        self.assertEqual(tomllib.loads((bob/'config.toml').read_text())['cli_auth_credentials_store'], 'file')

    def test_seed_materializes_local_links_and_preserves_executable_assets(self):
        (self.stock/'bin').mkdir()
        script = self.stock/'bin'/'hook.sh'
        script.write_text('echo original')
        script.chmod(0o700)
        (self.stock/'hooks').mkdir()
        (self.stock/'hooks'/'run').symlink_to(script)
        self.owner.execute('accounts.create', {'selector':'bob', 'mode':'independent'})
        bob = Path(self.owner.execute('stores.resolve', {'selector':'bob'})['store']['home'])
        copied = bob/'hooks'/'run'
        self.assertFalse(copied.is_symlink())
        self.assertTrue(copied.stat().st_mode & 0o100)
        script.write_text('echo updated')
        args = dict(source='stock', destinations=['bob'], categories=['hooks'], operation_id='mode')
        preview = execute(self.owner, 'configuration.sync.preview', args)
        execute(self.owner, 'configuration.sync.apply', dict(args, expected_snapshot=preview['snapshot']))
        self.assertEqual(copied.read_text(), 'echo updated')
        self.assertTrue(copied.stat().st_mode & 0o100)
