import hashlib
import json

from codex_wake.controller_builds import ControllerBuilds


def test_named_pinned_build_launch_preserves_identity(tmp_path):
    executable = tmp_path / 'native'
    executable.write_text('#!/bin/sh\nprintf "%s" "$CODEX_BUILD_CHANNEL" > "$CODEX_HOME/result"\n')
    executable.chmod(0o700)
    home = tmp_path / 'private'
    home.mkdir()
    manifest = tmp_path / 'builds.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'builds': {'modded': {
        'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'upstream_version': '1', 'revision': 'fixture', 'source': 'local fixture'}}}))
    class Accounts:
        def execute(self, operation, arguments):
            return {'account': {'id': 'fixture', 'home': str(home), 'target': {'provider': 'codex'}}}
    owner = ControllerBuilds(manifest, Accounts())
    listed = owner.execute('builds.list', {'account': 'fixture'})
    target = next(row['target'] for row in listed['builds'] if row['name'] == 'modded')
    result = owner.execute('builds.launch', {'account': 'fixture', 'channel': 'modded', 'expected_target': target, 'args': ['--version']})
    from codex_wake.managed_inventory import InventoryError
    from codex_profiles.build_channels import _home_ownership
    for expected in ({}, dict(target, build_sha256='0' * 64)):
        try:
            owner.execute('builds.launch', {'account': 'fixture', 'channel': 'modded', 'expected_target': expected})
        except InventoryError as error:
            assert error.code == 'stale_target'
        else:
            raise AssertionError('stale build accepted')
    with _home_ownership(home):
        try:
            owner.execute('builds.launch', {'account': 'fixture', 'channel': 'modded', 'expected_target': target})
        except InventoryError as error:
            assert error.code == 'build_held'
        else:
            raise AssertionError('same home concurrent launch accepted')
    assert result['exit_code'] == 0
    assert result['target'] == target
    assert (home / 'result').read_text() == 'modded'


def test_unregistered_recipe_is_unauthorized(tmp_path):
    from codex_wake.managed_inventory import InventoryError
    owner = ControllerBuilds(tmp_path / 'builds.json', None)
    try:
        owner.execute('builds.stage', {'recipe': '/tmp/untrusted'})
    except InventoryError as error:
        assert error.code == 'unauthorized_target'
    else:
        raise AssertionError('untrusted recipe accepted')


import unittest
import tempfile

