"""Explicit sole-owned ACP stdio host through actual subprocess/socket seams."""
import base64,hashlib,json,os,subprocess,sys,tempfile,threading,time,unittest
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
  if p['prompt'][0]['text'] in ('lead','overflow'):
   metadata=dict(sessionId=p['sessionId'],update=dict(sessionUpdate='available_commands_update',availableCommands=[dict(name='session-info',description='Native metadata Δ🧪 café /'*3000)]))
   for unused in range(2 if p['prompt'][0]['text']=='lead' else 20):print(json.dumps(dict(jsonrpc='2.0',method='session/update',params=metadata)),flush=True)
  if p['prompt'][0]['text']=='lead':
   print(json.dumps(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId=p['sessionId'],update=dict(sessionUpdate='agent_message_chunk',content=dict(type='text',text='before-final'))))),flush=True)
  if p['prompt'][0]['text']=='future':
   print(json.dumps(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId=p['sessionId'],update=dict(sessionUpdate='future_content_update',content=dict(type='text',text='not qualified assistant text'))))),flush=True)
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
                first=page['events'][0]
                self.assertFalse(first['truncated'])
                self.assertEqual(first['kind'],'grok/session/metadata_fragment')
                self.assertEqual(first['provenance'],'native_protocol_notification')
                self.assertEqual(local.prompt('grok:existing','lead',key='live-grok')['result']['operation']['operation_id'],identifier)
                waiting=threading.Event(); waited=[]
                def wait_for_original():
                    waiting.set()
                    waited.append(LocalGrokControl(wake).result(identifier,timeout=5))
                waiter=threading.Thread(target=wait_for_original)
                waiter.start();self.assertTrue(waiting.wait(2));self.assertTrue(waiter.is_alive())
                (work/'release').write_text('release')
                waiter.join(5);self.assertFalse(waiter.is_alive())
                self.assertEqual(waited[0]['result']['operation']['phase'],'terminal')
                self.assertEqual(waited[0]['result']['operation']['execution'],'completed')
                final=LocalGrokControl(wake).output(identifier,mode='final',timeout=5)
                self.assertTrue(final['terminal'])
                self.assertEqual(final['text'],'before-finalowned-stdio-answer')
                self.assertTrue(final['retention']['history_complete'])
                events=[];cursor=0
                while True:
                    transcript=local.output(identifier,mode='transcript',cursor=cursor,limit=3)
                    events+=transcript['events'];cursor=transcript['next_cursor']
                    if cursor==transcript['latest_cursor']:break
                self.assertEqual([event['sequence'] for event in events],list(range(1,len(events)+1)))
                groups={}
                for event in events:
                    if event['kind']=='grok/session/metadata_fragment':
                        self.assertEqual(event['provenance'],'native_protocol_notification')
                        self.assertLessEqual(len(json.dumps(event['params'],sort_keys=True,separators=(',',':')).encode()),16384)
                        groups.setdefault(event['params']['group_id'],[]).append(event)
                self.assertEqual(len(groups),2)  # Identical native occurrences must remain distinct.
                expected=dict(sessionId='existing',update=dict(sessionUpdate='available_commands_update',
                    availableCommands=[dict(name='session-info',description='Native metadata Δ🧪 café /'*3000)]))
                hashes=[]
                for fragments in groups.values():
                    params=[event['params'] for event in fragments]
                    self.assertEqual([part['part_index'] for part in params],list(range(params[0]['part_count'])))
                    self.assertEqual(params[0]['occurrence_first_sequence'],fragments[0]['sequence'])
                    pieces=[base64.b64decode(part['data'],validate=True) for part in params]
                    self.assertTrue(all(len(piece)<=8192 for piece in pieces))
                    payload=b''.join(pieces)
                    self.assertGreater(len(payload),81*1024)
                    self.assertEqual(json.loads(payload),expected)
                    digest=hashlib.sha256(payload).hexdigest();hashes.append(digest)
                    self.assertTrue(all(part['sha256']==digest and part['total_bytes']==len(payload) for part in params))
                self.assertEqual(hashes[0],hashes[1])
                self.assertEqual([event['params']['update']['sessionUpdate'] for event in events if event['kind']=='grok/session/update'],
                    ['agent_message_chunk','agent_message_chunk'])
                self.assertEqual(local.output(identifier,mode='stream')['text'],'before-finalowned-stdio-answer')
                native_prompts=[json.loads(line) for line in (work/'native-methods.jsonl').read_text().splitlines() if json.loads(line)['method']=='session/prompt']
                self.assertEqual(len(native_prompts),2)
                self.assertEqual(local.output(identifier,mode='stream',cursor=final['latest_cursor'])['text'],'')
                self.assertNotIn('text',local.output(identifier,mode='silent'))
                future=local.prompt('grok:existing','future',key='unknown-kind')
                future_id=future['result']['operation']['operation_id']
                partial=local.output(future_id,mode='final',timeout=5)
                self.assertEqual(partial['text'],'owned-stdio-answer')
                self.assertFalse(partial['retention']['history_complete'])
                self.assertEqual(partial['retention']['unsupported_event_kinds'],['future_content_update'])
                self.assertEqual(local.output(future_id,mode='stream')['text'],'owned-stdio-answer')
                overflow=local.prompt('grok:existing','overflow',key='bounded-metadata')
                overflow_id=overflow['result']['operation']['operation_id']
                bounded=local.output(overflow_id,mode='final',timeout=10)
                self.assertTrue(bounded['terminal'])
                self.assertEqual(bounded['text'],'owned-stdio-answer')
                self.assertFalse(bounded['retention']['history_complete'])
                self.assertTrue(bounded['retention']['truncated'])
                self.assertEqual(bounded['retention']['max_events'],2048)
                self.assertEqual(bounded['retention']['max_bytes'],2*1024*1024)
                self.assertEqual(bounded['retention']['max_event_bytes'],16384)
                gap=local.output(overflow_id,mode='transcript',cursor=0)
                self.assertTrue(gap['retention']['cursor_gap'])
                self.assertGreater(gap['retention']['earliest_cursor'],0)
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
                self.assertEqual(len(native_prompts),5)
                (work/'release').write_text('release')

            finally:
                host.terminate()
                try:host.wait(timeout=6)
                except subprocess.TimeoutExpired:host.kill();host.wait(timeout=5)
                log.close()
                if native_pid is not None:self.assertIsNone(process_identity(native_pid))
