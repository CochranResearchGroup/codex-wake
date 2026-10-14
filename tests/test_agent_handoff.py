"""Fresh-context continuation guards through the public CLI."""
from contextlib import redirect_stdout
from io import StringIO
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from websockets.sync.server import unix_serve

from codex_wake.cli import run
from codex_wake.records import WakeError


class AgentHandoffTests(unittest.TestCase):
    def test_unknown_source_usage_holds_without_goal_mutation_or_successor(self):
        self.scenario()

    def test_cumulative_exhaustion_holds_even_when_source_goal_has_budget_left(self):
        self.scenario(tokens=50,carry=950,reason='cumulative_token_budget_exhausted')

    def test_original_deadline_holds_even_when_native_elapsed_counter_is_small(self):
        self.scenario(tokens=50,clock_upper=1893456120,reason='continuation_time_exhausted')

    def test_checkpoint_claim_without_outgoing_native_writer_evidence_holds(self):
        self.scenario(tokens=50,reason='checkpoint_writer_unverified')

    def test_malformed_host_allowance_is_rejected_before_native_or_journal_effects(self):
        self.scenario(tokens=50,bad_cap='1000')

    def test_native_goal_objective_change_holds_before_successor(self):
        self.scenario(tokens=50,goal_objective='Different fixture',reason='source_goal_authority_changed')

    def test_source_counter_reset_after_checkpoint_hold_never_restores_allowance(self):
        self.scenario(tokens=50,reason='checkpoint_writer_unverified',reset_on_repeat=True)

    def test_smaller_native_goal_budget_cannot_be_replenished_from_host_ceiling(self):
        self.scenario(tokens=50,budget=60,reason='checkpoint_writer_unverified',remaining=10)

    def test_explicit_host_cumulative_cap_bounds_an_unlimited_or_larger_native_budget(self):
        for budget in (None,2000):
            with self.subTest(budget=budget):
                self.scenario(tokens=50,budget=budget,reason='checkpoint_writer_unverified',remaining=950)

    def test_carried_native_elapsed_usage_cannot_be_ignored_by_wall_clock_window(self):
        self.scenario(tokens=50,seconds_carry=95,reason='cumulative_time_budget_exhausted')

    def test_incomplete_checkpoint_is_rejected_before_native_effects(self):
        self.scenario(tokens=50,incomplete=True)

    def test_checkpoint_cannot_change_caps_expiry_or_custody(self):
        for field in ('resources','expires_at','worktree','claim_holders'):
            with self.subTest(field=field):self.scenario(tokens=50,bad_checkpoint=field)

    def scenario(self, tokens=None, carry=0,seconds_carry=0, reason='source_usage_unknown',clock_upper=1893456020,bad_cap=None,goal_objective='Finish fixture',reset_on_repeat=False,budget=1000,remaining=None,incomplete=False,bad_checkpoint=None):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source='00000000-0000-7000-8000-000000000159'
            checkpoint=root/'checkpoint.json'
            checkpoint.write_text(json.dumps(dict(source_thread_id=source,
                objective='Finish fixture',authority='operator fixture',
                next_packet='Read checkpoint and run selected preflight',pending_obligations=[])))
            endpoint=root/'native.sock'
            methods=[]
            def handler(ws):
                for raw in ws:
                    request=json.loads(raw)
                    if 'id' not in request:continue
                    method=request['method'];methods.append(method)
                    if method=='initialize':value={'userAgent':'fixture'}
                    elif method=='thread/goal/get':
                        value={'goal':dict(threadId=source,objective=goal_objective,
                            status='paused',tokenBudget=budget,timeUsedSeconds=12,
                            createdAt=100,updatedAt=100)}
                        if tokens is not None:value['goal']['tokensUsed']=0 if reset_on_repeat and methods.count(method)>1 else tokens
                    elif method=='thread/read':value={'thread':{'id':source,'turns':[]}}
                    else:raise AssertionError('Unexpected effect '+method)
                    ws.send(json.dumps(dict(id=request['id'],result=value)))
            server=unix_serve(handler,str(endpoint))
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                profiles=root/'profiles.json'
                profiles.write_text(json.dumps(dict(version=1,profiles={'worker':dict(
                    cwd=tmp,app_server='unix://'+str(endpoint),codex_path='/bin/true',
                    tmux_session='owned',timeout=1)},continuations={source:dict(
                    objective='Finish fixture',token_cap=1000,time_cap_seconds=100,
                    tokens_before_source=carry,seconds_before_source=seconds_carry,
                    approval='operator fixture',started_at='2030-01-01T00:00:00Z')})))
                if not incomplete:
                    body=json.loads(checkpoint.read_text())
                    policy=json.loads(profiles.read_text())['continuations'][source]
                    body.update(repo=tmp,worktree=tmp,commit='a'*40,dirty_work='fixture; no Git changes',
                        acceptance_remaining=['fixture continuation'],evidence=['native writer fixture'],
                        pending_wakes=[],pending_messages=[],claim_holders=[],reply_route='original thread',
                        hard_stops=['original expiry and caps'],expires_at='2030-01-01T00:01:00Z',
                        resources={k:policy[k] for k in ('token_cap','time_cap_seconds','tokens_before_source','seconds_before_source','started_at')})
                    if bad_checkpoint=="resources":body["resources"]["token_cap"]=2000
                    elif bad_checkpoint=="expires_at":body["expires_at"]="2030-01-02T00:01:00Z"
                    elif bad_checkpoint=="worktree":body["worktree"]="/tmp"
                    elif bad_checkpoint=="claim_holders":body["claim_holders"]=["another actor"]
                    checkpoint.write_text(json.dumps(body))
                if bad_cap is not None:
                    registry=json.loads(profiles.read_text());registry['continuations'][source]['token_cap']=bad_cap
                    profiles.write_text(json.dumps(registry))
                output=StringIO()
                argv=['--wake-root',str(root/'wake'),'sessions','handoff',
                    '--profiles',str(profiles),'--profile','worker','--intent','handoff-1',
                    '--thread-id',source,'--checkpoint','checkpoint.json',
                    '--checkpoint-sha256',hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                    '--expires-at','2030-01-01T00:01:00Z','--mode','new-tab','--json']
                if incomplete or bad_checkpoint:
                    with redirect_stdout(output),self.assertRaisesRegex(WakeError,'restart-safe checkpoint'):
                        run(argv)
                    self.assertEqual(methods,[])
                    self.assertFalse((root/'wake/lifecycle').exists())
                    return
                if bad_cap is not None:
                    with redirect_stdout(output),self.assertRaisesRegex(WakeError,'continuation allowance'):
                        run(argv)
                    self.assertEqual(methods,[])
                    self.assertFalse((root/'wake/lifecycle').exists())
                    return
                with redirect_stdout(output),patch('codex_wake.native_clock.snapshot',
                        return_value={'utc':{'lower':clock_upper-1,'upper':clock_upper}}):
                    code=run(argv)
                receipt=json.loads(output.getvalue())
                self.assertEqual(code,5)
                self.assertEqual(receipt['state'],'blocked')
                self.assertEqual(receipt['reason'],reason)
                if remaining is not None:self.assertEqual(receipt['remaining_tokens'],remaining)
                self.assertNotIn('successor_thread_id',receipt)
                expected=['thread/goal/get']
                if reason=='checkpoint_writer_unverified':expected.append('thread/read')
                self.assertEqual([m for m in methods if m!='initialize'],expected)
                if reset_on_repeat:
                    repeated=StringIO()
                    with redirect_stdout(repeated):self.assertEqual(run(argv),5)
                    held=json.loads(repeated.getvalue())
                    self.assertEqual(held['reason'],'source_goal_accounting_changed')
                    self.assertEqual(held['source_goal']['tokensUsed'],50)
            finally:
                server.shutdown();worker.join(2)
