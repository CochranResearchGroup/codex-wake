"""One public run request drives retained diagnostics through qualification."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from codex_wake.release_driver import ReleaseDriver


class ReleaseWorkflowTests(unittest.TestCase):
    def fixture(self, root, fail=False):
        repo = root / 'repo'
        repo.mkdir()
        count = root / 'build-count'
        gate = root / 'release-build'
        script = """import sys,time
from pathlib import Path
count=Path(sys.argv[1]);count.write_text(count.read_text()+'build\\n' if count.exists() else 'build\\n')
end=time.monotonic()+12
while not Path(sys.argv[2]).exists():
 if time.monotonic()>end: raise SystemExit(8)
 time.sleep(.05)
if sys.argv[3]=='True':raise SystemExit(7)
p=Path('package/bin');p.mkdir(parents=True,exist_ok=True)
f=p/'codex';f.write_text('#!/bin/sh\\nexit 0\\n');f.chmod(0o700)
Path('package/codex-package.json').write_text('{}')
"""
        (repo / 'build.py').write_text(script)
        (repo / 'Cargo.lock').write_text('version = 3\n')
        for args in [('init','-q'),('config','user.name','Fixture'),('config','user.email','fixture@example.invalid'),('add','.'),('commit','-qm','fixture')]:
            subprocess.run(['git','-C',str(repo),*args],check=True,stdout=subprocess.DEVNULL)
        revision = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
        helper = root / 'qualify.py'
        helper.write_text("""import json,sys,hashlib,os
from pathlib import Path
p=Path(sys.argv[1]);files={str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
v=dict(schema_version=1,state='passed',uid=os.getuid(),package_inventory_sha256=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest(),external_model_calls=0,owned_processes=[],checks=dict(history=True,active_multiclient=True,reconnect=True,private_ownership=True,upgrade=True,rollback=True,failed_start=True))
Path(sys.argv[2]).write_text(json.dumps(v))
""")
        recipe = root / 'recipe.json'
        recipe.write_text(json.dumps(dict(source_repository=str(repo),package_directory='package',required_artifacts=['bin/codex','codex-package.json'],
            workflow_timeout_seconds=30,workflow_poll_seconds=.1,
            build_steps=[dict(name='package',argv=[sys.executable,'build.py',str(count),str(gate),str(fail)],inputs=['build.py','Cargo.lock'],outputs=['package/bin/codex','package/codex-package.json'])],
            qualification=dict(environment=dict(kind='owned_fixture',uid=os.getuid(),shared_kernel=True),steps=[dict(name='runtime',argv=[sys.executable,str(helper),'{package}','{report}'])]))))
        return ReleaseDriver(root / 'runs', {'fixture':recipe}), dict(recipe='fixture',upstream=revision,mod_revision=revision), count, gate

    def wait(self, driver, run_id, predicate):
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            result=driver.execute('status',dict(run_id=run_id,output='json'))
            if predicate(result):return result
            time.sleep(.05)
        self.fail('workflow did not reach expected state')

    def test_one_run_request_finishes_after_client_returns_and_retries_share_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            driver,args,count,gate=self.fixture(Path(directory))
            started=driver.execute('run',args)
            self.wait(driver,started['run_id'],lambda run:count.exists())
            repeated=driver.execute('run',dict(run_id=started['run_id']))
            self.assertEqual(started['orchestration']['identity'],repeated['orchestration']['identity'])
            gate.touch()
            done=self.wait(driver,started['run_id'],lambda run:run['status']=='qualified')
            self.assertEqual(done['orchestration']['status'],'completed')
            self.assertEqual(count.read_text(),'build\n')
            self.assertEqual(done['qualification']['evidence_scope'],'fixture_only')
            self.assertEqual(done['qualification']['checks']['rollback'],True)

    def test_interrupted_coordinator_reconciles_job_before_explicit_restart(self):
        import signal
        with tempfile.TemporaryDirectory() as directory:
            driver,args,count,gate=self.fixture(Path(directory))
            started=driver.execute('run',args)
            active=self.wait(driver,started['run_id'],lambda run:count.exists())
            os.kill(active['orchestration']['pid'],signal.SIGKILL)
            self.wait(driver,started['run_id'],lambda run:run['orchestration']['status']=='unknown')
            held=driver.execute('run',dict(run_id=started['run_id']))
            self.assertEqual(held['orchestration']['nonce'],started['orchestration']['nonce'])
            gate.touch()
            self.wait(driver,started['run_id'],lambda run:run['stages']['package']['status']=='passed')
            resumed=driver.execute('resume',dict(run_id=started['run_id']))
            self.assertEqual(resumed['status'],'built')
            restarted=driver.execute('run',dict(run_id=started['run_id']))
            self.assertNotEqual(restarted['orchestration']['nonce'],started['orchestration']['nonce'])
            self.wait(driver,started['run_id'],lambda run:run['status']=='qualified')
            self.assertEqual(count.read_text(),'build\n')

    def test_public_run_schema_accepts_pins_or_run_id_but_not_both(self):
        from jsonschema import Draft202012Validator
        from codex_wake.command_contract import public_tools
        schema=public_tools()['wake_builds_run'][1]
        validator=Draft202012Validator(schema)
        pins=dict(recipe='native',upstream='a'*40,mod_revision='b'*40)
        self.assertEqual(list(validator.iter_errors(pins)),[])
        self.assertEqual(list(validator.iter_errors(dict(run_id='c'*32))),[])
        self.assertTrue(list(validator.iter_errors({})))
        self.assertTrue(list(validator.iter_errors(dict(pins,run_id='c'*32))))

    def test_failed_worker_is_held_without_implicit_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            driver,args,count,gate=self.fixture(Path(directory),fail=True)
            gate.touch()
            started=driver.execute('run',args)
            failed=self.wait(driver,started['run_id'],lambda run:run['status']=='failed' and run['orchestration']['status']=='held')
            again=driver.execute('run',dict(run_id=started['run_id'],output='json'))
            self.assertEqual(again['status'],'failed')
            self.assertEqual(count.read_text(),'build\n')
            self.assertEqual(len(again['stages']['package']['attempts']),1)
            self.assertEqual(failed['orchestration']['status'],'held')


if __name__=='__main__':unittest.main()
