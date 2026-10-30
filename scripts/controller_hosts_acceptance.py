#!/usr/bin/env python3
"""Installed synthetic SSH-shaped transport qualification, not a real SSH/OS matrix."""
import hashlib
import base64
import socket
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def main():
    import codex_wake
    from codex_wake.managed_inventory import ManagedInventory, Observation
    env = dict(os.environ); env.pop('PYTHONPATH', None)
    with tempfile.TemporaryDirectory(prefix='wake-host400-') as directory:
        base = Path(directory)
        source, remote = base / 'source', base / 'remote'
        def cli(root, *args, expected=0):
            result = subprocess.run([str(Path(sys.executable).parent / 'codex-wake'), '--wake-root', str(root), 'hosts', *args], env=env, cwd=base, text=True, capture_output=True, timeout=20)
            assert result.returncode == expected, (result.returncode, result.stdout, result.stderr)
            return json.loads(result.stdout)
        destination = cli(remote, 'register', 'synthetic-host', 'synthetic-wsl', '--kind', 'wsl', '--authority', 'synthetic-authority', '--destination', 'synthetic-fixture')['result']['environment']
        target = destination['target']
        inventory = ManagedInventory(remote)
        for account in ('alice', 'bob'):
            inventory.enroll(Observation('codex', 'account:' + account, account, '/synthetic', 'ready', time.time(), 'native_metadata', {'pid': 123, 'start_ticks': 42, 'boot_id': 'synthetic'}, [], {}), operator=True)
        mapping = cli(remote, 'map-principal', 'fixed-key', '--subject', 'synthetic-service', '--scope', 'observe', '--targets', json.dumps([{'host': target['host'], 'environment': target['environment'], 'namespace': 'account:alice'}]), '--expires-at', str(time.time() + 600))
        assert mapping['result']['subject'] == 'synthetic-service'
        log, mode = base / 'fixture.calls', base / 'fixture.mode'
        mode.write_text('normal')
        fixture = base / 'synthetic-ssh'
        fixture.write_text('#!' + sys.executable + '\n' + '''import json, os, pathlib, shlex, subprocess, sys
assert sys.argv[1:6] == ['-T', '-oBatchMode=yes', '-oConnectTimeout=5', '-oStrictHostKeyChecking=yes', '--']
assert sys.argv[-2] == 'synthetic-fixture'
with open(''' + repr(str(log)) + ''', 'a') as stream: stream.write('synthetic SSH-shaped subprocess\\n')
mode = pathlib.Path(''' + repr(str(mode)) + ''').read_text()
result = subprocess.run(shlex.split(sys.argv[-1]), input=sys.stdin.buffer.read(65537), capture_output=True)
if mode == 'disconnect': sys.exit(255)
sys.stdout.buffer.write(result.stdout)
sys.exit(result.returncode)
''')
        fixture.chmod(0o700)
        receiver_command = shlex.join([str(Path(sys.executable).parent / 'codex-wake'), '--wake-root', str(remote), 'hosts', 'ssh-serve', '--principal-id', 'fixed-key', '--target', json.dumps(target)])
        source_row = cli(source, 'register', target['host'], target['environment'], '--kind', 'wsl', '--authority', target['authority'], '--generation=' + target['generation'], '--destination', 'synthetic-fixture', '--ssh-executable', str(fixture), '--command', receiver_command)['result']['environment']
        assert source_row['target'] == target
        windows = cli(source, 'register', target['host'], 'synthetic-windows', '--kind', 'windows', '--authority', 'synthetic-windows-authority', '--destination', 'synthetic-fixture')['result']['environment']
        fleet = cli(source, 'list')['result']['environments']
        assert len(fleet) == 2 and {r['kind'] for r in fleet} == {'windows', 'wsl'}
        def route(key, operation='inventory.list', pinned=target, expected=0):
            return cli(source, 'route', '--target', json.dumps(pinned), '--operation', operation, '--operation-id', 'operation-' + key, '--idempotency-key', key, expected=expected)
        original = route('first')['result']['route']
        assert (original['execution'], original['delivery'], original['effect']) == ('completed', 'received', 'none_read_only')
        result = original['result']
        assert result['actor']['subject'] == 'synthetic-service'
        assert [r['target']['namespace'] for r in result['result']['resources']] == ['account:alice']
        count = len(log.read_text().splitlines())
        assert route('first')['result']['route'] == original
        assert len(log.read_text().splitlines()) == count
        assert route('bad-mutation', 'runtime.input', expected=2)['error']['code'] == 'unsupported_operation'
        assert route('stale', pinned=dict(target, generation='replaced-generation'), expected=2)['error']['code'] == 'stale_target'
        assert len(log.read_text().splitlines()) == count
        mode.write_text('disconnect')
        uncertain = route('disconnect')['result']['route']
        assert uncertain['execution'] == 'unknown' and uncertain['delivery'] == 'uncertain'
        count = len(log.read_text().splitlines())
        mode.write_text('normal')
        # New CLI processes are the restart/reconnect boundary; durable admission
        # returns the original uncertain result without executing the transport.
        assert route('disconnect')['result']['route'] == uncertain
        assert len(log.read_text().splitlines()) == count
        cli(source, 'observe', '--target', json.dumps(target), '--online', 'false')
        assert route('offline', expected=2)['error']['code'] == 'offline_target'
        assert len(log.read_text().splitlines()) == count
        cli(source, 'observe', '--target', json.dumps(target), '--online', 'true')
        qualify_public_surfaces(source, target, env, base, log)
        cli(remote, 'revoke-principal', 'fixed-key')
        denied = route('revoked')['result']['route']
        assert denied['execution'] == 'failed' and denied['result']['error']['code'] == 'invalid_token'
        print(json.dumps(dict(status='passed', package=codex_wake.__file__, python=sys.executable, source_ref='07c396827e0824ff974aadd39d3ac7d2a02bde43', mcp_dependency=__import__('importlib.metadata', fromlist=['version']).version('mcp'),
            command=[str(Path(sys.executable).parent / 'codex-wake'), '--wake-root', '<private-disposable-root>', 'hosts'],
            transport='synthetic executable emulating OpenSSH argv and invoking the installed fixed-principal receiver; no SSH server or real Windows/WSL host',
            checks=['separate host/environment/authority IDs', 'explicit imported authority generation', 'installed mapped-principal read and target filtering', 'durable same-key delivery without replay', 'unsupported mutation and stale generation before transport', 'uncertain disconnect/restart without replay', 'offline refusal without queue', 'revoked SSH mapping refuses read', 'actual installed shared CLI', 'actual installed stdio MCP list/resolve', 'OAuth API/remote CLI/MCP list/resolve/route', 'exact scoped fleet filtering and route attenuation', 'OAuth grant revocation on API/MCP'],
            source_sha256={name: hashlib.sha256((Path(codex_wake.__file__).parent / name).read_bytes()).hexdigest() for name in ('controller_hosts.py', 'host_commands.py', 'controller_http.py', 'controller_operations.py', 'mcp_server.py', 'cli.py')},
            production_effects=False, provider_credentials=False, real_crossplatform_matrix=False), sort_keys=True))


