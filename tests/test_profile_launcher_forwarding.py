"""Channel launchers preserve native option order at the subprocess boundary."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ChannelLauncherForwardingTests(unittest.TestCase):
    def test_stock_and_modded_forward_leading_native_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'accounts'
            (state / 'codex-alice').mkdir(parents=True)
            shared = state / 'shared'
            shared.mkdir()
            executable = root / 'native-fixture'
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$FIXTURE_CAPTURE"\n')
            executable.chmod(0o700)
            record = dict(executable=str(executable),
                          sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                          upstream_version='0.165.0', revision='fixture', read_schemas=[5],
                          source='local-qualified')
            (shared / 'builds.json').write_text(json.dumps(dict(
                schema_version=1, builds=dict(stock=dict(record, source=
                    'https://github.com/openai/codex/releases/download/rust-v0.165.0/codex'),
                    modded=record))))
            config = root / 'profiles.toml'
            config.write_text('[profiles]\nstate_root=' + json.dumps(str(state)) +
                              '\nselection_mode="launcher"\ndefault_profile="alice"\n'
                              'known_profiles=["alice"]\ncheck_upstream_releases=false\nshared_links=[]\n')
            native_args = ['--no-alt-screen', '-C', str(root), 'resume', 'fixture-thread']
            for channel in ('stock', 'modded'):
                with self.subTest(channel=channel):
                    capture = root / (channel + '-argv')
                    env = dict(os.environ, HOME=str(root), CODEX_PROFILES_CONFIG=str(config),
                               CODEX_BUILD_UPDATE_CHECK='0', FIXTURE_CAPTURE=str(capture),
                               PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
                    env.pop('CODEX_WAKE_ACCOUNTS_CONFIG', None)
                    command = [sys.executable, '-c',
                               'from codex_wake.profile_compat import ' + channel + '_main; '
                               'raise SystemExit(' + channel + '_main())', *native_args]
                    result = subprocess.run(command, cwd=root, env=env, text=True,
                                            capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(capture.read_text().splitlines()[-len(native_args):], native_args)
