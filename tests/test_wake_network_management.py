"""Wake management over OAuth HTTP and MCP with authenticated spoke polling."""
import asyncio
import os
from pathlib import Path
import tempfile
import subprocess
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx2 as httpx

import test_external_oauth_connector


@unittest.skipUnless(os.environ.get('CODEX_WAKE_TEST_NETWORK_DSN'), 'requires disposable PostgreSQL')
class WakeNetworkManagementTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_use_management_and_separate_content_grant(self):
        from codex_wake.external_connector import create_app
        from codex_wake.wake_network import WakeNetwork
        from codex_wake.wake_network_management import LiveManagement, SpokeManagement

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = test_external_oauth_connector.ExternalConnectorTests()
            peer, thread = uuid4().hex, str(uuid4())
            credential = uuid4().hex
            config = fixture.config()
            dsn = root / 'dsn'
            dsn.touch(mode=0o600)
            dsn.write_text(os.environ['CODEX_WAKE_TEST_NETWORK_DSN'])
            config.update(wake_network=dict(dsn_file=str(dsn), stale_seconds=60),
                          scopes=['observe', 'history.observe', 'content.observe', 'control'],
                          targets=[dict(config['targets'][0], peer_id=peer, conversation_id=thread)])

            def clock():
                now = time.time()
                return {'utc': {'status': 'network', 'sources': ['a', 'b'], 'lower': now, 'upper': now}}

            hub = WakeNetwork(config['wake_network'], 'h', 'e', clock=clock)
            hub.initialize()
            hub.enroll(peer, credential)
            peer_headers = {'Authorization': 'Bearer ' + credential}
            base = f'/network/v1/peers/{peer}'
            live = LiveManagement(hub)
            with patch('codex_wake.wake_network.snapshot', clock), patch(
                    'codex_wake.wake_network_management.LiveManagement', return_value=live):
                app = create_app(config, root, identify=lambda _: 'operator', operations=fixture.operations(root))
            route = '/network/v1/management/history/search'
            address = {'peer_id': peer, 'conversation_id': thread}
            async with fixture.external_client(app, config) as (_, grant, connect):
                metadata = await grant('history.observe')
                content = await grant('history.observe content.observe')
                control = await grant('control')
                headers = {'Authorization': 'Bearer ' + metadata}
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=config['issuer']) as client:
                    self.assertEqual((await client.put(base + '/directory', headers=peer_headers,
                        json={'revision': 1, 'recipients': [{'conversation_id': thread, 'name': 'fixture'}]})).status_code, 200)
                    offline = await client.post(route, headers=headers, json=address)
                    self.assertEqual(offline.json(), {'status': 'offline'})
                    denied = await client.post(route.replace('search', 'read'), headers=headers, json=address)
                    self.assertEqual(denied.status_code, 403)
                    bad_peer = await client.post(base + '/management/pull', headers=headers, json={})
                    self.assertEqual(bad_peer.status_code, 401)

                    async def pull():
                        waiting = asyncio.create_task(client.post(base + '/management/pull', headers=peer_headers, json={}))
                        for _ in range(100):
                            if peer in live.polls:
                                return waiting
                            await asyncio.sleep(.01)
                        self.fail('spoke poll never registered')

                    class Protected:
                        def execute(self, token, operation, arguments):
                            if operation == 'history.search':
                                return {'result': {'bindings': [
                                    {'conversation_id': thread, 'last_known_presentation': 'absent'},
                                    {'conversation_id': 'another', 'last_known_presentation': 'active'}]}}
                            return {'result': {'records': ['withheld fixture content']}}

                    owner = SpokeManagement({thread: {
                        'network.history.search': {'former_tab': 'demo'},
                        'network.history.read': {'thread_id': thread},
                    }}, Protected(), 'fixture-local-token', clock)

                    async def complete(waiting):
                        envelope = (await waiting).json()['request']
                        response = await client.post(base + '/management/complete', headers=peer_headers,
                            json={'id': envelope['id'], 'result': owner.execute(envelope)})
                        self.assertEqual(response.json()['status'], 'completed')

                    waiting = await pull()
                    request = asyncio.create_task(client.post(route, headers=headers, json=address))
                    await complete(waiting)
                    self.assertEqual((await request).json()['result']['bindings'],
                                     [{'conversation_id': thread, 'last_known_presentation': 'absent'}])
                    async with connect(content) as session:
                        waiting = await pull()
                        request = asyncio.create_task(session.call_tool('wake_network_history_read', address))
                        await complete(waiting)
                        result = await request
                        self.assertFalse(result.is_error, result.structured_content)
                        self.assertEqual(result.structured_content['result']['records'], ['withheld fixture content'])

                    from codex_wake.controller_auth import Actor
                    from codex_wake.controller_http import ProtectedOperations
                    from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
                    from codex_wake.tab_lifecycle import TabLifecycle

                    socket = str(root / 'tmux.sock')

                    def tmux(*args):
                        return subprocess.check_output(['tmux', '-f', '/dev/null', '-S', socket, *args], text=True).strip()

                    tmux('new-session', '-d', '-s', 'fixture', '-n', 'original', 'sleep 120')
                    self.addCleanup(lambda: subprocess.run(['tmux', '-S', socket, 'kill-server'], capture_output=True))
                    operations = fixture.operations(root)
                    operations.tabs.workspaces['pilot'] = {
                        'kind': 'tmux', 'transport': TmuxAttachmentTransport(socket, '$0')}
                    lifecycle = TabLifecycle(root, workspaces=operations.tabs.workspaces, host='h', environment='e')
                    initial = lifecycle.inspect('pilot')
                    target = initial['target']
                    window = initial['snapshot']['windows'][0]['window_id']
                    terminal_actor = Actor('local', 'service', 'local', 'local',
                        'https://local.example', 'https://local.example/mcp', frozenset({'control'}),
                        [{key: value for key, value in target.items() if key != 'generation'}], time.time() + 120)

                    class TerminalAuthority:
                        def authenticate(self, token):
                            return terminal_actor

                    terminal_owner = SpokeManagement({thread: {'network.tabs.rename': dict(
                        workspace='pilot', expected_target=target, window=window)}},
                        ProtectedOperations(TerminalAuthority(), operations), 'fixture-local-token', clock)

                    async def rename(name, *, send_receipt):
                        waiting = await pull()
                        scheduled = asyncio.create_task(client.post('/network/v1/management/tabs/rename',
                            headers={'Authorization': 'Bearer ' + control}, json=dict(address, name=name)))
                        envelope = (await waiting).json()['request']
                        effect = await asyncio.to_thread(terminal_owner.execute, envelope)
                        self.assertEqual(effect['result']['operation']['execution'], 'completed', effect)
                        self.assertEqual(tmux('display-message', '-p', '-t', window, '#{window_name}'), name)
                        if send_receipt:
                            receipt = await client.post(base + '/management/complete', headers=peer_headers,
                                json={'id': envelope['id'], 'result': effect})
                            self.assertEqual(receipt.json()['status'], 'completed')
                        return (await scheduled).json(), envelope

                    uncertain, original = await rename('renamed', send_receipt=False)
                    self.assertEqual(uncertain['status'], 'uncertain')
                    terminal_owner.bindings[thread]['network.tabs.rename']['expected_target'] = lifecycle.inspect('pilot')['target']
                    restored, fresh = await rename('original', send_receipt=True)
                    self.assertEqual(restored['status'], 'completed')
                    self.assertNotEqual(original['id'], fresh['id'])
                    stale = await client.post(base + '/management/complete', headers=peer_headers,
                        json={'id': original['id'], 'result': {'status': 'completed'}})
                    self.assertEqual(stale.json(), {'status': 'expired'})
                    tmux('kill-server')
