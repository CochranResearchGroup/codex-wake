import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_conditions import validate_condition, Conditions
from codex_wake.managed_inventory import InventoryError


class ConditionsTests(unittest.TestCase):
    def test_short_circuit_trace_never_calls_second_operand(self):
        validate_condition({'op':'and','operands':[False,{'function':'danger','version':1,'arguments':{}}]})
        with tempfile.TemporaryDirectory() as directory:
            engine=Conditions(Path(directory),registry={'danger@1':dict(kind='deterministic',inputs={},expression=True)})
            state=dict(created_at=0,condition_usage=dict(calls=0,tokens=0),condition_trace=[])
            result=engine.evaluate({'op':'and','operands':[False,{'function':'danger','version':1,'arguments':{}}]},state,
                resolve=lambda value:value,compare=lambda expression:False,save=lambda:None,now=lambda:0)
            self.assertEqual(result['value'],False)
            self.assertEqual(result['trace'][1]['status'],'unevaluated')
            self.assertEqual(state['condition_usage']['calls'],0)

    def test_typed_nested_function_bound_and_cumulative_restart(self):
        import json
        from codex_wake.controller_flows import ControllerFlows
        from codex_wake.controller_auth import Actor
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            registry=root/'controller-conditions.json'
            registry.write_text(json.dumps(dict(version=1,functions={
                'positive@1':dict(kind='deterministic',inputs={'n':'integer'},expression=dict(op='gt',left={'ref':'arguments.n'},right=0)),
                'nested@1':dict(kind='deterministic',inputs={'n':'integer'},expression=dict(function='positive',version=1,arguments={'n':{'ref':'arguments.n'}}))})))
            registry.chmod(0o600)
            actor=Actor('author','service','client','grant','local://test','wake:controller',frozenset({'observe','control'}),[dict(host='host',environment='test',flow_id='fixture')],10000)
            def owner():return ControllerFlows(root,host='host',environment='test',invoke=lambda *a,**kw:self.fail('pure predicate invoked external effect'),authorize=lambda:actor,now=lambda:100)
            definition=dict(id='fixture',version=1,entry='choose',limits=dict(max_calls=3,max_depth=3,max_tokens=0),nodes=[
                dict(id='choose',type='branch',condition=dict(function='nested',version=1,arguments={'n':2}),then='yes',**{'else':'no'}),
                dict(id='yes',type='end',value=True),dict(id='no',type='end',value=False)])
            initial=owner();initial.publish(actor,definition)
            started=initial.start(actor,'fixture',1,inputs={},intent='one',binding='caller')
            done=owner().advance(actor,started['run_id'])
            self.assertEqual(done['result'],True)
            self.assertEqual(done['condition_usage'],dict(calls=2,tokens=0))
            self.assertEqual(owner().advance(actor,started['run_id']),done)
            self.assertEqual(len(done['condition_trace']),2)

    def test_explicit_parallel_unknown_and_false_are_distinct(self):
        with self.assertRaises(InventoryError):validate_condition(dict(op='and',operands=[True],parallel=True))
        with tempfile.TemporaryDirectory() as directory:
            engine=Conditions(Path(directory),registry={})
            state=dict(created_at=0,condition_usage=dict(calls=0,tokens=0))
            outcome=engine.evaluate(dict(op='or',operands=[False,dict(op='eq',left=0,right=1),True]),state,
                resolve=lambda value:value,compare=lambda expression:None,save=lambda:None,now=lambda:0)
            self.assertEqual(outcome['status'],'unknown')
            self.assertIsNone(outcome['value'])
            self.assertEqual(outcome['trace'][-1]['status'],'unevaluated')

    def test_exact_native_budget_and_observation_policy_refuse_before_effect(self):
        from codex_wake.controller_condition_native import invoke
        with tempfile.TemporaryDirectory() as directory:
            for bounds,function,code in ((dict(metering='exact'),{},'unsupported_condition_metering'),
                                        (dict(metering='estimate_opt_in'),dict(expected_target={'conversation_id':'source'}),'unsupported_observation_tool_policy')):
                with self.assertRaises(InventoryError) as caught:
                    invoke(Path(directory),None,function,{},bounds,20,{},authorize=lambda:self.fail('unqualified native dispatch'),request_id='one',binding='fixture')
                self.assertEqual(caught.exception.code,code)
