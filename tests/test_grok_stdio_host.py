"""Explicit sole-owned ACP stdio host through actual subprocess/socket seams."""
import json,os,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from codex_wake.controller_auth import Actor
from codex_wake.managed_inventory import InventoryError


FIXTURE='''import json,os,sys,time
from pathlib import Path
root=Path.cwd()
for line in sys.stdin:
 r=json.loads(line);method=r['method'];p=r.get('params',{})
 with (root/'native-methods.jsonl').open('a') as f:f.write(json.dumps(dict(method=method,params=p))+'\\n')
 if method=='initialize':v=dict(protocolVersion=1,agentCapabilities=dict(loadSession=True,sessionCapabilities=dict(list={})),authMethods=[],_meta=dict(agentVersion='fixture-ACP-v1',agentId='fixture-native-agent',agentInstanceId='fixture-native-instance',currentWorkingDirectory=str(root)))
 elif method=='session/prompt':
  if p['prompt'][0]['text']=='lead':
   print(json.dumps(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId=p['sessionId'],update=dict(sessionUpdate='agent_message_chunk',content=dict(type='text',text='before-final'))))),flush=True)
  if p['prompt'][0]['text'] in ('hold','lead'):
   (root/'started').write_text('started');deadline=time.monotonic()+10
   while not (root/'release').exists() and time.monotonic()<deadline:time.sleep(.01)
  print(json.dumps(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId=p['sessionId'],update=dict(sessionUpdate='agent_message_chunk',content=dict(type='text',text='owned-stdio-answer'))))),flush=True)
  v=dict(stopReason='end_turn')
 elif method=='session/new':v=dict(sessionId='created-native')
 elif method=='session/load':v={}
 elif method=='session/list':v=dict(sessions=[dict(sessionId='existing',cwd=str(root),title='Fixture')])
 elif method=='session/set_model':v=dict(_meta=dict(model=dict(Ok=p['modelId'])))
 else:raise AssertionError(method)
 print(json.dumps(dict(jsonrpc='2.0',id=r['id'],result=v)),flush=True)
'''