def qualify_public_surfaces(source, target, env, base, log):
    import asyncio
    executable = str(Path(sys.executable).parent / 'codex-wake')
    def controller(*args):
        result = subprocess.run([executable, '--wake-root', str(source), 'controller', *args], env=env, cwd=base, text=True, capture_output=True, timeout=20)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
        return json.loads(result.stdout)
    async def stdio_reads():
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        parameters = StdioServerParameters(command=str(Path(sys.executable).parent / 'codex-wake-mcp'), args=['--wake-root', str(source)], env=env)
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = {item.name for item in (await session.list_tools()).tools}
                assert {'wake_hosts_list', 'wake_hosts_resolve'} <= tools
                assert 'wake_hosts_route' not in tools  # No mapped native caller identity for routed work.
                listed = await session.call_tool('wake_hosts_list', {})
                listing = json.loads(listed.content[0].text)
                assert not listed.is_error and len(listing['result']['environments']) == 2
                resolved = await session.call_tool('wake_hosts_resolve', dict(host=target['host'], environment=target['environment'], expected_target=target))
                value = json.loads(resolved.content[0].text)
                assert not resolved.is_error and value['result']['environment']['target'] == target
    asyncio.run(stdio_reads())
    sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]; sock.close()
    endpoint = 'http://127.0.0.1:' + str(port)
    resource = endpoint + '/controller'
    controller('auth-configure', '--issuer', endpoint, '--resource', resource, '--owner', 'synthetic-owner')
    server = subprocess.Popen([executable, '--wake-root', str(source), 'controller', 'serve', '--port', str(port)], env=env, cwd=base, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    def http(path, body=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token: headers['Authorization'] = 'Bearer ' + token
        request = Request(endpoint + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            with urlopen(request, timeout=15) as response: return response.status, json.load(response)
        except HTTPError as error: return error.code, json.load(error)
    try:
        for _ in range(100):
            try:
                if http('/.well-known/oauth-protected-resource')[0] == 200: break
            except OSError: pass
            time.sleep(.02)
        else: raise AssertionError('public listener not ready')
        client = http('/register', {'redirect_uris': ['http://127.0.0.1:45000/callback']})[1]
        verifier = 'x' * 43
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        def token_for(scopes):
            code = controller('authorize-client', '--client-id=' + client['client_id'], '--redirect-uri', client['redirect_uris'][0], '--subject', 'synthetic-client', '--principal-kind', 'service', '--scope', 'observe', '--targets', json.dumps(scopes), '--code-challenge', challenge)['code']
            status, tokens = http('/token', dict(grant_type='authorization_code', client_id=client['client_id'], redirect_uri=client['redirect_uris'][0], code=code, code_verifier=verifier, resource=resource))
            assert status == 200
            return tokens['access_token']
        token = token_for([target])
        def api(operation, arguments, bearer=token): return http('/operations', dict(operation=operation, arguments=arguments), bearer)
        status, listing = api('hosts.list', {})
        assert status == 200 and [r['target'] for r in listing['result']['environments']] == [target]
        status, resolved = api('hosts.resolve', dict(host=target['host'], environment=target['environment'], expected_target=target))
        assert status == 200 and resolved['result']['environment']['target'] == target
        initialized = http('/mcp', dict(jsonrpc='2.0', id=1, method='initialize', params={'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'synthetic', 'version': '1'}}), token)
        assert initialized[0] == 200
        tools = http('/mcp', dict(jsonrpc='2.0', id=2, method='tools/list'), token)[1]['result']['tools']
        assert {'wake_hosts_list', 'wake_hosts_resolve', 'wake_hosts_route'} <= {t['name'] for t in tools}
        def mcp(name, arguments):
            status, result = http('/mcp', dict(jsonrpc='2.0', id=3, method='tools/call', params={'name': name, 'arguments': arguments}), token)
            assert status == 200 and not result['result']['isError'], result
            return result['result']['structuredContent']
        assert [r['target'] for r in mcp('wake_hosts_list', {})['result']['environments']] == [target]
        assert mcp('wake_hosts_resolve', dict(host=target['host'], environment=target['environment']))['result']['environment']['target'] == target
        route_args = dict(target=target, operation='inventory.list', arguments={}, operation_id='public-api-operation', idempotency_key='public-api-key')
        before_routing = len(log.read_text().splitlines())
        status, routed = api('hosts.route', route_args)
        assert status == 200 and routed['result']['route']['execution'] == 'completed', routed
        remote_rows = routed['result']['route']['result']['result']['resources']
        assert [r['target']['namespace'] for r in remote_rows] == ['account:alice']
        assert mcp('wake_hosts_route', route_args)['result']['route'] == routed['result']['route']
        private_token = base / 'oauth.token'; private_token.write_text(token); private_token.chmod(0o600)
        cli_route = controller('remote', '--endpoint', endpoint, '--token-file', str(private_token), 'hosts.route', '--arguments', json.dumps(route_args))
        assert cli_route['result']['route'] == routed['result']['route']
        assert len(log.read_text().splitlines()) == before_routing + 1
        broad = token_for([{'host': target['host'], 'environment': target['environment']}])
        status, rejected = api('hosts.route', dict(route_args, operation_id='broad-operation', idempotency_key='broad-key'), broad)
        assert status == 400 and rejected['error']['code'] == 'unauthorized_target', rejected
        assert len(log.read_text().splitlines()) == before_routing + 1
        narrowed = token_for([dict(target, namespace='account:bob')])
        status, rejected = api('hosts.route', dict(route_args, operation_id='narrow-operation', idempotency_key='narrow-key'), narrowed)
        assert status == 200 and rejected['result']['route']['execution'] == 'failed'
        assert rejected['result']['route']['result']['error']['code'] == 'insufficient_scope'
        controller('revoke-grant', '--', listing['actor']['grant_id'])
        assert api('hosts.list', {})[0] == 401
        assert http('/mcp', dict(jsonrpc='2.0', id=4, method='tools/list'), token)[0] == 401
    finally:
        server.terminate(); server.wait(timeout=5)


if __name__ == '__main__': main()
