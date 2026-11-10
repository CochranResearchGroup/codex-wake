"""Human output and machine contracts at the public CLI seam."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from codex_wake.entrypoint import main


class CLIPresentationTests(unittest.TestCase):
    def test_accounts_list_is_readable_even_when_redirected_and_json_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            homes = root / 'homes'
            (homes / 'codex-alice').mkdir(parents=True)
            (root / 'controller-accounts.toml').write_text(
                f'[profiles]\nstate_root = "{homes}"\nknown_profiles = ["alice"]\n'
                '[profiles.aliases]\nwork = "alice"\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['--wake-root', str(root), 'accounts', 'list'])
            self.assertEqual(code, 0)
            text = output.getvalue()
            self.assertIn('ACCOUNT', text)
            self.assertIn('ALIASES', text)
            self.assertIn('codex-alice', text)
            self.assertIn('work', text)
            self.assertNotIn('configuration_revision', text)
            self.assertNotIn('schema_version', text)
            self.assertFalse(text.lstrip().startswith('{'))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['--wake-root', str(root), 'accounts', 'list', '--json'])
            self.assertEqual(code, 0)
            value = json.loads(output.getvalue())
            self.assertEqual(value['operation'], 'accounts.list')
            self.assertEqual(value['schema_version'], 1)
            self.assertEqual(value['result']['accounts'][0]['id'], 'codex-alice')
            self.assertIn('configuration_revision', value['result']['accounts'][0]['target'])

    def test_empty_accounts_and_missing_account_explain_the_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'controller-accounts.toml').write_text(
                f'[profiles]\nstate_root = "{root / "homes"}"\nknown_profiles = []\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['--wake-root', str(root), 'accounts', 'list'])
            self.assertEqual(code, 0)
            self.assertEqual(output.getvalue(), 'No accounts found.\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['--wake-root', str(root), 'accounts', 'resolve', 'missing'])
            self.assertEqual(code, 2)
            self.assertIn('Error:', output.getvalue())
            self.assertIn('target_not_found', output.getvalue())
            self.assertNotIn('schema_version', output.getvalue())

    def test_resolve_has_readable_details_and_keeps_complete_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / 'homes' / 'codex-alice'
            home.mkdir(parents=True)
            (root / 'controller-accounts.toml').write_text(
                f'[profiles]\nstate_root = "{home.parent}"\nknown_profiles = ["alice"]\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['--wake-root', str(root), 'accounts', 'resolve', 'alice'])
            self.assertEqual(code, 0)
            self.assertIn('Account:', output.getvalue())
            self.assertIn('Id: codex-alice', output.getvalue())
            self.assertIn('Home: ' + str(home), output.getvalue())
            self.assertNotIn('home_generation', output.getvalue())

    def test_nested_history_content_and_owner_remain_visible_in_human_details(self):
        from types import SimpleNamespace
        from codex_wake.cli_output import emit
        output = io.StringIO()
        emit({'status': 'completed', 'result': {'owner': 'codex-alice', 'records': [
            {'type': 'response_item', 'payload': {'content': [
                {'type': 'output_text', 'text': 'First line\nSecond line'}]}}]}},
             SimpleNamespace(as_json=False), file=output)
        text = output.getvalue()
        self.assertIn('Owner: codex-alice', text)
        self.assertIn('First line', text)
        self.assertIn('Second line', text)
        self.assertNotIn("{'content'", text)

    def test_ssh_and_explicit_transcript_errors_keep_json_frames(self):
        import os
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
            for args, stream in [
                (['hosts', 'ssh-serve', '--principal-id', 'missing', '--target', '{}'], 'stdout'),
                (['control', 'output', 'missing', '--mode', 'transcript'], 'stderr'),
                (['operations', 'stream', 'missing'], 'stdout'),
            ]:
                with self.subTest(args=args):
                    result = subprocess.run([sys.executable, '-m', 'codex_wake.entrypoint',
                        '--wake-root', directory, *args], input='{}', capture_output=True,
                        text=True, env=env, timeout=10)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    value = json.loads(getattr(result, stream))
                    self.assertEqual(value['status'], 'failed')
                    self.assertIn('error', value)
