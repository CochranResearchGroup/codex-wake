import json
import tempfile
import unittest
from pathlib import Path


class AccountOperationsTests(unittest.TestCase):
    def test_alias_resolves_isolated_accounts_and_configuration_precedence(self):
        from codex_wake.controller_accounts import ControllerAccounts
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'homes'
            for name in ('alice', 'bob'):
                home = state / ('codex-' + name)
                home.mkdir(parents=True)
                (home / 'config.toml').write_text('model = "native"\n')
            config = root / 'controller-accounts.toml'
            config.write_text(f'''[profiles]
state_root = "{state}"
known_profiles = ["alice", "bob"]
[profiles.aliases]
work = "alice"
[configuration.base]
model = "base"
[configuration.host.local]
model = "host"
[configuration.provider.codex]
model = "provider"
[configuration.account.codex-alice]
model = "account"
''')
            service = ControllerAccounts(config, host='local', environment='wsl:test')
            alice = service.execute('accounts.resolve', {'selector': 'work'})['account']
            bob = service.execute('accounts.resolve', {'selector': 'bob'})['account']
            self.assertEqual(alice['id'], 'codex-alice')
            self.assertNotEqual(alice['home'], bob['home'])
            view = service.execute('configuration.explain', {'selector': 'work'})
            self.assertEqual(view['effective']['model'], 'account')
            self.assertEqual(view['provenance']['model'], 'account:codex-alice')
            self.assertEqual(view['owner'], 'codex-wake')
            self.assertEqual(view['configuration']['mcp']['codex_account_auth'],
                             'tenant-local; independent of MCP identity')

    def test_cli_mcp_and_api_share_alias_and_stale_generation_contract(self):
        import contextlib
        import io
        from codex_wake.cli import main
        from codex_wake.mcp_server import CommandRunner
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'homes'
            (state / 'codex-alice').mkdir(parents=True)
            (root / 'controller-accounts.toml').write_text(f'''[profiles]
state_root = "{state}"
known_profiles = ["alice"]
[profiles.aliases]
work = "alice"
''')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['--wake-root', str(root), 'accounts', 'resolve', 'work', '--json'])
            self.assertEqual(code, 0)
            cli = json.loads(output.getvalue())
            mcp, failed = CommandRunner(wake_root=root).call('wake_controller_account_resolve', {'selector': 'work'})
            self.assertFalse(failed)
            self.assertEqual(cli, mcp)
            target = cli['result']['account']['target']
            (root / 'controller-accounts.toml').write_text((root / 'controller-accounts.toml').read_text() + '\n# revision\n')
            stale, failed = CommandRunner(wake_root=root).call('wake_controller_account_resolve',
                {'selector': 'work', 'expected_target': target})
            self.assertTrue(failed)
            self.assertEqual(stale['error']['code'], 'stale_target')

    def test_wake_profiles_alias_applies_same_effective_configuration_to_launch(self):
        import hashlib
        from codex_wake.profile_compat import main
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'homes'
            (state / 'codex-alice').mkdir(parents=True)
            (state / 'codex-alice' / 'auth.json').write_text('{"fixture": "private"}')
            executable = root / 'fake-codex'
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$CODEX_PROFILE_NAME" "$@" > "$CODEX_HOME/launch.txt"\n')
            executable.chmod(0o700)
            manifest = root / 'builds.json'
            manifest.write_text(json.dumps({'schema_version': 1, 'builds': {'stock': {
                'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                'upstream_version': '0.164.0', 'revision': 'fixture', 'read_schemas': [5], 'source': 'https://github.com/openai/codex/releases/download/rust-v0.164.0/codex'}}}))
            config = root / 'controller-accounts.toml'
            config.write_text(f'''[profiles]
state_root = "{state}"
source_root = "{root / 'seed'}"
known_profiles = ["alice"]
check_upstream_releases = false
[profiles.aliases]
work = "alice"
[configuration.base]
model = "base"
[configuration.account.codex-alice]
model = "account"
''')
            self.assertEqual(main(['--config', str(config), 'run', '--channel', 'stock',
                '--build-manifest', str(manifest), 'work', '--', 'hello']), 0)
            launch = (state / 'codex-alice' / 'launch.txt').read_text()
            self.assertIn('codex-alice', launch)
            self.assertIn('"model"="account"', launch)
            self.assertEqual((state / 'codex-alice' / 'auth.json').read_text(), '{"fixture": "private"}')

    def test_configuration_never_exposes_mcp_environment_secrets(self):
        from codex_wake.controller_accounts import ControllerAccounts
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / 'homes' / 'codex-alice'
            home.mkdir(parents=True)
            (home / 'config.toml').write_text('[mcp_servers.fixture.env]\nSENSITIVE_VALUE = "never-print-this"\n')
            path = root / 'controller-accounts.toml'
            path.write_text(f'[profiles]\nstate_root="{root / "homes"}"\nknown_profiles=["alice"]\n')
            view = ControllerAccounts(path, host='local', environment='test').execute(
                'configuration.explain', {'selector': 'alice'})
            self.assertNotIn('never-print-this', json.dumps(view))

    def test_unknown_unsupported_and_shared_private_state_are_held(self):
        import os
        from codex_wake.controller_accounts import ControllerAccounts
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'homes'
            for name in ('alice', 'bob'):
                (state / ('codex-' + name)).mkdir(parents=True)
            path = root / 'controller-accounts.toml'
            path.write_text(f'[profiles]\nstate_root="{state}"\nknown_profiles=["alice","bob"]\n')
            owner = ControllerAccounts(path, host='local', environment='test')
            for operation, arguments, expected in (
                ('accounts.resolve', {'selector': 'missing'}, 'target_not_found'),
                ('accounts.resolve', {'selector': '../alice'}, 'invalid_argument'),
                ('accounts.resolve', {'selector': 'alice', 'caller': 'owner'}, 'invalid_argument'),
                ('accounts.launch', {'selector': 'alice'}, 'unsupported_operation')):
                with self.assertRaises(InventoryError) as raised:
                    owner.execute(operation, arguments)
                self.assertEqual(raised.exception.code, expected)
            first = state / 'codex-alice' / 'auth.json'
            first.write_text('{"fixture":"private"}')
            os.link(first, state / 'codex-bob' / 'auth.json')
            with self.assertRaises(InventoryError) as raised:
                owner.execute('accounts.resolve', {'selector': 'bob'})
            self.assertEqual(raised.exception.code, 'unsupported_target')

    def test_missing_compatibility_config_never_falls_back_to_operator_home(self):
        import contextlib
        import io
        from codex_wake.profile_compat import main
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict('os.environ', {'HOME': directory}), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['--config', str(Path(directory) / 'missing.toml'), 'status', '--json']), 2)

    def test_native_shared_configuration_change_invalidates_pinned_account(self):
        from codex_wake.controller_accounts import ControllerAccounts
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / 'homes' / 'codex-alice'
            home.mkdir(parents=True)
            native = home / 'config.toml'
            native.write_text('model="first"\n')
            path = root / 'controller-accounts.toml'
            path.write_text(f'[profiles]\nstate_root="{root / "homes"}"\nknown_profiles=["alice"]\n')
            owner = ControllerAccounts(path, host='local', environment='test')
            target = owner.execute('accounts.resolve', {'selector': 'alice'})['account']['target']
            native.write_text('model="changed"\n')
            with self.assertRaises(InventoryError) as raised:
                owner.execute('configuration.explain', {'selector': 'alice', 'expected_target': target})
            self.assertEqual(raised.exception.code, 'stale_target')
