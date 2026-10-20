"""CI scope selection must fail closed at the executable Git boundary."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_ci_scope.py'


class CIScopeTests(unittest.TestCase):
    def test_only_ordinary_evidence_changes_select_docs_lane(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
            git('init', '-q')
            git('config', 'user.email', 'fixture@example.invalid')
            git('config', 'user.name', 'Fixture')
            (root / 'seed').write_text('base')
            git('add', '.')
            git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            evidence = root / 'docs/dev/evidence/fixture/result.json'
            evidence.parent.mkdir(parents=True)
            evidence.write_text('{"verdict":"PASS"}')
            git('add', '.')
            git('commit', '-qm', 'evidence')
            result = subprocess.run([sys.executable, str(SCRIPT), '--base', base,
                '--head', 'HEAD', '--event', 'pull_request'], cwd=root,
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['scope'], 'docs')

            def scope(event='pull_request', comparison=base):
                output = subprocess.check_output([sys.executable, str(SCRIPT),
                    '--base', comparison, '--head', 'HEAD', '--event', event], cwd=root, text=True)
                return json.loads(output)['scope']

            self.assertEqual(scope('schedule'), 'full')
            self.assertEqual(scope('workflow_dispatch'), 'full')
            self.assertEqual(scope(comparison='missing-ref'), 'full')
            self.assertEqual(scope(comparison='HEAD'), 'full')
            evidence_base = git('rev-parse', 'HEAD')
            for path in ('src/app.py', 'docs/dev/policies/rule.md',
                         '.github/workflows/ci.yml', 'pyproject.toml',
                         'docs/dev/evidence/fixture/run.sh',
                         'docs/dev/evidence/fixture/invalid.json', 'README.md'):
                with self.subTest(path=path):
                    git('reset', '--hard', evidence_base)
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text('change')
                    git('add', '.')
                    git('commit', '-qm', 'non-evidence change')
                    self.assertEqual(scope(comparison=evidence_base), 'full')
            git('reset', '--hard', evidence_base)
            git('mv', 'docs/dev/evidence/fixture/result.json', 'docs/dev/evidence/fixture/renamed.json')
            git('commit', '-qm', 'rename evidence')
            self.assertEqual(scope(comparison=evidence_base), 'full')
            git('reset', '--hard', evidence_base)
            git('rm', 'docs/dev/evidence/fixture/result.json')
            git('commit', '-qm', 'delete evidence')
            self.assertEqual(scope(comparison=evidence_base), 'full')
            git('reset', '--hard', evidence_base)
            evidence.write_text('{"verdict":"UPDATED"}')
            git('add', '.')
            git('commit', '-qm', 'modify evidence')
            self.assertEqual(scope(comparison=evidence_base), 'docs')
            git('reset', '--hard', evidence_base)
            markdown = root / 'docs/dev/evidence/fixture/validation.md'
            markdown.write_text('Reviewed evidence.\n')
            git('add', '.')
            git('commit', '-qm', 'ordinary Markdown')
            self.assertEqual(scope(comparison=evidence_base), 'docs')
            markdown.write_bytes(b'\xff\x00')
            git('add', '.')
            git('commit', '-qm', 'binary evidence')
            self.assertEqual(scope(comparison=evidence_base), 'full')
            git('reset', '--hard', evidence_base)
            evidence.unlink()
            evidence.symlink_to('other.json')
            git('add', '.')
            git('commit', '-qm', 'symlink evidence')
            self.assertEqual(scope(comparison=evidence_base), 'full')


if __name__ == '__main__':
    unittest.main()
