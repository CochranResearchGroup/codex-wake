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
