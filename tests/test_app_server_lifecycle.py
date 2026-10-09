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
    def test_turn_survives_proxy_close_without_claiming_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            private = base / 'control'
            private.mkdir(mode=0o700)
            sockpath = private / 'daemon.sock'
            listener = socket.socket(socket.AF_UNIX)
            listener.bind(str(sockpath)); listener.listen(); listener.settimeout(5)
            started, disconnected, release, completed = [threading.Event() for _ in range(4)]
            errors = []
            def daemon():
                try:
                    conn, _ = listener.accept()
                    with conn, conn.makefile('rwb', buffering=0) as stream:
                        for line in stream:
                            req = json.loads(line)
                            method = req['method']
                            if method == 'initialize': result = {}
                            elif method == 'thread/resume': result = {'thread': {'id': 'thread_abc', 'status': {'type': 'idle'}}}
                            elif method == 'turn/start':
                                started.set(); result = {'turn': {'id': 'turn_owned'}}
                            else: raise AssertionError(method)
                            stream.write((json.dumps({'id': req['id'], 'result': result})+'\n').encode())
                    disconnected.set()
                    if release.wait(5): completed.set()
                except BaseException as exc: errors.append(exc)
            worker = threading.Thread(target=daemon)
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
'''.replace('SOCKET,',repr(str(sockpath))+','))
            executable.chmod(0o700)
            try:
                found = test_app_server.AppServerTests().make_record(base/'wake', base)
                result = dispatch_app_server_record(base/'wake', found, default_codex_cmd=str(executable))
                self.assertEqual(result.status, 'submitted')
                self.assertTrue(started.wait(.5), 'persistent daemon never received turn/start')
                self.assertTrue(disconnected.wait(2), 'owned proxy not closed')
                self.assertTrue(worker.is_alive(), 'proxy close terminated turn owner')
                record = json.loads((base/'wake/submitted/wake_app.json').read_text())
                self.assertEqual(record['dispatch_result']['turn_id'], 'turn_owned')
                self.assertNotIn('completed', record['dispatch_result'])
                release.set()
                self.assertTrue(completed.wait(2), 'daemon-owned turn could not complete after proxy teardown')
            finally:
                release.set();listener.close();worker.join(6)
            self.assertFalse(errors, errors)

    def test_missing_unsupported_and_nonprivate_daemon_refuse_before_turn_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); private=base/'control';private.mkdir(mode=0o700)
            sockpath=private/'daemon.sock';server=socket.socket(socket.AF_UNIX);server.bind(str(sockpath))
            executable=base/'codex';executable.write_text('#!/bin/sh\nexit 0\n');executable.chmod(0o700)
            from subprocess import CompletedProcess
            try:
                for case in ('missing','unsupported','nonprivate','wrong_actor','symlink'):
                    with self.subTest(case=case):
                        private.chmod(0o755 if case=='nonprivate' else 0o700)
                        data={'status':'stopped' if case=='missing' else 'running','socketPath':str(sockpath),'appServerVersion':'0.162.0'}
                        calls=[]
                        def run(argv,**kwargs):
                            calls.append(argv)
                            if 'version' in argv:return CompletedProcess(argv,0,json.dumps(data),'')
                            return CompletedProcess(argv,2 if case=='unsupported' else 0,'--sock','')
                        found=test_app_server.AppServerTests().make_record(base/('wake-'+case),base)
                        original=os.lstat
                        def lstat(path,*args,**kwargs):
                            value=original(path,*args,**kwargs)
                            if case=='wrong_actor' and Path(path)==sockpath:
                                from types import SimpleNamespace
                                return SimpleNamespace(st_mode=value.st_mode,st_uid=os.geteuid()+1)
                            return value
                        alias=private/'alias.sock'
                        if case=='symlink':alias.symlink_to(sockpath);data['socketPath']=str(alias)
                        with patch('codex_wake.app_server.subprocess.run',side_effect=run),patch('codex_wake.app_server.subprocess.Popen') as popen,patch('codex_wake.app_server.os.lstat',side_effect=lstat):
                            result=dispatch_app_server_record(base/('wake-'+case),found,default_codex_cmd=str(executable))
                        self.assertEqual(result.status,'failed');popen.assert_not_called()
                        self.assertTrue(all('start' not in c and 'restart' not in c for c in calls))
            finally:server.close()

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
