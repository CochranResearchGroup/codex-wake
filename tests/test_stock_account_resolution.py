import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_accounts import ControllerAccounts


class StockAccountResolutionTests(unittest.TestCase):
    def test_registered_stock_is_resolved_without_account_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stock = root / 'stock'
            stock.mkdir(mode=0o700)
            (stock / 'config.toml').write_text('model="stock"\n')
            owner = ControllerAccounts(root / 'controller-accounts.toml', host='fixture', environment='wsl')
            owner.execute('accounts.init', {})
            store = owner.execute('stores.register', {'selector':'stock', 'home':str(stock)})['store']
            row = owner.execute('accounts.resolve', {'selector':'stock'})['account']
            self.assertEqual(row['home'], str(stock))
            self.assertEqual(row['store_id'], store['store_id'])
            self.assertEqual(owner.execute('configuration.explain', {'selector':'stock'})['effective']['model'], 'stock')
            self.assertEqual(list(stock.iterdir()), [stock / 'config.toml'])
