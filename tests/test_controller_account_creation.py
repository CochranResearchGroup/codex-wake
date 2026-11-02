"""Public setup must create usable private accounts without adopting credentials."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from codex_wake.cli import main


class AccountCreationTests(unittest.TestCase):
    def invoke(self, root, *arguments, expected=0):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(['--wake-root', str(root), 'accounts', *arguments, '--json'])
        self.assertEqual(status, expected, output.getvalue())
        return json.loads(output.getvalue())

    def test_setup_creates_two_private_accounts_and_explains_shared_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.invoke(root, 'init')
            first = self.invoke(root, 'create', 'alice', '--alias', 'work')['result']['account']
            second = self.invoke(root, 'create', 'bob')['result']['account']
            self.assertEqual(first['id'], 'codex-alice')
            self.assertNotEqual(first['home'], second['home'])
            self.assertEqual(self.invoke(root, 'resolve', 'work')['result']['account']['id'], 'codex-alice')
            self.assertEqual(len(self.invoke(root, 'list')['result']['accounts']), 2)
            for account in (first, second):
                home = Path(account['home'])
                self.assertEqual(home.stat().st_mode & 0o777, 0o700)
                self.assertFalse((home / 'auth.json').exists())
                self.assertTrue((home / 'skills').is_symlink())
            from codex_wake.account_commands import execute
            view = execute('configuration.explain', {'selector': 'work'}, root)['result']
            self.assertTrue(view['configuration']['settings']['shared'])
            self.assertTrue(view['configuration']['skills']['shared'])
            self.assertEqual(view['configuration']['mcp']['servers'], [])

    def test_creation_does_not_silently_widen_an_explicit_account_admission_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.invoke(root, 'init')
            self.invoke(root, 'create', 'alice')
            registry = root / 'controller-accounts.toml'
            original = registry.read_text().replace('[accounts]', '[accounts]\nenabled = ["codex-alice"]')
            registry.write_text(original)
            result = self.invoke(root, 'create', 'bob', expected=2)
            self.assertEqual(result['error']['code'], 'unsupported_target')
            self.assertEqual(registry.read_text(), original)
            self.assertFalse((root / 'accounts' / 'codex-bob').exists())

    def test_repeats_and_conflicts_preserve_registry_credentials_and_unrelated_scopes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.invoke(root, 'init')
            registry = root / 'controller-accounts.toml'
            registry.write_text(registry.read_text() + '\n[configuration.base]\nmodel = "base"\n[history]\nreadable_accounts = ["alice"]\n')
            first = self.invoke(root, 'create', 'alice', '--alias', 'work')['result']['account']
            auth = Path(first['home']) / 'auth.json'
            auth.write_text('{"synthetic": "preserve-me"}')
            before = registry.read_bytes()
            self.assertFalse(self.invoke(root, 'init')['result']['created'])
            self.assertFalse(self.invoke(root, 'create', 'alice', '--alias', 'work')['result']['created'])
            collision = self.invoke(root, 'create', 'bob', '--alias', 'work', expected=2)
            self.assertEqual(collision['error']['code'], 'conflict')
            self.assertEqual(registry.read_bytes(), before)
            self.assertEqual(auth.read_text(), '{"synthetic": "preserve-me"}')
            self.invoke(root, 'create', 'bob')
            self.assertIn('[history]\nreadable_accounts = ["alice"]', registry.read_text())
            self.assertIn('[configuration.base]\nmodel = "base"', registry.read_text())

    def test_invalid_names_and_symlink_homes_are_not_adopted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.invoke(root, 'init')
            invalid = self.invoke(root, 'create', '../elsewhere', expected=2)
            self.assertEqual(invalid['error']['code'], 'invalid_argument')
            target = root / 'untouched'
            target.mkdir(mode=0o700)
            (root / 'accounts' / 'codex-alice').symlink_to(target, target_is_directory=True)
            result = self.invoke(root, 'create', 'alice', expected=2)
            self.assertEqual(result['error']['code'], 'conflict')
            self.assertEqual(list(target.iterdir()), [])

    def test_initialization_preserves_an_existing_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / 'controller-accounts.toml'
            registry.write_text('[profiles]\nstate_root = "/example/preserved"\n')
            result = self.invoke(root, 'init', expected=2)
            self.assertEqual(result['error']['code'], 'conflict')
            self.assertEqual(registry.read_text(), '[profiles]\nstate_root = "/example/preserved"\n')
            self.assertFalse((root / 'accounts').exists())

    def test_registry_lock_holds_concurrent_mutation_without_effects(self):
        import fcntl
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.invoke(root, 'init')
            descriptor = os.open(root / '.accounts.lock', os.O_RDWR)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = self.invoke(root, 'create', 'alice', expected=2)
                self.assertEqual(result['error']['code'], 'operation_in_progress')
                self.assertEqual(self.invoke(root, 'list')['result']['accounts'], [])
            finally:
                os.close(descriptor)

    def test_unqualified_peer_prevents_partial_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.invoke(root, 'init')
            first = self.invoke(root, 'create', 'alice')['result']['account']
            outside = root / 'existing-auth'
            outside.write_text('preserved')
            (Path(first['home']) / 'auth.json').symlink_to(outside)
            before = (root / 'controller-accounts.toml').read_bytes()
            result = self.invoke(root, 'create', 'bob', expected=2)
            self.assertEqual(result['error']['code'], 'unsupported_target')
            self.assertEqual((root / 'controller-accounts.toml').read_bytes(), before)
            self.assertFalse((root / 'accounts' / 'codex-bob').exists())


if __name__ == '__main__':
    unittest.main()
