#!/usr/bin/env python3
"""Installed provider-free history acceptance, using disposable native fixtures."""
import argparse
import base64
import hashlib
import io
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import codex_wake
from codex_wake.controller_accounts import ControllerAccounts
from codex_wake.controller_auth import OAuthAuthority
from codex_wake.controller_http import ControllerHTTPServer
from codex_wake.controller_operations import ControllerOperations
from codex_wake.managed_inventory import ManagedInventory
from codex_wake.mcp_server import CommandRunner

parser = argparse.ArgumentParser()
parser.add_argument('--bin-dir', type=Path, required=True)
args = parser.parse_args()
assert str(codex_wake.__file__).startswith(str(args.bin_dir.parent / 'lib')), codex_wake.__file__
# Only fixture code is imported from the source tree; product imports above and
# all child executable paths resolve to the disposable installed distribution.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
history_fixture = importlib.import_module('tests.test_controller_history')
ControllerHistoryTests, THREAD = history_fixture.ControllerHistoryTests, history_fixture.THREAD
HistoryAuthorizationTests = importlib.import_module('tests.test_controller_history_authorization').HistoryAuthorizationTests

fixture = ControllerHistoryTests(methodName='test_search_and_read_keep_duplicate_ids_bound_to_their_permitted_owner')
fixture.setUp()
try:
    root = fixture.root
    fixture.path.write_text(fixture.path.read_text() + f'\n[history.callers]\n"{THREAD}"=["alice"]\n')
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    def invoke(*command):
        result = subprocess.run([str(args.bin_dir / command[0]), *command[1:]], env=env,
            cwd=root, text=True, capture_output=True, timeout=10)
        assert result.returncode == 0, result.stderr + result.stdout
        return json.loads(result.stdout)
    found = invoke('codex-wake', '--wake-root', str(root), 'history', 'search', '--query', 'report', '--json')
    assert [row['owner'] for row in found['result']['sessions']] == ['codex-alice', 'codex-bob']
    cli = invoke('codex-wake', '--wake-root', str(root), 'history', 'read', THREAD, '--owner', 'alice', '--json')
    context = dict(threadId=THREAD, sessionId=THREAD, callId='installed-fixture', **{
        'x-codex-turn-metadata': dict(thread_id=THREAD, session_id=THREAD, turn_id='turn')})
    mcp, failed = CommandRunner(wake_root=root).call('wake_controller_history_read',
        {'caller_thread_id': THREAD, 'owner': 'alice', 'thread_id': THREAD}, native_context=context)
    assert not failed and cli == mcp
    denied, failed = CommandRunner(wake_root=root).call('wake_controller_history_read',
        {'caller_thread_id': THREAD, 'owner': 'bob', 'thread_id': THREAD}, native_context=context)
    assert failed and denied['error']['code'] == 'unauthorized_target'
    authority = OAuthAuthority(root / 'auth.sqlite', issuer='https://wake.fixture', resource='https://wake.fixture/mcp')
    target = ControllerAccounts(fixture.path, host=socket.gethostname(),
        environment=os.environ.get('WSL_DISTRO_NAME') or os.name).execute('accounts.resolve', {'selector': 'alice'})['account']['target']
    client = authority.register({'redirect_uris': ['http://localhost/callback']})
    verifier = 'x' * 43
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    code = authority.authorize(subject='reader', principal_kind='service', client_id=client['client_id'],
        redirect_uri=client['redirect_uris'][0], resource=authority.resource, scopes=['history.observe'],
        targets=[target], code_challenge=challenge)
    token = authority.token(dict(grant_type='authorization_code', client_id=client['client_id'], code=code,
        redirect_uri=client['redirect_uris'][0], code_verifier=verifier, resource=authority.resource))['access_token']
    token_file = root / 'caller.token'
    token_file.write_text(token)
    token_file.chmod(0o600)
    server = ControllerHTTPServer(('127.0.0.1', 0), authority,
        ControllerOperations(ManagedInventory(root), host=socket.gethostname(),
            environment=os.environ.get('WSL_DISTRO_NAME') or os.name,
            accounts=ControllerAccounts(fixture.path, host=socket.gethostname(),
                environment=os.environ.get('WSL_DISTRO_NAME') or os.name)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = 'http://127.0.0.1:' + str(server.server_port)
    def post(path, body):
        request = Request(endpoint + path, data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)
    try:
        status, api = post('/operations', {'operation': 'history.search', 'arguments': {}})
        assert status == 200, (status, api)
        assert [row['owner'] for row in api['result']['sessions']] == ['codex-alice']
        status, tools = post('/mcp', {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
        assert status == 200 and 'wake_controller_history_search' in {row['name'] for row in tools['result']['tools']}
        status, remote_mcp = post('/mcp', {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
            'params': {'name': 'wake_controller_history_search', 'arguments': {}}})
        assert status == 200 and remote_mcp['result']['structuredContent'] == api
        remote_cli = invoke('codex-wake', 'controller', 'remote', '--endpoint', endpoint,
            '--token-file', str(token_file), 'history.search')
        assert remote_cli == api
        status, _ = post('/operations', {'operation': 'history.read', 'arguments': {'owner': 'bob', 'thread_id': THREAD}})
        assert status == 403
        authority.revoke_grant(authority.authenticate(token).grant_id)
        status, _ = post('/operations', {'operation': 'history.search', 'arguments': {}})
        assert status == 401
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
finally:
    fixture.doCleanups()

suite = unittest.TestSuite([
    ControllerHistoryTests('test_resume_uses_existing_permission_and_durable_attachment_owner'),
    HistoryAuthorizationTests('test_resume_requires_independent_host_delegation_and_rechecks_oauth_before_effect'),
])
output = io.StringIO()
result = unittest.TextTestRunner(stream=output).run(suite)
assert result.wasSuccessful(), output.getvalue()
print(json.dumps(dict(status='passed', installed_module=str(codex_wake.__file__),
    cli_mcp_history_parity=True, oauth_api_mcp_remote_cli_parity=True, oauth_resume_api_mcp_remote_cli=True,
    native_unix_resume_adapter_tests=result.testsRun,
    private_attachment_effect_boundary='injected existing SavedRuntime terminal',
    uncertain_reconciliation_no_replay=True, mid_step_revocation_blocks_effect=True,
    accounting_unchanged=True, provider_calls=0, production_activation=False)))
