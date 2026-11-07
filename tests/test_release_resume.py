"""Resume behavior at the public release-run seam with real Cargo Signal jobs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from codex_wake.release_driver import ReleaseDriver


class ReleaseResumeTests(unittest.TestCase):
    def fixture(self, root):
        source = root / 'repo'
        source.mkdir()
        (source / '.gitignore').write_text('out/\npackage/\n')
        (source / 'a.txt').write_text('A')
        (source / 'b.txt').write_text('B')
        (source / 'builder.py').write_text("""from pathlib import Path
import sys
name = sys.argv[1]
out = Path('out'); out.mkdir(exist_ok=True)
if name in ('a', 'b'):
    (out / name).write_text(Path(name + '.txt').read_text())
else:
    p = Path('package/bin'); p.mkdir(parents=True, exist_ok=True)
    f = p / 'codex'; f.write_text('#!/bin/sh\\n# ' + (out / 'a').read_text() + (out / 'b').read_text() + '\\n'); f.chmod(0o700)
    Path('package/codex-package.json').write_text('{}')
""")
        for args in [('init', '-q'), ('config', 'user.name', 'Fixture'), ('config', 'user.email', 'fixture@example.invalid'), ('add', '.'), ('commit', '-qm', 'fixture')]:
            subprocess.run(['git', '-C', str(source), *args], check=True, stdout=subprocess.DEVNULL)
        revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
        steps = [dict(name=name, argv=[sys.executable, 'builder.py', name], inputs=['builder.py', name+'.txt'], outputs=['out/'+name], depends_on=[]) for name in ('a','b')]
        steps.append(dict(name='package', argv=[sys.executable,'builder.py','package'], inputs=['builder.py'], outputs=['package/bin/codex','package/codex-package.json'], depends_on=['a','b']))
        recipe = root / 'recipe.json'
        recipe.write_text(json.dumps(dict(source_repository=str(source), timeout_seconds=10, build_steps=steps, package_directory='package', required_artifacts=['bin/codex','codex-package.json'])))
        driver = ReleaseDriver(root / 'runs', {'fixture':recipe})
        return driver, driver.execute('prepare', dict(recipe='fixture', upstream=revision, mod_revision=revision))

    def settle(self, driver, run, operation='build'):
        deadline = time.monotonic()+20
        while time.monotonic()<deadline:
            result = driver.execute(operation, dict(run_id=run['run_id'], output='json'))
            if result['status'] not in ('building','prepared'):
                return result
            time.sleep(.03)
        self.fail('run did not settle')

    def test_changed_input_rebuilds_dependents_but_reuses_independent_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run = self.fixture(Path(directory))
            first = self.settle(driver, run)
            self.assertEqual(first['status'], 'built')
            old_attempt = first['stages']['a']['attempts'][0]
            (Path(run['worktree']) / 'a.txt').write_text('A2')
            result = self.settle(driver, run, 'resume')
            self.assertEqual(result['status'], 'built')
            self.assertEqual([len(result['stages'][x]['attempts']) for x in ('a','b','package')], [2,1,2])
            self.assertEqual(result['stages']['a']['attempts'][0], old_attempt)
            self.assertEqual(result['resume_summary']['reused'], ['b'])
            self.assertEqual(result['resume_summary']['invalidated'], ['a','package'])
            self.assertIn('A2B', (Path(result['package']['path'])/'bin/codex').read_text())

    def test_new_client_reconciles_running_job_and_missing_receipt_stays_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            driver, run = self.fixture(root)
            first = driver.execute('build', dict(run_id=run['run_id'], output='json'))
            stage = first['stages']['a']
            job = Path(stage['job_dir'])
            deadline = time.monotonic()+15
            while time.monotonic()<deadline:
                response = subprocess.run(['cargo-signal', 'status', '--brief', str(job)], capture_output=True, text=True, check=True)
                if json.loads(response.stdout)['status'] != 'running':
                    break
                time.sleep(.02)
            else:
                self.fail('owned worker did not finish')
            # The worker is terminal but the client's receipt storage becomes
            # unavailable before it can reconcile its recorded running state.
            job.rename(job.with_name(job.name+'-retained'))
            replacement = ReleaseDriver(driver.root, driver.recipes)
            result = replacement.execute('resume', dict(run_id=run['run_id'], output='json'))
            self.assertEqual(result['status'], 'unknown')
            self.assertEqual(result['resume_summary']['unresolved'], ['a'])
            retry = replacement.execute('resume', dict(run_id=run['run_id'], output='json'))
            self.assertEqual(len(retry['stages']['a']['attempts']), 1)
            self.assertEqual(set(retry['stages']), {'a'})

    def test_new_client_keeps_one_running_attempt_until_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run = self.fixture(Path(directory))
            tree = Path(run['worktree'])
            builder = tree/'builder.py'
            builder.write_text(builder.read_text().replace("if name in ('a', 'b'):", "if name == 'a':\n    import time\n    (out/'started').touch()\n    while not (out/'release').exists(): time.sleep(.01)\nif name in ('a', 'b'):"))
            first = driver.execute('build', dict(run_id=run['run_id'], output='json'))
            try:
                deadline = time.monotonic()+10
                while not (tree/'out/started').exists():
                    if time.monotonic() > deadline:
                        self.fail('owned step never announced readiness')
                    time.sleep(.01)
                replacement = ReleaseDriver(driver.root, driver.recipes)
                result = replacement.execute('resume', dict(run_id=run['run_id'], output='json'))
                self.assertEqual(result['status'], 'building')
                self.assertEqual(result['stages']['a']['job_dir'], first['stages']['a']['job_dir'])
                self.assertEqual(len(result['stages']['a']['attempts']), 1)
            finally:
                (tree/'out').mkdir(exist_ok=True)
                (tree/'out/release').touch()
            result = self.settle(replacement, run, 'resume')
            self.assertEqual(result['status'], 'built')
            self.assertEqual(len(result['stages']['a']['attempts']), 1)

    def test_tampered_output_is_rebuilt_even_when_inputs_match(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run = self.fixture(Path(directory))
            result = self.settle(driver, run)
            (Path(result['package']['path'])/'bin/codex').write_text('tampered')
            result = self.settle(driver, run, 'resume')
            self.assertEqual(result['status'], 'built')
            self.assertEqual([len(result['stages'][x]['attempts']) for x in ('a','b','package')], [1,1,2])
            self.assertEqual(result['resume_summary']['reused'], ['a','b'])
            self.assertEqual(result['resume_summary']['invalidated'], ['package'])

    def test_changed_source_withdraws_adoption_and_executes_the_build(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run = self.fixture(Path(directory))
            original = self.settle(driver, run)
            recipe_path = Path(driver.recipes['fixture'])
            recipe = json.loads(recipe_path.read_text())
            recipe['retained_package'] = dict(path=original['package']['path'], files=original['package']['files'],
                binding=dict(source_revision=run['source']['mod_revision'], target=None, profile=None, features=[]))
            recipe_path.write_text(json.dumps(recipe))
            adopted = driver.execute('prepare', dict(recipe='fixture', upstream=run['source']['upstream'], mod_revision=run['source']['mod_revision']))
            result = driver.execute('build', dict(run_id=adopted['run_id']))
            self.assertTrue(result['package']['reused'])
            (Path(adopted['worktree'])/'a.txt').write_text('A3')
            result = self.settle(driver, adopted, 'resume')
            self.assertEqual(result['status'], 'built')
            self.assertFalse(result['package']['reused'])
            self.assertEqual(set(result['resume_summary']['executed']), {'a','b','package'})
            self.assertIn('A3B', (Path(result['package']['path'])/'bin/codex').read_text())

    def test_retry_retains_failed_attempt_and_successful_independent_work(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run = self.fixture(Path(directory))
            builder = Path(run['worktree'])/'builder.py'
            code = builder.read_text()
            builder.write_text(code.replace("name = sys.argv[1]", "name = sys.argv[1]\nif name == 'b' and not Path('out/failed-once').exists():\n    Path('out/failed-once').write_text('failure retained')\n    raise SystemExit(7)"))
            first = self.settle(driver, run)
            self.assertEqual(first['status'], 'failed')
            failed_attempt = first['stages']['b']['attempts'][0]
            self.assertEqual(failed_attempt['receipt']['exit_code'], 7)
            result = self.settle(driver, run, 'resume')
            self.assertEqual(result['status'], 'built')
            self.assertEqual(len(result['stages']['a']['attempts']), 1)
            self.assertEqual(result['stages']['b']['attempts'][0], failed_attempt)
            self.assertEqual(len(result['stages']['b']['attempts']), 2)


if __name__ == '__main__':
    unittest.main()
