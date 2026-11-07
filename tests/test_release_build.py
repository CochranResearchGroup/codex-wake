"""Build behavior through the public release driver and real Cargo Signal transport."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from codex_wake.release_driver import ReleaseDriver


class ReleaseBuildTests(unittest.TestCase):
    def fixture(self, root, script):
        source = root / 'repo'; source.mkdir()
        (source / 'build.py').write_text(script)
        (source / 'Cargo.lock').write_text('version = 3\n')
        for args in [('init','-q'),('config','user.name','Fixture'),('config','user.email','fixture@example.invalid'),('add','.'),('commit','-qm','fixture')]:
            subprocess.run(['git','-C',str(source),*args],check=True,stdout=subprocess.DEVNULL)
        revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
        recipe = root / 'recipe.json'
        recipe.write_text(json.dumps(dict(source_repository=str(source),package_directory='package',required_artifacts=['bin/codex','codex-package.json'],
            build_steps=[dict(name='package',argv=[sys.executable,'build.py'],inputs=['build.py','Cargo.lock'],outputs=['package/bin/codex','package/codex-package.json'])])))
        driver=ReleaseDriver(root/'runs',{'fixture':recipe})
        run=driver.execute('prepare',dict(recipe='fixture',upstream=revision,mod_revision=revision))
        return driver,run

    def complete(self, driver, run):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            result=driver.execute('build',dict(run_id=run['run_id'],output='json',max_items=2))
            if result['status']!='building':return result
            time.sleep(.05)
        self.fail('build did not settle')

    def test_real_mcp_build_keeps_noise_on_disk_and_verifies_package(self):
        with tempfile.TemporaryDirectory() as directory:
            driver,run=self.fixture(Path(directory),"from pathlib import Path\nprint('noise\\n'*10000)\np=Path('package/bin');p.mkdir(parents=True)\nf=p/'codex';f.write_text('#!/bin/sh\\nexit 0\\n');f.chmod(0o700)\nPath('package/codex-package.json').write_text('{}')\n")
            result=self.complete(driver,run)
            self.assertEqual(result['status'],'built')
            self.assertEqual(result['package']['files']['bin/codex'],hashlib.sha256(b'#!/bin/sh\nexit 0\n').hexdigest())
            stage=result['stages']['package']
            self.assertEqual(stage['receipt']['exit_code'],0)
            self.assertNotIn('noise',json.dumps(result))
            self.assertGreater(Path(stage['receipt']['artifacts']['stdout']).stat().st_size,50000)
            self.assertEqual(len(stage['attempts']),1)

    def test_failed_step_cannot_become_a_complete_package(self):
        with tempfile.TemporaryDirectory() as directory:
            driver,run=self.fixture(Path(directory),"raise SystemExit(7)\n")
            result=self.complete(driver,run)
            self.assertEqual(result['status'],'failed')
            self.assertEqual(result['stages']['package']['receipt']['exit_code'],7)
            self.assertNotIn('package',result)


    def test_retained_package_requires_source_binding_and_reuses_without_job(self):
        from codex_wake.release_build import adoption_binding, package_inventory
        with tempfile.TemporaryDirectory() as directory:
            driver, run = self.fixture(Path(directory), "raise RuntimeError('must not build')\n")
            package=Path(directory)/'retained'
            (package/'bin').mkdir(parents=True)
            (package/'bin/codex').write_text('#!/bin/sh\nexit 0\n')
            (package/'bin/codex').chmod(0o700)
            (package/'codex-package.json').write_text('{}')
            retained=dict(path=str(package), files=package_inventory(run,package)['files'], binding=adoption_binding(driver,run))
            with driver.locked():
                raw=driver.load(run['run_id']);raw['recipe']['retained_package']=retained;driver.save(raw)
            result=driver.execute('build',dict(run_id=run['run_id']))
            self.assertTrue(result['package']['reused'])
            self.assertEqual(result['stages'],{})
            with driver.locked():
                raw=driver.load(run['run_id']);raw['status']='prepared';raw['recipe']['retained_package']['binding']['profile']='wrong';driver.save(raw)
            with self.assertRaisesRegex(ValueError,'binding mismatch'):
                driver.execute('build',dict(run_id=run['run_id']))

    def test_missing_fixture_helper_fails_before_submitting_a_job(self):
        with tempfile.TemporaryDirectory() as directory:
            driver,run=self.fixture(Path(directory),"raise RuntimeError('must not build')\n")
            with driver.locked():
                raw=driver.load(run['run_id']);raw['recipe']['preflight']={'files':['missing-helper.py']};driver.save(raw)
            with self.assertRaisesRegex(ValueError,'helper asset unavailable'):
                driver.execute('build',dict(run_id=run['run_id']))
            result=driver.execute('status',dict(run_id=run['run_id']))
            self.assertEqual(result['stages'],{})


if __name__=='__main__':unittest.main()
