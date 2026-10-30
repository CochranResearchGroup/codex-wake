import tempfile
import unittest
from pathlib import Path
from test_controller_flows import actor


class ForeachTests(unittest.TestCase):
    def test_new_sessions_pin_members_and_restart_preserves_per_item_results(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            effects = []
            def invoke(operation, arguments, **kwargs):
                kwargs['authorize']()
                if operation == 'sessions.capabilities':
                    return {'result': {'modes': ['new_session', 'sequential']}}
                if operation == 'sessions.create':
                    thread = 'thread-' + str(len(effects))
                    effects.append(('create', thread))
                    result = {'target': dict(arguments['expected_target'], conversation_id=thread)}
                elif operation == 'sessions.prompt':
                    effects.append(('prompt', arguments['expected_target']['conversation_id'], arguments['prompt']))
                    result = {'accepted': True}
                elif operation == 'sessions.wait':
                    return {'result': {'wait': {'status': 'completed'}, 'operation': {'execution':'completed','answer': {'text': 'actual answer'}}}}
                else:
                    raise AssertionError(operation)
                return {'result': {'operation': {'operation_id': kwargs['request']['operation_id'], 'result': result}}}
            source = dict(id='example', version=1, entry='each', nodes=[
                dict(id='each', type='foreach', items={'ref': 'inputs.members'}, mode='new_session',
                    profile='fixture', expected_target={'host': 'host', 'environment': 'test', 'account': 'alice'},
                    prompt={'ref': 'item'}, next='done'),
                dict(id='done', type='end', value={'ref': 'steps.each'})])
            owner = ControllerFlows(Path(directory), host='host', environment='test', invoke=invoke,
                authorize=lambda: actor(), now=lambda: 100)
            owner.publish(actor(), source)
            inputs = {'members': ['first', 'second']}
            run = owner.start(actor(), 'example', 1, inputs=inputs, intent='one', binding='caller')
            inputs['members'].append('later mutation')
            done = owner.advance(actor(), run['run_id'])
            self.assertEqual(done['phase'], 'completed')
            self.assertEqual([e[2] for e in effects if e[0] == 'prompt'], ['first', 'second'])
            self.assertEqual(len({e[1] for e in effects if e[0] == 'create'}), 2)
            self.assertEqual(len(done['result']['items']), 2)
            restarted = ControllerFlows(Path(directory), host='host', environment='test', invoke=invoke,
                authorize=lambda: actor(), now=lambda: 100)
            self.assertEqual(restarted.advance(actor(), run['run_id']), done)
            self.assertEqual(len(effects), 4)

    def test_unsupported_host_mode_is_rejected_before_creating_a_session(self):
        from codex_wake.controller_flows import ControllerFlows
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            effects = []
            def invoke(operation, arguments, **kwargs):
                if operation == 'sessions.capabilities':
                    return {'result': {'modes': ['sequential']}}
                effects.append(operation)
                return {}
            owner = ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=lambda:actor(),now=lambda:100)
            source = dict(id='example',version=1,entry='each',nodes=[dict(id='each',type='foreach',items=['one'],
                mode='new_session',profile='fixture',expected_target={'host':'host','environment':'test'},prompt={'ref':'item'})])
            owner.publish(actor(),source)
            with self.assertRaises(InventoryError) as caught:
                owner.start(actor(),'example',1,inputs={},intent='one',binding='caller')
            self.assertEqual(caught.exception.code,'unsupported_session_mode')
            self.assertEqual(effects,[])

    def test_sequential_prompts_wait_for_the_previous_turn_and_never_create_sessions(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            prompts = []
            completed = [False]
            def invoke(operation,arguments,**kwargs):
                if operation == 'sessions.capabilities':
                    return {'result': {'modes': ['sequential']}}
                if operation == 'sessions.prompt':
                    prompts.append((arguments['expected_target']['conversation_id'],arguments['prompt']))
                    return {'result': {'operation': {'operation_id': kwargs['request']['operation_id']}}}
                if operation == 'sessions.wait':
                    return {'result': {'wait': {'status': 'completed' if completed[0] else 'timeout'},
                        'operation': {'execution':'completed','answer': {'text': 'retained'}}}}
                raise AssertionError(operation)
            source = dict(id='example',version=1,entry='each',nodes=[dict(id='each',type='foreach',items=['one','two'],
                mode='sequential',profile='fixture',expected_target={'host':'host','environment':'test','conversation_id':'same'},
                prompt={'ref':'item'},next='done'),dict(id='done',type='end',value={'ref':'steps.each'})])
            owner = ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=lambda:actor(),now=lambda:100)
            owner.publish(actor(),source)
            run = owner.start(actor(),'example',1,inputs={},intent='one',binding='caller')
            self.assertEqual(owner.advance(actor(),run['run_id'])['phase'],'waiting')
            self.assertEqual(prompts,[('same','one')])
            completed[0] = True
            restarted = ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=lambda:actor(),now=lambda:100)
            done = restarted.advance(actor(),run['run_id'])
            self.assertEqual(done['phase'],'completed')
            self.assertEqual(prompts,[('same','one'),('same','two')])
            self.assertEqual([item['target']['conversation_id'] for item in done['result']['items']],['same','same'])

    def test_parallel_default_join_waits_for_siblings_and_reports_aggregate_failure(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            effects = []
            waits = []
            def invoke(operation,arguments,**kwargs):
                if operation == 'sessions.capabilities':return {'result': {'modes':['new_session']}}
                if operation == 'sessions.create':
                    thread='thread-'+str(len(effects))
                    effects.append(('create',thread))
                    return {'result': {'operation': {'result': {'target':dict(arguments['expected_target'],conversation_id=thread)}}}}
                if operation == 'sessions.prompt':
                    effects.append(('prompt',arguments['prompt']))
                    return {'result': {'operation': {'operation_id':kwargs['request']['operation_id']}}}
                if operation == 'sessions.wait':
                    self.assertEqual(len([e for e in effects if e[0]=='prompt']),2)
                    waits.append(arguments['operation_id'])
                    return {'result': {'wait': {'status':'completed'},'operation': {'execution':'failed' if len(waits)==1 else 'completed','answer':{'text':'retained'}}}}
                raise AssertionError(operation)
            source=dict(id='example',version=1,entry='each',nodes=[dict(id='each',type='foreach',items=['one','two'],parallelism=2,
                mode='new_session',profile='fixture',expected_target={'host':'host','environment':'test'},prompt={'ref':'item'},next='dependent'),
                dict(id='dependent',type='end',value='must not release')])
            owner=ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=lambda:actor(),now=lambda:100)
            owner.publish(actor(),source)
            run=owner.start(actor(),'example',1,inputs={},intent='one',binding='caller')
            done=owner.advance(actor(),run['run_id'])
            self.assertEqual(done['phase'],'failed')
            self.assertEqual(len(waits),2)
            self.assertEqual(done['steps']['each']['status'],'failed')
            self.assertEqual([i['result']['execution'] for i in done['steps']['each']['items']],['failed','completed'])
