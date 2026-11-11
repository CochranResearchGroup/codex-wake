"""Ordinary governor controls use the retained accounting/controller owners."""
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


class GovernorTests(unittest.TestCase):
    def test_status_does_not_provision_an_allowance_or_watcher(self):
        from codex_wake.governor import execute
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'uncreated'
            row = dict(thread_id='11111111-1111-1111-1111-111111111111', endpoint='unix:///owned')
            with patch('codex_wake.local_sessions.resolve', return_value=row):
                result = execute(root, 'status', dict(selector=row['thread_id']))
            self.assertEqual(result['state'], 'disconnected')
            self.assertIsNone(result['usage']['used_tokens'])
            self.assertEqual(result['reason'], 'not_enrolled')
            self.assertFalse(root.exists())

    def test_activation_starts_new_window_without_erasing_lifetime_history(self):
        import json
        import test_goal_supervision as fixtures
        from codex_wake.goal_supervision import enroll, poll
        harness = fixtures.GoalSupervisionTests()
        self.addCleanup(harness.doCleanups)
        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, _ = harness.fixture(directory)
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW):
                first = enroll(root, policy, fixtures.THREAD, 100, 120,
                    session_scope=True, activation_baseline=True)
                self.assertEqual(first['used_tokens'], 0)
                self.assertEqual(first['lifetime_used_tokens'], 40)
                self.assertEqual(first['deadline'], fixtures.NOW+120)
                again = enroll(root, policy, fixtures.THREAD, 90, 110,
                    session_scope=True, activation_baseline=True)
                self.assertEqual(again['generation'], first['generation'])
                self.assertEqual(again['lifetime_used_tokens'], 40)

    def test_operator_controls_retain_usage_and_model_cannot_loosen(self):
        import test_goal_supervision as fixtures
        from codex_wake.governor import execute, local_operator_principal
        from codex_wake.goal_supervision import enroll
        from codex_wake.session_permissions import Principal
        harness = fixtures.GoalSupervisionTests()
        self.addCleanup(harness.doCleanups)
        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, _ = harness.fixture(directory)
            native['goal']['status'] = 'paused'
            native['active'] = []
            row = dict(thread_id=fixtures.THREAD, endpoint='unix:///owned')
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW), patch('codex_wake.local_sessions.resolve', return_value=row):
                enroll(root, policy, fixtures.THREAD, 100, 120)
                with self.assertRaisesRegex(ValueError, 'authenticated operator'):
                    execute(root, 'extend', dict(selector=fixtures.THREAD, add_tokens=50), principal=Principal(fixtures.THREAD))
                args = dict(selector=fixtures.THREAD, add_tokens=50, add_seconds=30, request_id='extend-once')
                extended = execute(root, 'extend', args, principal=local_operator_principal())
                self.assertEqual(extended['limits']['token_limit'], 150)
                self.assertEqual(extended['usage']['used_tokens'], 40)
                self.assertEqual(execute(root, 'extend', args, principal=local_operator_principal())['limits']['token_limit'], 150)
                reset = execute(root, 'reset', dict(selector=fixtures.THREAD, request_id='reset-once'), principal=local_operator_principal())
                self.assertEqual(reset['usage']['used_tokens'], 0)
                self.assertEqual(reset['usage']['lifetime_used_tokens'], 40)
                advisory = execute(root, 'advisory', dict(selector=fixtures.THREAD), principal=local_operator_principal())
                self.assertEqual(advisory['state'], 'advisory')
                disabled = execute(root, 'disable', dict(selector=fixtures.THREAD), principal=local_operator_principal())
                self.assertEqual(disabled['state'], 'disabled')
                self.assertEqual(disabled['usage']['lifetime_used_tokens'], 40)
                self.assertEqual(native['goal']['status'], 'paused')

    def test_active_session_window_can_be_extended_without_stopping_or_resuming_it(self):
        import test_goal_supervision as fixtures
        from codex_wake.governor import execute, local_operator_principal
        from codex_wake.goal_supervision import enroll
        harness = fixtures.GoalSupervisionTests()
        self.addCleanup(harness.doCleanups)
        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, _ = harness.fixture(directory)
            row = dict(thread_id=fixtures.THREAD, endpoint='unix:///owned')
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW), patch('codex_wake.local_sessions.resolve', return_value=row):
                enroll(root, policy, fixtures.THREAD, 100, 120, session_scope=True, activation_baseline=True)
                result = execute(root, 'extend', dict(selector=fixtures.THREAD, add_tokens=50, add_seconds=30), principal=local_operator_principal())
                self.assertEqual(result['limits']['token_limit'], 150)
                self.assertEqual(result['usage']['used_tokens'], 0)
                self.assertEqual(native['goal']['status'], 'active')
                self.assertEqual(native['active'], ['work'])
                self.assertFalse(result['operation']['resumed'])

    def test_reactivation_requires_operator_and_keeps_the_same_window(self):
        import test_goal_supervision as fixtures
        from codex_wake.governor import execute, local_operator_principal
        from codex_wake.goal_supervision import enroll
        from codex_wake.session_permissions import Principal
        harness = fixtures.GoalSupervisionTests()
        self.addCleanup(harness.doCleanups)
        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, _ = harness.fixture(directory)
            row = dict(thread_id=fixtures.THREAD, endpoint='unix:///owned')
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW), patch('codex_wake.local_sessions.resolve', return_value=row):
                first = enroll(root, policy, fixtures.THREAD, 100, 120)
                execute(root, 'disable', dict(selector=fixtures.THREAD), principal=local_operator_principal())
                with self.assertRaisesRegex(ValueError, 'operator'):
                    execute(root, 'activate', dict(selector=fixtures.THREAD), principal=Principal(fixtures.THREAD))
                result = execute(root, 'activate', dict(selector=fixtures.THREAD), principal=local_operator_principal())
                self.assertNotEqual(result['state'], 'disabled')
                self.assertEqual(result['usage']['used_tokens'], 40)
                self.assertEqual(result['owner_receipt']['generation'], first['generation'])
                self.assertEqual(native['active'], ['work'])

    def test_request_id_cannot_name_a_different_mutation(self):
        import test_goal_supervision as fixtures
        from codex_wake.governor import execute, local_operator_principal
        from codex_wake.goal_supervision import enroll
        harness = fixtures.GoalSupervisionTests()
        self.addCleanup(harness.doCleanups)
        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, _ = harness.fixture(directory)
            row = dict(thread_id=fixtures.THREAD, endpoint='unix:///owned')
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW), patch('codex_wake.local_sessions.resolve', return_value=row):
                enroll(root, policy, fixtures.THREAD, 100, 120)
                arguments = dict(selector=fixtures.THREAD, request_id='operator-switch')
                execute(root, 'disable', arguments, principal=local_operator_principal())
                self.assertEqual(execute(root, 'disable', arguments, principal=local_operator_principal())['state'], 'disabled')
                with self.assertRaisesRegex(ValueError, 'different governor operation'):
                    execute(root, 'activate', arguments, principal=local_operator_principal())
                self.assertEqual(execute(root, 'status', dict(selector=fixtures.THREAD))['state'], 'disabled')

    def test_resume_existing_goal_less_session_uses_current_allowance_once(self):
        import time
        import test_goal_supervision as fixtures
        from codex_wake.governor import execute, local_operator_principal
        from codex_wake.goal_supervision import enroll, show
        harness = fixtures.GoalSupervisionTests()
        self.addCleanup(harness.doCleanups)
        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, request = harness.fixture(directory)
            native['active'] = []
            def native_call(endpoint, executable, method, params, timeout):
                if method == 'thread/goal/get':
                    return {'goal': None}
                value = request(endpoint, executable, method, params, timeout)
                if method == 'turn/start':
                    native['active'] = ['resumed-work']
                return value
            row = dict(thread_id=fixtures.THREAD, endpoint='unix:///owned')
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW), patch('codex_wake.goal_supervision.native_request', side_effect=native_call), patch('codex_wake.local_sessions.resolve', return_value=row):
                first = enroll(root, policy, fixtures.THREAD, 100, 120, session_scope=True, activation_baseline=True)
                deadline = time.monotonic()+7
                while not show(root, policy, fixtures.THREAD).get('engagement', {}).get('engaged'):
                    self.assertLess(time.monotonic(), deadline, 'independent watcher acknowledgement missing')
                    time.sleep(.05)
                args = dict(selector=fixtures.THREAD, request_id='continue-existing')
                resumed = execute(root, 'resume', args, principal=local_operator_principal())
                self.assertTrue(resumed['operation']['resumed'])
                self.assertEqual(resumed['limits']['token_limit'], 100)
                self.assertEqual(resumed['owner_receipt']['generation'], first['generation'])
                self.assertEqual(execute(root, 'resume', args, principal=local_operator_principal())['operation'], resumed['operation'])
                self.assertEqual(sum(method=='turn/start' for method, _ in native['calls']), 1)

    def test_exhaustion_stops_qualified_children_and_preserves_unrelated_task(self):
        import json
        import test_goal_supervision as fixtures
        from codex_wake.goal_supervision import enroll, poll
        harness = fixtures.GoalSupervisionTests()
        self.addCleanup(harness.doCleanups)
        child = '00000000-0000-7000-8000-000000000290'
        peer = '00000000-0000-7000-8000-000000000291'
        with tempfile.TemporaryDirectory() as directory:
            root, policy, log, native, request = harness.fixture(directory)
            native['siblings'] = {identity: dict(goal=dict(threadId=identity, createdAt=fixtures.NOW, status='active'), active=['child-work'], calls=[]) for identity in (child, peer)}
            def native_call(endpoint, executable, method, params, timeout):
                if params.get('threadId') == child:
                    member = native['siblings'][child]
                    if method == 'thread/goal/set':
                        member['goal']['status'] = params['status']
                        return {}
                    if method == 'turn/interrupt':
                        member['active'].remove(params['turnId'])
                        return {}
                return request(endpoint, executable, method, params, timeout)
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW), patch('codex_wake.goal_supervision.native_request', side_effect=native_call):
                enroll(root, policy, fixtures.THREAD, 39, 120, session_scope=True, activation_baseline=True)
                rows = [json.loads(line) for line in log.read_text().splitlines()]
                child_rows = json.loads(json.dumps(rows).replace(fixtures.THREAD, child))
                child_rows[0]['payload'].update(parent_thread_id=fixtures.THREAD, session_id=fixtures.THREAD,
                    source={'subagent': {'thread_spawn': {'parent_thread_id': fixtures.THREAD}}})
                child_rows.pop(1)
                child_rows[-1]['payload'].update(session_id=fixtures.THREAD, response_id='child-response')
                (log.parent/'child.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in child_rows))
                stopped = poll(root)[0]
                self.assertEqual(stopped['used_tokens'], 40)
                self.assertEqual(native['active'], [])
                self.assertEqual(native['siblings'][child]['active'], [])
                self.assertEqual(native['siblings'][child]['goal']['status'], 'paused')
                self.assertEqual(native['siblings'][peer]['active'], ['child-work'])
                self.assertTrue(stopped['descendant_stop_verified'])

    def test_task_allowances_stack_under_shared_host_ceiling(self):
        import json
        import test_goal_supervision as fixtures
        from codex_wake.goal_supervision import enroll
        harness = fixtures.GoalSupervisionTests()
        self.addCleanup(harness.doCleanups)
        peer = '00000000-0000-7000-8000-000000000291'
        with tempfile.TemporaryDirectory() as directory:
            root, policy, log, native, _ = harness.fixture(directory)
            grant = json.loads(policy.read_text())['callers'][fixtures.THREAD]
            grant.pop('allocation_id')
            policy.write_text(json.dumps(dict(version=2, native_caller_binding=True,
                default_allocation='shared', allocations={'shared': grant})))
            rows = json.loads(log.read_text().splitlines()[0])
            peer_rows = json.loads(json.dumps([json.loads(line) for line in log.read_text().splitlines()]).replace(fixtures.THREAD, peer))
            (log.parent/'peer.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in peer_rows))
            native['siblings'] = {peer: dict(goal=dict(threadId=peer,createdAt=fixtures.NOW,status='active'),active=['work'],calls=[])}
            context = lambda thread: dict(threadId=thread, sessionId=thread, callId='activate',
                **{'x-codex-turn-metadata': dict(thread_id=thread,session_id=thread,turn_id='work')})
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW):
                first = enroll(root, policy, fixtures.THREAD, 100, 120, session_scope=True,
                    activation_baseline=True, native_context=context(fixtures.THREAD))
                self.assertEqual(first['token_limit'], 100)
                self.assertEqual(first['shared_limits']['token_limit'], 1000)
                second = enroll(root, policy, peer, 200, 180, session_scope=True,
                    activation_baseline=True, native_context=context(peer))
                self.assertEqual(second['token_limit'], 200)
                self.assertEqual(second['used_tokens'], 0)
                self.assertEqual(second['shared_limits']['token_limit'], 1000)
                from codex_wake.governor import execute, local_operator_principal
                from codex_wake.goal_supervision import poll
                response=json.loads(log.read_text().splitlines()[-1])
                response['payload'].update(response_id='later-work',usage=dict(input_tokens=118,cached_input_tokens=0,output_tokens=2,total_tokens=120))
                with log.open('a') as stream:stream.write(json.dumps(response)+'\n')
                stopped=poll(root)
                selected=next(item for item in stopped if item['thread_id']==fixtures.THREAD)
                self.assertEqual(selected['reason'],'task_exhausted')
                self.assertEqual(native['active'],[])
                self.assertEqual(native['siblings'][peer]['active'],['work'])
                row=dict(thread_id=fixtures.THREAD,endpoint='unix:///owned')
                with patch('codex_wake.local_sessions.resolve',return_value=row):
                    extended=execute(root,'extend',dict(selector=fixtures.THREAD,add_tokens=50),principal=local_operator_principal())
                    self.assertEqual(extended['limits']['token_limit'],150)
                    self.assertEqual(extended['limits']['shared']['token_limit'],1000)
                    self.assertEqual(extended['usage']['used_tokens'],120)
                    reset=execute(root,'reset',dict(selector=fixtures.THREAD),principal=local_operator_principal())
                    self.assertEqual(reset['usage']['used_tokens'],0)
                    self.assertEqual(reset['limits']['shared']['used_tokens'],160)
                    execute(root,'disable',dict(selector=fixtures.THREAD),principal=local_operator_principal())
                from codex_wake.goal_supervision import show
                self.assertTrue(show(root,policy,peer).get('governor_enabled',True))
                response['payload'].update(response_id='shared-ceiling',usage=dict(input_tokens=948,cached_input_tokens=0,output_tokens=2,total_tokens=950))
                with log.open('a') as stream:stream.write(json.dumps(response)+'\n')
                shared_stop=poll(root)
                self.assertTrue(all(item['reason']=='allocation_exhausted' for item in shared_stop))
                self.assertEqual(native['siblings'][peer]['active'],[])



    def test_ordinary_activation_needs_no_uuid_grant_and_counts_only_new_usage(self):
        import json
        import test_goal_supervision as fixtures
        from codex_wake.governor import execute, local_operator_principal
        from codex_wake.goal_supervision import poll
        harness = fixtures.GoalSupervisionTests()
        self.addCleanup(harness.doCleanups)
        with tempfile.TemporaryDirectory() as directory:
            root, policy, log, native, request = harness.fixture(directory)
            log.chmod(0o600)
            grant=json.loads(policy.read_text())['callers'][fixtures.THREAD]
            row=dict(thread_id=fixtures.THREAD,endpoint=grant['app_server'],
                target=dict(home=grant['codex_home'],executable=grant['codex_path']))
            def native_call(endpoint, executable, method, params, timeout):
                result=request(endpoint, executable, method, params, timeout)
                if method=='thread/read':result['thread']['path']=str(log)
                return result
            with harness.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper',return_value=fixtures.NOW), patch('codex_wake.native_clock.snapshot',return_value=dict(utc=dict(status='network',sources=['a','b'],lower=fixtures.NOW,upper=fixtures.NOW),counter=None,reason='bounded_utc')), patch('codex_wake.local_sessions.resolve',return_value=row), patch('codex_wake.goal_supervision.native_request',side_effect=native_call):
                result=execute(root,'activate',dict(selector=fixtures.THREAD,token_limit=100,time_limit_seconds=120,request_id='activate-without-provisioning'),principal=local_operator_principal())
                self.assertEqual(result['usage']['used_tokens'],0)
                self.assertEqual(result['usage']['lifetime_used_tokens'],40)
                self.assertEqual(result['limits']['token_limit'],100)
                self.assertEqual(result['state'],'disconnected')
                self.assertEqual(result['reason'],'native_guard_capability_unavailable')
                response=json.loads(log.read_text().splitlines()[-1])
                response['payload'].update(response_id='new-response',usage=dict(input_tokens=18,cached_input_tokens=0,output_tokens=2,total_tokens=20))
                with log.open('a') as stream:stream.write(json.dumps(response)+'\n')
                self.assertEqual(poll(root)[0]['used_tokens'],20)
                current=execute(root,'status',dict(selector=fixtures.THREAD))
                self.assertEqual(current['usage']['lifetime_used_tokens'],60)
                with patch('codex_wake.local_sessions.resolve',side_effect=AssertionError('enrolled status must use retained exact scope')):
                    self.assertEqual(execute(root,'status',dict(selector=fixtures.THREAD))['usage']['used_tokens'],20)

    def test_native_guard_ack_and_trusted_host_policy_bound_activation(self):
        import json
        import time
        import test_goal_supervision as fixtures
        from codex_wake.governor import execute, native_principal
        harness=fixtures.GoalSupervisionTests()
        self.addCleanup(harness.doCleanups)
        with tempfile.TemporaryDirectory() as directory:
            root,policy,log,native,request=harness.fixture(directory)
            log.chmod(0o600)
            grant=json.loads(policy.read_text())['callers'][fixtures.THREAD]
            row=dict(thread_id=fixtures.THREAD,endpoint=grant['app_server'],target=dict(home=grant['codex_home'],executable=grant['codex_path']))
            native['lease_reply']=dict(armed=True,expired=False,stopVerified=False,ttlMs=10000)
            def native_call(endpoint, executable, method, params, timeout):
                if method=='thread/goal/get' and native.get('goal_missing'):return {'goal':None}
                result=request(endpoint,executable,method,params,timeout)
                if method=='thread/read':result['thread']['path']=str(log)
                return result
            actor=native_principal(fixtures.THREAD,policy=policy)
            with harness.controller(root),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=fixtures.NOW),patch('codex_wake.local_sessions.resolve',return_value=row),patch('codex_wake.goal_supervision.native_request',side_effect=native_call):
                with self.assertRaisesRegex(ValueError,'inherited host ceilings'):
                    execute(root,'activate',dict(selector=fixtures.THREAD,token_limit=1001,time_limit_seconds=120),principal=actor)
                with self.assertRaisesRegex(ValueError,'local operator'):
                    execute(root,'activate',dict(selector=fixtures.THREAD,token_limit=100,time_limit_seconds=120,policy='/arbitrary'),principal=actor)
                result=execute(root,'activate',dict(selector=fixtures.THREAD,token_limit=100,time_limit_seconds=120),principal=actor)
                until=time.monotonic()+7
                while result['state']!='enforced':
                    self.assertLess(time.monotonic(),until,result)
                    time.sleep(.05)
                    result=execute(root,'status',dict(selector=fixtures.THREAD),principal=actor)
                self.assertTrue(result['watcher']['native_guard_qualified'])
                self.assertEqual(result['limits']['token_limit'],100)
                self.assertTrue(native['lease_calls'])
                from codex_wake.goal_supervision import poll
                response=json.loads(log.read_text().splitlines()[-1])
                response['payload'].update(response_id='guard-stop-work',usage=dict(input_tokens=118,cached_input_tokens=0,output_tokens=2,total_tokens=120))
                with log.open('a') as stream:stream.write(json.dumps(response)+'\n')
                stopping=poll(root)[0]
                self.assertEqual(stopping['state'],'stop_unverified')
                self.assertEqual(native['lease_calls'][-1]['ttlMs'],1)
                native['goal']['status']='paused'
                native['active']=[]
                native['lease_reply']=dict(armed=False,expired=True,stopVerified=True,ttlMs=10000)
                held=poll(root)[0]
                self.assertEqual(held['state'],'stopped')
                self.assertTrue(held['stop_proof'])
                self.assertEqual(held['native_guard']['status'],'expired')
                native['active']=['operator-reply']
                poll(root)
                self.assertEqual(native['active'],['operator-reply'])
                self.assertEqual(execute(root,'status',dict(selector=fixtures.THREAD),principal=actor)['state'],'limit_reached')
                native['goal_missing']=True
                native['active']=[]
                from codex_wake.governor import local_operator_principal
                execute(root,'reset',dict(selector=fixtures.THREAD),principal=local_operator_principal())
                poll(root)
                idle=execute(root,'status',dict(selector=fixtures.THREAD),principal=actor)
                self.assertEqual(idle['state'],'disconnected')
                self.assertEqual(idle['reason'],'idle_session_future_task_isolation_unsupported')
                self.assertFalse(any(method in ('thread/goal/set','turn/start') for method,_ in native['calls']))
