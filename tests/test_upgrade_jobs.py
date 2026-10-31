import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from codex_wake.upgrade_jobs import UpgradeJobs


class UpgradeJobsTests(unittest.TestCase):
    def test_durable_job_deduplicates_release_and_disable_preserves_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = {'host': 'fixture', 'environment': 'test', 'namespace': 'upgrade-test'}
            actor = SimpleNamespace(subject='owner', scopes={'admin', 'observe'}, targets=[target])
            (root / 'upgrade-bot.json').write_text(json.dumps({'schema_version': 1,
                'target': target, 'recipes': {'release': str(root / 'recipe.json')}}))
            (root / 'recipe.json').write_text(json.dumps({'id': 'candidate', 'upstream_version': '0.166.0'}))
            owner = UpgradeJobs(root)
            def call(verb, **arguments):
                return owner.execute(actor, 'upgrades.' + verb,
                    dict(expected_target=target, **arguments), authorize=lambda: actor)['result']
            self.assertFalse(call('status')['enabled'])
            call('enable')
            first = call('start', recipe='release')['job']
            self.assertEqual(first['state'], 'queued')
            second = call('start', recipe='release')['job']
            self.assertEqual(first['id'], second['id'])
            call('disable')
            owner = UpgradeJobs(root)
            after = call('show', job_id=first['id'])['job']
            self.assertEqual(after['state'], 'disabled')
            self.assertEqual(after['repair_attempts'], 0)
            self.assertEqual(call('status')['limits']['compiler_jobs'], 2)

    def test_installed_stage_and_public_adapters_use_same_job(self):
        import hashlib
        import tarfile
        import contextlib
        import io
        import time
        from codex_wake.cli import main
        from codex_wake.mcp_server import CommandRunner
        from codex_wake.controller_http import ProtectedOperations, TOOLS
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import ManagedInventory
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir()
            for name in ('bin/codex','bin/codex-code-mode-host','codex-path/rg','codex-resources/bwrap'):
                file=source/'package'/name;file.parent.mkdir(parents=True,exist_ok=True)
                file.write_text('#!/bin/sh\nexit 0\n');file.chmod(0o700)
            (source/'package/codex-package.json').write_text('{}')
            archive=root/'source.tar'
            with tarfile.open(archive,'w') as stream:stream.add(source/'package',arcname='package')
            recipe=root/'recipe.json'
            recipe.write_text(json.dumps(dict(schema_version=1,id='fixture',channel='stock',upstream_version='0.166.0',revision='fixture',package='package',
                source=dict(official_url='https://github.com/openai/codex/archive/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.tar.gz',archive_file=str(archive),sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
                qualify=[['/bin/echo','{"schema_version":1,"checks":{"official_cli":true}}']],read_schemas=[1],write_schema=1)))
            reviewer=root/'reviewer.py'
            reviewer.write_text("import os,json,pathlib\np=json.loads(pathlib.Path(os.environ['CODEX_UPGRADE_PACKET']).read_text())\npathlib.Path(os.environ['CODEX_UPGRADE_RESPONSE']).write_text(json.dumps(dict(schema_version=1,status='approved',reviewer='independent',candidate_digest=p['candidate_digest'],tests_digest=p['tests_digest'],capabilities={'official_cli':'Fixture executable passes pinned version check'},retirements={})))\n")
            target={'host':'fixture','environment':'test','namespace':'upgrade-test'}
            declaration=dict(subject='owner',client_id='client',grant_id='grant',issuer='issuer',resource='resource',scopes=['observe','admin'],targets=[target],expires_at=time.time()+1000)
            (root/'upgrade-bot.json').write_text(json.dumps(dict(schema_version=1,target=target,recipes={'release':str(recipe)},repair=dict(patches=[],worker=dict(identity='worker',argv=['/bin/false']),reviewer=dict(identity='independent',argv=[__import__('sys').executable,str(reviewer)]),regenerate=[],verify=[['/bin/true']]))))
            (root/'controller-messaging.json').write_text(json.dumps(dict(version=1,local_caller=declaration)))
            (root/'controller-messaging.json').chmod(0o600)
            from codex_wake.operation_commands import local_actor
            actor=local_actor(root)
            protected=ProtectedOperations(SimpleNamespace(authenticate=lambda _:actor),ControllerOperations(ManagedInventory(root),host='fixture',environment='test'))
            args=dict(expected_target=target)
            protected.execute('token','upgrades.enable',args)
            job=protected.execute('token','upgrades.start',dict(args,recipe='release'))['result']['job']
            result=protected.execute('token','upgrades.advance',dict(args,job_id=job['id']))
            self.assertEqual(result['result']['job']['state'],'qualifying',result)
            self.assertEqual(result['result']['job']['results']['stage']['status'],'staged')
            self.assertEqual(result['result']['job']['results']['repair']['status'],'reviewed')
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                code=main(['--wake-root',str(root),'upgrades','show','--arguments',json.dumps(dict(args,job_id=job['id']))])
            self.assertEqual(code,0)
            self.assertEqual(json.loads(output.getvalue())['result']['job']['id'],job['id'])
            runner=CommandRunner(wake_root=root)
            value,error=runner.call('wake_upgrades_show',dict(args,job_id=job['id']))
            self.assertFalse(error,value)
            self.assertEqual(value['result']['job']['id'],job['id'])
            self.assertEqual(TOOLS['wake_upgrades_show'][0],'upgrades.show')

    def test_restart_does_not_extend_deadline_or_replay_interrupted_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);clock=[100.0]
            target={'host':'fixture'}
            actor=SimpleNamespace(subject='owner',scopes={'admin','observe'},targets=[target])
            (root/'recipe.json').write_text(json.dumps(dict(id='candidate',upstream_version='0.166')))
            (root/'upgrade-bot.json').write_text(json.dumps(dict(schema_version=1,target=target,recipes={'release':str(root/'recipe.json')},limits={'total_seconds':10})))
            owner=UpgradeJobs(root,now=lambda:clock[0]);args={'expected_target':target}
            def call(verb,**extra):return owner.execute(actor,'upgrades.'+verb,dict(args,**extra))['result']
            call('enable');job=call('start',recipe='release')['job']
            calls=[]
            def crashed(frozen):
                calls.append(frozen['id'])
                raise KeyboardInterrupt()
            owner.executor=crashed
            with self.assertRaises(KeyboardInterrupt):call('advance',job_id=job['id'])
            owner=UpgradeJobs(root,now=lambda:clock[0],executor=lambda _:calls.append('replayed'))
            held=call('advance',job_id=job['id'])['job']
            self.assertEqual(held['state'],'held')
            self.assertEqual(calls,[job['id']])
            self.assertEqual(held['deadline'],110)

    def test_disable_during_work_rejects_late_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target={'host':'fixture'}
            actor=SimpleNamespace(subject='owner',scopes={'admin','observe'},targets=[target])
            (root/'recipe.json').write_text(json.dumps(dict(id='candidate',upstream_version='0.166')))
            (root/'upgrade-bot.json').write_text(json.dumps(dict(schema_version=1,target=target,recipes={'release':str(root/'recipe.json')})))
            owner=UpgradeJobs(root);args={'expected_target':target}
            def call(verb,**extra):return owner.execute(actor,'upgrades.'+verb,dict(args,**extra))['result']
            call('enable');job=call('start',recipe='release')['job']
            def delayed(job):
                call('disable')
                return dict(status='staged')
            owner.executor=delayed
            result=call('advance',job_id=job['id'])['job']
            self.assertEqual(result['state'],'disabled')
            self.assertEqual(result['results'],{})
            call('enable')
            same=call('start',recipe='release')['job']
            self.assertEqual(same['id'],job['id'])
            self.assertEqual(same['state'],'disabled')
