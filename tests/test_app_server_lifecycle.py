"""Provider-free dispatch lifetime: client teardown must not kill an owned turn."""
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from codex_wake.app_server import dispatch_app_server_record
import test_app_server


class PersistentDispatchTests(unittest.TestCase):
    def test_turn_survives_websocket_close_without_claiming_completion(self):
        for owned_alias in (False, True):
            with self.subTest(owned_alias=owned_alias):
                self._qualify_turn_lifetime(owned_alias)

    def _qualify_turn_lifetime(self, owned_alias):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            private = base / 'control'
            private.mkdir(mode=0o700)
            target_private = base / 'daemon-private'
            target_private.mkdir(mode=0o700)
            sockpath = target_private / 'daemon.sock'
            reported_path = private / 'app-server-control.sock'
            if owned_alias:
                reported_path.symlink_to(sockpath)
            else:
                reported_path = sockpath
            from websockets.sync.server import serve
            from websockets.exceptions import ConnectionClosed
            listener = socket.socket(socket.AF_UNIX)
            listener.bind(str(sockpath)); listener.listen()
            started, disconnected, release, completed = [threading.Event() for _ in range(4)]
            errors = []
            def daemon(conn):
                try:
                    for message in conn:
                        req = json.loads(message)
                        method = req['method']
                        if method == 'initialized': continue
                        if method == 'initialize': result = {}
                        elif method == 'thread/resume': result = {'thread': {'id': 'thread_abc', 'status': {'type': 'idle'}}}
                        elif method == 'turn/start':
                            started.set(); result = {'turn': {'id': 'turn_owned'}}
                        else: raise AssertionError(method)
                        conn.send(json.dumps({'id': req['id'], 'result': result}))
                    disconnected.set()
                    if release.wait(5): completed.set()
                except ConnectionClosed: disconnected.set()
                except BaseException as exc: errors.append(exc)
            server = serve(daemon, sock=listener, open_timeout=.2, close_timeout=.2)
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            executable = base / 'codex'
            executable.write_text('''#!/usr/bin/python3
import json, socket, sys
args=sys.argv[1:]
if args==['app-server','daemon','version']:
 print(json.dumps({'status':'running','socketPath':SOCKET,'appServerVersion':'0.162.0'}));sys.exit()
if args==['app-server','proxy','--help']:
 print('Proxy stdio bytes; --sock SOCKET_PATH');sys.exit()
if args[:3]==['app-server','proxy','--sock']:
 s=socket.socket(socket.AF_UNIX);s.connect(args[3]);f=s.makefile('rwb',buffering=0)
 for line in sys.stdin.buffer:
  f.write(line);sys.stdout.buffer.write(f.readline());sys.stdout.buffer.flush()
 sys.exit()
# Old standalone lifecycle accepts then dies when dispatch closes its child.
for line in sys.stdin:
 q=json.loads(line);m=q['method'];r={} if m=='initialize' else {'thread':{'id':'thread_abc','status':{'type':'idle'}}} if m=='thread/resume' else {'turn':{'id':'turn_owned'}}
 print(json.dumps({'id':q['id'],'result':r}),flush=True)
'''.replace('SOCKET,',repr(str(reported_path))+','))
            executable.chmod(0o700)
            try:
                found = test_app_server.AppServerTests().make_record(base/'wake', base)
                result = dispatch_app_server_record(base/'wake', found, default_codex_cmd=str(executable))
                self.assertEqual(result.status, 'submitted')
                self.assertTrue(started.wait(.5), 'persistent daemon never received turn/start')
                self.assertTrue(disconnected.wait(2), 'owned connection not closed')
                self.assertTrue(worker.is_alive(), 'connection close terminated turn owner')
                record = json.loads((base/'wake/submitted/wake_app.json').read_text())
                self.assertEqual(record['dispatch_result']['turn_id'], 'turn_owned')
                self.assertNotIn('completed', record['dispatch_result'])
                release.set()
                self.assertTrue(completed.wait(2), 'daemon-owned turn could not complete after connection teardown')
            finally:
                release.set();server.shutdown();worker.join(6)
            self.assertFalse(errors, errors)

    def test_missing_unsupported_and_nonprivate_daemon_refuse_before_turn_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); private=base/'control';private.mkdir(mode=0o700)
            sockpath=private/'daemon.sock';server=socket.socket(socket.AF_UNIX);server.bind(str(sockpath))
            executable=base/'codex';executable.write_text('#!/bin/sh\nexit 0\n');executable.chmod(0o700)
            from subprocess import CompletedProcess
            try:
                for case in ('missing','unsupported','nonprivate','wrong_actor','symlink_chain','foreign_alias','dangling_alias','unsafe_target','ancestor_alias','foreign_target'):
                    with self.subTest(case=case):
                        private.chmod(0o755 if case=='nonprivate' else 0o700)
                        data={'status':'stopped' if case=='missing' else 'running','socketPath':str(sockpath),'appServerVersion':'0.162.0'}
                        calls=[]
                        def run(argv,**kwargs):
                            calls.append(argv)
                            if 'version' in argv:return CompletedProcess(argv,2 if case=='unsupported' else 0,json.dumps(data),'')
                            return CompletedProcess(argv,2 if case=='unsupported' else 0,'--sock','')
                        found=test_app_server.AppServerTests().make_record(base/('wake-'+case),base)
                        original=os.lstat
                        def lstat(path,*args,**kwargs):
                            value=original(path,*args,**kwargs)
                            if ((case=='wrong_actor' and Path(path)==sockpath)
                                    or (case=='foreign_alias' and Path(path)==alias)
                                    or (case=='foreign_target' and Path(path)==sockpath)):
                                from types import SimpleNamespace
                                return SimpleNamespace(st_mode=value.st_mode,st_uid=os.geteuid()+1)
                            return value
                        alias=private/'alias.sock'
                        if alias.is_symlink(): alias.unlink()
                        if case in ('symlink_chain','foreign_alias','dangling_alias','unsafe_target','ancestor_alias','foreign_target'):
                            if case=='symlink_chain':
                                intermediate=private/'intermediate.sock'
                                intermediate.symlink_to(sockpath)
                                alias.symlink_to(intermediate)
                            elif case=='ancestor_alias':
                                parent_alias=base/'control-alias';parent_alias.symlink_to(private)
                                alias.symlink_to(sockpath);data['socketPath']=str(parent_alias/'alias.sock')
                            elif case=='dangling_alias': alias.symlink_to(private/'missing.sock')
                            elif case=='unsafe_target':
                                unsafe=base/'unsafe';unsafe.mkdir(mode=0o755);unsafe.chmod(0o755)
                                unsafe_socket=socket.socket(socket.AF_UNIX)
                                unsafe_socket.bind(str(unsafe/'daemon.sock'));unsafe_socket.close()
                                alias.symlink_to(unsafe/'daemon.sock')
                            else: alias.symlink_to(sockpath)
                            if case!='ancestor_alias':data['socketPath']=str(alias)
                        with patch('codex_wake.app_server.subprocess.run',side_effect=run),patch('codex_wake.app_server.subprocess.Popen') as popen,patch('websockets.sync.client.unix_connect') as connect,patch('codex_wake.app_server.os.lstat',side_effect=lstat):
                            result=dispatch_app_server_record(base/('wake-'+case),found,default_codex_cmd=str(executable))
                        self.assertEqual(result.status,'failed');popen.assert_not_called();connect.assert_not_called()
                        failed=json.loads((base/('wake-'+case)/'failed/wake_app.json').read_text())
                        if case=='missing':self.assertIn('is not running',failed['last_error'])
                        if case=='unsupported':self.assertIn('discovery unsupported',failed['last_error'])
                        self.assertTrue(all('start' not in c and 'restart' not in c for c in calls))
            finally:server.close()

    def test_framed_rpc_invalid_messages_and_absolute_deadline(self):
        from websockets.sync.server import serve
        from websockets.exceptions import ConnectionClosed
        from codex_wake.app_server import UnixWebSocketAppServerClient
        from codex_wake.records import WakeError
        import time
        for case in ('silent', 'notifications', 'invalid', 'binary', 'error', 'wrong_id', 'boolean_id', 'nonobject', 'oversized'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'daemon.sock'
                listener=socket.socket(socket.AF_UNIX);listener.bind(str(path));listener.listen()
                def handler(conn):
                    try:
                        req=json.loads(conn.recv())
                        if case in ('silent','wrong_id','boolean_id'):
                            if case in ('wrong_id','boolean_id'):conn.send(json.dumps({'id':True if case=='boolean_id' else 999,'result':{}}))
                            time.sleep(.15)
                        elif case=='notifications':
                            while True:
                                conn.send(json.dumps({'method':'notice'}));time.sleep(.005)
                        elif case=='invalid':conn.send('not json')
                        elif case=='binary':conn.send(b'{}')
                        elif case=='error':conn.send(json.dumps({'id':req['id'],'error':{'code':-1}}))
                        elif case=='nonobject':conn.send(json.dumps({'id':req['id'],'result':[]}))
                        else:conn.send('x'*(32*1024*1024+1))
                    except ConnectionClosed:pass
                server=serve(handler,sock=listener,close_timeout=.05)
                worker=threading.Thread(target=server.serve_forever);worker.start()
                with patch('codex_wake.app_server.persistent_app_server_socket',return_value=path):
                    client=UnixWebSocketAppServerClient(timeout_seconds=.08)
                started=time.monotonic()
                try:
                    with self.assertRaises(WakeError):client.initialize()
                finally:client.close();server.shutdown();worker.join(2)
                self.assertLess(time.monotonic()-started,2)

    def test_rpc_timeout_reaps_only_owned_client(self):
        import sys
        import time
        from codex_wake.app_server import StdioAppServerClient
        from codex_wake.records import WakeError
        client = StdioAppServerClient(
            command=[sys.executable, '-c', 'import time; time.sleep(300)'],
            timeout_seconds=.05,
        )
        started = time.monotonic()
        try:
            with self.assertRaisesRegex(WakeError, 'timed out'):
                client.initialize()
        finally:
            client.close()
        self.assertLess(time.monotonic() - started, 3)
        self.assertIsNotNone(client.process.poll())

    def test_discovery_timeout_does_not_start_a_proxy_or_daemon(self):
        from subprocess import TimeoutExpired
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            executable = base/'codex'
            executable.write_text('#!/bin/sh\nexit 0\n'); executable.chmod(0o700)
            found = test_app_server.AppServerTests().make_record(base/'wake', base)
            with patch('codex_wake.app_server.subprocess.run', side_effect=TimeoutExpired('discovery', 5)), patch('codex_wake.app_server.subprocess.Popen') as spawn:
                result = dispatch_app_server_record(base/'wake', found, default_codex_cmd=str(executable))
            self.assertEqual(result.status, 'failed')
            spawn.assert_not_called()
