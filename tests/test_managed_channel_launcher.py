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
            binary.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$FIXTURE_CAPTURE"\nexit 87\n')
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
            result = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True, timeout=20)
            self.assertEqual(capture.read_text().splitlines(), ['app-server', 'daemon', 'start'])
            self.assertEqual(result.returncode, 2)
            self.assertIn('account daemon start failed', result.stderr)
