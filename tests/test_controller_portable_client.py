"""Published client seam; these tests do not require a native Wake owner."""
import contextlib
import io
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path


class PortableClientTests(unittest.TestCase):
    def test_linux_and_portable_callers_reject_oversized_controller_responses(self):
        import subprocess
        import sys
        body = json.dumps({'fixture': 'x' * 4194304}).encode()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token = Path(directory) / 'token'
                token.write_text('synthetic-token')
                token.chmod(0o600)
                for module in ('codex_wake.controller_client', 'codex_wake.cli'):
                    with self.subTest(module=module):
                        result = subprocess.run([sys.executable, '-m', module, 'controller', 'remote',
                            '--endpoint', 'http://127.0.0.1:' + str(server.server_port),
                            '--token-file', str(token), 'inventory.list'], capture_output=True, text=True, timeout=15)
                        self.assertEqual(result.returncode, 2)
                        self.assertEqual(json.loads(result.stdout)['status'], 'failed')
                        self.assertEqual(json.loads(result.stdout)['error']['code'], 'response_limit')
                        self.assertLess(len(result.stdout), 4096)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_portable_client_preserves_api_and_oauth_mcp_envelopes(self):
        from codex_wake.controller_client import main
        requests=[]
        envelope=dict(schema_version=1,operation='inventory.list',status='completed',result={'resources':[]})
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                requests.append((self.path,self.headers['Authorization'],json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                result=envelope if self.path=='/operations' else dict(jsonrpc='2.0',id=1,result={'structuredContent':envelope})
                body=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token=Path(directory)/'token';token.write_text('synthetic-token');token.chmod(0o600)
                for transport in ('api','mcp'):
                    out=io.StringIO()
                    with contextlib.redirect_stdout(out):
                        code=main(['controller','remote','--endpoint','http://127.0.0.1:'+str(server.server_port),'--token-file',str(token),
                                   '--transport',transport,'inventory.list'])
                    self.assertEqual(code,0);self.assertEqual(json.loads(out.getvalue()),envelope)
                self.assertEqual([row[0] for row in requests],['/operations','/mcp'])
                self.assertTrue(all(row[1]=='Bearer synthetic-token' for row in requests))
                self.assertEqual(requests[1][2]['params']['name'],'wake_controller_list')
        finally:server.shutdown();server.server_close();worker.join()

    def test_portable_client_refuses_public_token_and_native_owner_commands(self):
        from codex_wake.controller_client import main
        with tempfile.TemporaryDirectory() as directory:
            token=Path(directory)/'token';token.write_text('synthetic-token');token.chmod(0o644)
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                code=main(['controller','remote','--endpoint','https://wake.invalid','--token-file',str(token),'inventory.list'])
            self.assertEqual(code,2)
            self.assertEqual(json.loads(out.getvalue())['error']['code'],'token_file_not_private')
            out=io.StringIO()
            with contextlib.redirect_stdout(out):code=main(['controller','serve'])
            self.assertEqual(code,2)
            self.assertEqual(json.loads(out.getvalue())['error']['code'],'unsupported_native_windows_owner')

    def test_bearer_is_not_forwarded_on_redirect(self):
        from codex_wake.controller_client import main
        paths=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                paths.append(self.path)
                self.send_response(307);self.send_header('Location','/other');self.send_header('Content-Length','0');self.end_headers()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token=Path(directory)/'token';token.write_text('synthetic-token');token.chmod(0o600)
                with contextlib.redirect_stdout(io.StringIO()):
                    code=main(['controller','remote','--endpoint','http://127.0.0.1:'+str(server.server_port),'--token-file',str(token),'inventory.list'])
                self.assertEqual(code,2);self.assertEqual(paths,['/operations'])
        finally:server.shutdown();server.server_close();worker.join()

    def test_published_bootstrap_preserves_linux_cli(self):
        import os
        import subprocess
        import sys
        if os.name=='nt':self.skipTest('Linux delegation qualified on Linux only')
        answer=subprocess.run([sys.executable,'-m','codex_wake.entrypoint','--help'],text=True,capture_output=True,timeout=20)
        self.assertEqual(answer.returncode,0,answer.stderr)
        self.assertIn('wakes',answer.stdout)
        self.assertIn('controller',answer.stdout)
