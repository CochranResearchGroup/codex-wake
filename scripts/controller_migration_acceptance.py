#!/usr/bin/env python3
"""Installed migration qualification, confined to disposable synthetic stores."""
import argparse
import base64
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import codex_wake
from codex_wake.controller_accounts import ControllerAccounts
from codex_wake.controller_auth import OAuthAuthority
from codex_wake.controller_http import ControllerHTTPServer
from codex_wake.controller_operations import ControllerOperations
from codex_wake.managed_inventory import ManagedInventory
from codex_wake.mcp_server import CommandRunner
from codex_wake.migration_commands import owner_from_root

parser = argparse.ArgumentParser()
parser.add_argument('--bin-dir', type=Path, required=True)
args = parser.parse_args()
assert str(codex_wake.__file__).startswith(str(args.bin_dir.parent / 'lib')), codex_wake.__file__
# Fixture code only; product imports and subprocess entrypoints use the wheel.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
fixture_module = importlib.import_module('tests.test_controller_migration')
fixture_class = fixture_module.ControllerMigrationTests
fixture = fixture_class('test_apply_and_rollback_preserve_native_credential_inode_and_original_shared_store')
fixture.setUp()
try:
    root = fixture.root
    fixture.path.write_text(fixture.path.read_text().replace('known_profiles=["alice"]', 'known_profiles=["alice"]\nshared_dir_name="common"'))
    (fixture.accounts / 'common').mkdir()
    (fixture.accounts / 'common' / '.current-profile').write_text('codex-alice\n')
    fixture.path.write_text(fixture.path.read_text() + '\n[history]\nreadable_accounts=["alice"]\n[configuration.base]\nmodel="qualified-fixture-policy"\n')
    def clear_witness(unused):
        return dict(status='complete', writers=[], coverage='controlled_disposable_fixture')
    owner = owner_from_root(root, writer_probe=clear_witness)
    scope = owner.scope_target()
    preserved_state = fixture.home / 'wake' / 'objective-ledgers' / 'prior.json'
    preserved_state.parent.mkdir(parents=True)
    preserved_state.write_bytes(b'{"used":93,"original_deadline":1800000010,"unknown":true}')
    accounting_before = preserved_state.read_bytes()
    preserved_authority = fixture.home / 'wake' / 'authority.json'
    preserved_authority.write_bytes(b'{"scope":"original","pending":"unknown"}')
    authority_before = preserved_authority.read_bytes()
    local = dict(subject='fixture-migration-operator', client_id='fixture-local-client', grant_id='fixture-local-grant',
        issuer='https://fixture.local', resource='https://fixture.local/mcp',
        scopes=['migration.observe', 'admin', 'observe'], targets=[scope], expires_at=time.time() + 3600)
    host_config = root / 'controller-messaging.json'
    host_config.write_text(json.dumps(dict(version=1, local_caller=local)))
    host_config.chmod(0o600)
    os_home = root / 'os-home'
    os_home.mkdir(mode=0o700)
    env = dict(PATH=str(args.bin_dir) + ':' + os.environ.get('PATH', '/usr/bin:/bin'),
        HOME=str(os_home), LANG='C.UTF-8')
    if os.environ.get('WSL_DISTRO_NAME'):
        env['WSL_DISTRO_NAME'] = os.environ['WSL_DISTRO_NAME']
    def binary(name, *command):
        result = subprocess.run([str(args.bin_dir / name), *command], cwd=root,
            env=env, text=True, capture_output=True, timeout=15)
        assert result.returncode == 0, result.stderr + result.stdout
        return json.loads(result.stdout)
    def cli(*command):
        return binary('codex-wake', *command)
    def normal_consumers(expected_home):
        listed = cli('--wake-root', str(root), 'accounts', 'list', '--json')
        assert listed['result']['accounts'][0]['home'] == str(expected_home)
        assert (expected_home / 'wake' / 'objective-ledgers' / 'prior.json').read_bytes() == accounting_before
        assert (expected_home / 'wake' / 'authority.json').read_bytes() == authority_before
        explained = cli('--wake-root', str(root), 'configuration', 'explain', 'alice', '--json')
        assert explained['result']['effective']['model'] == 'qualified-fixture-policy'
        history = cli('--wake-root', str(root), 'history', 'read', fixture_module.THREAD, '--owner', 'alice', '--json')
        assert history['result']['session']['target']['home'] == str(expected_home)
        legacy = binary('codex-profiles', '--config', str(fixture.path), 'inspect', 'alice', '--json')
        assert legacy['account_root'] == str(expected_home)
        selected = binary('codex-profiles', '--config', str(fixture.path), 'inspect', '--json')
        assert selected['account_root'] == str(expected_home)
        unified = cli('profiles', '--config', str(fixture.path), 'inspect', 'alice', '--json')
        assert unified['account_root'] == str(expected_home)
        return explained['result']['account']['target']
    normal_preview = cli('--wake-root', str(root), 'migration', 'preview', '--json')
    assert normal_preview['result']['production_effect_status'] == 'not_authorized'
    normal_mcp, failed = CommandRunner(wake_root=root).call('wake_controller_migration_preview', {})
    assert not failed, normal_mcp
    for key in ('accounts', 'links', 'plan', 'history', 'phase', 'production_effect_status', 'production_gate'):
        assert normal_mcp['result'][key] == normal_preview['result'][key], key
    # Census observations are independently fresh. Their unknown/positive
    # findings and plan revisions need not match across two real process scans.
    assert {key: value for key, value in normal_mcp['result']['target'].items() if key != 'migration_revision'} == scope
    # A real writable FD is positive evidence even when other host coverage is
    # unknown. No host process identities or paths enter the curated receipt.
    writer = subprocess.Popen([str(args.bin_dir / 'python'), '-c',
        'import sys; f=open(sys.argv[1],"r+"); print("ready",flush=True); sys.stdin.readline()',
        str(fixture.source / 'config.toml')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert writer.stdout.readline().strip() == 'ready'
        held = cli('--wake-root', str(root), 'migration', 'preview', '--json')['result']
        assert 'competing_writer' in held['holds']
    finally:
        writer.communicate('stop\n', timeout=5)
    authority = OAuthAuthority(root / 'oauth.sqlite', issuer='https://fixture.oauth', resource='https://fixture.oauth/mcp')
    def grant(scopes, target=scope):
        client = authority.register({'redirect_uris': ['http://localhost/callback']})
        verifier = 'x' * 43
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        code = authority.authorize(subject='fixture-admin', principal_kind='service', client_id=client['client_id'],
            redirect_uri=client['redirect_uris'][0], resource=authority.resource, scopes=scopes,
            targets=[target], code_challenge=challenge)
        return authority.token(dict(grant_type='authorization_code', client_id=client['client_id'], code=code,
            redirect_uri=client['redirect_uris'][0], code_verifier=verifier, resource=authority.resource))['access_token']
    token, readonly = grant(['migration.observe', 'admin', 'observe']), grant(['migration.observe'])
    token_file = root / 'caller.token'
    token_file.write_text(token)
    token_file.chmod(0o600)
    service = ControllerOperations(ManagedInventory(root), host=socket.gethostname(),
        environment=os.environ.get('WSL_DISTRO_NAME') or os.name,
        accounts=ControllerAccounts(fixture.path, host=socket.gethostname(), environment=os.environ.get('WSL_DISTRO_NAME') or os.name), migration=owner)
    server = ControllerHTTPServer(('127.0.0.1', 0), authority, service)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    endpoint = 'http://127.0.0.1:' + str(server.server_port)
    def post(path, body, bearer=token):
        request = Request(endpoint + path, data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + bearer})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)
    def api(operation, arguments):
        status, value = post('/operations', {'operation': operation, 'arguments': arguments})
        assert status == 200, (status, value)
        return value
    def mcp(operation, arguments):
        status, value = post('/mcp', {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'wake_controller_' + operation.replace('.', '_'), 'arguments': arguments}})
        assert status == 200 and not value['result']['isError'], value
        return value['result']['structuredContent']
    def remote(operation, arguments):
        return cli('controller', 'remote', '--endpoint', endpoint, '--token-file', str(token_file),
                   operation, '--arguments', json.dumps(arguments))
    def request(target, label, **extra):
        return dict(extra, expected_target=target, _request=dict(operation_id=label, idempotency_key=label,
            correlation_id='correlation-' + label, binding='fixture-operator', target=target))
    original_account_target = normal_consumers(fixture.home)
    old_account_token = grant(['account.observe', 'configuration.observe', 'history.observe'], original_account_target)
    auth_inode = (fixture.home / 'auth.json').stat().st_ino
    shared = (fixture.source / 'config.toml').read_bytes()
    unassigned = (fixture.source / 'sessions' / 'unassigned.jsonl').read_bytes()
    try:
        preview = api('migration.preview', {})
        assert preview['result']['status'] == 'ready'
        assert mcp('migration.preview', {}) == preview
        assert remote('migration.preview', {}) == preview
        status, tools = post('/mcp', {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
        assert status == 200 and 'wake_controller_migration_apply' in {tool['name'] for tool in tools['result']['tools']}
        denied_args = request(preview['result']['target'], 'readonly-denied')
        status, _ = post('/operations', {'operation': 'migration.apply', 'arguments': denied_args}, readonly)
        assert status == 403 and not (fixture.lab / 'candidate').exists()
        # Real effects through each capable transport, all with the SAME token.
        for number, (apply_call, rollback_call) in enumerate(((remote, api), (mcp, remote), (api, mcp)), 1):
            current = api('migration.preview', {})['result']['target']
            apply_args = request(current, 'apply-' + str(number))
            record = apply_call('migration.apply', apply_args)['result']['operation']
            assert record['execution'] == 'completed', record
            applied = record['result']
            assert applied['status'] == 'applied'
            assert mcp('migration.apply', apply_args)['result']['operation']['operation_id'] == record['operation_id']
            candidate_home = fixture.lab / 'candidate' / 'accounts' / 'codex-alice'
            assert (candidate_home / 'auth.json').stat().st_ino == auth_inode
            current_account = normal_consumers(candidate_home)
            status, _ = post('/operations', {'operation': 'accounts.resolve', 'arguments': {'selector': 'alice'}}, old_account_token)
            assert status == 403
            new_account_token = grant(['account.observe', 'configuration.observe', 'history.observe'], current_account)
            status, account_view = post('/operations', {'operation': 'accounts.resolve', 'arguments': {'selector': 'alice'}}, new_account_token)
            assert status == 200 and account_view['result']['account']['home'] == str(candidate_home)
            assert (fixture.source / 'config.toml').read_bytes() == shared
            assert (fixture.source / 'sessions' / 'unassigned.jsonl').read_bytes() == unassigned
            rolled = rollback_call('migration.rollback', request(applied['target'], 'rollback-' + str(number),
                receipt_id=applied['receipt_id']))['result']['operation']
            assert rolled['execution'] == 'completed' and rolled['result']['status'] == 'rolled_back', rolled
            assert (fixture.home / 'auth.json').stat().st_ino == auth_inode
            assert fixture.pointer.resolve() == fixture.legacy
            normal_consumers(fixture.home)
        native = CommandRunner(wake_root=root, migration_writer_probe=clear_witness)
        native_preview, failed = native.call('wake_controller_migration_preview', {})
        assert not failed and native_preview['result']['status'] == 'ready'
        native_applied, failed = native.call('wake_controller_migration_apply',
            request(native_preview['result']['target'], 'native-apply'))
        assert not failed and native_applied['result']['operation']['execution'] == 'completed', native_applied
        native_result = native_applied['result']['operation']['result']
        normal_consumers(fixture.lab / 'candidate' / 'accounts' / 'codex-alice')
        native_rolled, failed = native.call('wake_controller_migration_rollback',
            request(native_result['target'], 'native-rollback', receipt_id=native_result['receipt_id']))
        assert not failed and native_rolled['result']['operation']['result']['status'] == 'rolled_back', native_rolled
        normal_consumers(fixture.home)
        # Post-cutover work refuses rollback even with a freshly pinned target.
        current = api('migration.preview', {})['result']['target']
        applied = api('migration.apply', request(current, 'changed-apply'))['result']['operation']['result']
        note = fixture.lab / 'candidate' / 'accounts' / 'codex-alice' / 'new-work'
        note.write_text('preserve post-cutover work')
        changed = api('migration.preview', {})['result']['target']
        refused = api('migration.rollback', request(changed, 'changed-refusal', receipt_id=applied['receipt_id']))['result']['operation']
        assert refused['execution'] == 'unknown' and refused['reason'] == 'target_changed'
        assert note.read_text() == 'preserve post-cutover work'
        authority.revoke_grant(authority.authenticate(token).grant_id)
        status, _ = post('/operations', {'operation': 'migration.preview', 'arguments': {}})
        assert status == 401
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    print(json.dumps(dict(status='passed', installed_module=str(codex_wake.__file__),
        normal_host_writer_status=normal_preview['result']['writers']['status'], real_writer_detected=True,
        controlled_fixture_writer_witness='trusted host injection, no client bypass',
        api_oauth_mcp_remote_cli_preview_parity=True, same_grant_apply_rollback_cycles=3,
        actual_transport_effects=['remote_cli', 'api', 'oauth_mcp', 'native_mcp'], replay_suppressed=True,
        changed_rollback_preserved=True, credential_inode_preserved=True, credential_copy=False,
        original_shared_store_preserved=True, unassigned_history_not_copied=True,
        original_accounting_and_authority_bytes_preserved=True,
        normal_account_config_history_profile_consumers=True, selected_account_preserved=True, old_account_grants_not_transferred=True,
        production_activation=False, production_gate='issue380', provider_calls=0)))
finally:
    fixture.doCleanups()
