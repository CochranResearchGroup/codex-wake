import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_auth import Actor
from codex_wake.controller_flows import ControllerFlows


class ConditionLimitStopTests(unittest.TestCase):
    def test_call_or_time_limit_requests_only_owned_pending_child_cancellation(self):
        for mode in ('calls','time'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                clock=[100]
                actor=Actor('author','service','client','grant','local://fixture','wake:controller',frozenset({'observe','control'}),[dict(host='host',environment='fixture',flow_id='fixture')],10000)
                effects=[]
                pending=[]
                def invoke(operation,arguments,**kwargs):
                    kwargs['authorize']()
                    effects.append((operation,arguments))
                    if operation=='sessions.prompt':
                        identifier=kwargs['request']['operation_id'];pending.append(identifier)
                        if mode=='time':clock[0]=102
                        return dict(status='completed',result=dict(operation=dict(operation_id=identifier,phase='waiting',execution='running')))
                    if operation=='sessions.cancel':
                        self.assertIn(arguments['operation_id'],pending)
                        return dict(status='completed',result=dict(operation=dict(operation_id=arguments['operation_id'],phase='terminal',execution='cancelled',cancellation='confirmed')))
                    self.fail('limit allowed another work submission')
                owner=ControllerFlows(Path(directory),host='host',environment='fixture',invoke=invoke,authorize=lambda:actor,now=lambda:clock[0])
                source=dict(id='fixture',version=1,entry='first',limits=dict(max_calls=1) if mode=='calls' else dict(max_seconds=1,metering='estimate_opt_in'),nodes=[
                    dict(id='first',type='call',operation='sessions.prompt',arguments={},next='second'),
                    dict(id='second',type='call',operation='sessions.prompt',arguments={})])
                owner.publish(actor,source)
                run=owner.start(actor,'fixture',1,inputs={},intent=mode,binding='original')
                stopped=owner.advance(actor,run['run_id'])
                self.assertEqual([item[0] for item in effects],['sessions.prompt','sessions.cancel'])
                self.assertEqual(stopped['limit_stop']['cancellation'],'confirmed')
                self.assertEqual(stopped['condition_usage']['calls'],1)
                self.assertEqual(owner.advance(actor,run['run_id']),stopped)
