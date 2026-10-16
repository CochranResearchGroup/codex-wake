"""Strict policy through public lifecycle configuration; no runtime effects."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from codex_wake.cli import run


class StrictConfigurationTests(unittest.TestCase):
    def test_effective_policy_requires_all_controls_and_reports_sampled_token_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);instructions=root/'instructions.md';instructions.write_text('Review the evidence.')
            limits=dict(memory_max_bytes=134217728,memory_swap_max_bytes=0,cpu_quota_percent=20,
                        tasks_max=16,stop_grace_seconds=1,checkpoint_grace_seconds=1,
                        poll_seconds=.2,accounting_max_age_seconds=2)
            config=dict(profiles={'worker':dict(cwd=tmp,strict_execution=limits)},
                lifecycle_defaults=dict(handoff_writer=dict(name='writer',path=str(instructions)),
                    preflight_reviewer=dict(name='reviewer',path=str(instructions)),
                    session_token_limit=100,objective_token_limit=500,
                    session_time_limit_seconds=10,objective_time_limit_seconds=30,max_correction_cycles=1),
                continuations={'source':dict(objective='bounded work',approval='operator',started_at='2030-01-01T00:00:00Z')})
            path=root/'profiles.json';path.write_text(json.dumps(config))
            args=['--wake-root',str(root/'wake'),'sessions','configuration','--profiles',str(path),
                  '--profile','worker','--thread-id','source','--json']
            out=StringIO()
            with redirect_stdout(out):self.assertEqual(run(args),0)
            value=json.loads(out.getvalue())
            self.assertEqual(value['strict_execution']['token_enforcement'],'sampled_stop')
            self.assertIsNone(value['strict_execution']['maximum_token_overshoot'])
            self.assertEqual(value['strict_execution']['limits'],limits)
            del config['profiles']['worker']['strict_execution']['memory_max_bytes']
            path.write_text(json.dumps(config));out=StringIO()
            with redirect_stdout(out):self.assertEqual(run(args),2)
            self.assertEqual(json.loads(out.getvalue())['error']['code'],'configuration_unavailable')

    def test_strict_spawn_without_budget_is_rejected_before_runtime_effects(self):
        from codex_wake.records import WakeError
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'profiles.json'
            path.write_text(json.dumps(dict(version=1,profiles={'worker':dict(cwd=tmp,
                app_server='unix://'+tmp+'/server.sock',codex_path='/bin/true',tmux_session='fixture',
                timeout=1,strict_execution={})})))
            with redirect_stdout(StringIO()),self.assertRaisesRegex(WakeError,'strict execution requires an approved objective'):
                run(['--wake-root',tmp,'sessions','spawn','--profiles',str(path),'--profile','worker',
                     '--intent','strict','--name','strict','--task','bounded','--expires-at','2030-01-01T00:00:00Z','--json'])
            self.assertFalse((root/'lifecycle').exists())

    def test_operator_execution_status_reports_not_enrolled_without_creating_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);instruction=root/'review.md';instruction.write_text('Review evidence.')
            config=dict(profiles={'worker':dict(cwd=tmp,strict_execution=dict(memory_max_bytes=134217728,
                memory_swap_max_bytes=0,cpu_quota_percent=20,tasks_max=16,stop_grace_seconds=1,
                checkpoint_grace_seconds=1,poll_seconds=.2,accounting_max_age_seconds=2))},
                lifecycle_defaults=dict(handoff_writer=dict(name='writer',path=str(instruction)),
                    preflight_reviewer=dict(name='reviewer',path=str(instruction)),session_token_limit=100,
                    objective_token_limit=500,session_time_limit_seconds=10,objective_time_limit_seconds=30,
                    max_correction_cycles=1),continuations={'source':dict(objective='work',approval='operator',
                    started_at='2030-01-01T00:00:00Z')})
            profiles=root/'profiles.json';profiles.write_text(json.dumps(config));out=StringIO()
            with redirect_stdout(out):
                code=run(['--wake-root',str(root/'wake'),'sessions','execution','--profiles',str(profiles),
                          '--profile','worker','--thread-id','source','--json'])
            self.assertEqual(code,0)
            self.assertIsNone(json.loads(out.getvalue())['execution'])
            self.assertFalse((root/'wake').exists())

    def test_only_bound_executor_socket_alias_is_accepted_by_both_native_readers(self):
        from codex_wake.native_protocol import native_request
        from codex_wake.shared_app_server import SharedAppServerReader
        from codex_wake.strict_runtime import location
        from websockets.sync.server import unix_serve
        import os,threading
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=location(root,'owned');directory.mkdir(parents=True,mode=0o700)
            target=root/'real.sock';alias=directory/'app-server.sock'
            def handle(ws):
                for raw in ws:
                    msg=json.loads(raw)
                    if 'id' in msg:ws.send(json.dumps(dict(id=msg['id'],result={} if msg['method']=='initialize' else {'data':[]})))
            server=unix_serve(handle,str(target));worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            alias.symlink_to(target)
            binding=directory/'binding.json';binding.write_text(json.dumps(dict(objective_id='owned',state='running',
                identity=dict(unit='codex-wake-objective-fixture.service',invocation_id='fixture',control_group='/fixture'))));binding.chmod(0o600)
            try:
                with patch('codex_wake.strict_runtime.SystemdExecution.inspect',return_value={'members':[os.getpid()],'populated':True}):
                    endpoint='unix://'+str(alias)
                    self.assertEqual(native_request(endpoint,'/bin/true','thread/list',{'limit':1},2),{'data':[]})
                    with SharedAppServerReader(endpoint,timeout=2) as reader:
                        self.assertEqual(reader.request('thread/list',{'limit':1}),{'data':[]})
            finally:server.shutdown();worker.join(2)


class StrictLaunchRefusalTests(unittest.TestCase):
    def test_public_spawn_refuses_shared_endpoint_and_unsupported_host_before_native_effect(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from codex_wake.strict_runtime import location
        from codex_wake.lifecycle_supervision import publish_supervision
        from codex_wake.objective_ledger import ObjectiveLedger
        from codex_wake.records import WakeError
        for shared in (True,False):
            with self.subTest(shared=shared),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);wake=root/'wake';wake.mkdir(mode=0o700)
                home=location(wake,'goal')/'home';home.mkdir(parents=True,mode=0o700)
                home.parent.chmod(0o700)
                instruction=root/'review.md';instruction.write_text('Review fixture only.')
                selection=dict(name='fixture',path=str(instruction))
                limits=dict(memory_max_bytes=134217728,memory_swap_max_bytes=0,cpu_quota_percent=20,
                    tasks_max=16,stop_grace_seconds=1,checkpoint_grace_seconds=1,
                    poll_seconds=.2,accounting_max_age_seconds=2)
                profile=dict(cwd=tmp,codex_home=str(home),codex_path='/bin/true',tmux_session='fixture',
                    timeout=1,app_server='unix://'+str(root/'shared.sock' if shared else home.parent/'app-server.sock'),
                    strict_execution=limits)
                config=dict(version=1,profiles={'worker':profile},lifecycle_defaults=dict(
                    handoff_writer=selection,preflight_reviewer=selection,session_token_limit=100,
                    objective_token_limit=500,session_time_limit_seconds=80,objective_time_limit_seconds=100,
                    max_correction_cycles=1),continuations={'source':dict(objective_id='goal',objective='work',
                    approval='operator fixture',started_at='1970-01-01T00:01:40Z')})
                profiles=root/'profiles.json';profiles.write_text(json.dumps(config))
                expected='objective-owned home and endpoint' if shared else 'cgroup-v2 and suspend-aware BOOTTIME'
                with patch('codex_wake.native_clock.snapshot',return_value={'utc':{'lower':100,'upper':101}}), \
                        patch('codex_wake.strict_runtime.time',SimpleNamespace()), \
                        patch('codex_wake.native_protocol.native_request') as native, \
                        patch('codex_wake.host_execution.subprocess.run') as host:
                    publish_supervision(wake,1)
                    with redirect_stdout(StringIO()),self.assertRaisesRegex(WakeError,expected):
                        run(['--wake-root',str(wake),'sessions','spawn','--profiles',str(profiles),
                            '--profile','worker','--objective-ref','source','--intent','refusal','--name','worker',
                            '--task','No effects permitted','--expires-at','2030-01-01T00:00:00Z','--json'])
                    native.assert_not_called();host.assert_not_called()
                view=ObjectiveLedger(wake,'goal').inspect(now=101)
                self.assertEqual(len(view['actors']),1)
                self.assertEqual(view['tokens_used'],0)
