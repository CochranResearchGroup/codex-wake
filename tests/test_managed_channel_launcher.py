"""A registered managed account must never fall through to a private writer."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ManagedChannelLauncherTests(unittest.TestCase):
    def test_failed_managed_start_is_held_without_private_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'accounts'
            (state / 'codex-alice').mkdir(parents=True)
            shared = state / 'shared'
            shared.mkdir()
            binary = root / 'native-fixture'
            binary.write_text('#!/bin/sh\numask > "$FIXTURE_CAPTURE.umask"\n: > "$FIXTURE_CAPTURE.history"\nprintf "%s\\n" "$@" > "$FIXTURE_CAPTURE"\nexit 87\n')
            binary.chmod(0o700)
            (shared / 'builds.json').write_text(json.dumps(dict(schema_version=1, builds=dict(
                modded=dict(executable=str(binary), sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                            upstream_version='0.165.0', revision='fixture', read_schemas=[5],
                            source='local-qualified', backend='managed')))))
            config = root / 'profiles.toml'
            config.write_text('[profiles]\nstate_root=' + json.dumps(str(state)) +
                              '\nselection_mode="launcher"\ndefault_profile="alice"\n'
                              'known_profiles=["alice"]\ncheck_upstream_releases=false\nshared_links=[]\n')
            capture = root / 'native-argv'
            env = dict(os.environ, HOME=str(root), CODEX_PROFILES_CONFIG=str(config),
                       CODEX_BUILD_UPDATE_CHECK='0', FIXTURE_CAPTURE=str(capture),
                       PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
            env.pop('CODEX_WAKE_ACCOUNTS_CONFIG', None)
            command = [sys.executable, '-c',
                       'from codex_wake.profile_compat import modded_main; raise SystemExit(modded_main())',
                       '--no-alt-screen', '-C', str(root)]
            result = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True, timeout=20, umask=0o002)
            self.assertEqual(capture.read_text().splitlines(), ['app-server', 'daemon', 'start'])
            self.assertEqual(result.returncode, 2)
            self.assertIn('account daemon start failed', result.stderr)
            self.assertEqual(int(Path(str(capture) + '.umask').read_text(), 8), 0o077)
            self.assertEqual(Path(str(capture) + '.history').stat().st_mode & 0o777, 0o600)

    def test_private_native_ui_creates_private_history_with_permissive_parent(self):
        for channel, expected_umask in (('modded', 0o077), ('stock', 0o002)):
            with self.subTest(channel=channel), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                state = root / 'accounts'
                (state / 'codex-alice').mkdir(parents=True)
                shared = state / 'shared'
                shared.mkdir()
                binary = root / 'native-fixture'
                binary.write_text('#!/bin/sh\numask > "$FIXTURE_CAPTURE.umask"\n'
                                  ': > "$FIXTURE_CAPTURE.history"\nexit 0\n')
                binary.chmod(0o700)
                (shared / 'builds.json').write_text(json.dumps(dict(schema_version=1, builds=dict(
                    **{channel: dict(executable=str(binary), sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                                upstream_version='0.165.0', revision='fixture', read_schemas=[5],
                                source=('local-qualified' if channel == 'modded' else
                                        'https://github.com/openai/codex/releases/download/fixture'),
                                backend='private')}))))
                config = root / 'profiles.toml'
                config.write_text('[profiles]\nstate_root=' + json.dumps(str(state)) +
                                  '\nselection_mode="launcher"\ndefault_profile="alice"\n'
                                  'known_profiles=["alice"]\ncheck_upstream_releases=false\nshared_links=[]\n')
                capture = root / 'native'
                env = dict(os.environ, HOME=str(root), CODEX_PROFILES_CONFIG=str(config),
                           CODEX_BUILD_UPDATE_CHECK='0', FIXTURE_CAPTURE=str(capture),
                           PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
                env.pop('CODEX_WAKE_ACCOUNTS_CONFIG', None)
                command = [sys.executable, '-c',
                           f'from codex_wake.profile_compat import {channel}_main; raise SystemExit({channel}_main())',
                           '--no-alt-screen', '-C', str(root)]
                # Set umask only in this child, never in the concurrent test runner.
                result = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True,
                                        timeout=20, umask=0o002)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(int(Path(str(capture) + '.umask').read_text(), 8), expected_umask)
                self.assertEqual(Path(str(capture) + '.history').stat().st_mode & 0o777,
                                     0o600 if channel == 'modded' else 0o664)

    def test_managed_lifecycle_timeout_is_held_with_reconciliation_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'accounts'
            (state / 'codex-alice').mkdir(parents=True)
            shared = state / 'shared'
            shared.mkdir()
            binary = root / 'native-fixture'
            binary.write_text('#!/bin/sh\nexit 87\n')
            binary.chmod(0o700)
            (shared / 'builds.json').write_text(json.dumps(dict(schema_version=1, builds=dict(
                modded=dict(executable=str(binary), sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                            upstream_version='0.165.0', revision='fixture', read_schemas=[5],
                            source='local-qualified', backend='managed')))))
            config = root / 'profiles.toml'
            config.write_text('[profiles]\nstate_root=' + json.dumps(str(state)) +
                              '\nselection_mode="launcher"\ndefault_profile="alice"\n'
                              'known_profiles=["alice"]\ncheck_upstream_releases=false\nshared_links=[]\n')
            env = dict(os.environ, HOME=str(root), CODEX_PROFILES_CONFIG=str(config),
                       CODEX_BUILD_UPDATE_CHECK='0',
                       PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
            env.pop('CODEX_WAKE_ACCOUNTS_CONFIG', None)
            # Inject an OS process timeout at the subprocess boundary; no daemon runs.
            program = """import subprocess
original = subprocess.run
def run(command, *args, **kwargs):
    if command[1:4] == ['app-server', 'daemon', 'start']:
        raise subprocess.TimeoutExpired(command, 100)
    return original(command, *args, **kwargs)
subprocess.run = run
from codex_wake.profile_compat import modded_main
raise SystemExit(modded_main())
"""
            result = subprocess.run([sys.executable, '-c', program], cwd=root, env=env,
                                    text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('build launch held: account daemon start timed out', result.stderr)
            self.assertIn('outcome is unknown', result.stderr)
            self.assertIn('reconcile', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
