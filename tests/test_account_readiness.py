import json
import os
from pathlib import Path
import tempfile
import unittest

from codex_wake.controller_accounts import ControllerAccounts


class AccountReadinessTests(unittest.TestCase):
    def test_missing_registration_is_actionable_without_claiming_runtime_readiness(self):
        from codex_wake.account_readiness import execute
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / 'homes' / 'codex-alice'
            home.mkdir(parents=True, mode=0o700)
            config = root / 'accounts.toml'
            config.write_text('[profiles]\nstate_root=' + json.dumps(str(root/'homes')) + '\nknown_profiles=["alice"]\n')
            accounts = ControllerAccounts(config, host='fixture', environment='test')
            before = sorted(str(p) for p in root.rglob('*'))
            result = execute(root, {'selector':'alice'}, accounts=accounts)['result']
            self.assertEqual(result['status'], 'incomplete')
            self.assertEqual(result['checks']['build']['state'], 'missing')
            self.assertTrue(result['checks']['build']['remedy'])
            self.assertEqual(result['checks']['limits']['state'], 'not_qualified')
            self.assertEqual(before, sorted(str(p) for p in root.rglob('*')))
