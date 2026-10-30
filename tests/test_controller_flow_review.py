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

    def test_wall_clock_rollback_holds_without_dispatch_or_budget_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            clock=[100];calls=[]
            def owner():return ControllerFlows(Path(directory),host='host',environment='test',invoke=lambda *a,**k:calls.append(a[0]) or {},authorize=actor,now=lambda:clock[0])
            source=dict(id='example',version=1,entry='call',limits=dict(max_seconds=1,metering='estimate_opt_in'),nodes=[dict(id='call',type='call',operation='inventory.list',arguments={})])
            owner().publish(actor(),source);run=owner().start(actor(),'example',1,inputs={},intent='rollback',binding='caller')
            clock[0]=99
            held=owner().advance(actor(),run['run_id'])
            self.assertEqual(held['phase'],'held')
            self.assertEqual(held['reason'],'flow_clock_uncertain')
            self.assertEqual(calls,[])
            self.assertEqual(held['created_at'],100)
            self.assertEqual(held['condition_usage'],dict(calls=0,tokens=0))

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