class StdioHostTests(unittest.TestCase):
    def test_owned_child_identity_cached_native_initialize_and_no_queue(self):
        from codex_wake.controller_grok import ControllerGrok
        from codex_wake.process import process_identity
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);wake=root/'wake';home=root/'home';home.mkdir();work=root/'work';work.mkdir();ready=root/'ready.json'
            (work/'agent').write_text(FIXTURE)
            source=str(Path(__file__).resolve().parents[1]/'src')
            environment=dict(os.environ,PYTHONPATH=source)
            code='from codex_wake.grok_stdio_host import serve_host; serve_host('+repr(str(wake))+',profile="fixture",binary='+repr(str(Path(sys.executable).resolve()))+',home='+repr(str(home))+',cwd='+repr(str(work))+',account="fixture",ready_file='+repr(str(ready))+',block_network=True)'
            log=(root/'host.log').open('wb')
            host=subprocess.Popen([sys.executable,'-c',code],env=environment,stdout=log,stderr=subprocess.STDOUT)
            native_pid=None
            try:
                deadline=time.monotonic()+10
                while not ready.exists():
                    self.assertIsNone(host.poll(),(root/'host.log').read_text());self.assertLess(time.monotonic(),deadline);time.sleep(.02)
                metadata=json.loads(ready.read_text());target=metadata['target'];native_pid=int(target['process_pid'])
                self.assertNotEqual(native_pid,host.pid)
                self.assertEqual(metadata['transport_owner']['pid'],host.pid)
                actor=Actor('host','service','fixture','grant','issuer','resource',frozenset({'observe','control'}),[target],time.time()+120)
                owner=ControllerGrok(wake)
                for unused in range(2):
                    caps=owner.execute(actor,'grok.capabilities',dict(profile='fixture',expected_target=target),authorize=lambda:actor)
                    self.assertEqual(caps['result']['native_identity']['agent_instance_id'],'fixture-native-instance')
                lines=[json.loads(line) for line in (work/'native-methods.jsonl').read_text().splitlines()]
                self.assertEqual([r['method'] for r in lines],['initialize'])
                profile=owner.profile('fixture')
                with owner._connection(profile,lambda:None) as connection:
                    self.assertEqual(connection.call('session/list',dict(cwd=str(work)),'list')['sessions'][0]['sessionId'],'existing')
                    self.assertEqual(connection.call('session/set_model',dict(sessionId='existing',modelId='fixture-model'),'model')['_meta']['model']['Ok'],'fixture-model')
                    with self.assertRaises(InventoryError):connection.call('session/unknown',{},'unknown')
                def args(key,prompt):
                    selected=dict(target,conversation_id='existing')
                    return dict(profile='fixture',expected_target=selected,prompt=prompt,_request=dict(operation_id=key,idempotency_key=key,correlation_id=key,binding='fixture',target=selected))
                replies=[]
                task=threading.Thread(target=lambda:replies.append(owner.execute(actor,'grok.prompt',args('first','hold'),authorize=lambda:actor)))
                task.start();deadline=time.monotonic()+5
                while not (work/'started').exists():self.assertLess(time.monotonic(),deadline);time.sleep(.01)
                busy=owner.execute(actor,'grok.prompt',args('second','must-not-queue'),authorize=lambda:actor)['result']['operation']
                self.assertEqual(busy['execution'],'not_started')
                self.assertEqual(busy['reason'],'native_owner_busy')
                (work/'release').write_text('release');task.join(5);self.assertFalse(task.is_alive())
                self.assertEqual(replies[0]['result']['operation']['answer']['text'],'owned-stdio-answer')
                lines=[json.loads(line) for line in (work/'native-methods.jsonl').read_text().splitlines()]
                self.assertEqual([r['method'] for r in lines],['initialize','session/list','session/set_model','session/prompt'])
                self.assertFalse((wake/'goal-supervision').exists())
                from codex_wake.local_grok_control import LocalGrokControl
                local=LocalGrokControl(wake)
                (work/'release').unlink()
                admitted=local.prompt('grok:existing','lead',key='live-grok')
                identifier=admitted['result']['operation']['operation_id']
                page=local.output(identifier,mode='transcript',timeout=5)
                self.assertFalse(page['terminal'])
                self.assertEqual(page['events'][0]['params']['update']['content']['text'],'before-final')
                self.assertEqual(local.prompt('grok:existing','lead',key='live-grok')['result']['operation']['operation_id'],identifier)
                (work/'release').write_text('release')
                final=LocalGrokControl(wake).output(identifier,mode='final',timeout=5)
                self.assertTrue(final['terminal'])
                self.assertEqual(final['text'],'before-finalowned-stdio-answer')
                native_prompts=[json.loads(line) for line in (work/'native-methods.jsonl').read_text().splitlines() if json.loads(line)['method']=='session/prompt']
                self.assertEqual(len(native_prompts),2)
                self.assertEqual(local.output(identifier,mode='stream',cursor=final['latest_cursor'])['text'],'')
                self.assertNotIn('text',local.output(identifier,mode='silent'))
                (work/'release').unlink()
                lost=local.prompt('grok:existing','lead',key='lost-collector')
                lost_id=lost['result']['operation']['operation_id']
                local.output(lost_id,mode='transcript',timeout=5)
                collector=lost['result']['operation']['result']['collector_pid']
                os.kill(collector,15)
                deadline=time.monotonic()+5
                while process_identity(collector) is not None:
                    self.assertLess(time.monotonic(),deadline);time.sleep(.01)
                uncertain=LocalGrokControl(wake).result(lost_id)['result']['operation']
                self.assertEqual(uncertain['execution'],'unknown')
                self.assertEqual(uncertain['phase'],'uncertain')
                local.prompt('grok:existing','lead',key='lost-collector')
                native_prompts=[json.loads(line) for line in (work/'native-methods.jsonl').read_text().splitlines() if json.loads(line)['method']=='session/prompt']
                self.assertEqual(len(native_prompts),3)
                (work/'release').write_text('release')

            finally:
                host.terminate()
                try:host.wait(timeout=6)
                except subprocess.TimeoutExpired:host.kill();host.wait(timeout=5)
                log.close()
                if native_pid is not None:self.assertIsNone(process_identity(native_pid))
