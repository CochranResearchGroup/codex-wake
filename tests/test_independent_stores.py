import json
from pathlib import Path
import tempfile
import unittest

from codex_wake.controller_accounts import ControllerAccounts


class IndependentStoreTests(unittest.TestCase):
    def test_stock_identity_survives_login_changes_and_two_seeds_are_private(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            stock = root / 'stock'
            stock.mkdir(mode=0o700)
            (stock / 'config.toml').write_text('model="stock"\n[mcp_servers.demo]\nurl="https://example.invalid"\n')
            (stock / 'auth.json').write_text('{"account":"A"}')
            (stock / 'sessions').mkdir()
            (stock / 'skills').mkdir()
            (stock / 'skills' / 'guide.md').write_text('stock guide')
            owner = ControllerAccounts(root / 'controller-accounts.toml', host='test', environment='wsl')
            owner.execute('accounts.init', {})
            registered = owner.execute('stores.register', {'selector': 'stock', 'home': str(stock)})['store']
            (stock / 'auth.json').write_text('{"account":"B"}')
            self.assertEqual(owner.execute('stores.resolve', {'selector': 'stock'})['store']['store_id'], registered['store_id'])
            for name in ('alice', 'bob'):
                seeded = owner.execute('accounts.create', {'selector': name, 'mode': 'independent', 'source': 'stock'})
                home = Path(seeded['account']['home'])
                self.assertFalse((home / 'config.toml').is_symlink())
                self.assertFalse((home / 'auth.json').exists())
                self.assertFalse((home / 'sessions').exists())
                self.assertEqual((home / 'skills' / 'guide.md').read_text(), 'stock guide')
            alice = Path(owner.execute('stores.resolve', {'selector': 'alice'})['store']['home'])
            (alice / 'skills' / 'guide.md').write_text('alice edit')
            self.assertEqual((stock / 'skills' / 'guide.md').read_text(), 'stock guide')
            self.assertNotIn('"account": "B"', json.dumps(owner.execute('stores.list', {})))

    def test_seed_reports_external_config_dependencies_without_exposing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stock = root / 'stock'
            stock.mkdir(mode=0o700)
            (stock / 'config.toml').write_text('notify=["/outside/private-hook"]\n[mcp_servers.demo.env]\nTOKEN="secret-value"\n')
            owner = ControllerAccounts(root / 'controller-accounts.toml', host='test', environment='wsl')
            owner.execute('accounts.init', {})
            owner.execute('stores.register', {'selector':'stock', 'home':str(stock)})
            result = owner.execute('accounts.create', {'selector':'alice','mode':'independent','source':'stock'})
            self.assertIn({'entry':['notify', '0'], 'scope':'external', 'value':'[redacted]'}, result['inventory']['dependencies'])
            self.assertNotIn('private-hook', json.dumps(result))
            self.assertNotIn('secret-value', json.dumps(result))

    def test_seed_materializes_external_skill_links_and_syncs_their_updates(self):
        from codex_wake.configuration_sync import execute
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stock = root / 'stock'
            stock.mkdir(mode=0o700)
            (stock / 'config.toml').write_text('model="stock"\n')
            assets = root / 'configured-skills'
            assets.mkdir()
            (assets / 'SKILL.md').write_text('first skill revision')
            (stock / 'skills').mkdir()
            (stock / 'skills' / 'demo').symlink_to(assets)
            owner = ControllerAccounts(root / 'controller-accounts.toml', host='test', environment='wsl')
            owner.execute('accounts.init', {})
            owner.execute('stores.register', {'selector':'stock','home':str(stock)})
            created = owner.execute('accounts.create', {'selector':'alice','mode':'independent','source':'stock'})
            copied = Path(created['account']['home']) / 'skills' / 'demo'
            self.assertFalse(copied.is_symlink())
            self.assertEqual((copied / 'SKILL.md').read_text(), 'first skill revision')
            (assets / 'SKILL.md').write_text('second skill revision')
            self.assertEqual((copied / 'SKILL.md').read_text(), 'first skill revision')
            args = dict(source='stock',destinations=['alice'],categories=['skills'],operation_id='skill-update')
            preview = execute(owner,'configuration.sync.preview',args)
            execute(owner,'configuration.sync.apply',dict(args,expected_snapshot=preview['snapshot']))
            self.assertEqual((copied / 'SKILL.md').read_text(), 'second skill revision')

    def test_skill_seed_reports_runtime_environment_instead_of_copying_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stock = root / 'stock'
            skill = stock / 'skills' / 'demo'
            skill.mkdir(parents=True)
            stock.chmod(0o700)
            (skill / 'SKILL.md').write_text('Use the skill; install its runtime dependencies separately.')
            (skill / '.venv').mkdir()
            (skill / '.venv' / 'large-runtime.so').write_bytes(b'x' * (4 * 1024 * 1024 + 1))
            owner = ControllerAccounts(root / 'controller-accounts.toml', host='test', environment='wsl')
            owner.execute('accounts.init', {})
            owner.execute('stores.register', {'selector':'stock','home':str(stock)})
            result = owner.execute('accounts.create', {'selector':'alice','mode':'independent','source':'stock'})
            home = Path(result['account']['home'])
            self.assertTrue((home / 'skills/demo/SKILL.md').is_file())
            self.assertFalse((home / 'skills/demo/.venv').exists())
            self.assertIn({'entry':'skills/demo/.venv','reason':'runtime_dependency_not_copied'}, result['inventory']['unsupported_entries'])
