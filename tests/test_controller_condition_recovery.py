"""Recovery at the durable public flow boundary, with no provider turns."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_wake.controller_auth import Actor
from codex_wake.controller_flows import ControllerFlows


class ConditionRecoveryTests(unittest.TestCase):
    def test_nested_semantic_turn_recovers_original_handle_without_replaying_or_charging(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            registry=root/'controller-conditions.json'
            functions={
                'parent@1':dict(kind='semantic',inputs={},effects='action',estimated_tokens=4,callees=['child@1']),
                'child@1':dict(kind='semantic',inputs={},effects='action',estimated_tokens=4)}
            registry.write_text(json.dumps(dict(version=1,functions=functions)));registry.chmod(0o600)
            actor=Actor('author','service','client','grant','local://test','wake:controller',frozenset({'observe','control'}),
                        [dict(host='host',environment='test',flow_id='fixture')],10000)
            def owner():
                return ControllerFlows(root,host='host',environment='test',invoke=lambda *a,**k:self.fail('unrelated effect'),authorize=lambda:actor,now=lambda:100)
            definition=dict(id='fixture',version=1,entry='choose',limits=dict(max_calls=2,max_depth=3,max_tokens=8,metering='estimate_opt_in'),nodes=[
                dict(id='choose',type='branch',condition=dict(function='parent',version=1,arguments={}),then='yes',**{'else':'no'}),
                dict(id='yes',type='end',value=True),dict(id='no',type='end',value=False)])
            first=owner();first.publish(actor,definition)
            started=first.start(actor,'fixture',1,inputs={},intent='one',binding='caller')
            submissions=[]
            def submit(root,actor,function,args,bounds,tokens,receipt,**kwargs):
                submissions.append(kwargs['request_id'])
                self.assertEqual(owner().reconcile(actor,started['run_id'])['reason'],'condition_in_progress')
                if len(submissions)==1:
                    return dict(status='delegate',value=None,call=dict(function='child',version=1,arguments={}),usage={'tokens':4})
                raise SystemExit('process lost after native submission')
            with patch('codex_wake.controller_condition_native.invoke',side_effect=submit):
                with self.assertRaises(SystemExit):first.advance(actor,started['run_id'])
            interrupted=owner().inspect(actor,started['run_id'])
            self.assertEqual(interrupted['condition_usage'],dict(calls=2,tokens=8))
            observations=[]
            def recovered(actor,operation,args,**kwargs):
                kwargs['authorize']();observations.append((operation,args))
                return dict(result=dict(operation=dict(operation_id=submissions[-1],phase='terminal',execution='completed',answer={'text':'{"value":true}'}),wait={'status':'answered'}))
            def pending(actor,operation,args,**kwargs):
                kwargs['authorize']()
                self.assertEqual((operation,args['operation_id']),('sessions.wait',submissions[-1]))
                return dict(result=dict(operation=dict(phase='waiting',execution='queued'),wait={'status':'timeout'}))
            with patch('codex_wake.controller_condition_native.ControllerFlowSessions.execute',side_effect=pending):
                held=owner().reconcile(actor,started['run_id'])
            self.assertEqual(held['phase'],'uncertain')
            self.assertEqual(held['condition_usage'],dict(calls=2,tokens=8))
            from codex_wake.managed_inventory import InventoryError
            with patch('codex_wake.controller_condition_native.ControllerFlowSessions.execute',side_effect=InventoryError('operation_not_found','missing')):
                self.assertEqual(owner().reconcile(actor,started['run_id'])['phase'],'uncertain')
            with patch('codex_wake.controller_condition_native.ControllerFlowSessions.execute',side_effect=recovered):
                reconciled=owner().reconcile(actor,started['run_id'])
            self.assertEqual(reconciled['phase'],'ready')
            done=owner().advance(actor,started['run_id'])
            self.assertIs(done['result'],True)
            self.assertEqual(done['condition_usage'],dict(calls=2,tokens=8))
            self.assertEqual(len(done['condition_trace']),2)
            self.assertEqual([(op,args['operation_id']) for op,args in observations],[('sessions.wait',submissions[-1])])
            self.assertEqual(len(submissions),2)
            self.assertEqual(owner().reconcile(actor,started['run_id']),done)

    def test_recovery_after_original_deadline_requests_owned_cancellation_without_renewal(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);clock=[100]
            registry=root/'controller-conditions.json'
            registry.write_text(json.dumps(dict(version=1,functions={'one@1':dict(kind='semantic',inputs={},effects='action',estimated_tokens=4)})));registry.chmod(0o600)
            actor=Actor('author','service','client','grant','local://test','wake:controller',frozenset({'observe','control'}),
                        [dict(host='host',environment='test',flow_id='fixture')],10000)
            cancellations=[]
            def invoke(operation,args,**kwargs):
                kwargs['authorize']();self.assertEqual(operation,'sessions.cancel');cancellations.append(args['operation_id'])
                return dict(result=dict(operation=dict(phase='terminal',execution='cancelled',cancellation='confirmed')))
            def owner():return ControllerFlows(root,host='host',environment='test',invoke=invoke,authorize=lambda:actor,now=lambda:clock[0])
            definition=dict(id='fixture',version=1,entry='choose',limits=dict(max_seconds=1,max_tokens=4,metering='estimate_opt_in'),nodes=[
                dict(id='choose',type='branch',condition=dict(function='one',version=1,arguments={}),then='yes',**{'else':'no'}),
                dict(id='yes',type='end',value=True),dict(id='no',type='end',value=False)])
            first=owner();first.publish(actor,definition);run=first.start(actor,'fixture',1,inputs={},intent='deadline',binding='caller')
            with patch('codex_wake.controller_condition_native.invoke',side_effect=SystemExit):
                with self.assertRaises(SystemExit):first.advance(actor,run['run_id'])
            original=owner().inspect(actor,run['run_id']);identifier=original['condition_trace'][0]['native_operation_id']
            clock[0]=102
            with patch('codex_wake.controller_condition_native.ControllerFlowSessions.execute',return_value=dict(result=dict(operation=dict(phase='waiting',execution='queued')))):
                stopped=owner().reconcile(actor,run['run_id'])
            self.assertEqual(stopped['limit_stop']['cancellation'],'confirmed')
            self.assertEqual(cancellations,[identifier])
            self.assertEqual(stopped['condition_usage'],dict(calls=1,tokens=4))
            self.assertEqual(stopped['created_at'],100)
            self.assertEqual(owner().advance(actor,run['run_id']),stopped)

    def test_interrupted_legacy_receipts_without_path_identity_remain_explicitly_uncertain(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path=root/'controller-conditions.json'
            path.write_text(json.dumps(dict(version=1,functions={'one@1':dict(kind='semantic',inputs={},effects='action')})));path.chmod(0o600)
            actor=Actor('author','service','client','grant','local://test','wake:controller',frozenset({'observe','control'}),
                        [dict(host='host',environment='test',flow_id='fixture')],10000)
            def owner():return ControllerFlows(root,host='host',environment='test',invoke=lambda *a,**k:self.fail('legacy effect replayed'),authorize=lambda:actor,now=lambda:100)
            definition=dict(id='fixture',version=1,entry='choose',nodes=[
                dict(id='choose',type='branch',condition=dict(function='one',version=1,arguments={}),then='yes',**{'else':'no'}),
                dict(id='yes',type='end',value=True),dict(id='no',type='end',value=False)])
            first=owner();first.publish(actor,definition);run=first.start(actor,'fixture',1,inputs={},intent='legacy',binding='caller')
            def legacy_evaluate(expression,state,**kwargs):
                # Serialized v0 receipt had no evaluation/path/frame identity.
                state['condition_trace']=[dict(function='one@1',depth=1,effects='action',status='known',value=True)]
                state['condition_usage']=dict(calls=1,tokens=8);kwargs['save']()
                raise SystemExit('legacy evaluator exited before branch commit')
            with patch('codex_wake.controller_conditions.Conditions.evaluate',side_effect=legacy_evaluate):
                with self.assertRaises(SystemExit):first.advance(actor,run['run_id'])
            with patch('codex_wake.controller_condition_native.invoke',side_effect=AssertionError('legacy effect replayed')):
                held=owner().reconcile(actor,run['run_id'])
            self.assertEqual(held['phase'],'uncertain')
            self.assertEqual(held['reason'],'legacy_condition_interrupted_no_replay')
            self.assertEqual(held['condition_usage'],dict(calls=1,tokens=8))
            self.assertEqual(owner().inspect(actor,run['run_id']),held)
