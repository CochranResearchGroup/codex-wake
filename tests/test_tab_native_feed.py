"""Passive native feed protocol and ownership acceptance."""
import json
import os
import struct
from types import SimpleNamespace
from pathlib import Path
import tempfile
import threading
import time
import unittest

from websockets.sync.server import unix_serve
from websockets.sync.client import unix_connect

from codex_wake.tab_native_feed import NativeStatusFeed


class NativeFeedTests(unittest.TestCase):
    def test_metadata_only_baseline_passive_update_and_owned_close(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'native.sock')
            methods = []
            ready = threading.Event()
            connections = []

            def handler(connection):
                connections.append(connection)
                try:
                    for raw in connection:
                        message = json.loads(raw)
                        method = message.get('method')
                        methods.append(method)
                        if method == 'initialized':
                            continue
                        if method == 'initialize':
                            connection.send(json.dumps(dict(id='approval-request', method='item/commandExecution/requestApproval', params=dict(secret='excluded'))))
                            result = dict(codexHome='/synthetic/home', userAgent='fixture', secret='excluded')
                        elif method == 'thread/loaded/list':
                            result = dict(data=['t1'], nextCursor=None)
                        elif method == 'thread/read':
                            self.assertIs(message['params']['includeTurns'], False)
                            result = dict(thread=dict(id='t1', cwd='/synthetic', modelProvider='openai',
                                                      status=dict(type='idle'), turns=[dict(secret='excluded')],
                                                      preview='excluded'))
                        else:
                            raise AssertionError(method)
                        connection.send(json.dumps(dict(id=message['id'], result=result)))
                        if method == 'thread/read':
                            connection.send(json.dumps(dict(method='thread/status/changed', params=dict(threadId='t1', status=dict(type='active', activeFlags=[])))))
                            ready.set()
                except Exception:
                    pass

            with unix_serve(handler, path=path) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                def other_uid_connector(*args, **kwargs):
                    connection = unix_connect(*args, **kwargs)
                    return SimpleNamespace(socket=SimpleNamespace(getsockopt=lambda *args:
                        struct.pack('3i', os.getpid(), os.geteuid() + 1, os.getegid())),
                        close=connection.close)

                rejected = NativeStatusFeed('unix://' + path, connector=other_uid_connector)
                self.assertEqual(rejected.poll()[0]['kind'], 'unavailable')
                rejected.close()
                self.assertEqual(methods, [])
                feed = NativeStatusFeed('unix://' + path)
                try:
                    first = feed.poll()
                    self.assertEqual(first[0]['kind'], 'baseline')
                    self.assertEqual(first[0]['data']['peer']['pid'], os.getpid())
                    self.assertNotIn('excluded', json.dumps(first))
                    self.assertTrue(ready.wait(1))
                    events = first[1:] + feed.poll(.5)
                    self.assertEqual(events[-1]['data'], dict(thread_id='t1', status=dict(type='active', activeFlags=[])))
                    self.assertGreater(events[-1]['sequence'], first[0]['sequence'])
                    self.assertEqual(events[-1]['epoch'], first[0]['epoch'])
                    self.assertEqual(feed.status()['state'], 'connected')
                    self.assertEqual(set(methods), {'initialize', 'initialized', 'thread/loaded/list', 'thread/read'})
                    old_epoch = feed.status()['epoch']
                    connections[-1].close()
                    lost = feed.poll(.5)
                    self.assertEqual(lost[-1]['kind'], 'unavailable')
                    self.assertEqual(feed.status()['state'], 'unavailable')
                    self.assertEqual(feed.poll(), [])  # backoff avoids reconnect spin
                    time.sleep(.51)
                    resumed = feed.poll()
                    self.assertEqual(resumed[0]['kind'], 'baseline')
                    self.assertNotEqual(resumed[0]['epoch'], old_epoch)
                    self.assertEqual(resumed[0]['sequence'], 1)
                finally:
                    feed.close()
                    server.shutdown()
                    thread.join(2)
                self.assertEqual(feed.poll(), [])

    def test_burst_latency_and_malformed_status_invalidate_without_retaining_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'native.sock')
            send_burst = threading.Event()
            sent = threading.Event()
            finish = threading.Event()
            stamps = []

            def handler(connection):
                try:
                    for raw in connection:
                        request = json.loads(raw)
                        method = request.get('method')
                        if method == 'initialized':
                            continue
                        result = {} if method == 'initialize' else dict(data=[], nextCursor=None)
                        connection.send(json.dumps(dict(id=request['id'], result=result)))
                        if method == 'thread/loaded/list':
                            send_burst.wait(2)
                            for index in range(100):
                                stamps.append(time.monotonic())
                                connection.send(json.dumps(dict(method='thread/status/changed', params=dict(
                                    threadId=str(index), status=dict(type='idle')))))
                            sent.set()
                            finish.wait(2)
                            connection.send(json.dumps(dict(method='thread/status/changed', params=dict(
                                threadId='broken', status=dict(type='private transcript must not be retained')))))
                except Exception:
                    pass

            with unix_serve(handler, path=path) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                feed = NativeStatusFeed('unix://' + path)
                try:
                    baseline = feed.poll()
                    self.assertEqual(baseline[0]['kind'], 'baseline')
                    send_burst.set()
                    self.assertTrue(sent.wait(2))
                    events = feed.poll(.1)
                    self.assertEqual(len(events), 100)
                    latencies = sorted(time.monotonic() - stamp for stamp in stamps)
                    self.__class__.burst_p95_seconds = latencies[94]
                    self.assertLess(latencies[94], 2)
                    self.assertEqual([event['sequence'] for event in events], list(range(2, 102)))
                    finish.set()
                    failed = feed.poll(.5)
                    self.assertEqual(failed[-1]['kind'], 'unavailable')
                    self.assertNotIn('private transcript', json.dumps(failed) + json.dumps(feed.status()))
                finally:
                    send_burst.set()
                    finish.set()
                    feed.close()
                    server.shutdown()
                    thread.join(2)

    def test_non_socket_and_invalid_endpoint_fail_without_crashing_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ordinary'
            path.write_text('not a socket')
            feed = NativeStatusFeed('unix://' + str(path))
            self.assertEqual(feed.poll()[0]['kind'], 'unavailable')
            feed.close()
        with self.assertRaises(ValueError):
            NativeStatusFeed('https://untrusted')


if __name__ == '__main__':
    unittest.main()
