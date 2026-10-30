#!/usr/bin/env python3
"""Installed, synthetic-only OAuth/API/MCP acceptance; no shared services.

Run with the disposable candidate Python, e.g. candidate/bin/python this-script.
The only credential is generated in this script's private temporary Wake root.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


def main():
    import codex_wake
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    with tempfile.TemporaryDirectory(prefix='wake-oauth-399-') as directory:
        root = Path(directory) / 'wake'
        sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]; sock.close()
        base = f'http://127.0.0.1:{port}'
        resource = base + '/controller'
        def cli(*args, expected=0):
            result = subprocess.run([str(Path(sys.executable).parent / 'codex-wake'), '--wake-root', str(root), 'controller', *args], env=env, cwd=directory, text=True, capture_output=True, timeout=20)
            assert result.returncode == expected, (result.returncode, result.stdout, result.stderr)
            return json.loads(result.stdout)
        configured = cli('auth-configure', '--issuer', base, '--resource', resource, '--owner', 'synthetic-owner')
        assert configured['activated'] is False
        from codex_wake.managed_inventory import ManagedInventory, Observation
        inventory = ManagedInventory(root)
        for account in ('alice', 'bob'):
            inventory.enroll(Observation('codex', 'account:' + account, 'synthetic-' + account, '/synthetic', 'ready', time.time(), 'native_metadata', {'pid': 123, 'start_ticks': 42, 'boot_id': 'synthetic'}, [], {}), operator=True)
        process = subprocess.Popen([str(Path(sys.executable).parent / 'codex-wake'), '--wake-root', str(root), 'controller', 'serve', '--port', str(port)], env=env, cwd=directory, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        opener = build_opener(NoRedirect)
        def http(path, body=None, token=None, form=False):
            headers = {}
            if token: headers['Authorization'] = 'Bearer ' + token
            if body is not None:
                headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
                body = (urlencode(body) if form else json.dumps(body)).encode()
            try:
                with opener.open(Request(base + path, data=body, headers=headers), timeout=5) as response:
                    return response.status, dict(response.headers), response.read()
            except HTTPError as error: return error.code, dict(error.headers), error.read()
        try:
            for _ in range(100):
                try: status, _, raw = http('/.well-known/oauth-authorization-server'); break
                except OSError: time.sleep(.02)
            else: raise AssertionError('listener did not start')
            assert status == 200 and json.loads(raw)['issuer'] == base
            assert json.loads(http('/.well-known/oauth-protected-resource')[2])['resource'] == resource
            assert http('/operations', {'operation': 'inventory.list', 'arguments': {}})[0] == 401
            client = json.loads(http('/register', {'redirect_uris': ['http://127.0.0.1:45000/callback'], 'client_name': 'synthetic-consumer'})[2])
            verifier = 'x' * 43
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            authorization = dict(response_type='code', client_id=client['client_id'], redirect_uri=client['redirect_uris'][0], resource=resource, scope='observe', targets=json.dumps([{'host': socket.gethostname(), 'namespace': 'account:alice'}]), code_challenge_method='S256', code_challenge=challenge, state='synthetic-state')
            assert http('/authorize?' + urlencode(authorization))[0] == 200
            assert http('/authorize', dict(authorization, consent_secret='wrong'), form=True)[0] == 400
            secret = (root / 'controller-auth' / 'consent.secret').read_text()
            status, headers, _ = http('/authorize', dict(authorization, consent_secret=secret), form=True)
            assert status == 303
            callback = parse_qs(urlsplit(headers['Location']).query)
            assert callback['state'] == ['synthetic-state']
            exchange = dict(grant_type='authorization_code', client_id=client['client_id'], code=callback['code'][0], redirect_uri=client['redirect_uris'][0], code_verifier=verifier, resource=resource)
            assert http('/token', dict(exchange, resource=resource + '/other'), form=True)[0] == 400
            tokens = json.loads(http('/token', exchange, form=True)[2])
            assert http('/token', exchange, form=True)[0] == 400
            token = tokens['access_token']
            operation = dict(operation='inventory.list', arguments={})
            api = json.loads(http('/operations', operation, token)[2])
            assert [row['target']['namespace'] for row in api['result']['resources']] == ['account:alice']
            assert api['actor']['subject'] == 'synthetic-owner'
            def canonical(value):
                value = json.loads(json.dumps(value))
                for row in value['result']['resources']: row['observation'].pop('age_seconds')
                return value
            grant = api['actor']['grant_id']
            token_file = Path(directory) / 'caller.token'; token_file.write_text(token); token_file.chmod(0o600)
            assert canonical(cli('remote', '--endpoint', base, '--token-file', str(token_file), 'inventory.list')) == canonical(api)
            initialization = json.loads(http('/mcp', dict(jsonrpc='2.0', id=1, method='initialize', params={'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'fixture', 'version': '1'}}), token)[2])
            assert initialization['result']['capabilities']['tools'] == {'listChanged': False}
            assert http('/mcp', dict(jsonrpc='2.0', method='notifications/initialized'), token)[0] == 202
            tools = json.loads(http('/mcp', dict(jsonrpc='2.0', id=2, method='tools/list'), token)[2])
            assert len(tools['result']['tools']) == 2
            call = dict(jsonrpc='2.0', id=3, method='tools/call', params={'name': 'wake_controller_list', 'arguments': {}})
            assert canonical(json.loads(http('/mcp', call, token)[2])['result']['structuredContent']) == canonical(api)
            assert http('/operations', dict(operation='runtime.input', arguments={}), token)[0] == 403
            assert http('/operations', dict(operation='unknown', arguments={}), token)[0] == 400
            refresh = dict(grant_type='refresh_token', client_id=client['client_id'], refresh_token=tokens['refresh_token'], resource=resource)
            rotated = json.loads(http('/token', refresh, form=True)[2])
            assert http('/mcp', call, token)[0] == 401
            assert json.loads(http('/mcp', call, rotated['access_token'])[2])['result']['structuredContent']['actor']['grant_id'] == grant
            service_code = cli('authorize-client', '--client-id', client['client_id'], '--redirect-uri', client['redirect_uris'][0], '--subject', 'synthetic-service', '--principal-kind', 'service', '--scope', 'observe', '--targets', json.dumps([{'host': socket.gethostname(), 'namespace': 'account:bob'}]), '--code-challenge', challenge)['code']
            service_token = json.loads(http('/token', dict(exchange, code=service_code), form=True)[2])['access_token']
            service_api = json.loads(http('/operations', operation, service_token)[2])
            assert service_api['actor']['principal_kind'] == 'service'
            assert service_api['actor']['subject'] == 'synthetic-service'
            assert [row['target']['namespace'] for row in service_api['result']['resources']] == ['account:bob']
            # Listener crash/reconnect retains credentials/grants but creates no new work.
            process.terminate(); process.wait(timeout=5)
            process = subprocess.Popen([str(Path(sys.executable).parent / 'codex-wake'), '--wake-root', str(root), 'controller', 'serve', '--port', str(port)], env=env, cwd=directory, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            for _ in range(100):
                try:
                    status, _, _ = http('/mcp', call, rotated['access_token'])
                    if status == 200: break
                except OSError: pass
                time.sleep(.02)
            else: raise AssertionError('reconnect did not recover')
            revoked = cli('revoke-grant', grant)
            assert revoked['cancellation'] == 'no_owned_active_work' and revoked['uncertain_effects'] == []
            assert http('/mcp', call, rotated['access_token'])[0] == 401
            assert http('/operations', operation, rotated['access_token'])[0] == 401
            assert http('/operations', operation, service_token)[0] == 200
            print(json.dumps(dict(status='passed', package=codex_wake.__file__, python=sys.executable,
                checks=['installed CLI configure/serve/remote/revoke', 'HTTP discovery/DCR/operator consent/S256/token', 'exact audience and one-use code', 'OAuth MCP initialize/list/call equals API and CLI', 'scope separation', 'rotation and crash/reconnect reauthentication', 'persistent grant revocation, no active read-only work'],
                source_sha256={name: hashlib.sha256((Path(codex_wake.__file__).parent / name).read_bytes()).hexdigest() for name in ('controller_auth.py', 'controller_http.py', 'controller_remote_commands.py', 'controller_commands.py')},
                production_effects=False, provider_credentials=False), sort_keys=True))
        finally:
            process.terminate(); process.wait(timeout=5)


if __name__ == '__main__': main()
