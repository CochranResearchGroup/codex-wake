"""Local profile command delegates source qualification with isolated state."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / 'scripts/local_validation.py'


class LocalValidationTests(unittest.TestCase):
    def test_public_profile_isolates_account_and_preserves_first_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repo = base / 'repo'
            repo.mkdir()
            for args in [('init', '-q'), ('config', 'user.email', 'fixture@example.invalid'),
                         ('config', 'user.name', 'Fixture')]:
                subprocess.run(['git', '-C', str(repo), *args], check=True)
            (repo / 'source').write_text('original')
            subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(repo), 'commit', '-qm', 'fixture'], check=True)
            profile = base / 'profile.json'
            profile.write_text(json.dumps({'tiers': {'focused': [
                {'name': 'account isolation', 'argv': ['{runtime}', '-c',
                 "import os; from pathlib import Path; assert not Path(os.environ['HOME'], 'credential').exists(); assert 'SECRET_TOKEN' not in os.environ; print(os.environ['CODEX_HOME'])"]},
                {'name': 'required failure', 'argv': ['{runtime}', '-c', 'raise SystemExit(23)']},
                {'name': 'later success', 'argv': ['{runtime}', '-c', 'pass']}]}}))
            (base / 'credential').write_text('private')
            receipt = base / 'receipt.json'
            command = [sys.executable, str(LAUNCHER), '--repo', str(repo), '--runtime', sys.executable,
                       '--profile', str(profile), '--receipt', str(receipt), '--tier', 'focused']
            result = subprocess.run(command, env={**os.environ, 'HOME': str(base), 'SECRET_TOKEN': 'secret'}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            data = json.loads(receipt.read_text())
            self.assertEqual([row['status'] for row in data['checks']], ['PASS', 'FAIL', 'BLOCKED'])
            self.assertEqual(data['checks'][1]['returncode'], 23)
            self.assertEqual(data['actions'], [])
            self.assertEqual(data['profile']['tier'], 'focused')
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            original = receipt.read_bytes()
            subprocess.run(command, capture_output=True)
            self.assertEqual(receipt.read_bytes(), original)

    def test_setup_names_missing_build_dependency(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / 'runtime'
            subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(runtime)], check=True, capture_output=True)
            receipt = Path(temp) / 'setup.json'
            result = subprocess.run([sys.executable, str(LAUNCHER), '--repo', str(ROOT), '--runtime', str(runtime / 'bin/python'), '--tier', 'presubmit', '--receipt', str(receipt)], capture_output=True, text=True)
            data = json.loads(receipt.read_text())
            self.assertEqual(data['checks'][0]['status'], 'FAIL')
            self.assertIn('build', data['checks'][0]['stdout'])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('build', result.stdout + result.stderr)
            self.assertIn('setup', result.stdout + result.stderr)

    def test_real_planning_header_failure_then_corrected_fresh_receipt(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repo = base / 'repo'
            repo.mkdir()
            shutil.copytree(ROOT / 'docs/dev', repo / 'docs/dev')
            for name in ('ROADMAP.md', 'RUNBOOK.md', 'AGENTS.md'):
                shutil.copyfile(ROOT / name, repo / name)
            audit = '.codex/skills/repo-policy-selector/scripts/audit_planning_contract.py'
            (repo / audit).parent.mkdir(parents=True)
            shutil.copyfile(ROOT / audit, repo / audit)
            plan = repo / 'docs/dev/plans/9999-2026-10-31-regression.md'
            plan.write_text('# Header regression\n\nState: malformed\n\n## Current State\nHistorical fixture.\n')
            for args in [('init', '-q'), ('config', 'user.email', 'fixture@example.invalid'),
                         ('config', 'user.name', 'Fixture'), ('add', '.'), ('commit', '-qm', 'fixture')]:
                subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)
            profile = base / 'profile.json'
            profile.write_text(json.dumps({'tiers': {'focused': [
                {'name': 'active planning audit', 'axis': 'planning', 'argv': ['{runtime}', audit, '--repo-root', '.', '--active-only', '--json']},
                {'name': 'later success', 'argv': ['{runtime}', '-c', 'pass']}]}}))
            def run(receipt):
                return subprocess.run([sys.executable, str(LAUNCHER), '--repo', str(repo), '--runtime', sys.executable,
                                       '--profile', str(profile), '--tier', 'focused', '--receipt', str(receipt)], capture_output=True, text=True)
            failed = base / 'failed.json'
            self.assertEqual(run(failed).returncode, 1)
            first = failed.read_bytes()
            data = json.loads(first)
            self.assertEqual([x['status'] for x in data['checks']], ['FAIL', 'BLOCKED'])
            self.assertIn('missing deterministic state', data['checks'][0]['stdout'])
            plan.write_text('# Header regression\n\nState: CLOSED\n\n## Current State\nHistorical fixture.\n')
            passed = base / 'passed.json'
            result = run(passed)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(passed.read_text())['status'], 'PASS')
            self.assertEqual(failed.read_bytes(), first)

    def test_required_timeout_names_operation_and_blocks_remaining_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repo = base / 'repo'
            repo.mkdir()
            for args in [('init', '-q'), ('config', 'user.email', 'fixture@example.invalid'),
                         ('config', 'user.name', 'Fixture'), ('commit', '--allow-empty', '-qm', 'fixture')]:
                subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)
            profile = base / 'profile.json'
            profile.write_text(json.dumps({'tiers': {'focused': [
                {'name': 'bounded check', 'argv': ['{runtime}', '-c', 'import time; time.sleep(30)']},
                {'name': 'later success', 'argv': ['{runtime}', '-c', 'pass']}]}}))
            receipt = base / 'receipt.json'
            result = subprocess.run([sys.executable, str(LAUNCHER), '--repo', str(repo), '--runtime', sys.executable,
                                     '--profile', str(profile), '--tier', 'focused', '--receipt', str(receipt), '--timeout', '0.05'], capture_output=True)
            self.assertEqual(result.returncode, 1)
            data = json.loads(receipt.read_text())
            self.assertEqual([x['status'] for x in data['checks']], ['FAIL', 'BLOCKED'])
            self.assertIn('timed out', data['checks'][0]['error'])
            self.assertEqual(data['checks'][0]['name'], 'bounded check')
