"""Exact source fencing through public observation and real native transports."""
import json
import os
from contextlib import ExitStack
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

from websockets.sync.server import unix_serve
from codex_wake.controller_tabs import controller_tabs_from_root
from codex_wake.process import process_identity
from codex_wake.tab_observation import ObservationCache
from codex_wake.tab_observer import TabObserver


@unittest.skipUnless(shutil.which('tmux'), 'stock tmux required')
class ObserverIdentityTests(unittest.TestCase):
    def test_same_basename_and_thread_cannot_substitute_native_source(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            homes = [root/'a'/'home', root/'b'/'home']
            for home in homes:
                home.mkdir(parents=True)
            tmux = ['tmux', '-S', str(root/'tmux.sock')]
            subprocess.run([*tmux, 'new-session', '-d', '-s', 'fixture', '-c', str(root), 'sleep 60'], check=True)
            stack.callback(lambda: subprocess.run([*tmux, 'kill-server'], capture_output=True))
            subprocess.run([*tmux, 'select-pane', '-t', '%0', '-T', 'source-a'], check=True)
            config = root/'controller-tabs.json'
            config.write_text(json.dumps(dict(schema_version=1, workspaces=dict(fixture=dict(
                kind='tmux', socket_path=str(root/'tmux.sock'), session_id='$0')))))
            config.chmod(0o600)
            connections = [[], []]
            endpoints = []
            servers = []
            def handler(index, connection):
                connections[index].append(connection)
                try:
                    for raw in connection:
                        request = json.loads(raw)
                        method = request.get('method')
                        if method == 'initialized':
                            continue
                        if method == 'initialize':
                            result = dict(codexHome=str(homes[index]), userAgent='identity-fixture')
                        elif method == 'thread/loaded/list':
                            result = dict(data=['shared-thread'], nextCursor=None)
                        elif method == 'thread/read':
                            result = dict(thread=dict(id='shared-thread', name='source-a' if index == 0 else 'source-b',
                                cwd=str(root) if index == 0 else str(homes[index]), status=dict(type='idle' if index == 0 else 'active', activeFlags=[])))
                        else:
                            raise AssertionError(method)
                        connection.send(json.dumps(dict(id=request['id'], result=result)))
                except Exception:
                    pass
            for index in range(2):
                socket = str(root/f'native-{index}.sock')
                server = stack.enter_context(unix_serve(lambda connection, i=index: handler(i, connection), path=socket))
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                stack.callback(thread.join, 2)
                stack.callback(server.shutdown)
                servers.append(server)
                endpoints.append('unix://'+socket)
            def process_probe(pid, deadline):
                birth = process_identity(pid)
                return ([dict(process=dict(pid=pid, start_ticks=birth['start_time_ticks'], boot_id=birth['boot_id']),
                    executable='/synthetic/codex', argv=[], cwd=str(root))], True)
            mono = [0.]
            owner = controller_tabs_from_root(root)
            owner.observation_cache = ObservationCache(root, process_probe=process_probe, monotonic=lambda: mono[0])
            observer = TabObserver(root, owner=owner, settings=dict(health=False, errors=False),
                monotonic=lambda: mono[0], native_endpoints=endpoints)
            stack.callback(observer.close)
            initial = observer.tick()
            pane = initial['resources'][0]['traits']['panes'][0]
            self.assertEqual(pane['binding']['conversation_id'], 'shared-thread')
            self.assertEqual(pane['traits']['activity']['value'], 'idle')
            self.assertEqual(pane['native_endpoint'], endpoints[0])
            self.assertTrue(pane['traits']['activity']['source_available'])
            connections[0][-1].close()
            servers[0].shutdown()
            # Force a real metadata rebaseline on B while A's identity-bound
            # observation is still within its two-second cache lifetime.
            connections[1][-1].send(json.dumps(dict(method='thread/status/changed', params=dict(
                threadId='new-thread', status=dict(type='active', activeFlags=[])))))
            mono[0] = 1.1
            until = time.monotonic()+3
            while True:
                result = observer.tick()
                if any(source.get('state') == 'unavailable' for source in result['observer']['sources']
                       if source.get('source_kind') == 'native'):
                    break
                self.assertLess(time.monotonic(), until)
            pane = result['resources'][0]['traits']['panes'][0]
            self.assertFalse(pane['traits']['activity']['source_available'])
            self.assertNotEqual(pane['traits']['activity']['value'], 'running')
            self.assertNotEqual(pane['native_endpoint'], endpoints[1])
            self.assertIsNotNone(process_identity(os.getpid()))
