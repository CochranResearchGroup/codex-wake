"""Public operation seam over an actual owned Unix native-protocol peer."""
import json
import contextlib
import io
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from websockets.sync.server import unix_serve

from codex_wake.local_session_operations import LocalSessionControl


class OutputModesTests(unittest.TestCase):
    def test_output_frames_timeout_origin_precedes_first_handle_and_terminal_pages_drain_untimed(self):
        from codex_wake import measurements
        from codex_wake.local_control_commands import output_frames
        from test_measurements import observation
        counter = [1000]
        unavailable = [False]
        timeouts = []
        class Owner:
            def output(self, identifier, **options):
                timeouts.append(options['timeout'])
                cursor = options['cursor']
                if cursor: unavailable[0] = True
                return dict(terminal=True, phase='terminal', execution='completed', mode='stream',
                    text='B' if cursor else 'A', next_cursor=cursor+1, latest_cursor=2, reason=None,
                    retention=dict(history_complete=True, cursor_gap=False, truncated=False))
        def clock():
            if unavailable[0]: raise measurements.TimeUnavailable('unqualified')
            return observation(counter[0])
        with patch('codex_wake.measurements.snapshot', side_effect=clock):
            frames = output_frames(Owner(), 'one', 'stream', 1)
            self.assertEqual(next(frames), {'operation_id': 'one'})
            counter[0] = 10000
            expired = list(frames)
            self.assertEqual(timeouts, [])
            self.assertEqual(expired[-1], {'exit_code': 124})
            counter[0] = 1000
            retained = list(output_frames(Owner(), 'one', 'stream', 1))
        self.assertEqual([frame['stdout'] for frame in retained if 'stdout' in frame], ['A', 'B'])
        self.assertEqual(timeouts[-1], 0)
        self.assertEqual(retained[-1], {'exit_code': 0})

    def test_output_frames_rechecks_time_before_publishing_text_after_consumer_pause(self):
        from codex_wake import measurements
        from codex_wake.local_control_commands import output_frames
        from test_measurements import observation
        unavailable = [False]
        class Owner:
            def output(self, identifier, **options):
                return dict(terminal=True, phase='terminal', execution='completed', mode='final',
                    text='done', next_cursor=1, latest_cursor=1, reason=None,
                    retention=dict(history_complete=True, cursor_gap=False, truncated=False))
        def clock():
            if unavailable[0]: raise measurements.TimeUnavailable('unqualified')
            return observation(1000)
        with patch('codex_wake.measurements.snapshot', side_effect=clock):
            frames = output_frames(Owner(), 'one', 'final', 1)
            self.assertEqual(next(frames), {'operation_id': 'one'})
            self.assertIn('output', next(frames))
            unavailable[0] = True
            with self.assertRaises(measurements.TimeUnavailable): next(frames)

    def test_output_frames_does_not_publish_a_terminal_reply_observed_after_original_deadline(self):
        from codex_wake.local_control_commands import output_frames
        from test_measurements import observation
        counter = [1000]
        class Owner:
            def output(self, identifier, **options):
                counter[0] = 10000
                return dict(terminal=True, phase='terminal', execution='completed', mode='final',
                    text='late', next_cursor=1, latest_cursor=1, reason=None,
                    retention=dict(history_complete=True, cursor_gap=False, truncated=False))
        with patch('codex_wake.measurements.snapshot', side_effect=lambda: observation(counter[0])):
            frames = list(output_frames(Owner(), 'one', 'final', 1))
        self.assertFalse(any('stdout' in frame or 'output' in frame for frame in frames))
        self.assertEqual(frames[-1], {'exit_code': 124})
        self.assertEqual(json.loads(''.join(frame.get('stderr', '') for frame in frames))['reason'], 'wait_timeout')

    def test_output_frames_requires_qualified_wait_but_zero_timeout_inspection_is_untimed(self):
        from codex_wake import measurements
        from codex_wake.local_control_commands import output_frames
        class Owner:
            def __init__(self): self.timeouts = []
            def output(self, identifier, **options):
                self.timeouts.append(options['timeout'])
                return dict(terminal=True, phase='terminal', execution='completed', mode='final',
                    text='done', next_cursor=0, latest_cursor=0, reason=None,
                    retention=dict(history_complete=True, cursor_gap=False, truncated=False))
        owner = Owner()
        with patch('codex_wake.measurements.snapshot', side_effect=measurements.TimeUnavailable('unqualified')):
            with self.assertRaises(measurements.TimeUnavailable):
                list(output_frames(owner, 'one', 'final', 1))
            self.assertEqual(owner.timeouts, [])
            frames = list(output_frames(owner, 'one', 'final', 0))
        self.assertEqual(owner.timeouts, [0])
        self.assertEqual([frame['stdout'] for frame in frames if 'stdout' in frame], ['done'])
        self.assertEqual(frames[-1], {'exit_code': 0})

    def test_detached_collector_retains_live_text_order_and_original_retry(self):
        from codex_wake import measurements
        release=threading.Event();delta=threading.Event();submissions=[]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);home=root/'home';home.mkdir();endpoint='unix://'+str(root/'native.sock')
            def handler(ws):
                subscribed=False
                for raw in ws:
                    message=json.loads(raw)
                    if 'id' not in message:continue
                    method=message['method']
                    if method=='initialize':value={'codexHome':str(home)}
                    elif method=='thread/loaded/list':value={'data':['one'],'nextCursor':None}
                    elif method=='thread/read':value={'thread':{'id':'one','cwd':str(root),'status':{'type':'idle'},'turns':[]}}
                    elif method=='thread/resume':
                        subscribed=True;value={'thread':{'id':'one'}}
                    elif method=='turn/start':value={'turn':{'id':'native-turn','status':'inProgress'}};submissions.append(message)
                    else:raise AssertionError(method)
                    ws.send(json.dumps(dict(id=message['id'],result=value)))
                    if method=='turn/start':
                        if not subscribed:return
                        def event(method,**params):ws.send(json.dumps(dict(method=method,params=dict(threadId='one',turnId='native-turn',**params))))
                        event('turn/started',turn={'id':'native-turn','status':'inProgress'})
                        # Schema-shaped telemetry from the qualified native protocol; not a live capture.
                        event('turn/moderationMetadata',metadata={'decision':'allowed'})
                        event('item/agentMessage/delta',itemId='answer',delta='Hello ');delta.set()
                        release.wait()
                        event('item/started',item={'id':'tool','type':'commandExecution','command':'echo fixture'})
                        event('item/completed',item={'id':'tool','type':'commandExecution','exitCode':0})
                        event('item/agentMessage/delta',itemId='answer',delta='world')
                        event('item/completed',item={'id':'answer','type':'agentMessage','phase':'final_answer','text':'Hello world'})
                        counts=dict(cachedInputTokens=0,inputTokens=10,outputTokens=2,reasoningOutputTokens=0,totalTokens=12)
                        event('thread/tokenUsage/updated',tokenUsage={'last':counts,'total':counts,'modelContextWindow':32000})
                        event('turn/completed',turn={'id':'native-turn','status':'completed'})
                        return
            with unix_serve(handler,str(root/'native.sock')) as server:
                worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
                try:
                    owner=LocalSessionControl(root)
                    caller=subprocess.run([sys.executable,'-c',
                        'import json,sys; from codex_wake.local_session_operations import LocalSessionControl; print(json.dumps(LocalSessionControl(sys.argv[1]).prompt("thread:one","fixture question","stable-key",endpoint=sys.argv[2])))',
                        str(root),endpoint],capture_output=True,text=True,timeout=15)
                    self.assertEqual(caller.returncode,0,caller.stderr)
                    submitted=json.loads(caller.stdout)
                    operation=submitted['result']['operation'];identifier=operation['operation_id']
                    self.assertTrue(delta.wait(3))
                    live=owner.output(identifier,mode='stream',timeout=3)
                    deadline=measurements.Deadline(5)
                    while not live['text'] and not deadline.expired():
                        live=owner.output(identifier,mode='stream',cursor=live['next_cursor'],timeout=3)
                    self.assertEqual(live['text'],'Hello ')
                    self.assertFalse(live['terminal'])
                    # Fresh caller; neither waiting nor disconnect cancels original work.
                    again=LocalSessionControl(root).prompt('thread:one','fixture question','stable-key',endpoint=endpoint)
                    self.assertEqual(again['result']['operation']['operation_id'],identifier)
                    self.assertEqual(len(submissions),1)
                    from codex_wake.local_control_commands import present
                    out=io.StringIO();err=io.StringIO()
                    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
                        code=present(owner,identifier,mode='silent',timeout=0)
                    self.assertEqual(code,124);self.assertEqual(out.getvalue(),'')
                    self.assertIn(identifier,err.getvalue())
                    release.set()
                    final=owner.output(identifier,mode='final',timeout=3)
                    self.assertEqual(final['text'],'Hello world',json.dumps(final,sort_keys=True))
                    transcript=owner.output(identifier,mode='transcript')
                    self.assertEqual([event['kind'] for event in transcript['events']],['turn/started','turn/moderationMetadata','item/agentMessage/delta','item/started','item/completed','item/agentMessage/delta','item/completed','thread/tokenUsage/updated','turn/completed'])
                    self.assertTrue(transcript['retention']['history_complete'])
                    tail=owner.output(identifier,mode='transcript',cursor=live['next_cursor'])
                    self.assertEqual(tail['events'][0]['kind'],'item/started')
                    silent=owner.output(identifier,mode='silent')
                    self.assertNotIn('text',silent);self.assertNotIn('events',silent)
                    for mode,expected in [('final','Hello world'),('silent','')]:
                        out=io.StringIO();err=io.StringIO()
                        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
                            code=present(owner,identifier,mode=mode,timeout=0)
                        self.assertEqual(code,0);self.assertEqual(out.getvalue(),expected);self.assertEqual(err.getvalue(),'')
                finally:
                    release.set();server.shutdown();worker.join(2)

    def test_retention_exposes_lost_cursor_and_oversized_event_without_claiming_complete_history(self):
        from codex_wake.local_session_events import TurnEvents
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            store=TurnEvents(directory);store.update('retained',status='collecting')
            for index in range(132):store.append('retained','item/agentMessage/delta',{'delta':'x'*16000})
            page=store.read('retained',0)
            self.assertGreater(page['events'][0]['sequence'],1)
            self.assertGreaterEqual(page['retention']['earliest_cursor'],1)
            self.assertTrue(page['retention']['cursor_gap'])
            self.assertTrue(page['retention']['truncated'])
            store.append('retained','item/agentMessage/delta',{'delta':'x'*16385})
            last=store.read('retained',132)
            self.assertTrue(last['events'][0]['params']['omitted'])
            self.assertFalse(last['retention']['history_complete'])
            with self.assertRaises(InventoryError):store.read('retained',999999)

    def test_silent_cli_reports_failed_native_turn_without_success_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);home=root/'home';home.mkdir();endpoint='unix://'+str(root/'native.sock')
            def handler(ws):
                subscribed=False
                for raw in ws:
                    message=json.loads(raw)
                    if 'id' not in message:continue
                    method=message['method']
                    if method=='initialize':result={'codexHome':str(home)}
                    elif method=='thread/loaded/list':result={'data':['one'],'nextCursor':None}
                    elif method=='thread/read':result={'thread':{'id':'one','cwd':str(root),'status':{'type':'idle'},'turns':[]}}
                    elif method=='thread/resume':result={'thread':{'id':'one'}}
                    elif method=='turn/start':result={'turn':{'id':'failed-turn'}}
                    else:raise AssertionError(method)
                    ws.send(json.dumps(dict(id=message['id'],result=result)))
                    if method=='turn/start':
                        ws.send(json.dumps(dict(method='turn/completed',params=dict(threadId='one',turnId='failed-turn',turn=dict(id='failed-turn',status='failed')))))
                        return
            with unix_serve(handler,str(root/'native.sock')) as server:
                worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
                try:
                    caller=subprocess.run([sys.executable,'-m','codex_wake','--wake-root',str(root),'control','prompt','thread:one','fixture failure',
                        '--idempotency-key','failure-key','--endpoint',endpoint,'--mode','silent','--timeout','3'],capture_output=True,text=True,timeout=15)
                    self.assertEqual(caller.returncode,2,caller.stderr)
                    self.assertEqual(caller.stdout,'');self.assertIn('operation_id',caller.stderr)
                    from codex_wake.local_control_service import LocalOperations
                    from codex_wake.local_control_client import cli_frames
                    diagnostic=json.loads(caller.stderr.strip().splitlines()[-1])
                    self.assertEqual(diagnostic['reason'],'native_turn_failed')
                    frames=list(cli_frames(LocalOperations(root),['output',diagnostic['operation_id'],'--mode','silent','--timeout','0']))
                    self.assertEqual([frame['exit_code'] for frame in frames if 'exit_code' in frame],[2])
                    self.assertFalse(any(frame.get('stdout') for frame in frames))
                    framed=json.loads(''.join(frame.get('stderr','') for frame in frames))
                    self.assertEqual(framed['reason'],'native_turn_failed')
                    self.assertEqual(framed['operation_id'],diagnostic['operation_id'])
                finally:server.shutdown();worker.join(2)
