import tempfile
import unittest
from pathlib import Path

from codex_wake.controller_auth import Actor
from codex_wake.managed_inventory import InventoryError


def actor():
    return Actor('author', 'service', 'client', 'grant', 'local://test', 'wake:controller',
        frozenset({'observe', 'control'}), [{'host': 'host', 'environment': 'test', 'flow_id': 'example'}], 10000)


def definition():
    return {'id': 'example', 'version': 1, 'entry': 'choose', 'nodes': [
        {'id': 'choose', 'type': 'branch', 'condition': {'op': 'eq', 'left': {'ref': 'inputs.go'}, 'right': True},
         'then': 'call', 'else': 'end'},
        {'id': 'call', 'type': 'call', 'operation': 'inventory.list', 'arguments': {}, 'next': 'end'},
        {'id': 'end', 'type': 'end', 'value': {'ref': 'steps.call'}}]}


class FlowTests(unittest.TestCase):
    def test_sdk_and_proposal_publish_the_same_immutable_version(self):
        from codex_wake.controller_flows import FlowDefinition, ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            owner = ControllerFlows(Path(directory), host='host', environment='test',
                invoke=lambda *args, **kwargs: {}, authorize=lambda: actor(), now=lambda: 100)
            sdk = FlowDefinition.compile(definition())
            proposal = owner.propose(actor(), definition())
            published = owner.publish(actor(), sdk)
            self.assertEqual(published['definition_sha256'], proposal['definition_sha256'])
            self.assertEqual(owner.publish(actor(), definition()), published)
            changed = definition()
            changed['nodes'][1]['operation'] = 'accounts.list'
            with self.assertRaises(InventoryError) as caught:
                owner.publish(actor(), changed)
            self.assertEqual(caught.exception.code, 'immutable_flow_version')

    def test_pinned_branch_result_survives_restart_without_repeating_call(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def invoke(operation, arguments, **kwargs):
                kwargs['authorize']()
                calls.append(operation)
                return {'observed': True}
            owner = ControllerFlows(Path(directory), host='host', environment='test',
                invoke=invoke, authorize=lambda: actor(), now=lambda: 100)
            owner.publish(actor(), definition())
            started = owner.start(actor(), 'example', 1, inputs={'go': True}, intent='one', binding='caller')
            done = owner.advance(actor(), started['run_id'])
            self.assertEqual(done['phase'], 'completed')
            self.assertEqual(done['result'], {'observed': True})
            self.assertEqual(calls, ['inventory.list'])
            restarted = ControllerFlows(Path(directory), host='host', environment='test',
                invoke=lambda *args, **kwargs: self.fail('completed step replayed'), authorize=lambda: actor(), now=lambda: 100)
            newer = definition(); newer['version'] = 2
            restarted.publish(actor(), newer)
            restored = restarted.inspect(actor(), started['run_id'])
            self.assertEqual(restored['version'], 1)
            self.assertEqual(restarted.advance(actor(), started['run_id']), restored)
            self.assertEqual(restarted.start(actor(), 'example', 1, inputs={'go': True}, intent='one', binding='caller')['run_id'], started['run_id'])

    def test_missing_and_typed_unknown_conditions_never_take_false_branch(self):
        from codex_wake.controller_flows import ControllerFlows
        for inputs in ({}, {'go': {'type': 'boolean', 'status': 'unknown', 'value': None}}):
            with self.subTest(inputs=inputs), tempfile.TemporaryDirectory() as directory:
                owner = ControllerFlows(Path(directory), host='host', environment='test',
                    invoke=lambda *args, **kwargs: self.fail('unknown condition dispatched a branch'),
                    authorize=lambda: actor(), now=lambda: 100)
                source = definition()
                source['nodes'][0]['condition']['left'] = {'ref': 'inputs.go.value'} if inputs else {'ref': 'inputs.go'}
                owner.publish(actor(), source)
                started = owner.start(actor(), 'example', 1, inputs=inputs, intent='one', binding='caller')
                result = owner.advance(actor(), started['run_id'])
                self.assertEqual(result['phase'], 'held')
                self.assertEqual(result['reason'], 'condition_unknown')

    def test_wait_timeout_preserves_cursor_and_restart_returns_child_answer(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            ready = [False]
            calls = []
            def invoke(operation, arguments, **kwargs):
                kwargs['authorize']()
                calls.append(operation)
                if operation == 'operations.send':
                    return {'status': 'completed', 'result': {'operation': {'operation_id': 'child-one', 'phase': 'waiting'}}}
                self.assertEqual((operation, arguments['operation_id']), ('operations.wait', 'child-one'))
                if not ready[0]:
                    return {'status': 'completed', 'result': {'wait': {'status': 'timeout', 'ends_work': False},
                        'operation': {'operation_id': 'child-one', 'phase': 'waiting'}}}
                return {'status': 'completed', 'result': {'wait': {'status': 'answered'},
                    'operation': {'operation_id': 'child-one', 'phase': 'terminal', 'answer': {'text': 'final'}}}}
            source = {'id': 'example', 'version': 1, 'entry': 'submit', 'nodes': [
                {'id': 'submit', 'type': 'call', 'operation': 'operations.send', 'arguments': {}, 'next': 'await'},
                {'id': 'await', 'type': 'wait', 'operation_id': {'ref': 'steps.submit.result.operation.operation_id'}, 'timeout': 0, 'next': 'end'},
                {'id': 'end', 'type': 'end', 'value': {'ref': 'steps.await.result.operation.answer.text'}}]}
            owner = ControllerFlows(Path(directory), host='host', environment='test', invoke=invoke, authorize=lambda: actor(), now=lambda: 100)
            owner.publish(actor(), source)
            started = owner.start(actor(), 'example', 1, inputs={}, intent='one', binding='caller')
            pending = owner.advance(actor(), started['run_id'])
            self.assertEqual((pending['phase'], pending['cursor']), ('waiting', 'await'))
            ready[0] = True
            restarted = ControllerFlows(Path(directory), host='host', environment='test', invoke=invoke, authorize=lambda: actor(), now=lambda: 100)
            done = restarted.advance(actor(), started['run_id'])
            self.assertEqual((done['phase'], done['result']), ('completed', 'final'))
            self.assertEqual(calls.count('operations.send'), 1)

    def test_interrupted_step_reconciles_existing_result_without_redispatch(self):
        from codex_wake.controller_flows import ControllerFlows
        from codex_wake.controller_runtime import ControllerRuntime
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = ControllerRuntime(root, now=lambda: 100)
            effects = []
            def invoke(operation, arguments, **kwargs):
                if operation == 'operations.result':
                    return runtime.operation(actor(), operation, arguments, authorize=kwargs['authorize'])
                result = runtime.execute(actor(), operation, dict(arguments, _request=kwargs['request']),
                    authorize=kwargs['authorize'], dispatch=lambda op, args: effects.append(op) or {'value': 'retained'})
                raise SystemExit('caller lost after owner retained result')
            source = {'id': 'example', 'version': 1, 'entry': 'call', 'nodes': [
                {'id': 'call', 'type': 'call', 'operation': 'fixture.effect', 'arguments': {}, 'next': 'end'},
                {'id': 'end', 'type': 'end', 'value': {'ref': 'steps.call.result.operation.result.value'}}]}
            owner = ControllerFlows(root, host='host', environment='test', invoke=invoke, authorize=lambda: actor(), now=lambda: 100)
            owner.publish(actor(), source)
            started = owner.start(actor(), 'example', 1, inputs={}, intent='one', binding='caller')
            with self.assertRaises(SystemExit):
                owner.advance(actor(), started['run_id'])
            restarted = ControllerFlows(root, host='host', environment='test', invoke=invoke, authorize=lambda: actor(), now=lambda: 100)
            self.assertEqual(restarted.advance(actor(), started['run_id'])['phase'], 'executing')
            resumed = restarted.reconcile(actor(), started['run_id'])
            self.assertEqual(resumed['phase'], 'ready')
            done = restarted.advance(actor(), started['run_id'])
            self.assertEqual(done['result'], 'retained')
            self.assertEqual(effects, ['fixture.effect'])

    def test_cancel_preserves_completed_outputs_and_stops_new_steps(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            effects = []
            owner = ControllerFlows(Path(directory), host='host', environment='test',
                invoke=lambda operation, arguments, **kw: effects.append(operation) or {},
                authorize=lambda: actor(), now=lambda: 100)
            owner.publish(actor(), definition())
            run = owner.start(actor(), 'example', 1, inputs={'go': True}, intent='one', binding='caller')
            cancelled = owner.cancel(actor(), run['run_id'])
            self.assertEqual(cancelled['phase'], 'cancelled')
            self.assertEqual(owner.advance(actor(), run['run_id'])['phase'], 'cancelled')
            self.assertEqual(effects, [])

    def test_waiting_cancel_requests_only_the_owned_child(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            cancelled = []
            def invoke(operation, arguments, **kw):
                if operation == 'operations.wait':
                    return {'result': {'wait': {'status': 'timeout'}}}
                cancelled.append(arguments['operation_id'])
                return {'result': {'operation': {'cancellation': 'confirmed'}}}
            owner = ControllerFlows(Path(directory), host='host', environment='test',
                invoke=invoke, authorize=lambda: actor(), now=lambda: 100)
            source = {'id': 'example', 'version': 1, 'entry': 'wait', 'nodes': [
                {'id': 'wait', 'type': 'wait', 'operation_id': {'ref': 'inputs.child'}, 'timeout': 0}]}
            owner.publish(actor(), source)
            run = owner.start(actor(), 'example', 1, inputs={'child': 'owned-child'}, intent='one', binding='caller')
            self.assertEqual(owner.advance(actor(), run['run_id'])['phase'], 'waiting')
            self.assertEqual(owner.cancel(actor(), run['run_id'])['phase'], 'cancelled')
            self.assertEqual(cancelled, ['owned-child'])

    def test_foreign_principal_and_revoked_grant_cannot_resume_or_read(self):
        from dataclasses import replace
        from codex_wake.controller_auth import AuthError
        from codex_wake.controller_flows import ControllerFlows
        from codex_wake.controller_runtime import ControllerRuntime
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owner = ControllerFlows(root, host='host', environment='test', invoke=lambda *a, **kw: {},
                authorize=lambda: actor(), now=lambda: 100)
            owner.publish(actor(), definition())
            run = owner.start(actor(), 'example', 1, inputs={}, intent='one', binding='caller')
            foreign = replace(actor(), subject='other')
            with self.assertRaises(AuthError):
                owner.inspect(foreign, run['run_id'])
            runtime = ControllerRuntime(root, now=lambda: 100)
            runtime.revoke_grant('grant', issuer='local://test', resource='wake:controller')
            with self.assertRaises(AuthError):
                owner.advance(actor(), run['run_id'])

    def test_invalid_predicate_is_rejected_before_any_run_can_be_started(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            effects = []
            owner = ControllerFlows(Path(directory), host='host', environment='test',
                invoke=lambda *a, **kw: effects.append(a) or {}, authorize=lambda: actor(), now=lambda: 100)
            source = definition()
            source['nodes'][0]['condition']['op'] = 'python.eval'
            with self.assertRaises(InventoryError) as caught:
                owner.publish(actor(), source)
            self.assertEqual(caught.exception.code, 'invalid_condition')
            self.assertEqual(effects, [])

    def test_opt_in_read_retry_is_bounded_and_survives_caller_restart(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            calls=[]
            def invoke(operation,arguments,**kw):
                calls.append(operation)
                if len(calls)==1:raise InventoryError('timeout','temporary readonly source timeout')
                return {'result': {'value':'retained'}}
            source=dict(id='example',version=1,entry='read',nodes=[
                dict(id='read',type='call',operation='inventory.list',arguments={},retry=dict(max_attempts=2,when=['timeout']),next='done'),
                dict(id='done',type='end',value={'ref':'steps.read.result.value'})])
            owner=ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=lambda:actor(),now=lambda:100)
            owner.publish(actor(),source)
            run=owner.start(actor(),'example',1,inputs={},intent='one',binding='caller')
            first=owner.advance(actor(),run['run_id'])
            self.assertEqual((first['phase'],first['reason']),('ready','retry_scheduled'))
            restarted=ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=lambda:actor(),now=lambda:100)
            done=restarted.advance(actor(),run['run_id'])
            self.assertEqual(done['result'],'retained')
            self.assertEqual(done['attempt_counts']['read'],2)
            self.assertEqual(restarted.advance(actor(),run['run_id']),done)
            self.assertEqual(calls,['inventory.list','inventory.list'])

    def test_uncertain_effect_blocks_dependents_and_reconciles_without_replay(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            effects=[];lookups=[]
            def invoke(operation,arguments,**kw):
                if operation=='operations.result':
                    lookups.append(arguments['operation_id'])
                    return {'result':{'operation':{'phase':'uncertain','execution':'unknown'}}}
                effects.append(operation)
                return {'result':{'operation':{'operation_id':kw['request']['operation_id'],'phase':'uncertain','execution':'unknown'}}}
            source=dict(id='example',version=1,entry='effect',nodes=[dict(id='effect',type='call',operation='fixture.effect',arguments={},next='dependent'),
                dict(id='dependent',type='call',operation='fixture.dependent',arguments={})])
            owner=ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=lambda:actor(),now=lambda:100)
            owner.publish(actor(),source)
            run=owner.start(actor(),'example',1,inputs={},intent='one',binding='caller')
            uncertain=owner.advance(actor(),run['run_id'])
            self.assertEqual(uncertain['phase'],'uncertain')
            owner.advance(actor(),run['run_id'])
            self.assertEqual(owner.reconcile(actor(),run['run_id'])['phase'],'uncertain')
            self.assertEqual(effects,['fixture.effect'])
            self.assertEqual(len(lookups),1)

    def test_read_retry_exhaustion_stops_at_its_declared_total(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            calls=[]
            def invoke(operation,arguments,**kw):
                calls.append(operation)
                raise TimeoutError('owned readonly transport timed out')
            source=dict(id='example',version=1,entry='read',nodes=[dict(id='read',type='call',operation='inventory.list',arguments={},retry=dict(max_attempts=2,when=['timeout']))])
            owner=ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=lambda:actor(),now=lambda:100)
            owner.publish(actor(),source)
            run=owner.start(actor(),'example',1,inputs={},intent='one',binding='caller')
            owner.advance(actor(),run['run_id'])
            stopped=owner.advance(actor(),run['run_id'])
            self.assertEqual((stopped['phase'],stopped['reason']),('held','retry_exhausted'))
            owner.advance(actor(),run['run_id'])
            self.assertEqual(len(calls),2)

    def test_effectful_operations_cannot_claim_read_retry_safety(self):
        from codex_wake.controller_flows import FlowDefinition
        source=definition()
        source['nodes'][1].update(operation='operations.send',retry=dict(max_attempts=3,when=['timeout']))
        with self.assertRaises(InventoryError) as caught:
            FlowDefinition.compile(source)
        self.assertEqual(caught.exception.code,'unsafe_retry')

    def test_requested_cancellation_reconciles_owner_outcome_without_resending(self):
        from codex_wake.controller_flows import ControllerFlows
        with tempfile.TemporaryDirectory() as directory:
            cancellations=[]
            def invoke(operation,arguments,**kw):
                if operation=='operations.wait':return {'result':{'wait':{'status':'timeout'}}}
                if operation=='operations.cancel':
                    cancellations.append(arguments['operation_id'])
                    return {'result':{'operation':{'cancellation':'requested'}}}
                if operation=='operations.result':return {'result':{'operation':{'phase':'terminal','execution':'cancelled'}}}
                raise AssertionError(operation)
            owner=ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=lambda:actor(),now=lambda:100)
            owner.publish(actor(),dict(id='example',version=1,entry='wait',nodes=[dict(id='wait',type='wait',operation_id='owned',timeout=0)]))
            run=owner.start(actor(),'example',1,inputs={},intent='one',binding='caller')
            owner.advance(actor(),run['run_id'])
            self.assertEqual(owner.cancel(actor(),run['run_id'])['phase'],'uncertain')
            self.assertEqual(owner.reconcile(actor(),run['run_id'])['phase'],'cancelled')
            self.assertEqual(cancellations,['owned'])
