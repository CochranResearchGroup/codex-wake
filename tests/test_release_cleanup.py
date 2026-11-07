"""Explicit cache cleanup through the public release driver."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from codex_wake.release_driver import ReleaseDriver


class ReleaseCleanupTests(unittest.TestCase):
    def fixture(self, root):
        source = root / 'repo'
        source.mkdir()
        (source / 'Cargo.lock').write_text('version = 3\n')
        for argv in [('init', '-q'), ('config', 'user.name', 'Fixture'),
                     ('config', 'user.email', 'fixture@example.invalid'), ('add', '.'),
                     ('commit', '-qm', 'fixture')]:
            subprocess.run(['git', '-C', str(source), *argv], check=True, stdout=subprocess.DEVNULL)
        revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
        recipe = root / 'recipe.json'
        recipe.write_text(json.dumps(dict(source_repository=str(source), target_directory='target')))
        driver = ReleaseDriver(root / 'runs', {'fixture': recipe})
        run = driver.execute('prepare', dict(recipe='fixture', upstream=revision, mod_revision=revision))
        target = Path(run['worktree']) / 'target'
        target.mkdir()
        (target / 'cached-object').write_bytes(b'owned disposable object')
        return driver, run, target

    def test_preview_preserves_contents_and_explicit_cleanup_removes_only_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run, target = self.fixture(Path(directory))
            preview = driver.execute('cleanup', dict(run_id=run['run_id']))['cleanup']
            self.assertEqual(preview['status'], 'preview')
            self.assertTrue(preview['eligible'], preview)
            self.assertTrue((target / 'cached-object').exists())
            result = driver.execute('cleanup', dict(run_id=run['run_id'], confirm=True,
                                                    expected_cache=preview['expected_cache']))['cleanup']
            self.assertEqual(result['status'], 'cleaned', result)
            self.assertFalse(target.exists())
            self.assertTrue((Path(run['worktree']) / 'Cargo.lock').exists())
            self.assertTrue(Path(run['manifest']).exists())

    def test_changed_identity_refuses_without_removing_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run, target = self.fixture(Path(directory))
            preview = driver.execute('cleanup', dict(run_id=run['run_id']))['cleanup']
            (target / 'new-object').write_text('changed after preview')
            result = driver.execute('cleanup', dict(run_id=run['run_id'], confirm=True,
                                                    expected_cache=preview['expected_cache']))['cleanup']
            self.assertEqual(result['status'], 'refused')
            self.assertTrue((target / 'cached-object').exists())
            self.assertTrue((target / 'new-object').exists())

    def test_unresolved_writer_claim_refuses_without_changing_cache(self):
        from codex_wake.release_driver import fingerprint
        with tempfile.TemporaryDirectory() as directory:
            driver, run, target = self.fixture(Path(directory))
            preview = driver.execute('cleanup', dict(run_id=run['run_id']))['cleanup']
            claims = driver.root / 'cache-claims'
            claims.mkdir(mode=0o700)
            (claims / (fingerprint(str(target)) + '.json')).write_text(json.dumps(dict(
                run_id='different-run', cache=str(target))))
            from unittest.mock import patch
            # Filesystem deletion is the external effect boundary: refusal must
            # never call it, even if an erroneous call would later fail.
            with patch('shutil.rmtree', side_effect=AssertionError('cleaner invoked after failed preflight')):
                result = driver.execute('cleanup', dict(run_id=run['run_id'], confirm=True,
                                                        expected_cache=preview['expected_cache']))['cleanup']
            self.assertEqual(result['status'], 'refused')
            self.assertIn('unresolved writer claim', ' '.join(result['reasons']))
            self.assertTrue((target / 'cached-object').exists())

    def test_live_process_reference_refuses_then_becomes_eligible_after_exit(self):
        import sys
        with tempfile.TemporaryDirectory() as directory:
            driver, run, target = self.fixture(Path(directory))
            # A real process cwd is an externally observable reference even when
            # it has no Cargo name or cooperative claim record.
            child = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'], cwd=target)
            try:
                result = driver.execute('cleanup', dict(run_id=run['run_id']))['cleanup']
                self.assertEqual(result['status'], 'refused')
                self.assertIn(str(child.pid), ' '.join(result['reasons']))
                self.assertTrue((target / 'cached-object').exists())
            finally:
                child.terminate()
                child.wait(timeout=5)
            result = driver.execute('cleanup', dict(run_id=run['run_id']))['cleanup']
            self.assertTrue(result['eligible'], result)

    def test_malformed_recipe_cannot_clean_source_package_or_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run, target = self.fixture(Path(directory))
            for selected in (Path(run['worktree']), Path(run['manifest']).parent, target):
                with self.subTest(selected=str(selected)):
                    with driver.locked():
                        state = driver.load(run['run_id'])
                        state['recipe']['target_directory'] = str(selected)
                        if selected == target:
                            state['package'] = dict(path=str(target))
                        driver.save(state)
                    result = driver.execute('cleanup', dict(run_id=run['run_id'], confirm=True,
                                                            expected_cache='untrusted-pin'))['cleanup']
                    self.assertEqual(result['status'], 'refused')
                    self.assertTrue((target / 'cached-object').exists())
                    self.assertTrue(Path(run['manifest']).exists())
                    self.assertTrue((Path(run['worktree']) / 'Cargo.lock').exists())


if __name__ == '__main__':
    unittest.main()
