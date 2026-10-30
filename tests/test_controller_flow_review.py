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
