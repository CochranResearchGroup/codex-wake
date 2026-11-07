"""Exact-artifact qualification through the public driver and Cargo Signal MCP."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from codex_wake.release_driver import ReleaseDriver


class ReleaseQualificationTests(unittest.TestCase):
    def fixture(self, root, report_changes=None, mutate=False, missing=False):
        repo = root / 'repo'
        repo.mkdir()
        (repo / 'Cargo.lock').write_text('version = 3\n')
        for args in [('init', '-q'), ('config', 'user.name', 'Fixture'),
                     ('config', 'user.email', 'fixture@example.invalid'), ('add', '.'),
                     ('commit', '-qm', 'fixture')]:
            subprocess.run(['git', '-C', str(repo), *args], check=True, stdout=subprocess.DEVNULL)
        revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        package = root / 'package'
        (package / 'bin').mkdir(parents=True)
        (package / 'bin/codex').write_text('#!/bin/sh\nexit 0\n')
        (package / 'bin/codex').chmod(0o700)
        (package / 'codex-package.json').write_text('{}')
        import hashlib
        files = {str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in package.rglob('*') if p.is_file()}
        helper = root / 'qualify.py'
        helper.write_text("""import json,sys,os,hashlib
from pathlib import Path
package=Path(sys.argv[1]); report=Path(sys.argv[2])
files={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest() for p in package.rglob('*') if p.is_file()}
inventory=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
value=dict(schema_version=1,state='passed',uid=os.getuid(),package_inventory_sha256=inventory,
 external_model_calls=0,owned_processes=[],checks=dict(history=True,active_multiclient=True,
 reconnect=True,private_ownership=True,upgrade=True,rollback=True,failed_start=True))
value.update(json.loads(sys.argv[3]))
if sys.argv[4]=='True': (package/'bin/codex').write_text('changed during qualification')
if sys.argv[5]!='True': report.write_text(json.dumps(value))
""")
        import os
        recipe = root / 'recipe.json'
        recipe.write_text(json.dumps(dict(source_repository=str(repo), target='fixture', profile='fixture',
            required_artifacts=['bin/codex', 'codex-package.json'],
            retained_package=dict(path=str(package), files=files,
                binding=dict(source_revision=revision, target='fixture', profile='fixture', features=[])),
            qualification=dict(environment=dict(kind='owned_fixture', uid=os.getuid(), shared_kernel=True),
                preflight=dict(executables=[sys.executable], files=[str(helper)]),
                steps=[dict(name='runtime', argv=[sys.executable, str(helper), '{package}', '{report}',
                           json.dumps(report_changes or {}), str(mutate), str(missing)])]))))
        driver = ReleaseDriver(root / 'runs', {'fixture': recipe})
        run = driver.execute('prepare', dict(recipe='fixture', upstream=revision, mod_revision=revision))
        run = driver.execute('build', dict(run_id=run['run_id']))
        return driver, run

    def complete(self, driver, run):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            result = driver.execute('qualify', dict(run_id=run['run_id'], output='json'))
            if result['status'] != 'qualifying':
                return result
            time.sleep(.05)
        self.fail('qualification did not settle')

    def test_exact_package_gets_evidence_bound_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run = self.fixture(Path(directory))
            result = self.complete(driver, run)
            self.assertEqual(result['status'], 'qualified')
            self.assertEqual(result['qualification']['evidence_scope'], 'fixture_only')
            self.assertEqual(result['qualification']['checks']['rollback'], True)
            self.assertEqual(result['qualification']['steps']['runtime']['receipt']['exit_code'], 0)

    def test_zero_exit_with_missing_report_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run = self.fixture(Path(directory), missing=True)
            result = self.complete(driver, run)
            self.assertEqual(result['status'], 'failed')
            self.assertIn('report', result['qualification']['failure'])

    def test_failed_or_unknown_check_cannot_qualify(self):
        for verdict in [False, None]:
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as directory:
                driver, run = self.fixture(Path(directory), dict(checks=dict(history=verdict)))
                result = self.complete(driver, run)
                self.assertEqual(result['status'], 'failed')

    def test_changed_package_during_qualification_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            driver, run = self.fixture(Path(directory), mutate=True)
            result = self.complete(driver, run)
            self.assertEqual(result['status'], 'failed')
            self.assertIn('package', result['qualification']['failure'])


if __name__ == '__main__':
    unittest.main()
