#!/usr/bin/env python3
"""Disposable WSL/PowerShell CLI, REST and OAuth MCP profile parity. No model calls."""
import argparse
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codex_wake.controller_accounts import ControllerAccounts
from codex_wake.controller_auth import OAuthAuthority
from codex_wake.controller_http import ControllerHTTPServer
from codex_wake.controller_operations import ControllerOperations
from codex_wake.managed_inventory import ManagedInventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--powershell', type=Path)
    parser.add_argument('--receipt', type=Path, required=True)
    options = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    report = dict(schema_version=1, state='running', source_commit=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip(), model_calls=0, source_dirty=bool(subprocess.check_output(['git','status','--porcelain'], cwd=source, text=True).strip()),
        environment='disposable synthetic state; WSL source Python, Windows PowerShell HTTP client',
        powershell='not_run')
    try:
        with tempfile.TemporaryDirectory(prefix='wake-parity-494-') as directory:
            root = Path(directory)
            stock = root / 'stock'
            stock.mkdir(mode=0o700)
            (stock / 'config.toml').write_text('model="synthetic"\n')
            def cli(*args):
                env = dict(os.environ, PYTHONPATH=str(source / 'src'))
                result = subprocess.run([sys.executable, '-m', 'codex_wake.entrypoint', '--wake-root', str(root), *args],
                    env=env, cwd=source, capture_output=True, text=True, timeout=15)
                assert result.returncode == 0, result.stderr + result.stdout
                return json.loads(result.stdout)
            cli('accounts', 'init')
            registered = cli('stores', 'register', 'stock', '--home', str(stock))['result']['store']
            cli('accounts', 'create', 'alice', '--mode', 'independent', '--source', 'stock')
            host, environment = socket.gethostname(), os.environ.get('WSL_DISTRO_NAME') or os.name
            accounts = ControllerAccounts(root / 'controller-accounts.toml', host=host, environment=environment)
            target = dict(host=host, environment=environment,
                **{key: registered[key] for key in ('store_id','home','home_generation')})
            profile = accounts.execute('accounts.resolve', {'selector':'alice'})['account']['target']
            authority = OAuthAuthority(root / 'authority.sqlite', issuer='http://localhost', resource='http://localhost/controller')
            service = ControllerOperations(ManagedInventory(root), host=host, environment=environment, accounts=accounts)
            server = ControllerHTTPServer(('127.0.0.1', 0), authority, service)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            endpoint = 'http://127.0.0.1:' + str(server.server_port)
            try:
                client = authority.register({'redirect_uris':['http://localhost/callback']})
                verifier = 'x' * 43
                challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
                code = authority.authorize(subject='synthetic-parity', principal_kind='owner', client_id=client['client_id'],
                    redirect_uri=client['redirect_uris'][0], resource=authority.resource,
                    scopes=['account.observe','configuration.observe','control'], targets=[target, profile], code_challenge=challenge)
                token = authority.token(dict(grant_type='authorization_code', code=code, code_verifier=verifier,
                    resource=authority.resource, redirect_uri=client['redirect_uris'][0], client_id=client['client_id']))['access_token']
                def post(path, payload):
                    with urlopen(Request(endpoint + path, data=json.dumps(payload).encode(),
                        headers={'Authorization':'Bearer '+token, 'Content-Type':'application/json'}), timeout=10) as response:
                        return json.load(response)
                def mcp(tool, args):
                    value = post('/mcp', dict(jsonrpc='2.0', id=1, method='tools/call', params=dict(name=tool, arguments=args)))
                    assert not value['result']['isError'], value
                    return value['result']['structuredContent']
                local = cli('stores', 'resolve', 'stock')
                payload = dict(operation='stores.resolve', arguments=dict(selector='stock'))
                rest = post('/operations', payload)
                oauth = mcp('wake_controller_store_resolve', payload['arguments'])
                assert local['result'] == rest['result'] == oauth['result']
                args = dict(source='stock', destinations=['alice'], categories=['mcp'], operation_id='acceptance')
                preview = post('/operations', dict(operation='configuration.sync.preview', arguments=args))
                assert preview['result'] == mcp('wake_controller_configuration_sync_preview', args)['result']
                args['expected_snapshot'] = preview['result']['snapshot']
                applied = post('/operations', dict(operation='configuration.sync.apply', arguments=args))
                assert applied['result'] == mcp('wake_controller_configuration_sync_apply', args)['result']
                # Native MCP uses the same scopes through the existing host caller binding.
                actor = authority.authenticate(token)
                (root / 'controller-messaging.json').write_text(json.dumps(dict(version=1,
                    local_caller=dict(subject=actor.subject, client_id=actor.client_id, grant_id=actor.grant_id,
                        issuer=actor.issuer, resource=actor.resource, scopes=sorted(actor.scopes),
                        targets=actor.targets, expires_at=actor.expires_at))))
                async def native_stdio():
                    from mcp import Client, StdioServerParameters
                    parameters = StdioServerParameters(command=sys.executable,
                        args=['-m', 'codex_wake.mcp_server', '--wake-root', str(root)], cwd=source,
                        env=dict(os.environ, PYTHONPATH=str(source / 'src')))
                    async with Client(parameters, mode='legacy') as native:
                        tools = {tool.name for tool in (await native.list_tools()).tools}
                        assert 'wake_controller_store_resolve' in tools
                        observed = await native.call_tool('wake_controller_store_resolve', {'selector':'stock'})
                        assert not observed.is_error, observed
                        assert json.loads(observed.content[0].text)['result'] == rest['result']
                        copied = await native.call_tool('wake_controller_configuration_sync_apply', args)
                        assert not copied.is_error, copied
                        assert json.loads(copied.content[0].text)['result'] == applied['result']
                asyncio.run(native_stdio())
                if options.powershell:
                    script = "$ErrorActionPreference='Stop'\n$ProgressPreference='SilentlyContinue'\n"
                    script += "$headers=@{Authorization='Bearer " + token + "'}\n"
                    for name, path, body in [('store','/operations',payload), ('sync','/operations',dict(operation='configuration.sync.apply',arguments=args)),
                            ('mcp','/mcp',dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='wake_controller_store_resolve',arguments=payload['arguments'])))]:
                        encoded = base64.b64encode(json.dumps(body).encode()).decode()
                        script += "$body=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('" + encoded + "'))\n"
                        script += "$" + name + "=Invoke-RestMethod -Method Post -Uri '" + endpoint + path + "' -Headers $headers -ContentType 'application/json' -Body $body\n"
                    script += "@{version=$PSVersionTable.PSVersion.ToString();store=$store.result;sync=$sync.result;mcp=$mcp.result.structuredContent.result}|ConvertTo-Json -Depth 50 -Compress\n"
                    process = subprocess.run([str(options.powershell), '-NoProfile', '-NonInteractive', '-Command', '-'],
                        input=script, text=True, capture_output=True, timeout=30)
                    assert process.returncode == 0, process.stderr
                    windows = json.loads(process.stdout.strip())
                    assert windows['store'] == rest['result'] == windows['mcp']
                    assert windows['sync'] == applied['result']
                    report['powershell'] = dict(state='passed', version=windows['version'],
                        operations=['stores.resolve REST','configuration.sync.apply REST','stores.resolve OAuth MCP'])
                report.update(state='passed', cli=True, rest=True, oauth_mcp=True, native_mcp=True,
                    sync_preview_apply_replay=True, native_mcp_transport='stdio subprocess', final_owned_server='closed', elapsed_at=time.time())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
    except Exception as error:
        report.update(state='failed', error=str(error))
        raise
    finally:
        options.receipt.parent.mkdir(parents=True, exist_ok=True)
        options.receipt.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
