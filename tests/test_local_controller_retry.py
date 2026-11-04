"""A disconnected caller can reconcile the exact intent sent over HTTP."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer


class RetryTests(unittest.TestCase):
    def test_disconnected_creation_or_prompt_retains_explicit_or_generated_key(self):
        from codex_wake.local_control_client import remote
        from codex_wake.process import process_identity
        from codex_wake.shortcut_store import private_directory,write
        received=[]
        class Drop(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.close_connection=True
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with ThreadingHTTPServer(('127.0.0.1',0),Drop) as server:
                threading.Thread(target=server.serve_forever,daemon=True).start()
                private_directory(root/'local-controller')
                write(root/'local-controller'/'connection.json',dict(version=1,url='http://127.0.0.1:'+str(server.server_port),token='x'*43,uid=os.getuid(),pid=os.getpid(),process=process_identity(os.getpid())))
                for command in (['prompt','owned','hello'],['create','--harness','grok','--profile','owned']):
                    for supplied in (['--idempotency-key=explicit-equals'],['--idempotency-key','explicit-space'],[]):
                        with self.subTest(supplied=supplied):
                            with self.assertRaises(ValueError) as failed:
                                remote(root,[*command,*supplied])
                            arguments=received[-1]['arguments']
                            keys=[value.split('=',1)[1] for value in arguments if value.startswith('--idempotency-key=')]
                            keys += [arguments[index+1] for index,value in enumerate(arguments) if value=='--idempotency-key']
                            self.assertEqual(len(keys),1,arguments)
                            self.assertIn(keys[0],str(failed.exception))
                server.shutdown()
