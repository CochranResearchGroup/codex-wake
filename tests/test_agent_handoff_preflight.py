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

    def scenario(self,source_budget=1000,lost_goal=False):
        source='00000000-0000-7000-8000-000000000159'
        target='00000000-0000-7000-8000-000000000160'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);home=root/'home';(home/'sessions').mkdir(parents=True)
            codex=root/'codex';codex.write_text(f'#!{sys.executable}\nimport ctypes,time\n'
                "ctypes.CDLL(None).prctl(15,b'codex',0,0,0)\nprint('ready',flush=True)\ntime.sleep(60)\n")
            codex.chmod(0o700)
            clients=[];fds=[];panes={};methods=[];threads={source:{'name':'original-worker','turns':[]}}
            goals={source:dict(threadId=source,objective='Finish fixture',status='paused',
                tokenBudget=source_budget,tokensUsed=50,timeUsedSeconds=12,createdAt=100,updatedAt=100)}
            queue={};goal_sets=[]
            external_run=subprocess.run
            visibility={'show_goal':not lost_goal}
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
                        goals[tid]=dict(threadId=tid,objective=params['objective'],status=params['status'],
                            tokenBudget=params['tokenBudget'],tokensUsed=0,timeUsedSeconds=0,createdAt=1001,updatedAt=1001)
                        if lost_goal:ws.close();return
                        value={'goal':goals[tid]}
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
                        value={}
                    else:raise AssertionError('unexpected native method '+method)
                    ws.send(json.dumps(dict(id=req['id'],result=value)))
            def command(argv,**kwargs):
                if 'list-panes' in argv:
                    if '-a' in argv:
                        out='\n'.join('\t'.join(['$1','owned','@'+pane[1:],'1',p['name'],pane,'0',
                            threads[p['thread']]['name'],tmp,p['tty']]) for pane,p in panes.items())
                    else:out='\n'.join(p for p in panes if '@'+p[1:] in argv)
                elif 'capture-pane' in argv:out='\n\n\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m\n'
                elif 'display-message' in argv:out='2,2'
                elif 'new-window' in argv:
                    launch(['sh','-c','exec '+argv[-1]],'%160',argv[argv.index('-n')+1],target);out='@160\t%160'
                else:out=''
                return subprocess.CompletedProcess(argv,0,out,'')
            argv=['--wake-root',tmp,'sessions','handoff','--profiles',str(profiles),'--profile','worker',
                '--intent','handoff-1','--thread-id',source,'--checkpoint','checkpoint.json',
                '--checkpoint-sha256',digest,'--expires-at','2030-01-01T00:00:00Z','--mode','new-tab','--json']
            server=unix_serve(handler,str(endpoint));worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                with patch('subprocess.run',side_effect=command),patch('codex_wake.native_clock.snapshot',
                        return_value={'utc':{'lower':1000,'upper':1001}}):
                    for _ in range(2):
                        output=StringIO()
                        with redirect_stdout(output):self.assertEqual(run(argv),5)
                        receipt=json.loads(output.getvalue())
                        if source_budget==60:
                            self.assertEqual(receipt['reason'],'preflight_allowance_insufficient')
                            self.assertEqual(methods.count('thread/start'),0)
                            self.assertEqual(goal_sets,[])
                            return
                        if lost_goal:
                            self.assertEqual(receipt['state'],'uncertain')
                            self.assertEqual(receipt['uncertain_effect'],'thread/goal/prepare_successor')
                            continue
                        self.assertEqual(receipt['state'],'awaiting_activation')
                        self.assertEqual(receipt['successor_thread_id'],target)
                        self.assertEqual(receipt['remaining_tokens'],920)
                        self.assertEqual(receipt['preflight']['state'],'passed')
                    if lost_goal:
                        self.assertEqual(len(goal_sets),1)
                        visibility['show_goal']=True
                        output=StringIO()
                        with redirect_stdout(output):self.assertEqual(run(argv),5)
                        self.assertEqual(json.loads(output.getvalue())['state'],'awaiting_activation')
                self.assertEqual(methods.count('thread/start'),1)
                self.assertEqual(methods.count('thread/queue/add'),1)
                self.assertEqual(methods.count('thread/queue/start'),1)
                self.assertEqual(len(goal_sets),1)
                self.assertEqual(goals[source]['tokensUsed'],50)
                self.assertEqual(goals[source]['status'],'paused')
                self.assertEqual(goals[target]['status'],'paused')
                self.assertEqual(goals[target]['tokenBudget'],920)
                self.assertTrue(all(c.poll() is None for c in clients))
            finally:
                server.shutdown();worker.join(2)
                for client in clients:client.terminate();client.wait(timeout=2);client.stdout.close()
                for fd in fds:os.close(fd)
