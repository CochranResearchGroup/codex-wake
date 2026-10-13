"""Owned successor/preflight integration through CLI, native socket and real PTYs."""
from contextlib import redirect_stdout
from io import StringIO
import hashlib
import json
import os
from pathlib import Path
import pty
import shlex
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from websockets.sync.server import unix_serve

from codex_wake.cli import run


class HandoffPreflightTests(unittest.TestCase):
    def test_one_successor_runs_preflight_without_two_active_goals_or_duplicate_assignment(self):
        self.scenario()

    def test_preflight_allowance_must_fit_before_creating_a_successor(self):
        self.scenario(source_budget=60)

    def test_lost_goal_creation_response_never_repeats_unobserved_creation(self):
        self.scenario(lost_goal=True)

    def test_usage_spent_while_pausing_is_deducted_before_successor_preparation(self):
        self.scenario(pause_used=53)

    def test_preflight_crossing_original_deadline_cannot_prepare_a_goal(self):
        self.scenario(expire_preflight=True)

    def test_daemon_expires_prepared_continuation_at_original_deadline(self):
        self.scenario(monitor_expiry=True)

    def test_continuous_monitor_activates_one_owner_with_remaining_allowance(self):
        self.scenario(activate=True)

    def test_monitor_pauses_and_interrupts_owned_turn_before_original_deadline(self):
        self.scenario(activate=True,enforce_deadline=True)

    def test_lost_deadline_pause_response_reconciles_without_repeating_pause(self):
        self.scenario(activate=True,enforce_deadline=True,lost_pause=True)

    def test_lost_activation_response_reconciles_original_goal_without_reactivation(self):
        self.scenario(activate=True,lost_activate=True)

    def test_monitor_shutdown_pauses_owned_goal_and_preserves_allowance(self):
        self.scenario(activate=True,shutdown=True)

    def test_same_intent_cli_readback_preserves_active_monitor_ownership(self):
        self.scenario(activate=True,readback=True)

    def test_another_live_monitor_generation_cannot_be_taken_over_or_stopped(self):
        self.scenario(activate=True,foreign_monitor=True)

    def test_explicit_rollback_reuses_source_and_deducts_successor_spending_once(self):
        self.scenario(rollback=True)

    def test_lost_rollback_budget_response_reconciles_without_second_debit(self):
        self.scenario(rollback=True,lost_rollback=True)

    def test_rollback_cannot_debit_source_after_another_transition_takes_ownership(self):
        self.scenario(rollback=True,owner_conflict=True)

    def test_running_preflight_over_allowance_interrupts_exact_assignment_once(self):
        self.scenario(running_overspend=True)

    def test_lost_preflight_interrupt_response_reconciles_without_reinterrupt(self):
        self.scenario(running_overspend=True,lost_preflight_interrupt=True)

    def test_same_tab_uses_fresh_identity_in_original_owned_pane_once(self):
        self.scenario(same_tab=True)

    def test_same_tab_lost_respawn_response_reconciles_new_generation_without_respawn(self):
        self.scenario(same_tab=True,lost_respawn=True)

    def test_same_tab_stale_title_cannot_replace_pinned_source_generation(self):
        self.scenario(same_tab=True,stale_title=True)

    def scenario(self,source_budget=1000,lost_goal=False,pause_used=None,expire_preflight=False,monitor_expiry=False,activate=False,enforce_deadline=False,lost_pause=False,lost_activate=False,shutdown=False,readback=False,foreign_monitor=False,rollback=False,lost_rollback=False,owner_conflict=False,running_overspend=False,lost_preflight_interrupt=False,same_tab=False,lost_respawn=False,stale_title=False):
        source='00000000-0000-7000-8000-000000000159'
        target='00000000-0000-7000-8000-000000000160'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);home=root/'home';(home/'sessions').mkdir(parents=True)
            codex=root/'codex';codex.write_text(f'#!{sys.executable}\nimport ctypes,time\n'
                "ctypes.CDLL(None).prctl(15,b'codex',0,0,0)\nprint('ready',flush=True)\ntime.sleep(60)\n")
            codex.chmod(0o700)
            clients=[];fds=[];panes={};methods=[];threads={source:{'name':'original-worker','turns':[]}}
            goals={source:dict(threadId=source,objective='Finish fixture',status='active' if pause_used is not None else 'paused',
                tokenBudget=source_budget,tokensUsed=50,timeUsedSeconds=12,createdAt=100,updatedAt=100)}
            queue={};goal_sets=[];interrupts=[];respawns=[]
            external_run=subprocess.run
            visibility={'show_goal':not lost_goal,'stale_title':stale_title}
            clock={'utc':{'lower':1000,'upper':1001}}
            def launch(command,pane,name,thread):
                master,slave=pty.openpty();fds.extend([master,slave])
                client=subprocess.Popen(command,stdin=slave,stdout=subprocess.PIPE)
                clients.append(client);self.assertEqual(client.stdout.readline(),b'ready\n')
                panes[pane]=dict(pid=client.pid,tty=os.ttyname(slave),name=name,thread=thread)
            launch([str(codex),'resume',source],'%159','original-worker',source)
            checkpoint=root/'checkpoint.json';checkpoint.write_text(json.dumps(dict(source_thread_id=source,
                objective='Finish fixture',authority='operator fixture',next_packet='Run selected preflight',pending_obligations=[])))
            digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
            threads[source]['turns']=[dict(id='writer-turn',status='completed',items=[dict(id='writer',
                type='commandExecution',status='completed',exitCode=0,cwd=tmp,
                aggregatedOutput='checkpoint:'+source+':'+digest)])]
            helper=root/'preflight.py'
            helper.write_text("""import os,sys,json,pathlib,hashlib
source,nonce,digest=sys.argv[1:]
p=pathlib.Path('checkpoint.json')
assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
target=os.environ['CODEX_THREAD_ID']
pathlib.Path('preflight.json').write_text(json.dumps(dict(version=1,state='passed',source_thread_id=source,successor_thread_id=target,checkpoint_sha256=digest,intent_fingerprint=nonce,selected_workflow='github-handoff',checks={'fixture':{'state':'passed'}})))
print('preflight:'+target+':'+nonce+':'+digest)
""")
            endpoint=root/'native.sock';profiles=root/'profiles.json'
            profile=dict(cwd=tmp,codex_home=str(home),app_server='unix://'+str(endpoint),
                codex_path=str(codex),tmux_session='owned',timeout=1)
            policy=dict(objective='Finish fixture',approval='operator fixture',token_cap=1000,
                time_cap_seconds=2000,tokens_before_source=0,seconds_before_source=0,
                started_at='1970-01-01T00:00:00Z',preflight=dict(script=str(helper),
                    sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),receipt='preflight.json',
                    workflow='github-handoff',required_checks=['fixture'],token_allowance=100))
            if activate:policy['activation']=dict(approved=True,max_poll_seconds=1,deadline_margin_seconds=10)
            profiles.write_text(json.dumps(dict(version=1,profiles={'worker':profile},continuations={source:policy})))
            def handler(ws):
                for raw in ws:
                    req=json.loads(raw)
                    if 'id' not in req:continue
                    method=req['method'];params=req.get('params',{});methods.append(method)
                    tid=params.get('threadId',target)
                    if method=='initialize':value={'userAgent':'fixture'}
                    elif method=='thread/loaded/list':value={'data':list(threads),'nextCursor':None}
                    elif method=='thread/start':threads[target]={'name':'','turns':[]};value={'thread':{'id':target}}
                    elif method=='thread/name/set':threads[tid]['name']=params['name'];value={}
                    elif method=='thread/read':
                        value={'thread':dict(id=tid,name=threads[tid]['name'],cwd=tmp,status={'type':'idle'},
                            canAcceptDirectInput=True,turns=threads[tid]['turns'],path=str(home/'sessions'/ (tid+'.jsonl')))}
                    elif method=='thread/goal/get':value={'goal':None if tid==target and not visibility['show_goal'] else goals.get(tid)}
                    elif method=='thread/goal/set':
                        goal_sets.append(params)
                        if tid==source:
                            goals[tid].update(status='paused',updatedAt=1002)
                            if pause_used is not None:goals[tid]['tokensUsed']=pause_used
                            if 'tokenBudget' in params:goals[tid]['tokenBudget']=params['tokenBudget']
                            if lost_rollback and 'tokenBudget' in params:ws.close();return
                            ws.send(json.dumps(dict(id=req['id'],result={'goal':goals[tid]})))
                            continue
                        if 'objective' not in params:
                            goals[tid].update(status=params['status'],updatedAt=1003)
                            if params['status']=='active' and enforce_deadline:
                                threads[tid]['turns'].append(dict(id='autonomous-turn',status='inProgress',items=[]))
                            if (lost_pause and params['status']=='paused') or (lost_activate and params['status']=='active'):ws.close();return
                            ws.send(json.dumps(dict(id=req['id'],result={'goal':goals[tid]})))
                            continue
                        goals[tid]=dict(threadId=tid,objective=params['objective'],status=params['status'],
                            tokenBudget=params['tokenBudget'],tokensUsed=0,timeUsedSeconds=0,createdAt=1001,updatedAt=1001)
                        if lost_goal:ws.close();return
                        value={'goal':goals[tid]}
                    elif method=='turn/interrupt':
                        interrupts.append(params)
                        for turn in threads[tid]['turns']:
                            if turn['id']==params['turnId']:turn['status']='interrupted'
                        if lost_preflight_interrupt:ws.close();return
                        value={}
                    elif method=='thread/queue/add':
                        queue[tid]=dict(id='preflight-queue',clientUserMessageId=params['clientUserMessageId'],input=params['input'])
                        value={'queuedSubmission':queue[tid]}
                    elif method=='thread/queue/list':value={'data':[queue[tid]] if tid in queue else [],'nextCursor':None}
                    elif method=='thread/queue/start':
                        q=queue.pop(tid);task=q['input'][0]['text']
                        contract=json.loads(task.split('PREFLIGHT_CONTRACT=',1)[1].split('\n',1)[0])
                        cmd=[sys.executable,str(helper),source,contract['intent_fingerprint'],digest]
                        p=external_run(cmd,cwd=tmp,env=dict(os.environ,CODEX_THREAD_ID=tid),capture_output=True,text=True,check=True)
                        threads[tid]['turns']=[dict(id='preflight-turn',status='completed',items=[
                            dict(id='user',type='userMessage',clientId=q['clientUserMessageId'],content=q['input']),
                            dict(id='preflight-command',type='commandExecution',status='completed',exitCode=p.returncode,
                                cwd=tmp,command=shlex.join(cmd),aggregatedOutput=p.stdout)])]
                        (home/'sessions'/ (tid+'.jsonl')).write_text(json.dumps(dict(type='event_msg',payload=dict(
                            type='token_count',info={'total_token_usage':{'total_tokens':30}})))+'\n')
                        if running_overspend:
                            threads[tid]['turns'][0]['status']='inProgress'
                            (home/'sessions'/ (tid+'.jsonl')).write_text(json.dumps(dict(type='event_msg',payload=dict(type='token_count',info={'total_token_usage':{'total_tokens':101}})))+'\n')
                        if expire_preflight:clock['utc'].update(lower=2001,upper=2002)
                        value={}
                    else:raise AssertionError('unexpected native method '+method)
                    ws.send(json.dumps(dict(id=req['id'],result=value)))
            def command(argv,**kwargs):
                if 'list-panes' in argv:
                    if '-a' in argv:
                        out='\n'.join('\t'.join(['$1','owned','@'+pane[1:],'1',p['name'],pane,'0',
                            threads[source]['name'] if visibility['stale_title'] and p['thread']==target else threads[p['thread']]['name'],tmp,p['tty']]) for pane,p in panes.items())
                    else:out='\n'.join(p for p in panes if '@'+p[1:] in argv)
                elif 'capture-pane' in argv:out='\n\n\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m\n'
                elif 'display-message' in argv:out='2,2'
                elif 'respawn-pane' in argv:
                    self.assertTrue(same_tab);respawns.append(argv)
                    self.assertEqual(argv[argv.index('-t')+1],'%159')
                    clients[0].terminate();clients[0].wait(timeout=2)
                    launch(['sh','-c','exec '+argv[-1]],'%159','original-worker',target);out=''
                    if lost_respawn:raise subprocess.TimeoutExpired(argv,1)
                elif 'new-window' in argv:
                    self.assertFalse(same_tab)
                    launch(['sh','-c','exec '+argv[-1]],'%160',argv[argv.index('-n')+1],target);out='@160\t%160'
                else:out=''
                return subprocess.CompletedProcess(argv,0,out,'')
            argv=['--wake-root',tmp,'sessions','handoff','--profiles',str(profiles),'--profile','worker',
                '--intent','handoff-1','--thread-id',source,'--checkpoint','checkpoint.json',
                '--checkpoint-sha256',digest,'--expires-at','2030-01-01T00:00:00Z','--mode','same-tab' if same_tab else 'new-tab','--json']
            server=unix_serve(handler,str(endpoint));worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                with patch('subprocess.run',side_effect=command),patch('codex_wake.native_clock.snapshot',
                        return_value=clock):
                    for _ in range(3 if stale_title else 2):
                        output=StringIO()
                        with redirect_stdout(output):self.assertEqual(run(argv),5)
                        receipt=json.loads(output.getvalue())
                        if stale_title and _<2:
                            if _==0:self.assertEqual(receipt['state'],'awaiting_preflight')
                            else:
                                self.assertEqual(receipt['reason'],'source_attachment_generation_changed')
                                visibility['stale_title']=False
                            continue
                        if lost_respawn and _==0:
                            self.assertEqual(receipt['state'],'uncertain')
                            self.assertEqual(receipt['successor']['uncertain_effect'],'tmux/respawn-pane')
                            continue
                        if running_overspend:
                            self.assertEqual(receipt['state'],'uncertain' if lost_preflight_interrupt and _==0 else 'blocked')
                            if not (lost_preflight_interrupt and _==0):
                                self.assertEqual(receipt['reason'],'preflight_allowance_exhausted')
                            self.assertEqual(receipt['preflight_tokens_used'],101)
                            self.assertEqual(interrupts,[dict(threadId=target,turnId='preflight-turn')])
                            self.assertNotIn(target,goals)
                            self.assertEqual(methods.count('thread/start'),1)
                            if _==1:return
                            continue
                        if expire_preflight:
                            self.assertEqual(receipt['state'],'expired')
                            self.assertEqual(receipt['reason'],'continuation_time_exhausted')
                            self.assertNotIn(target,goals)
                            self.assertEqual(goal_sets,[])
                            self.assertEqual(methods.count('thread/start'),1)
                            return
                        if source_budget==60:
                            self.assertEqual(receipt['reason'],'preflight_allowance_insufficient')
                            self.assertEqual(methods.count('thread/start'),0)
                            self.assertEqual(goal_sets,[])
                            return
                        if lost_goal:
                            self.assertEqual(receipt['state'],'uncertain')
                            self.assertEqual(receipt['uncertain_effect'],'thread/goal/prepare_successor')
                            continue
                        self.assertEqual(receipt['state'],'awaiting_activation',{'history':receipt.get('successor',{}).get('history'),'respawns':len(respawns)})
                        self.assertEqual(receipt['successor_thread_id'],target)
                        self.assertEqual(receipt['remaining_tokens'],920 if pause_used is None else 970-pause_used)
                        self.assertEqual(receipt['preflight']['state'],'passed')
                    if rollback:
                        if owner_conflict:
                            owner=root/'lifecycle'/ ('owner-'+hashlib.sha256(source.encode()).hexdigest()+'.json')
                            lease=json.loads(owner.read_text());lease['intent_fingerprint']='another-transition';owner.write_text(json.dumps(lease))
                            out=StringIO()
                            with redirect_stdout(out):self.assertEqual(run(argv+['--rollback']),5)
                            self.assertEqual(json.loads(out.getvalue())['rollback']['reason'],'source_owned_by_another_transition')
                            self.assertEqual(goals[source]['tokenBudget'],1000)
                            self.assertEqual(len(goal_sets),1)
                            return
                        for index in range(2):
                            out=StringIO()
                            with redirect_stdout(out):self.assertEqual(run(argv+['--rollback']),5 if lost_rollback and index==0 else 0)
                            restored=json.loads(out.getvalue())['rollback']
                            self.assertEqual(restored['state'],'uncertain' if lost_rollback and index==0 else 'completed')
                            self.assertEqual(restored['thread_id'],source)
                            self.assertEqual(restored['remaining_tokens'],920)
                            self.assertEqual(goals[source]['tokenBudget'],970)
                            self.assertEqual(goals[source]['tokensUsed'],50)
                        self.assertEqual(clients[0].poll(),None)
                    if activate:
                        from codex_wake.daemon import run as daemon_run
                        sleeps=[]
                        def sleep(_):
                            sleeps.append(1)
                            if foreign_monitor and len(sleeps)==1:
                                from codex_wake.process import process_identity
                                saved=root/'lifecycle'/ (hashlib.sha256(b'handoff-1').hexdigest()+'.json')
                                lease=json.loads(saved.read_text())
                                lease['deadline_fence'].update(pid=clients[0].pid,identity=process_identity(clients[0].pid))
                                saved.write_text(json.dumps(lease))
                                clock['utc'].update(lower=1990,upper=1991)
                                return
                            if enforce_deadline and len(sleeps)==1:
                                self.assertEqual(goals[target]['status'],'active')
                                clock['utc'].update(lower=1990,upper=1991)
                                return
                            if lost_pause and len(sleeps)==2:return
                            if lost_activate and len(sleeps)==1:return
                            if not enforce_deadline:
                                self.assertEqual(goals[target]['status'],'active')
                                if readback:
                                    out=StringIO()
                                    with redirect_stdout(out):self.assertEqual(run(argv),0)
                                    self.assertEqual(json.loads(out.getvalue())['state'],'active')
                                saved=root/'lifecycle'/ (hashlib.sha256(b'handoff-1').hexdigest()+'.json')
                                self.assertEqual(json.loads(saved.read_text())['state'],'active')
                            raise KeyboardInterrupt
                        with patch('codex_wake.daemon.time.sleep',side_effect=sleep),redirect_stdout(StringIO()):
                            with self.assertRaises(KeyboardInterrupt):
                                daemon_run(['--wake-root',tmp,'--no-dispatch','--interval','1'])
                        self.assertEqual(goals[target]['status'],'active' if foreign_monitor else 'paused')
                        if enforce_deadline:
                            self.assertEqual(interrupts,[dict(threadId=target,turnId='autonomous-turn')])
                            saved=root/'lifecycle'/ (hashlib.sha256(b'handoff-1').hexdigest()+'.json')
                            self.assertEqual(json.loads(saved.read_text())['state'],'expired')
                        self.assertEqual(goals[source]['status'],'paused')
                        if lost_activate:
                            saved=root/'lifecycle'/ (hashlib.sha256(b'handoff-1').hexdigest()+'.json')
                            self.assertEqual(json.loads(saved.read_text())['reason'],'monitor_stopped')
                    if monitor_expiry:
                        from codex_wake.daemon import run as daemon_run
                        clock['utc'].update(lower=2001,upper=2002)
                        with redirect_stdout(StringIO()):
                            self.assertEqual(daemon_run(['--wake-root',tmp,'--once','--no-dispatch']),0)
                        saved=root/'lifecycle'/ (hashlib.sha256(b'handoff-1').hexdigest()+'.json')
                        monitored=json.loads(saved.read_text())
                        self.assertEqual(monitored['state'],'expired')
                        self.assertEqual(monitored['reason'],'continuation_time_exhausted')
                    if lost_goal:
                        self.assertEqual(len(goal_sets),1)
                        visibility['show_goal']=True
                        output=StringIO()
                        with redirect_stdout(output):self.assertEqual(run(argv),5)
                        self.assertEqual(json.loads(output.getvalue())['state'],'awaiting_activation')
                self.assertEqual(methods.count('thread/start'),1)
                self.assertEqual(methods.count('thread/queue/add'),1)
                self.assertEqual(methods.count('thread/queue/start'),1)
                self.assertEqual(len(goal_sets),(2 if foreign_monitor else 3) if activate else (2 if rollback or pause_used is not None else 1))
                self.assertEqual(goals[source]['tokensUsed'],50 if pause_used is None else pause_used)
                self.assertEqual(goals[source]['status'],'paused')
                self.assertEqual(goals[target]['status'],'active' if foreign_monitor else 'paused')
                self.assertEqual(goals[target]['tokenBudget'],920 if pause_used is None else 970-pause_used)
                if same_tab:
                    self.assertIsNotNone(clients[0].poll())
                    self.assertEqual(list(panes),['%159'])
                    self.assertEqual(len(respawns),1)
                    self.assertEqual(receipt['successor']['pane_id'],'%159')
                    self.assertIsNone(clients[-1].poll())
                else:self.assertTrue(all(c.poll() is None for c in clients))
            finally:
                server.shutdown();worker.join(2)
                for client in clients:client.terminate();client.wait(timeout=2);client.stdout.close()
                for fd in fds:os.close(fd)
