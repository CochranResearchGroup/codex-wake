"""Portable API/MCP callers preserve tab outcomes and return nonzero on partial work."""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest


class RemoteTabExitTests(unittest.TestCase):
    def test_api_and_mcp_tab_partial_or_uncertain_results_exit_three(self):
        from codex_wake.controller_client import main
        outcome={'phase':'terminal','result':{'status':'partial'}}
        envelope={'schema_version':1,'operation':'tabs.format.enable','status':'completed','result':{'operation':outcome}}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                value=envelope if self.path=='/operations' else {'jsonrpc':'2.0','id':1,'result':{'isError':False,'structuredContent':envelope}}
                body=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                token=Path(directory)/'token';token.write_text('synthetic-token');token.chmod(0o600)
                for phase,status in (('terminal','partial'),('terminal','held'),('terminal','uncertain'),('uncertain',None)):
                    outcome['phase']=phase
                    outcome['result']={'status':status} if status is not None else None
                    for transport in ('api','mcp'):
                        with self.subTest(phase=phase,status=status,transport=transport):
                            output=io.StringIO()
                            with contextlib.redirect_stdout(output):
                                code=main(['controller','remote','--endpoint',f'http://127.0.0.1:{server.server_port}',
                                    '--token-file',str(token),'--transport',transport,'tabs.format.enable'])
                            self.assertEqual(json.loads(output.getvalue()),envelope)
                            self.assertEqual(code,3)
        finally:
            server.shutdown();server.server_close();thread.join()
