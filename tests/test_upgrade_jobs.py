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
            actor = SimpleNamespace(subject='owner', client_id='client', grant_id='grant', scopes={'admin', 'observe'}, targets=[target])
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
            actor=SimpleNamespace(subject='owner',client_id='client',grant_id='grant',scopes={'admin','observe'},targets=[target])
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
            actor=SimpleNamespace(subject='owner',client_id='client',grant_id='grant',scopes={'admin','observe'},targets=[target])
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

    def test_terminal_failure_reclaims_only_the_owned_compiler_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target={'host':'fixture'}
            actor=SimpleNamespace(subject='owner',client_id='client',grant_id='grant',scopes={'admin','observe'},targets=[target])
            (root/'recipe.json').write_text(json.dumps(dict(id='candidate',upstream_version='0.166')))
            (root/'upgrade-bot.json').write_text(json.dumps(dict(schema_version=1,target=target,recipes={'release':str(root/'recipe.json')})))
            owner=UpgradeJobs(root);args={'expected_target':target}
            def call(verb,**extra):return owner.execute(actor,'upgrades.'+verb,dict(args,**extra))['result']
            call('enable');job=call('start',recipe='release')['job']
            def failed(job):
                cache=root/'upgrade-jobs'/job['id']/'cargo-target';cache.mkdir(parents=True)
                (cache/'rebuildable').write_bytes(b'12345678')
                return dict(status='failed',reason='compile_rejected')
            owner.executor=failed
            call('advance',job_id=job['id'])
            after=call('show',job_id=job['id'])['job']
            self.assertEqual(after['state'],'held')
            self.assertEqual(after['cache_reclamation']['status'],'reclaimed')
            self.assertEqual(after['cache_reclamation']['bytes'],8)

    def test_expired_host_grant_cannot_enable_the_bot(self):
        import time
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target={'host':'fixture'}
            (root/'upgrade-bot.json').write_text(json.dumps(dict(schema_version=1,target=target,recipes={})))
            actor=SimpleNamespace(subject='owner',client_id='client',grant_id='grant',scopes={'admin','observe'},targets=[target],expires_at=time.time()-1)
            with self.assertRaises(InventoryError):
                UpgradeJobs(root).execute(actor,'upgrades.enable',dict(expected_target=target),authorize=lambda:actor)

    def test_writable_host_configuration_is_refused_before_enabling(self):
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target={'host':'fixture'}
            path=root/'upgrade-bot.json'
            path.write_text(json.dumps(dict(schema_version=1,target=target,recipes={})))
            path.chmod(0o666)
            actor=SimpleNamespace(subject='owner',client_id='client',grant_id='grant',scopes={'admin','observe'},targets=[target])
            with self.assertRaises(InventoryError):
                UpgradeJobs(root).execute(actor,'upgrades.enable',dict(expected_target=target))

    def test_small_wall_adjustment_cannot_extend_the_monotonic_job_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);wall=[100.0];mono=[10.0]
            target={'host':'fixture'}
            actor=SimpleNamespace(subject='owner',client_id='client',grant_id='grant',scopes={'admin','observe'},targets=[target])
            (root/'recipe.json').write_text(json.dumps(dict(id='candidate',upstream_version='0.166')))
            (root/'upgrade-bot.json').write_text(json.dumps(dict(schema_version=1,target=target,recipes={'release':str(root/'recipe.json')},limits={'total_seconds':10})))
            owner=UpgradeJobs(root,now=lambda:wall[0],clock=lambda:dict(boot_id='boot-one',seconds=mono[0]),executor=lambda _:dict(status='staged'))
            def call(verb,**extra):return owner.execute(actor,'upgrades.'+verb,dict(expected_target=target,**extra))['result']
            call('enable');job=call('start',recipe='release')['job']
            wall[0]=99.8;mono[0]=10.3
            first=call('advance',job_id=job['id'])['job']
            self.assertEqual(first['state'],'qualifying',first)
            self.assertGreater(first['clock_anchor']['wall_adjustment_count'],0)
            wall[0]=100;mono[0]=20.1
            expired=call('advance',job_id=job['id'])['job']
            self.assertEqual(expired['reason'],'deadline_exhausted')

    def test_local_operator_can_disable_without_a_service_grant_ritual(self):
        import contextlib
        import io
        from codex_wake.cli import main
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target={'host':'fixture'}
            (root/'upgrade-bot.json').write_text(json.dumps(dict(schema_version=1,target=target,recipes={})))
            actor=SimpleNamespace(subject='owner',client_id='client',grant_id='grant',scopes={'admin','observe'},targets=[target])
            UpgradeJobs(root).execute(actor,'upgrades.enable',dict(expected_target=target))
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                code=main(['--wake-root',str(root),'upgrades','disable'])
            self.assertEqual(code,0)
            self.assertFalse(json.loads(output.getvalue())['result']['enabled'])
            state=UpgradeJobs(root).execute(actor,'upgrades.status',dict(expected_target=target))['result']
            self.assertFalse(state['enabled'])

    def test_oauth_mcp_catalog_advertises_upgrade_tools_without_an_account_owner(self):
        import base64
        import hashlib
        import threading
        from urllib.request import Request, urlopen
        from codex_wake.controller_auth import OAuthAuthority
        from codex_wake.controller_http import ControllerHTTPServer
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import ManagedInventory
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target={'host':'fixture','environment':'test'}
            (root/'upgrade-bot.json').write_text(json.dumps(dict(schema_version=1,target=target,recipes={})))
            auth=OAuthAuthority(root/'oauth.sqlite',issuer='https://wake.test',resource='https://wake.test/mcp')
            client=auth.register({'redirect_uris':['http://localhost/callback']});verifier='x'*43
            challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            code=auth.authorize(subject='owner',principal_kind='owner',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],resource=auth.resource,scopes=['observe','admin'],targets=[target],code_challenge=challenge)
            token=auth.token(dict(grant_type='authorization_code',client_id=client['client_id'],code=code,redirect_uri=client['redirect_uris'][0],code_verifier=verifier,resource=auth.resource))['access_token']
            server=ControllerHTTPServer(('127.0.0.1',0),auth,ControllerOperations(ManagedInventory(root),host='fixture',environment='test'))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def post(path,body):
                request=Request('http://127.0.0.1:'+str(server.server_port)+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
                with urlopen(request,timeout=5) as response:return json.load(response)
            try:
                tools=post('/mcp',dict(jsonrpc='2.0',id=1,method='tools/list'))['result']['tools']
                self.assertIn('wake_upgrades_status',[tool['name'] for tool in tools])
                args={'expected_target':target}
                direct=post('/operations',dict(operation='upgrades.status',arguments=args))
                mcp=post('/mcp',dict(jsonrpc='2.0',id=2,method='tools/call',params=dict(name='wake_upgrades_status',arguments=args)))
                self.assertEqual(mcp['result']['structuredContent']['result'],direct['result'])
            finally:
                server.shutdown();server.server_close();thread.join(timeout=2)
