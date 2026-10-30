import tempfile
import unittest
from pathlib import Path

from codex_wake.controller_auth import Actor
from codex_wake.controller_flows import ControllerFlows
from codex_wake.managed_inventory import InventoryError


class FlowCapabilityLimitTests(unittest.TestCase):
    def test_foreach_rejects_parallelism_beyond_negotiated_runtime_before_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            actor=Actor('owner','service','client','grant','issuer','resource',frozenset({'observe','control'}),
                [dict(host='host',environment='test',flow_id='fixture')],1000)
            calls=[]
            def invoke(operation,args,**kwargs):
                calls.append(operation)
                self.assertEqual(operation,'sessions.capabilities')
                return dict(result=dict(modes=['new_session','sequential'],max_parallelism=1))
            owner=ControllerFlows(Path(directory),host='host',environment='test',authorize=lambda:actor,invoke=invoke,now=lambda:100)
            owner.publish(actor,dict(id='fixture',version=1,entry='items',nodes=[
                dict(id='items',type='foreach',mode='new_session',parallelism=2,profile='grok',
                    expected_target=dict(host='host',environment='test',runtime='grok'),items=['one','two'],prompt={'ref':'item'},next='end'),
                dict(id='end',type='end',value='finished')]))
            with self.assertRaises(InventoryError) as caught:
                owner.start(actor,'fixture',1,inputs={},intent='one',binding='caller')
            self.assertEqual(caught.exception.code,'unsupported_parallelism')
            self.assertEqual(calls,['sessions.capabilities'])
