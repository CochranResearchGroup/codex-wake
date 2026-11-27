"""Wake management over OAuth HTTP and MCP with authenticated spoke polling."""
import asyncio
import json
import sqlite3
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
        from codex_wake.controller_auth import OAuthAuthority
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
                          targets=[dict(config['targets'][0], peer_id=peer, conversation_id=thread), config['targets'][0]])

            epoch = 2_000_000_000

            def clock():
                return {'utc': {'status': 'network', 'sources': ['a', 'b'], 'lower': epoch, 'upper': epoch}}

            hub = WakeNetwork(config['wake_network'], 'h', 'e', clock=clock)
            hub.initialize()
            hub.enroll(peer, credential)
            peer_headers = {'Authorization': 'Bearer ' + credential}
            base = f'/network/v1/peers/{peer}'
            live = LiveManagement(hub)
            def fixture_authority(*args, **kwargs):
                return OAuthAuthority(*args, **kwargs, now=lambda: epoch)

            with patch('codex_wake.external_connector.OAuthAuthority', fixture_authority), patch(
                    'codex_wake.wake_network_management.LiveManagement', return_value=live):
                app = create_app(config, root, identify=lambda _: 'operator', operations=fixture.operations(root))
            route = '/network/v1/management/history/search'
            address = {'peer_id': peer, 'conversation_id': thread}
            async with fixture.external_client(app, config) as (_, grant, connect):
                metadata = await grant('history.observe')
                content = await grant('history.observe content.observe')
                control = await grant('control')
                broad = await grant('history.observe', targets='1')
                headers = {'Authorization': 'Bearer ' + metadata}
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=config['issuer']) as client:
                    self.assertEqual((await client.put(base + '/directory', headers=peer_headers,
                        json={'revision': 1, 'recipients': [{'conversation_id': thread, 'name': 'fixture'}]})).status_code, 200)
                    offline = await client.post(route, headers=headers, json=address)
                    self.assertEqual(offline.json(), {'status': 'offline'})
                    refused = await client.post(route, headers={'Authorization': 'Bearer ' + broad}, json=address)
                    self.assertEqual(refused.status_code, 403)
                    async with connect(broad) as broad_session:
                        visible = {tool.name for tool in (await broad_session.list_tools()).tools}
                        self.assertNotIn('wake_network_history_search', visible)
                    denied = await client.post(route.replace('search', 'read'), headers=headers, json=address)
                    self.assertEqual(denied.status_code, 403)
                    bad_peer = await client.post(base + '/management/pull', headers=headers, json={})
                    self.assertEqual(bad_peer.status_code, 401)

                    async def pull():
                        waiting = asyncio.create_task(client.post(base + '/management/pull', headers=peer_headers, json={}))
                        for _ in range(250):
                            if peer in live.polls:
                                return waiting
                            if waiting.done():
                                self.fail((await waiting).json())
                            await asyncio.sleep(.01)
                        waiting.cancel()
                        self.fail('spoke poll never registered')

                    from codex_wake.controller_accounts import ControllerAccounts
                    from codex_wake.controller_auth import Actor
                    from codex_wake.controller_http import ProtectedOperations
                    from codex_wake.tab_monitor import TabMonitor

                    accounts_path = root / 'controller-accounts.toml'
                    accounts_path.write_text(f'[profiles]\nstate_root="{root / "homes"}"\nknown_profiles=["pilot"]\n'
                                             '[history]\nreadable_accounts=["pilot"]\n')
                    accounts_path.chmod(0o600)
                    home = root / 'homes' / 'codex-pilot'
                    sessions = home / 'sessions'
                    sessions.mkdir(parents=True)
                    rollout = sessions / 'saved.jsonl'
                    marker = 'withheld fixture content'
                    rollout.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': thread}}) + '\n'
                        + json.dumps({'type': 'response_item', 'payload': {'content': marker}}) + '\n')
                    with sqlite3.connect(home / 'state_5.sqlite') as db:
                        db.execute('CREATE TABLE threads (id text, cwd text, title text, rollout_path text)')
                        db.execute('INSERT INTO threads VALUES (?,?,?,?)', (thread, '/original', 'fixture', str(rollout)))
                    home_info = home.stat()
                    account_target = ControllerAccounts(accounts_path, host='h', environment='e').execute(
                        'accounts.resolve', {'selector': 'pilot'})['account']['target']
                    monitor = TabMonitor(root, clock=time.time)
                    pane = {'pane_id': '%1', 'pane_current_path': '/last-observed'}
                    binding = dict(runtime='codex', conversation_id=thread,
                        process=dict(pid=123, start_ticks=456, boot_id='fixture'), fresh=True,
                        source='native_metadata', observed_at=time.time(),
                        native_source=dict(home=str(home), home_generation=f'{home_info.st_dev}:{home_info.st_ino}'))
                    resource = dict(target=dict(host='h', environment='e', workspace='old', presentation='tmux',
                                                generation='fixture'),
                        window=dict(window_id='@1', index=1, name='demo', panes=[pane]),
                        traits=dict(panes=[dict(pane_id='%1', binding=binding)]))
                    frame = dict(observed_at=time.time(), workspaces=['old'], unavailable=[], resources=[resource],
                                 observation_scope=dict(host='h', environment='e'))
                    monitor.publish_observation(frame, {})
                    monitor.publish_observation(dict(frame, resources=[]), {})
                    history_actor = Actor('local', 'service', 'local', 'history',
                        'https://local.example', 'https://local.example/mcp',
                        frozenset({'history.observe', 'content.observe'}), [account_target], epoch + 120)

                    class HistoryAuthority:
                        def authenticate(self, token):
                            return history_actor

                    owner = SpokeManagement({thread: {
                        'network.history.search': {'former_tab': 'demo', 'owners': ['pilot']},
                        'network.history.read': {'thread_id': thread, 'owner': 'pilot'},
                    }}, ProtectedOperations(HistoryAuthority(), fixture.operations(root)), 'local-test', clock)

                    async def complete(waiting):
                        claim = (await waiting).json()
                        self.assertEqual(claim['status'], 'claimed', claim)
                        envelope = claim['request']
                        response = await client.post(base + '/management/complete', headers=peer_headers,
                            json={'id': envelope['id'], 'result': owner.execute(envelope)})
                        self.assertEqual(response.json()['status'], 'completed')

                    waiting = await pull()
                    request = asyncio.create_task(client.post(route, headers=headers, json=address))
                    await complete(waiting)
                    former = (await request).json()
                    recorded, = former['result']['bindings']
                    self.assertEqual(recorded['conversation_id'], thread)
                    self.assertEqual(recorded['last_known_presentation'], 'absent')
                    self.assertEqual(recorded['last_observed_cwd'], '/last-observed')
                    self.assertNotIn(marker, json.dumps(former))
                    async with connect(content) as session:
                        waiting = await pull()
                        request = asyncio.create_task(session.call_tool('wake_network_history_read', address))
                        await complete(waiting)
                        result = await request
                        self.assertFalse(result.is_error, result.structured_content)
                        self.assertEqual(result.structured_content['result']['records'][1]['payload']['content'], marker)

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
                        [{key: value for key, value in target.items() if key != 'generation'}], epoch + 120)

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
                        claim = (await waiting).json()
                        self.assertEqual(claim['status'], 'claimed', claim)
                        envelope = claim['request']
                        expired = await asyncio.to_thread(terminal_owner.execute, dict(
                            envelope, deadline=epoch * 1_000_000))
                        self.assertEqual(expired, {'status': 'expired'})
                        effect = await asyncio.to_thread(terminal_owner.execute, envelope)
                        self.assertIn('result', effect, effect)
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
