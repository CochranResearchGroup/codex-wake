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
            return {'account': {'id': 'fixture', 'home': str(home), 'target': {'provider': 'codex'}},
                    'effective': {}, 'provenance': {}}
    owner = ControllerBuilds(manifest, Accounts())
    listed = owner.execute('builds.list', {'account': 'fixture'})
    target = next(row['target'] for row in listed['builds'] if row['name'] == 'modded')
    result = owner.execute('builds.launch', {'account': 'fixture', 'channel': 'modded', 'expected_target': target, 'args': ['fixture prompt']})
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
            owner.execute('builds.launch', {'account': 'fixture', 'channel': 'modded', 'expected_target': target, 'args': ['fixture prompt']})
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
    def test_pure_version_cli_inspection_leaves_locked_legacy_accounts_unchanged(self):
        import fcntl
        import os
        from pathlib import Path
        import stat
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            homes = root / "homes"
            home = homes / "codex-alice"
            shared = homes / "shared"
            home.mkdir(parents=True)
            shared.mkdir()
            (shared / "sessions").mkdir()
            (shared / "sessions/history.jsonl").write_text(
                "synthetic retained history\n"
            )
            (shared / "state_5.sqlite").write_bytes(
                b"synthetic shared database, never opened"
            )
            (shared / "config.toml").write_text(
                "intentionally invalid native configuration"
            )
            (home / "auth.json").write_text('{"fixture_identity":"must-not-be-read"}')
            for name in ("sessions", "state_5.sqlite", "config.toml"):
                (home / name).symlink_to(shared / name)
            config = root / "profiles.toml"
            config.write_text(
                "[profiles]\nstate_root="
                + json.dumps(str(homes))
                + "\nsource_root="
                + json.dumps(str(root / "seed"))
                + '\nknown_profiles=["alice"]\ndefault_profile="alice"\nselection_mode="launcher"\nshared_links=["config.toml","sessions","state_5.sqlite"]\n'
            )
            native = root / "native-version"
            native.write_text(
                "#!" + sys.executable + "\nimport os,sys\nfrom pathlib import Path\n"
                'assert sys.argv[1:] in (["--version"],["-V"])\n'
                'h=Path(os.environ["HOME"]); c=Path(os.environ["CODEX_HOME"])\n'
                "assert h==Path.cwd() and c.is_relative_to(h)\n"
                "assert not h.is_relative_to(Path(" + repr(str(homes)) + "))\n"
                'assert not any(k in os.environ for k in ("OPENAI_API_KEY","CODEX_ACCESS_TOKEN","CODEX_THREAD_ID","CODEX_PROFILE"))\n'
                '(h/"version-marker").write_text("temporary version output")\n'
                'print("codex-cli 9.9.9")\n'
            )
            native.chmod(0o700)
            pin = hashlib.sha256(native.read_bytes()).hexdigest()
            builds = {
                channel: dict(
                    executable=str(native),
                    sha256=pin,
                    upstream_version="9.9.9",
                    revision="fixture",
                    source="https://github.com/openai/codex/releases/download/rust-v9.9.9/codex.tar.gz"
                    if channel == "stock"
                    else "registered fixture",
                    backend="managed",
                )
                for channel in ("stock", "modded")
            }
            (shared / "builds.json").write_text(
                json.dumps(dict(schema_version=1, builds=builds))
            )

            def snapshot():
                result = {}
                for path in [homes, *homes.rglob("*")]:
                    metadata = path.lstat()
                    result[str(path.relative_to(homes))] = dict(
                        inode=metadata.st_ino,
                        mode=metadata.st_mode,
                        size=metadata.st_size,
                        mtime_ns=metadata.st_mtime_ns,
                        ctime_ns=metadata.st_ctime_ns,
                        target=os.readlink(path) if path.is_symlink() else None,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest()
                        if stat.S_ISREG(metadata.st_mode)
                        else None,
                    )
                return result

            lock = home / ".build-channel.lock"
            lock.write_text(
                json.dumps(
                    dict(
                        pid=os.getpid(), channel="modded", start_ticks="retained-owner"
                    )
                )
            )
            lock.chmod(0o600)
            env = {
                key: os.environ[key]
                for key in ("PATH", "LANG", "LC_ALL")
                if key in os.environ
            }
            env.update(
                PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
                CODEX_PROFILES_CONFIG=str(config),
                HOME=str(root / "operator"),
                OPENAI_API_KEY="synthetic-test-key",
                CODEX_ACCESS_TOKEN="synthetic-test-token",
                CODEX_THREAD_ID="synthetic-thread",
                CODEX_PROFILE="synthetic-inherited-profile",
                CODEX_BUILD_UPDATE_CHECK="0",
            )
            with lock.open("r+") as retained:
                fcntl.flock(retained, fcntl.LOCK_EX | fcntl.LOCK_NB)
                before = snapshot()
                for flag in ("--version", "-V"):
                    for entry, arguments, label in (
                        (
                            "main",
                            ["run", "--channel", "modded", "alice", "--", flag],
                            "MODDED",
                        ),
                        ("profile_main", [flag], "MODDED"),
                        ("stock_main", [flag], "STOCK"),
                        ("modded_main", [flag], "MODDED"),
                    ):
                        with self.subTest(entry=entry, flag=flag):
                            command = [
                                sys.executable,
                                "-c",
                                "from codex_wake.profile_compat import "
                                + entry
                                + ";raise SystemExit("
                                + entry
                                + "())",
                                *arguments,
                            ]
                            result = subprocess.run(
                                command,
                                env=env,
                                cwd=root,
                                capture_output=True,
                                text=True,
                                timeout=10,
                            )
                            self.assertEqual(result.returncode, 0, result.stderr)
                            self.assertEqual(result.stdout.strip(), "codex-cli 9.9.9")
                            self.assertIn(label, result.stderr)
                            self.assertIn(pin, result.stderr)
                            self.assertEqual(snapshot(), before)
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "codex_profiles.build_channels",
                            "--config",
                            str(config),
                            "--manifest",
                            str(shared / "builds.json"),
                            "--profile",
                            "alice",
                            "--",
                            flag,
                        ],
                        env=env,
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), "codex-cli 9.9.9")
                    self.assertEqual(snapshot(), before)
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from codex_wake.profile_compat import modded_main;raise SystemExit(modded_main())",
                        "--version",
                        "extra",
                    ],
                    env=env,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertEqual(snapshot(), before)

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
        import shlex
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
            native.write_text('#!/bin/sh\nprintf "effect\\n" >> '+shlex.quote(str(root/'effects'))+'\n')
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
                self.assertEqual((root / 'effects').read_text(), 'effect\n')
            finally:
                server.shutdown(); server.server_close(); thread.join()
