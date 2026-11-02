"""Public lifecycle selection must never redirect a stale account operation."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from codex_wake.cli import main


class DaemonCommandsTests(unittest.TestCase):
    def test_public_status_names_exact_account_and_stale_start_has_no_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / 'accounts/codex-alice'
            home.mkdir(parents=True)
            executable = root / 'native'
            executable.write_text('#!/bin/sh\ntouch "EFFECT"\nmkdir -p "$CODEX_HOME/packages/app-server-daemon/current/bin"\ncp "$0" "$CODEX_HOME/packages/app-server-daemon/current/bin/codex"\nprintf \'{"status":"updated"}\\n\'\n'.replace("EFFECT", str(root / "effect")))
            executable.chmod(0o700)
            import hashlib
            manifest = root / 'builds.json'
            manifest.write_text(json.dumps({'schema_version': 1, 'builds': {'modded': {
                'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                'upstream_version': '0.166.0', 'revision': 'fixture', 'source': 'fixture',
                'read_schemas': [5], 'backend': 'managed'}}}))
            (root / 'controller-accounts.toml').write_text(
                f'[profiles]\nstate_root="{root / "accounts"}"\nknown_profiles=["alice"]\n'
                f'[builds]\nmanifest="{manifest}"\n')
            def cli(*args):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = main(['--wake-root', str(root), 'daemons', *args])
                return code, json.loads(out.getvalue())
            code, status = cli('status', 'alice')
            self.assertEqual(code, 0)
            daemon = status['result']['daemon']
            self.assertEqual(daemon['target']['account'], 'codex-alice')
            self.assertEqual(daemon['state'], 'unavailable')
            changed = dict(daemon['target'], home_generation='replaced')
            code, held = cli('start', 'alice', '--expected-target', json.dumps(changed), '--idempotency-key', 'stale-start')
            self.assertEqual(code, 2)
            self.assertEqual(held['error']['code'], 'stale_target')
            self.assertFalse((root / 'effect').exists())
            code, selected = cli('update', 'alice', '--expected-target', json.dumps(daemon['target']), '--idempotency-key', 'cold-update', '--yes')
            self.assertEqual(code, 0, selected)
            self.assertEqual(selected['result']['operation']['result']['activation'], 'future_start')
