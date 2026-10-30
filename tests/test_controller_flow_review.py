"""Accepted post-review regressions through the public durable flow owner."""
import json
import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_auth import Actor
from codex_wake.controller_flows import ControllerFlows


def actor():
    return Actor('author','service','client','grant','local://test','wake:controller',frozenset({'observe','control'}),[dict(host='host',environment='test',flow_id='example')],10000)


class FlowReviewTests(unittest.TestCase):
    def test_running_version_keeps_its_original_predicate_after_future_registry_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'controller-conditions.json'
            functions={'predicate@1':dict(kind='deterministic',inputs={},expression=True)}
            path.write_text(json.dumps(dict(version=1,functions=functions)));path.chmod(0o600)
            def owner():return ControllerFlows(root,host='host',environment='test',invoke=lambda *a,**k:self.fail('deterministic condition dispatched'),authorize=actor,now=lambda:100)
            source=dict(id='example',version=1,entry='choose',nodes=[dict(id='choose',type='branch',condition=dict(function='predicate',version=1,arguments={}),then='yes',**{'else':'no'}),dict(id='yes',type='end',value=True),dict(id='no',type='end',value=False)])
            owner().publish(actor(),source);run=owner().start(actor(),'example',1,inputs={},intent='original',binding='caller')
            functions['predicate@2']=dict(kind='deterministic',inputs={},expression=False)
            path.write_text(json.dumps(dict(version=1,functions=functions)))
            done=owner().advance(actor(),run['run_id'])
            self.assertIs(done['result'],True)
            self.assertEqual(done['condition_usage']['calls'],1)
            path.unlink()
            self.assertEqual(owner().advance(actor(),run['run_id']),done)

    def test_wall_rollback_never_extends_original_qualified_elapsed_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            wall=[100];sample={'boot_id':'fixture-clock-only','seconds':10};calls=[]
            def owner():return ControllerFlows(Path(directory),host='host',environment='test',invoke=lambda *a,**k:calls.append(a[0]) or {},authorize=actor,now=lambda:wall[0],clock=lambda:dict(sample))
            source=dict(id='example',version=1,entry='call',limits=dict(max_seconds=1,metering='estimate_opt_in'),nodes=[dict(id='call',type='call',operation='inventory.list',arguments={})])
            owner().publish(actor(),source);run=owner().start(actor(),'example',1,inputs={},intent='rollback',binding='caller')
            wall[0]=99;sample['seconds']=12
            stopped=owner().advance(actor(),run['run_id'])
            self.assertEqual(stopped['phase'],'cancelled')
            self.assertEqual(stopped['limit_stop']['reason'],'flow_nested_limit')
            self.assertEqual(calls,[])
            self.assertEqual(stopped['created_at'],100)
            self.assertGreaterEqual(stopped['elapsed_clock']['elapsed'],2)
            self.assertEqual(stopped['elapsed_clock']['wall_latest'],100)
            self.assertEqual(stopped['elapsed_clock']['wall_observation'],'regressed')
            self.assertEqual(stopped['condition_usage'],dict(calls=0,tokens=0))

    def test_qualified_elapsed_counter_continues_under_budget_with_visible_wall_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            wall=[100];sample={'boot_id':'fixture-clock-only','seconds':10};calls=[]
            def owner():return ControllerFlows(Path(directory),host='host',environment='test',invoke=lambda *a,**k:calls.append(a[0]) or {},authorize=actor,now=lambda:wall[0],clock=lambda:dict(sample))
            source=dict(id='example',version=1,entry='call',limits=dict(max_seconds=1,metering='estimate_opt_in'),nodes=[dict(id='call',type='call',operation='inventory.list',arguments={})])
            owner().publish(actor(),source);run=owner().start(actor(),'example',1,inputs={},intent='rollback-under-budget',binding='caller')
            wall[0]=99;sample['seconds']=10.25
            done=owner().advance(actor(),run['run_id'])
            self.assertEqual(done['phase'],'completed')
            self.assertEqual(calls,['inventory.list'])
            self.assertEqual(done['elapsed_clock']['elapsed'],.25)
            self.assertEqual(done['elapsed_clock']['wall_latest'],100)
            self.assertEqual(done['elapsed_clock']['wall_observation'],'regressed')
            self.assertGreater(done['elapsed_clock']['wall_regression_observations'],0)

    def test_elapsed_budget_survives_handoff_and_boot_or_counter_loss_holds(self):
        for mode in ('elapsed','boot','counter'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                sample={'boot_id':'fixture-clock-only','seconds':10};calls=[]
                def owner():return ControllerFlows(Path(directory),host='host',environment='test',invoke=lambda *a,**k:calls.append(a[0]) or {},authorize=actor,now=lambda:100,clock=lambda:dict(sample))
                source=dict(id='example',version=1,entry='call',limits=dict(max_seconds=1,metering='estimate_opt_in'),nodes=[dict(id='call',type='call',operation='inventory.list',arguments={})])
                owner().publish(actor(),source);run=owner().start(actor(),'example',1,inputs={},intent=mode,binding='caller')
                if mode=='elapsed':sample['seconds']=12
                elif mode=='boot':sample['boot_id']='different-fixture-boot'
                else:sample['seconds']=9
                held=owner().advance(actor(),run['run_id'])
                self.assertEqual(calls,[])
                self.assertEqual(held['created_at'],100)
                if mode=='elapsed':self.assertEqual(held['limit_stop']['cancellation'],'confirmed')
                else:self.assertEqual((held['phase'],held['reason']),('held','flow_clock_uncertain'))

    def test_foreach_iteration_estimates_and_frames_survive_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            effects=[]
            def invoke(operation,args,**kwargs):
                kwargs['authorize']()
                if operation=='sessions.capabilities':return dict(result=dict(modes=['sequential']))
                effects.append(operation)
                if operation=='sessions.prompt':return dict(result=dict(operation=dict(operation_id=kwargs['request']['operation_id'],phase='waiting',execution='queued')))
                if operation=='sessions.wait':return dict(result=dict(wait=dict(status='completed'),operation=dict(phase='terminal',execution='completed',answer={'text':'fixture result'})))
                self.fail(operation)
            def owner():return ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=actor,now=lambda:100)
            source=dict(id='example',version=1,entry='each',limits=dict(max_calls=10,max_tokens=8,max_seconds=10,metering='estimate_opt_in'),nodes=[
                dict(id='each',type='foreach',items=['one','two'],mode='sequential',profile='fixture',expected_target={'conversation_id':'existing'},prompt={'ref':'item'},limits=dict(max_calls=4,max_tokens=4,max_seconds=5),next='end'),
                dict(id='end',type='end',value={'ref':'steps.each'})])
            owner().publish(actor(),source);run=owner().start(actor(),'example',1,inputs={},intent='iterations',binding='caller')
            done=owner().advance(actor(),run['run_id'])
            self.assertEqual(done['phase'],'completed')
            self.assertEqual(done['condition_usage'],dict(calls=4,tokens=8))
            self.assertEqual([item['usage'] for item in done['iteration_frames'].values()],[dict(calls=2,tokens=4),dict(calls=2,tokens=4)])
            self.assertTrue(all(item['phase']=='completed' for item in done['iteration_frames'].values()))
            self.assertEqual(owner().advance(actor(),run['run_id']),done)
            self.assertEqual(effects,['sessions.prompt','sessions.wait','sessions.prompt','sessions.wait'])

    def test_expired_iteration_cancels_only_original_item_and_reconciles_without_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            wall=[100];prompts=[];cancellations=[];late=[False];created=[0]
            def invoke(operation,args,**kwargs):
                kwargs['authorize']()
                if operation=='sessions.capabilities':return dict(result=dict(modes=['new_session']))
                if operation=='sessions.create':
                    created[0]+=1
                    return dict(result=dict(operation=dict(phase='terminal',execution='completed',result=dict(target={'conversation_id':'child-'+str(created[0])}))))
                if operation=='sessions.prompt':
                    prompts.append(kwargs['request']['operation_id'])
                    if len(prompts)==1:wall[0]=101
                    return dict(result=dict(operation=dict(operation_id=kwargs['request']['operation_id'],phase='waiting',execution='queued')))
                if operation=='sessions.cancel':
                    cancellations.append(args['operation_id'])
                    return dict(result=dict(operation=dict(phase='waiting',execution='running',cancellation='requested')))
                if operation=='sessions.wait':
                    if args['operation_id']==prompts[0]:
                        return dict(result=dict(wait=dict(status='answered' if late[0] else 'timeout'),operation=dict(phase='terminal' if late[0] else 'waiting',execution='cancelled' if late[0] else 'running')))
                    return dict(result=dict(wait=dict(status='answered'),operation=dict(phase='terminal',execution='completed',answer={'text':'peer preserved'})))
                self.fail(operation)
            def owner():return ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=actor,now=lambda:wall[0],clock=lambda:dict(boot_id='fixture-scope-only',seconds=wall[0]))
            source=dict(id='example',version=1,entry='each',limits=dict(max_calls=20,max_tokens=8,max_seconds=20,metering='estimate_opt_in'),nodes=[
                dict(id='each',type='foreach',items=['one','two'],mode='new_session',parallelism=2,profile='fixture',expected_target={},prompt={'ref':'item'},limits=dict(max_seconds=2,max_tokens=3),next='end'),dict(id='end',type='end',value={'ref':'steps.each'})])
            owner().publish(actor(),source);run=owner().start(actor(),'example',1,inputs={},intent='scope',binding='caller')
            waiting=owner().advance(actor(),run['run_id']);self.assertEqual(waiting['phase'],'waiting')
            wall[0]=102
            stopped=owner().advance(actor(),run['run_id'])
            self.assertEqual(stopped['phase'],'uncertain')
            self.assertEqual(cancellations,[prompts[0]])
            self.assertEqual(stopped['iteration_frames']['each.0']['phase'],'cancelling')
            self.assertEqual(stopped['iteration_frames']['each.1']['phase'],'active')
            wall[0]=102.5;late[0]=True
            restored=owner().reconcile(actor(),run['run_id']);self.assertEqual(restored['phase'],'ready')
            done=owner().advance(actor(),run['run_id'])
            self.assertEqual(done['phase'],'failed')
            self.assertEqual([item['result']['execution'] for item in done['result']['items']],['failed','completed'])
            self.assertEqual(done['result']['items'][1]['result']['answer']['text'],'peer preserved')
            self.assertEqual(done['condition_usage'],dict(calls=6,tokens=6))
            self.assertEqual(cancellations,[prompts[0]])
            self.assertEqual(len(prompts),2)

    def test_zero_iteration_token_bound_stops_before_creating_a_child(self):
        with tempfile.TemporaryDirectory() as directory:
            effects=[]
            def invoke(operation,args,**kwargs):
                kwargs['authorize']()
                if operation=='sessions.capabilities':return dict(result=dict(modes=['new_session']))
                effects.append(operation)
                if operation=='sessions.create':return dict(result=dict(operation=dict(phase='terminal',execution='completed',result=dict(target={'conversation_id':'should-not-create'}))))
                self.fail(operation)
            owner=ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=actor,now=lambda:100)
            source=dict(id='example',version=1,entry='each',limits=dict(max_tokens=6,metering='estimate_opt_in'),nodes=[dict(id='each',type='foreach',items=['one'],mode='new_session',profile='fixture',expected_target={},prompt='fixture',limits=dict(max_tokens=0))])
            owner.publish(actor(),source);run=owner.start(actor(),'example',1,inputs={},intent='zero',binding='caller')
            done=owner.advance(actor(),run['run_id'])
            self.assertEqual(effects,[])
            self.assertEqual(done['phase'],'failed')
            self.assertIsNone(done['result']['items'][0]['target'])
            self.assertEqual(done['condition_usage'],dict(calls=0,tokens=0))

    def test_wait_retries_charge_the_original_iteration_across_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            prompts=[];cancels=[]
            def invoke(operation,args,**kwargs):
                kwargs['authorize']()
                if operation=='sessions.capabilities':return dict(result=dict(modes=['sequential']))
                if operation=='sessions.prompt':
                    prompts.append(kwargs['request']['operation_id'])
                    return dict(result=dict(operation=dict(operation_id=prompts[-1],phase='waiting',execution='queued')))
                if operation=='sessions.cancel':
                    cancels.append(args['operation_id'])
                    return dict(result=dict(operation=dict(phase='terminal',execution='cancelled',cancellation='confirmed')))
                if operation=='sessions.wait':
                    pending=args['operation_id']==prompts[0]
                    return dict(result=dict(wait=dict(status='timeout' if pending else 'completed'),operation=dict(operation_id=args['operation_id'],phase='waiting' if pending else 'terminal',execution='queued' if pending else 'completed')))
                self.fail(operation)
            def owner():return ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=actor,now=lambda:100)
            source=dict(id='example',version=1,entry='each',limits=dict(max_calls=10,max_tokens=10,metering='estimate_opt_in'),nodes=[
                dict(id='each',type='foreach',items=['one','two'],mode='sequential',profile='fixture',expected_target={'conversation_id':'existing'},prompt={'ref':'item'},join='all_complete',limits=dict(max_calls=2,max_tokens=3),next='end'),dict(id='end',type='end',value={'ref':'steps.each'})])
            owner().publish(actor(),source);run=owner().start(actor(),'example',1,inputs={},intent='retry',binding='caller')
            waiting=owner().advance(actor(),run['run_id']);self.assertEqual(waiting['phase'],'waiting')
            done=owner().advance(actor(),run['run_id'])
            self.assertEqual(done['phase'],'completed')
            self.assertEqual(done['result']['status'],'failed')
            self.assertEqual(done['iteration_frames']['each.0']['reason'],'iteration_call_limit')
            self.assertEqual([frame['usage'] for frame in done['iteration_frames'].values()],[dict(calls=2,tokens=3),dict(calls=2,tokens=3)])
            self.assertEqual(done['condition_usage'],dict(calls=4,tokens=6))
            self.assertEqual(cancels,[prompts[0]]);self.assertEqual(len(prompts),2)

    def test_iteration_limits_tighten_parent_and_parent_reservations_never_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            prompts=[]
            def invoke(operation,args,**kwargs):
                kwargs['authorize']()
                if operation=='sessions.capabilities':return dict(result=dict(modes=['sequential']))
                if operation=='sessions.prompt':
                    prompts.append(kwargs['request']['operation_id'])
                    return dict(result=dict(operation=dict(operation_id=prompts[-1],phase='waiting',execution='queued')))
                if operation=='sessions.wait':return dict(result=dict(wait=dict(status='completed'),operation=dict(operation_id=args['operation_id'],phase='terminal',execution='completed')))
                self.fail(operation)
            def owner():return ControllerFlows(Path(directory),host='host',environment='test',invoke=invoke,authorize=actor,now=lambda:100)
            source=dict(id='example',version=1,entry='each',limits=dict(max_calls=10,max_tokens=6,max_seconds=5,metering='estimate_opt_in'),nodes=[
                dict(id='each',type='foreach',items=['one','two'],mode='sequential',profile='fixture',expected_target={'conversation_id':'existing'},prompt={'ref':'item'},limits=dict(max_calls=20,max_tokens=10,max_seconds=20))])
            owner().publish(actor(),source);run=owner().start(actor(),'example',1,inputs={},intent='parent',binding='caller')
            done=owner().advance(actor(),run['run_id'])
            self.assertEqual(done['limit_stop']['reason'],'flow_token_limit')
            self.assertEqual(done['condition_usage'],dict(calls=2,tokens=6))
            frame=done['iteration_frames']['each.0']
            self.assertEqual((frame['limits']['max_calls'],frame['limits']['max_tokens'],frame['limits']['max_seconds']),(10,6,5))
            self.assertEqual(frame['phase'],'completed');self.assertEqual(len(prompts),1)
            self.assertEqual(owner().advance(actor(),run['run_id']),done)

    def test_nested_predicate_reservation_tightens_remaining_foreach_parent_budget(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'controller-conditions.json'
            path.write_text(json.dumps(dict(version=1,functions={'predicate@1':dict(kind='semantic',inputs={},effects='action',estimated_tokens=4)})));path.chmod(0o600)
            def invoke(operation,args,**kwargs):
                kwargs['authorize']()
                if operation=='sessions.capabilities':return dict(result=dict(modes=['new_session']))
                self.fail('parent token reservation admitted another native effect')
            owner=ControllerFlows(root,host='host',environment='test',invoke=invoke,authorize=actor,now=lambda:100)
            source=dict(id='example',version=1,entry='choose',limits=dict(max_calls=10,max_tokens=6,metering='estimate_opt_in'),nodes=[
                dict(id='choose',type='branch',condition=dict(function='predicate',version=1,arguments={}),then='each',**{'else':'end'}),
                dict(id='each',type='foreach',items=['one'],mode='new_session',profile='fixture',expected_target={},prompt='fixture',limits=dict(max_tokens=4),next='end'),dict(id='end',type='end')])
            owner.publish(actor(),source);run=owner.start(actor(),'example',1,inputs={},intent='nested',binding='caller')
            def semantic(root,actor,function,args,bounds,tokens,receipt,**kwargs):
                receipt['native_execution']='completed'
                return dict(status='known',value=True,usage={'tokens':4})
            with patch('codex_wake.controller_condition_native.invoke',side_effect=semantic):done=owner.advance(actor(),run['run_id'])
            self.assertEqual(done['limit_stop']['reason'],'flow_token_limit')
            self.assertEqual(done['condition_usage'],dict(calls=1,tokens=4))
            self.assertEqual(done['iteration_frames']['each.0']['usage'],dict(calls=0,tokens=0))
