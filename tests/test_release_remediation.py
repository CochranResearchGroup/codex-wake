"""Review regressions at the public release-driver and native discovery seams."""
import json
import importlib.util
from pathlib import Path
import tempfile
import time
import unittest

import sys
import test_release_qualification as qualification_fixture


class ReleaseReviewRegressionTests(unittest.TestCase):
    def test_resume_retains_active_qualification_before_source_invalidation(self):
        fixture = qualification_fixture.ReleaseQualificationTests()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            driver, run = fixture.fixture(root)
            recipe_path = root / 'recipe.json'
            recipe = json.loads(recipe_path.read_text())
            recipe['build_steps'] = [dict(name='package', argv=[sys.executable, '-c', "raise RuntimeError('must not build while qualification runs')"], inputs=['Cargo.lock'])]
            recipe_path.write_text(json.dumps(recipe))
            run = driver.execute('prepare', dict(recipe='fixture', upstream=run['source']['upstream'], mod_revision=run['source']['mod_revision']))
            run = driver.execute('build', dict(run_id=run['run_id']))
            helper = root / 'qualify.py'
            original = helper.read_text()
            gate = root / 'allow-qualification'
            helper.write_text('import time\nfrom pathlib import Path\nwhile not Path(' + repr(str(gate)) + ').exists(): time.sleep(.02)\n' + original)
            started = driver.execute('qualify', dict(run_id=run['run_id'], output='json'))
            job = started['qualification']['steps']['runtime']['job_dir']
            (Path(run['worktree']) / 'Cargo.lock').write_text('version = 4\n')
            try:
                resumed = driver.execute('resume', dict(run_id=run['run_id'], output='json'))
                self.assertIn('qualification', resumed)
                self.assertEqual(resumed['qualification']['steps']['runtime']['job_dir'], job)
                self.assertEqual(resumed['qualification']['steps']['runtime']['status'], 'running')
                self.assertEqual(resumed['stages'], {})
            finally:
                gate.touch()
                # Reconcile this exact submitted fixture job before deleting its state.
                from codex_wake.release_signal import SignalClient
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    with SignalClient() as client:
                        receipt = client.call('get_command_status', dict(job_dir=job, brief=True))
                    if receipt['status'] != 'running': break
                    time.sleep(.05)


    def test_explicit_resume_retries_failed_qualification_and_retains_receipt(self):
        fixture = qualification_fixture.ReleaseQualificationTests()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            driver, run = fixture.fixture(root)
            recipe_path = root / 'recipe.json'
            recipe = json.loads(recipe_path.read_text())
            recipe['build_steps'] = [dict(name='package', argv=[sys.executable, '-c', "raise RuntimeError('retained package should be reused')"], inputs=['Cargo.lock'])]
            recipe_path.write_text(json.dumps(recipe))
            run = driver.execute('prepare', dict(recipe='fixture', upstream=run['source']['upstream'], mod_revision=run['source']['mod_revision']))
            run = driver.execute('build', dict(run_id=run['run_id']))
            marker = root / 'fail-qualification'
            marker.touch()
            helper = root / 'qualify.py'
            helper.write_text("from pathlib import Path\nif Path(" + repr(str(marker)) + ").exists(): raise SystemExit(7)\n" + helper.read_text())
            failed = fixture.complete(driver, run)
            self.assertEqual(failed['status'], 'failed')
            old_job = failed['qualification']['steps']['runtime']['job_dir']
            marker.unlink()
            resumed = driver.execute('resume', dict(run_id=run['run_id'], output='json'))
            qualified = fixture.complete(driver, resumed)
            self.assertEqual(qualified['status'], 'qualified')
            self.assertEqual(qualified['qualification_attempts'][0]['steps']['runtime']['job_dir'], old_job)
            self.assertEqual(qualified['qualification_attempts'][0]['status'], 'failed')
            self.assertNotEqual(qualified['qualification']['steps']['runtime']['job_dir'], old_job)


    def test_failed_preparation_keeps_an_inspectable_run(self):
        import os
        import shutil
        from unittest.mock import patch
        fixture = qualification_fixture.ReleaseQualificationTests()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            driver, original = fixture.fixture(root)
            binaries = root / 'git-only'
            binaries.mkdir()
            (binaries / 'git').symlink_to(shutil.which('git'))
            with patch.dict(os.environ, PATH=str(binaries)):
                result = driver.execute('prepare', dict(recipe='fixture', upstream=original['source']['upstream'], mod_revision=original['source']['mod_revision']))
            self.assertEqual(result['status'], 'failed')
            self.assertIn('rustc', result['failure'])
            self.assertTrue(Path(result['manifest']).is_file())
            observed = driver.execute('status', dict(run_id=result['run_id']))
            self.assertEqual(observed['status'], 'failed')


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'install codex-wake[mcp] for native discovery tests')
class NativeReleaseSchemaReviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_discovery_exposes_the_same_run_input_alternatives(self):
        import os
        from jsonschema import Draft202012Validator
        from mcp import Client, StdioServerParameters
        root = Path(__file__).resolve().parents[1]
        parameters = StdioServerParameters(command=sys.executable,
            args=['-m', 'codex_wake.mcp_server'], cwd=root,
            env=dict(os.environ, PYTHONPATH=str(root / 'src')))
        async with Client(parameters, mode='legacy') as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            validator = Draft202012Validator(tools['wake_builds_run'].input_schema)
            pins = dict(recipe='native', upstream='a'*40, mod_revision='b'*40)
            self.assertEqual(list(validator.iter_errors(pins)), [])
            self.assertEqual(list(validator.iter_errors(dict(run_id='c'*32))), [])
            self.assertTrue(list(validator.iter_errors({})))
            self.assertTrue(list(validator.iter_errors(dict(pins, run_id='c'*32))))


if __name__ == '__main__':
    unittest.main()
