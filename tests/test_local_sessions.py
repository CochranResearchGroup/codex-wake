"""Owned local discovery through the real CLI and a Unix native protocol peer."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import time
from websockets.sync.server import unix_serve


class LocalSessionTests(unittest.TestCase):
    def test_discovery_and_exact_resolution_need_no_profile_and_reject_stale_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / 'home'; home.mkdir()
            endpoint = 'unix://' + str(root / 'native.sock')
            def handler(ws):
                for text in ws:
                    message=json.loads(text)
                    if 'id' not in message:continue
                    method=message['method']
                    if method=='initialize':value={'codexHome':str(home)}
                    elif method=='thread/loaded/list':value={'data':['one','two'],'nextCursor':None}
                    elif method=='thread/read':value={'thread':{'id':message['params']['threadId'],'name':'same-name','cwd':str(root),'status':{'type':'idle'},'modelProvider':'openai','turns':[{'id':'turn-one','status':'completed','items':[{'type':'agentMessage','text':'known answer'}]}]}}
                    elif method=='turn/start':value={'turn':{'id':'turn-one'}}
                    else:raise AssertionError(method)
                    ws.send(json.dumps({'id':message['id'],'result':value}))
                    if method=='turn/start':
                        for method,params in [('item/completed',{'item':{'id':'answer','type':'agentMessage','phase':'final_answer','text':'known answer'}}),('turn/completed',{'turn':{'id':'turn-one','status':'completed'}})]:
                            ws.send(json.dumps({'method':method,'params':dict(threadId="one",turnId="turn-one",**params)}))
                        return
            with unix_serve(handler,str(root/'native.sock')) as server:
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                def call(*args):
                    p=subprocess.run([sys.executable,'-m','codex_wake','--wake-root',str(root),'control',*args,'--endpoint',endpoint],capture_output=True,text=True)
                    return p,json.loads(p.stdout)
                p,listing=call('list');self.assertEqual(p.returncode,0,p.stderr)
                self.assertEqual([x['thread_id'] for x in listing['sessions']],['one','two'])
                self.assertEqual(listing['sessions'][0]['target']['uid'],os.getuid())
                p,chosen=call('resolve','thread:one');self.assertEqual(p.returncode,0,p.stderr)
                self.assertEqual(chosen['target']['conversation_id'],'one')
                p,ambiguous=call('resolve','same-name');self.assertEqual(p.returncode,2)
                self.assertEqual(ambiguous['error']['code'],'ambiguous_target')
                stale=dict(chosen['target'],socket_generation='replaced')
                p,failure=call('resolve','thread:one','--expected-target',json.dumps(stale));self.assertEqual(p.returncode,2)
                self.assertEqual(failure['error']['code'],'stale_target')
                p,submitted=call('prompt','thread:one','known question','--idempotency-key','test-intent')
                self.assertEqual(p.returncode,0,p.stderr)
                operation=submitted['result']['operation']
                self.assertEqual(operation['result']['turn_id'],'turn-one')
                p,finished=call('result',operation['operation_id'])
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertEqual(finished['result']['operation']['answer']['text'],'known answer')
                p,repeated=call('prompt','thread:one','known question','--idempotency-key','test-intent')
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertEqual(repeated['result']['operation']['operation_id'],operation['operation_id'])
                from codex_wake.local_session_events import TurnEvents
                state=TurnEvents(root).state(operation['operation_id']);deadline=time.monotonic()+3
                while Path('/proc',str(state.get('pid'))).exists() and time.monotonic()<deadline:time.sleep(.01)
                server.shutdown()
