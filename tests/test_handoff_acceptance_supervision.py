"""Acceptance runner keeps the same native assignment alive during clock holds."""
import sys
import json
import os
import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import agent_handoff_acceptance as runner


class OwnedCleanupTests(unittest.TestCase):
    def test_generated_writer_emits_parseable_checkpoint_with_native_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            program=runner.checkpoint_program({'commit':'a'*40},'Finish fixture')
            result=subprocess.run([sys.executable,'-c',program],cwd=tmp,
                env=dict(os.environ,CODEX_THREAD_ID='native-source'),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            checkpoint=json.loads((Path(tmp)/'checkpoint.json').read_text())
            self.assertEqual(checkpoint['source_thread_id'],'native-source')
            self.assertEqual(checkpoint['objective'],'Finish fixture')
            self.assertIn('checkpoint:native-source:',result.stdout)

    def test_generated_preflight_is_executable_python_before_paid_admission(self):
        program=runner.preflight_program({'repo': '/fixture', 'head': 'a'*40})
        compile(program, 'preflight.py', 'exec')

    def test_paid_fixture_catalog_keeps_exact_selected_skills_and_holds_missing_sources(self):
        catalog={'data':[{'skills':[{'path':p,'enabled':True} for p in ('writer','reviewer','guide','unrelated')]}]}
        self.assertEqual(runner.excluded_skill_paths(catalog,['writer','reviewer','guide']),['unrelated'])
        with self.assertRaisesRegex(RuntimeError,'exact selected'):
            runner.excluded_skill_paths(catalog,['missing'])
    def test_prefight_without_goal_interrupts_only_its_exact_native_assignment(self):
        calls=[]
        running={'value':True}
        def request(method, params):
            calls.append((method,params))
            if method=='thread/goal/get':return {'goal':None}
            if method=='turn/interrupt':running['value']=False;return {}
            return {'thread':dict(id='receiver',turns=[dict(id='owned-turn',
                status='inProgress' if running['value'] else 'interrupted',
                items=[dict(type='userMessage',clientId='owned-task')])])}
        result=runner.settle_owned_successor(request,dict(successor_thread_id='receiver',
            successor={'submission_id':'owned-task'}))
        self.assertTrue(result['settled'])
        self.assertEqual([p for m,p in calls if m=='turn/interrupt'],[dict(threadId='receiver',turnId='owned-turn')])

    def test_foreign_preflight_turn_cannot_be_interrupted(self):
        effects=[]
        def request(method, params):
            if method=='thread/goal/get':return {'goal':None}
            if method=='turn/interrupt':effects.append(params)
            return {'thread':dict(id='receiver',turns=[dict(id='foreign',status='inProgress',
                items=[dict(type='userMessage',clientId='other-task')])])}
        with self.assertRaisesRegex(RuntimeError,'not owned'):
            runner.settle_owned_successor(request,dict(successor_thread_id='receiver',successor={'submission_id':'owned-task'}))
        self.assertEqual(effects,[])


class PreflightSupervisionTests(unittest.TestCase):
    def test_transient_time_hold_observes_same_intent_until_preflight_ready(self):
        intent = ['sessions', 'handoff', '--intent', 'original']
        states = iter([
            (2, dict(state='blocked', reason='admissible_time_unavailable',
                     successor_thread_id='receiver', successor={'submission_id': 'task'})),
            (0, dict(state='awaiting_activation', successor_thread_id='receiver')),
        ])
        calls, observations = [], []
        def invoke(args):
            calls.append(args)
            return next(states)
        with patch.object(runner.time, 'monotonic', return_value=0), patch.object(runner.time, 'sleep'):
            result = runner.wait_for_preflight(invoke, intent, 10, observations.append)
        self.assertEqual(result['state'], 'awaiting_activation')
        self.assertEqual(calls, [intent, intent])
        self.assertEqual(len(observations), 2)

    def test_clock_hold_cannot_extend_observation_deadline(self):
        state = dict(state='blocked', reason='admissible_time_unavailable')
        calls = []
        def invoke(args):
            calls.append(args)
            return 2, state
        with patch.object(runner.time, 'monotonic', return_value=11), patch.object(runner.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'admissible_time_unavailable'):
                runner.wait_for_preflight(invoke, ['original'], 10, lambda state: None)
        self.assertEqual(calls, [['original']])

    def test_exhausted_allowance_remains_terminal(self):
        state = dict(state='blocked', reason='preflight_allowance_exhausted')
        with patch.object(runner.time, 'monotonic', return_value=0):
            with self.assertRaisesRegex(RuntimeError, 'preflight_allowance_exhausted'):
                runner.wait_for_preflight(lambda args: (2, state), ['original'], 10, lambda state: None)


class HostNativeObservationTests(unittest.TestCase):
    def test_native_mcp_setup_proves_readback_and_missing_checkpoint_stays_effect_free(self):
        calls=[]
        def request(method,params):
            calls.append((method,params))
            if params['tool']=='wake_sessions_configuration':
                return {'content':[dict(type='text',text=json.dumps(dict(source_thread_id='probe',revision='frozen')))]}
            return dict(isError=True,content=[dict(type='text',text=json.dumps(
                dict(error={'code':'invalid_cli_response'},reconciliation_required=True)))])
        proof=runner.qualify_lifecycle_mcp(request,'probe','worker','2030-01-01T00:00:00Z')
        self.assertEqual(proof['configuration_revision'],'frozen')
        self.assertTrue(proof['handoff_negative_case_rejected'])
        self.assertEqual([p['tool'] for _,p in calls],['wake_sessions_configuration','wake_sessions_handoff'])

    def test_host_readback_binds_resource_to_source_and_successor(self):
        calls = []
        def request(method, params):
            calls.append((method, params))
            if method == 'thread/goal/get':
                return {'goal': {'threadId': 'source', 'status': 'paused'}}
            if method == 'skills/list':
                return {'data': [{'skills': [{'path': '/guide', 'enabled': True}]}]}
            return {'content': [{'text': '{"session":{"thread_id":"source"},"complete":true}'}]}
        result = runner.observe_native_preflight(request, 'source', 'successor', '/guide', '/workspace')
        self.assertEqual(result['source_thread_id'], 'source')
        self.assertEqual(result['successor_thread_id'], 'successor')
        self.assertEqual(result['native_resource']['state'], 'passed')
        self.assertEqual(calls[-1][0], 'mcpServer/tool/call')
        self.assertEqual(calls[-1][1]['threadId'], 'successor')
        self.assertEqual(calls[-1][1]['arguments'], {'selector': 'thread:source'})

    def test_host_readback_rejects_another_resource_identity(self):
        def request(method, params):
            if method == 'thread/goal/get':
                return {'goal': {'threadId': 'source', 'status': 'paused'}}
            if method == 'skills/list':
                return {'data': [{'skills': [{'path': '/guide', 'enabled': True}]}]}
            return {'content': [{'text': '{"session":{"thread_id":"foreign"},"complete":true}'}]}
        with self.assertRaisesRegex(RuntimeError, 'identity/readiness mismatch'):
            runner.observe_native_preflight(request, 'source', 'successor', '/guide', '/workspace')


if __name__ == '__main__':
    unittest.main()
