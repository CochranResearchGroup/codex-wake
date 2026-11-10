"""Release preparation at the build-owner seam, using an owned Git repository."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from codex_wake.controller_builds import ControllerBuilds


class ReleasePreparationTests(unittest.TestCase):
    def test_prepare_pins_isolated_source_and_status_survives_new_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
            git('init', '-q')
            git('config', 'user.email', 'fixture@example.invalid')
            git('config', 'user.name', 'Fixture')
            (source / 'Cargo.lock').write_text('version = 3\n')
            git('add', '.')
            git('commit', '-qm', 'fixture')
            revision = git('rev-parse', 'HEAD')
            recipe = root / 'recipe.json'
            recipe.write_text(json.dumps(dict(source_repository=str(source), target='x86_64-unknown-linux-gnu', profile='dev-small')))
            owner = ControllerBuilds(root / 'builds.json', None, recipes={'fixture': recipe})
            result = owner.execute('builds.prepare', dict(recipe='fixture', upstream=revision, mod_revision=revision))
            self.assertEqual(result['status'], 'prepared')
            self.assertEqual(result['source']['upstream'], revision)
            self.assertNotEqual(result['worktree'], str(source))
            self.assertEqual(git('rev-parse', 'HEAD'), revision)
            other = ControllerBuilds(root / 'builds.json', None, recipes={'fixture': recipe})
            state = other.execute('builds.status', {'run_id': result['run_id']})
            self.assertEqual(state['source'], result['source'])
            self.assertEqual(state['recipe']['profile'], 'dev-small')
            self.assertEqual(Path(state['manifest']).stat().st_mode & 0o777, 0o600)
            # Real adapters share the persisted run, not an in-memory test owner.
            import socket
            import os
            import sys
            from codex_wake.mcp_server import CommandRunner
            (root / 'controller-accounts.toml').write_text(
                '[profiles]\nstate_root = ' + json.dumps(str(root / 'homes')) +
                '\nknown_profiles = []\n[builds]\nmanifest = ' + json.dumps(str(root / 'builds.json')) +
                '\n[builds.recipes]\nfixture = ' + json.dumps(str(recipe)) + '\n')
            messaging = root / 'controller-messaging.json'
            messaging.write_text(json.dumps(dict(version=1, local_caller=dict(
                subject='fixture', client_id='fixture', grant_id='fixture', issuer='fixture',
                resource='fixture', scopes=['admin'], expires_at=9999999999,
                targets=[dict(host=socket.gethostname(), environment=os.environ.get('WSL_DISTRO_NAME') or os.name)]))))
            messaging.chmod(0o600)
            cli = subprocess.run([sys.executable, '-m', 'codex_wake.entrypoint', '--wake-root', str(root),
                'builds', 'status', '--run-id', state['run_id'], '--json'], capture_output=True, text=True)
            self.assertEqual(cli.returncode, 0, cli.stderr)
            native, failed = CommandRunner(wake_root=root).call('wake_builds_status', {'run_id': state['run_id']})
            self.assertFalse(failed, native)
            self.assertEqual(json.loads(cli.stdout)['result'], native['result'])
            from types import SimpleNamespace
            from codex_wake.operation_commands import local_actor
            from codex_wake.build_commands import owner_from_root
            from codex_wake.controller_http import ProtectedOperations
            from codex_wake.controller_operations import ControllerOperations
            from codex_wake.managed_inventory import ManagedInventory
            registered = owner_from_root(root)
            operations = ControllerOperations(ManagedInventory(root), host=registered.accounts.host,
                environment=registered.accounts.environment, builds=registered)
            api = ProtectedOperations(SimpleNamespace(authenticate=lambda token: local_actor(root)), operations)
            reply = api.execute('fixture', 'builds.status', {'run_id': state['run_id']})
            self.assertEqual(reply['result'], native['result'])


if __name__ == '__main__':
    unittest.main()
