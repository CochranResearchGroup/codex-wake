"""Peer directory and client visibility through HTTP and OAuth MCP."""
import asyncio
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx2 as httpx

import test_external_oauth_connector


@unittest.skipUnless(os.environ.get('CODEX_WAKE_TEST_NETWORK_DSN'), 'requires disposable PostgreSQL')
class WakeNetworkTests(unittest.TestCase):
    def test_peer_owned_directory_and_scoped_client_lookup(self):
        from codex_wake.external_connector import create_app
        from codex_wake.wake_network import enroll_main

        async def scenario(root):
            fixture = test_external_oauth_connector.ExternalConnectorTests()
            config = fixture.config()
            peer, other = ('peer-' + uuid4().hex for _ in range(2))
            dsn = root / 'dsn'
            dsn.write_text(os.environ['CODEX_WAKE_TEST_NETWORK_DSN'])
            dsn.chmod(0o600)
            credentials = root / 'credential'
            credentials.touch(mode=0o600)
            token, other_token = uuid4().hex, uuid4().hex
            for identity, secret in ((peer, token), (other, other_token)):
                credentials.write_text(secret)
                self.assertEqual(enroll_main(['--dsn-file', str(dsn), '--peer-id', identity,
                                              '--credential-file', str(credentials)]), 0)
            config['wake_network'] = dict(dsn_file=str(dsn), stale_seconds=10)
            config['targets'].append(dict(config['targets'][0], peer_id=peer))
            now = 2_000_000_000

            def clock():
                return {'utc': {'status': 'network', 'sources': ['test-a', 'test-b'], 'lower': now, 'upper': now}}

            with patch('codex_wake.wake_network.snapshot', clock):
                app = create_app(config, root, identify=lambda request: 'operator', operations=fixture.operations(root))
            async with fixture.external_client(app, config) as (_, grant, connector):
                local_access = await grant('observe')
                access = await grant('observe', targets='1')
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=config['issuer']) as client:
                    first = dict(revision=1, recipients=[dict(conversation_id='stable-a', name='Pilot'),
                                                         dict(conversation_id='stable-b', name='Pilot')])
                    route = f'/network/v1/peers/{peer}/directory'
                    header = {'Authorization': 'Bearer ' + token}
                    wrong = await client.put(route, headers={'Authorization': 'Bearer ' + other_token}, json=first)
                    self.assertEqual(wrong.status_code, 401)
                    self.assertEqual((await client.put(route, headers=header, json=first)).status_code, 200)
                    hidden = await client.put(f'/network/v1/peers/{other}/directory',
                        headers={'Authorization': 'Bearer ' + other_token}, json=first)
                    self.assertEqual(hidden.status_code, 200)
                    changed = dict(revision=2, recipients=[dict(conversation_id='stable-a', name='Renamed'),
                                                           dict(conversation_id='stable-b', name='Renamed')])
                    self.assertEqual((await client.put(route, headers=header, json=changed)).status_code, 200)
                    self.assertEqual((await client.put(route, headers=header, json=first)).status_code, 409)
                    public = '/network/v1/recipients'
                    self.assertEqual((await client.post(public, headers=header, json={})).status_code, 401)
                    local = await client.post(public, headers={'Authorization': 'Bearer ' + local_access}, json={})
                    self.assertEqual(local.json(), {'status': 'ok', 'recipients': []})
                    result = await client.post(public, headers={'Authorization': 'Bearer ' + access},
                                               json={'name': 'renamed'})
                    self.assertEqual(result.status_code, 200, result.text)
                    self.assertEqual(result.json()['status'], 'ambiguous')
                    self.assertEqual([r['peer_id'] for r in result.json()['recipients']], [peer, peer])
                now += 11
                async with connector(access) as session:
                    names = {tool.name for tool in (await session.list_tools()).tools}
                    self.assertIn('wake_network_recipients', names)
                    result = await session.call_tool('wake_network_recipients', {'conversation_id': 'stable-a'})
                    self.assertFalse(result.is_error, result.structured_content)
                    rows = result.structured_content['recipients']
                    self.assertEqual([(r['peer_id'], r['name'], r['availability']) for r in rows],
                                     [(peer, 'Renamed', 'stale')])

        with tempfile.TemporaryDirectory() as directory:
            asyncio.run(scenario(Path(directory)))
