import base64
import hashlib
import json
from pathlib import Path
import socket
import os
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError


class FlowSurfaceTests(unittest.TestCase):
    def test_oauth_api_and_mcp_share_pinned_run_and_deny_revocation(self):
        from codex_wake.controller_auth import OAuthAuthority
        from codex_wake.controller_http import ControllerHTTPServer
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import ManagedInventory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            auth = OAuthAuthority(root / 'auth.sqlite', issuer='https://wake.test', resource='https://wake.test/controller')
            client = auth.register({'redirect_uris': ['http://localhost/callback']})
            verifier = 'x' * 43
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            target = dict(host=socket.gethostname(), environment=os.environ.get('WSL_DISTRO_NAME') or os.name, flow_id='fixture')
            code = auth.authorize(subject='author', principal_kind='service', client_id=client['client_id'],
                redirect_uri='http://localhost/callback', resource=auth.resource, scopes=['observe', 'control'],
                targets=[target], code_challenge=challenge)
            token = auth.token(dict(grant_type='authorization_code', code=code, client_id=client['client_id'],
                redirect_uri='http://localhost/callback', code_verifier=verifier, resource=auth.resource))['access_token']
            server = ControllerHTTPServer(('127.0.0.1', 0), auth,
                ControllerOperations(ManagedInventory(root / 'wake'), host=target['host'], environment=target['environment']))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def request(path, body):
                req = Request('http://127.0.0.1:' + str(server.server_port) + path, data=json.dumps(body).encode(),
                    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
                try:
                    with urlopen(req) as response:
                        return response.status, json.load(response)
                except HTTPError as error:
                    return error.code, json.load(error)
            def api(verb, args):
                return request('/operations', dict(operation='flows.' + verb, arguments=args))
            def mcp(verb, args):
                return request('/mcp', dict(jsonrpc='2.0', id=1, method='tools/call',
                    params=dict(name='wake_flows_' + verb, arguments=args)))
            try:
                definition = dict(id='fixture', version=1, entry='done', nodes=[dict(id='done', type='end', value='retained')])
                self.assertEqual(api('publish', dict(definition=definition))[0], 200)
                status, started = mcp('start', dict(flow_id='fixture', version=1, inputs={}, intent='one', binding='original'))
                self.assertEqual(status, 200)
                run = started['result']['structuredContent']['result']
                status, advanced = api('advance', dict(run_id=run['run_id']))
                self.assertEqual((status, advanced['result']['phase'], advanced['result']['result']), (200, 'completed', 'retained'))
                inspected = mcp('inspect', dict(run_id=run['run_id']))[1]['result']['structuredContent']['result']
                self.assertEqual(inspected, advanced['result'])
                import subprocess
                import sys
                token_file = root / 'token'
                token_file.write_text(token)
                token_file.chmod(0o600)
                remote = subprocess.run([sys.executable, '-m', 'codex_wake.cli', 'controller', 'remote',
                    '--endpoint', 'http://127.0.0.1:' + str(server.server_port), '--token-file', str(token_file),
                    'flows.inspect', '--arguments', json.dumps(dict(run_id=run['run_id']))],
                    text=True, capture_output=True)
                self.assertEqual(remote.returncode, 0, remote.stderr + remote.stdout)
                self.assertEqual(json.loads(remote.stdout)['result'], advanced['result'])
                changed = dict(definition, version=2)
                changed['nodes'] = [dict(id='done', type='end', value='future')]
                self.assertEqual(api('publish', dict(definition=changed))[0], 200)
                self.assertEqual(api('inspect', dict(run_id=run['run_id']))[1]['result']['result'], 'retained')
                auth.revoke_grant(auth.authenticate(token).grant_id)
                self.assertEqual(api('advance', dict(run_id=run['run_id']))[0], 401)
            finally:
                server.shutdown(); server.server_close(); thread.join()