class BuildTests(unittest.TestCase):
    def test_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            test_named_pinned_build_launch_preserves_identity(__import__('pathlib').Path(directory))

    def test_unauthorized(self):
        with tempfile.TemporaryDirectory() as directory:
            test_unregistered_recipe_is_unauthorized(__import__('pathlib').Path(directory))

    def test_staging_is_repeatable_and_pinned(self):
        import tarfile
        from pathlib import Path
        from codex_profiles import upgrades
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            (source / 'package/bin').mkdir(parents=True)
            binary = source / 'package/bin/codex'
            binary.write_text('#!/bin/sh\nexit 0\n')
            binary.chmod(0o700)
            for name in ('bin/codex-code-mode-host', 'codex-resources/bwrap', 'codex-path/rg'):
                extra = source / 'package' / name
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_bytes(binary.read_bytes())
                extra.chmod(0o700)
            (source / 'package/codex-package.json').write_text('{}')
            archive = root / 'source.tar'
            with tarfile.open(archive, 'w') as stream:
                stream.add(source / 'package', arcname='package')
            recipe = root / 'recipe.json'
            recipe.write_text(json.dumps(dict(schema_version=1, id='fixture', channel='stock',
                upstream_version='1', revision='fixture', package='package',
                source=dict(official_url='https://github.com/openai/codex/releases/download/fixture/source.tar',
                            archive_file=str(archive), sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
                qualify=[['/bin/echo', '{"schema_version":1,"checks":{"official_cli":true}}']],
                read_schemas=[1], write_schema=1)))
            owner = ControllerBuilds(root / 'install/builds.json', None, recipes={'fixture': recipe})
            first = owner.execute('builds.stage', {'recipe': 'fixture'})
            self.assertEqual(first['status'], 'staged', first)
            self.assertEqual(owner.execute('builds.stage', {'recipe': 'fixture'}), first)
            home = root / 'home'
            home.mkdir()
            selected = upgrades.select(root / 'install', home, identifier='fixture')
            self.assertEqual(selected['status'], 'selected')
            payload = json.loads(recipe.read_text())
            payload['id'] = 'successor'
            payload['revision'] = 'second'
            recipe.write_text(json.dumps(payload))
            second = owner.execute('builds.stage', {'recipe': 'fixture'})
            self.assertEqual(second['status'], 'staged')
            upgrades.select(root / 'install', home, identifier='successor')
            rolled = upgrades.select(root / 'install', home, channel='stock', rollback=True)
            self.assertEqual(rolled['id'], 'fixture')

class PublicBuildAdapterTests(unittest.TestCase):
    def test_cli_and_mcp_report_same_pinned_build_envelope(self):
        from pathlib import Path
        import contextlib
        import io
        import socket
        import os
        from codex_wake.cli import main
        from codex_wake.mcp_server import CommandRunner
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            homes = root / 'homes'
            home = homes / 'codex-alice'
            home.mkdir(parents=True)
            native = root / 'native'
            native.write_text('#!/bin/sh\nexit 0\n')
            native.chmod(0o700)
            manifest = root / 'builds.json'
            manifest.write_text(json.dumps({'schema_version': 1, 'builds': {'modded': {
                'executable': str(native), 'sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
                'upstream_version': '1', 'revision': 'fixture', 'source': 'local fixture'}}}))
            (root / 'controller-accounts.toml').write_text('[profiles]\nstate_root = "' + str(homes) + '"\nknown_profiles = ["alice"]\n[builds]\nmanifest = "' + str(manifest) + '"\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['--wake-root', str(root), 'builds', 'list', '--arguments', '{"account":"alice"}'])
            mcp, failed = CommandRunner(wake_root=root).call('wake_builds_list', {'account': 'alice'})
            self.assertFalse(failed)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue()), mcp)

    def test_protected_build_launch_is_durable_across_api_and_mcp_retries(self):
        import base64
        import socket
        import os
        import threading
        from pathlib import Path
        from urllib.request import Request, urlopen
        from codex_wake.controller_auth import OAuthAuthority
        from codex_wake.controller_http import ControllerHTTPServer
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import ManagedInventory
        from codex_wake.build_commands import owner_from_root
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            homes = root / 'homes'
            home = homes / 'codex-alice'
            home.mkdir(parents=True)
            native = root / 'native'
            native.write_text('#!/bin/sh\nprintf "effect\\n" >> "$CODEX_HOME/effects"\n')
            native.chmod(0o700)
            manifest = root / 'builds.json'
            manifest.write_text(json.dumps({'schema_version': 1, 'builds': {'modded': {
                'executable': str(native), 'sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
                'upstream_version': '1', 'revision': 'fixture', 'source': 'local fixture'}}}))
            (root / 'controller-accounts.toml').write_text('[profiles]\nstate_root = "' + str(homes) + '"\nknown_profiles = ["alice"]\n[builds]\nmanifest = "' + str(manifest) + '"\n')
            owner = owner_from_root(root)
            target = next(row['target'] for row in owner.execute('builds.list', {'account': 'alice'})['builds'] if row['name'] == 'modded')
            authority = OAuthAuthority(root / 'oauth.sqlite', issuer='https://wake.test', resource='https://wake.test/mcp')
            client = authority.register({'redirect_uris': ['http://localhost/callback']})
            verifier = 'x' * 43
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            code = authority.authorize(subject='operator', principal_kind='owner', client_id=client['client_id'], redirect_uri=client['redirect_uris'][0], resource=authority.resource, scopes=['observe', 'control'], targets=[target], code_challenge=challenge)
            token = authority.token(dict(grant_type='authorization_code', client_id=client['client_id'], code=code, redirect_uri=client['redirect_uris'][0], code_verifier=verifier, resource=authority.resource))['access_token']
            operations = ControllerOperations(ManagedInventory(root), host=owner.accounts.host,
                environment=owner.accounts.environment, accounts=owner.accounts, builds=owner)
            server = ControllerHTTPServer(('127.0.0.1', 0), authority, operations)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def post(path, data):
                request = Request('http://127.0.0.1:' + str(server.server_port) + path,
                    data=json.dumps(data).encode(), headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
                with urlopen(request, timeout=5) as response:
                    return json.load(response)
            arguments = {'account': 'alice', 'channel': 'modded', 'expected_target': target,
                'args': ['--version'], '_request': {'operation_id': 'launch-one', 'idempotency_key': 'intent-one',
                'correlation_id': 'answer-one', 'binding': 'caller-one', 'target': target}}
            try:
                first = post('/operations', {'operation': 'builds.launch', 'arguments': arguments})
                second = post('/mcp', {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                    'params': {'name': 'wake_builds_launch', 'arguments': arguments}})
                self.assertEqual(first['result']['operation']['execution'], 'completed')
                self.assertEqual(second['result']['structuredContent']['result'], first['result'])
                import subprocess
                import sys
                token_file = root / 'caller-token'
                token_file.write_text(token)
                token_file.chmod(0o600)
                cli = subprocess.run([str(Path(sys.executable).with_name('codex-wake')), 'controller', 'remote',
                    '--endpoint', 'http://127.0.0.1:' + str(server.server_port), '--token-file', str(token_file),
                    'builds.launch', '--arguments', json.dumps(arguments)], capture_output=True, text=True, timeout=5)
                self.assertEqual(cli.returncode, 0, cli.stderr)
                self.assertEqual(json.loads(cli.stdout)['result'], first['result'])
                from dataclasses import asdict
                from codex_wake.mcp_server import CommandRunner
                absent, denied = CommandRunner(wake_root=root).call('wake_builds_launch', arguments)
                self.assertTrue(denied)
                self.assertEqual(absent['error']['code'], 'configuration_unavailable')
                local = asdict(authority.authenticate(token))
                local['scopes'] = sorted(local['scopes'])
                messaging = root / 'controller-messaging.json'
                messaging.write_text(json.dumps({'version': 1, 'local_caller': local}))
                messaging.chmod(0o600)
                native_mcp, failed = CommandRunner(wake_root=root).call('wake_builds_launch', arguments)
                self.assertFalse(failed, native_mcp)
                self.assertEqual(native_mcp['result'], first['result'])
                self.assertEqual((home / 'effects').read_text(), 'effect\n')
            finally:
                server.shutdown(); server.server_close(); thread.join()
