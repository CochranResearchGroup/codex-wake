"""Two independent Wake owners using public HTTPS and OAuth MCP custody."""
import asyncio
import base64
import hashlib
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx2 as httpx
import uvicorn

import test_external_oauth_connector

from codex_wake.external_connector import create_app
from codex_wake.message_delivery import DeliveryReceipt, PostgresMessages
from codex_wake.wake_network import WakeNetwork
from codex_wake.wake_network_spoke import ExchangeUnavailable, NetworkSpoke, PeerHTTPS


def private(path, content):
    path.write_text(content)
    path.chmod(0o600)
    return path


def envelope(peer, conversation, body, *, due=None, expiry=2_000_000_090, reply=None):
    return dict(id=str(uuid4()), peer_id=peer, conversation_id=conversation, body=body,
                not_before_micros=due * 1_000_000 if due is not None else None,
                expires_at_micros=expiry * 1_000_000, in_reply_to=reply)


async def authorize(client, config, scopes, target):
    callback = config['redirect_uris'][0]
    registered = await client.post('/register', json=dict(redirect_uris=[callback]))
    registered.raise_for_status()
    client_id = registered.json()['client_id']
    verifier = 'v' * 43
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    params = dict(client_id=client_id, redirect_uri=callback, resource=config['issuer'] + '/mcp',
                  response_type='code', code_challenge=challenge, code_challenge_method='S256', scope=scopes)
    landing = await client.get('/authorize', params=params)
    landing.raise_for_status()
    flow = re.search(r'name="flow" value="([^"]+)"', landing.text)[1]
    approved = await client.post('/authorize', data=dict(flow=flow, decision='approve', mode='operator',
        scopes=scopes, targets=target), headers={'Origin': config['issuer']})
    code = parse_qs(urlsplit(approved.headers['location']).query)['code'][0]
    token = await client.post('/token', data=dict(grant_type='authorization_code', code=code, client_id=client_id,
        redirect_uri=callback, resource=params['resource'], code_verifier=verifier))
    token.raise_for_status()
    return token.json()['access_token']


_DATABASES = ('CODEX_WAKE_TEST_NETWORK_DSN', 'CODEX_WAKE_TEST_SPOKE_A_DSN', 'CODEX_WAKE_TEST_SPOKE_B_DSN')


@unittest.skipUnless(all(os.environ.get(name) for name in _DATABASES), 'requires three disposable PostgreSQL databases')
class NetworkMessageTests(unittest.TestCase):
    def test_exact_custody_reply_and_idempotent_retry_over_tls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._exercise(root)

    def _exercise(self, root):
        dsns = [os.environ[name] for name in _DATABASES]
        cert, key = root/'certificate.pem', root/'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
        self.assertEqual(len(set(dsns)), 3)
        sock = socket.socket()
        self.addCleanup(sock.close)
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        origin = 'https://localhost:' + str(port)
        fixture = test_external_oauth_connector.ExternalConnectorTests()
        peer_a, peer_b = ('peer-' + uuid4().hex for _ in range(2))
        conv_a, conv_b = (str(uuid4()) for _ in range(2))
        config = dict(fixture.config(), issuer=origin, scopes=['observe', 'control', 'content.observe'],
                      wake_network=dict(dsn_file=str(private(root/'dsn', dsns[0])), stale_seconds=50))
        config['targets'] = [dict(host='h', environment='e', peer_id=peer_b, conversation_id=conv_b),
                             dict(host='h', environment='e')]
        now = 2_000_000_000

        def clock():
            return {'utc': {'status': 'network', 'sources': ['test-a', 'test-b'], 'lower': now, 'upper': now}}

        with patch('codex_wake.wake_network.snapshot', clock):
            app = create_app(config, root, identify=lambda request: 'operator', operations=fixture.operations(root))
        enrollment = WakeNetwork(config['wake_network'], 'h', 'e', clock=clock)
        enrollment.initialize()
        credentials = []
        for peer in (peer_a, peer_b):
            token = uuid4().hex
            enrollment.enroll(peer, token)
            credentials.append(private(root/(peer + '.key'), token))
        server = uvicorn.Server(uvicorn.Config(app, log_level='error', ssl_certfile=str(cert),
                                               ssl_keyfile=str(key), lifespan='on'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        thread.start()

        def stop():
            server.should_exit = True
            thread.join(5)
        self.addCleanup(stop)
        deadline = time.monotonic() + 6
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(server.started)

        effects = []
        losses = set()

        def driver(peer):
            def submit(message):
                effects.append((peer, message))
                return DeliveryReceipt('submitted', 'native-receipt-' + message.identifier,
                                       evidence_kind='fixture_native_receipt')
            return submit

        workers = []
        for index, (peer, conv) in enumerate(((peer_a, conv_a), (peer_b, conv_b))):
            state = root/peer
            state.mkdir(mode=0o700)
            transport = PeerHTTPS(origin, peer, credentials[index], ca_file=str(cert))

            def exchange(verb, request, transport=transport, peer=peer):
                receipt = transport(verb, request)
                if (peer, verb) in losses:
                    losses.remove((peer, verb))
                    raise ExchangeUnavailable('fixture_lost_response')
                return receipt

            worker = NetworkSpoke(state, peer, PostgresMessages(dsns[index+1]), exchange,
                                  {conv: driver(peer)}, hub=origin, clock=clock)
            directory = dict(revision=1, recipients=[dict(conversation_id=conv, name='Pilot '+peer)])
            for _ in range(3):
                ready = worker.tick(directory)
                if ready['status'] == 'ready':
                    break
            self.assertEqual(ready, {'status': 'ready', 'failures': {}})
            workers.append(worker)
        a, b = workers
        original = dict(envelope(peer_b, conv_b, 'retained-body', due=now+10), sender_conversation_id=conv_a)
        losses.add((peer_a, 'send'))
        self.assertEqual(a.send(original)['status'], 'waiting_for_hub')
        self.assertEqual(a.tick()['failures']['outgoing'], 'fixture_lost_response')
        self.assertEqual(a.status(original['id'])['status'], 'waiting_for_hub')
        self.assertEqual(b.tick()['status'], 'ready')
        self.assertEqual(b.status(original['id'], inbound=True)['status'], 'waiting_for_time')
        self.assertEqual(effects, [])
        # Recreate the spoke object to prove journal custody survives process loss.
        b = NetworkSpoke(b.root, b.peer, b.store, b.exchange, b.bindings, hub=origin, clock=clock)
        now += 10
        losses.add((peer_b, 'pull'))
        self.assertEqual(b.tick()['failures']['pull'], 'fixture_lost_response')
        self.assertEqual(effects, [])
        with self.assertRaisesRegex(ExchangeUnavailable, 'insufficient_scope'):
            a.exchange('receipt', dict(id=original['id'], conversation_id=conv_b,
                expires_at_micros=original['expires_at_micros'], not_before_micros=original['not_before_micros'],
                in_reply_to=None, outcome={'status': 'owner_admitted'}))
        losses.add((peer_b, 'receipt'))
        self.assertEqual(b.tick()['failures']['receipt'], 'fixture_lost_response')
        self.assertEqual(b.status(original['id'], inbound=True)['status'], 'submitted')
        self.assertEqual(b.tick()['status'], 'ready')
        self.assertEqual(a.tick()['status'], 'ready')
        visible = a.status(original['id'])
        self.assertEqual((visible['status'], visible['not_before_micros'], visible['expires_at_micros']),
                         ('submitted', original['not_before_micros'], original['expires_at_micros']))
        self.assertEqual(visible['outcome']['receipt_id'], 'native-receipt-' + original['id'])
        self.assertEqual([row[1].identifier for row in effects], [original['id']])
        with b.store._connect() as db:
            row = db.execute('SELECT state,receipt_id FROM wake_message_attempts_v1 WHERE message_id=%s',
                             (original['id'],)).fetchall()
        self.assertEqual(row, [('submitted', visible['outcome']['receipt_id'])])

        reply = dict(envelope(peer_a, conv_a, 'peer reply', reply=original['id']), sender_conversation_id=conv_b)
        b.send(reply)
        self.assertEqual(b.tick()['status'], 'ready')
        self.assertEqual(a.tick()['status'], 'ready')
        self.assertEqual(a.status(original['id'], refresh=True)['replies'][0]['id'], reply['id'])
        self.assertEqual(effects[-1][1].in_reply_to, original['id'])

        async def oauth_journey():
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client

            tls = ssl.create_default_context(cafile=str(cert))
            async with httpx.AsyncClient(base_url=origin, verify=tls) as client:
                with patch('codex_wake.controller_auth._qualified_upper', return_value=now):
                    access = await authorize(client, config, 'observe control content.observe', '0')
                    local_only = await authorize(client, config, 'observe control', '1')
                    value = envelope(peer_b, conv_b, 'OAuth original')
                    rejected = await client.post('/network/v1/messages/send', json=value,
                                                headers={'Authorization': 'Bearer ' + local_only})
                    self.assertEqual(rejected.status_code, 403)
                    async with httpx.AsyncClient(verify=tls, headers={'Authorization': 'Bearer '+access}) as mcp_http:
                        async with streamable_http_client(origin+'/mcp', http_client=mcp_http) as streams:
                            async with ClientSession(streams[0], streams[1]) as session:
                                await session.initialize()
                                admission = await session.call_tool('wake_network_send', value)
                                self.assertFalse(admission.is_error, admission.structured_content)
                                self.assertEqual(admission.structured_content['outcome'], {'status': 'hub_accepted'})
                                self.assertEqual(await asyncio.to_thread(b.tick), {'status': 'ready', 'failures': {}})
                                answer = dict(envelope(None, None, 'OAuth reply', reply=value['id']),
                                              sender_conversation_id=conv_b)
                                b.send(answer)
                                self.assertEqual(await asyncio.to_thread(b.tick), {'status': 'ready', 'failures': {}})
                                read = await session.call_tool('wake_network_message_status', {'id': value['id']})
                                self.assertFalse(read.is_error, read.structured_content)
                                result = read.structured_content
                                self.assertEqual(result['outcome']['receipt_id'], 'native-receipt-'+value['id'])
                                self.assertEqual(result['replies'][0]['body'], answer['body'])
                                self.assertEqual(result['replies'][0]['in_reply_to'], value['id'])
                                http_receipt = await client.post('/network/v1/messages/status', json={'id': value['id']},
                                                                 headers={'Authorization': 'Bearer '+access})
                                self.assertEqual(http_receipt.status_code, 200)
                                self.assertEqual(http_receipt.json(), result)
                                conflict = await client.post('/network/v1/messages/send', json=dict(value, body='changed'),
                                                             headers={'Authorization': 'Bearer '+access})
                                self.assertEqual(conflict.status_code, 409)
        asyncio.run(oauth_journey())
        self.assertEqual(len(effects), 3)
        expired = dict(envelope(peer_b, conv_b, 'expired', expiry=now), sender_conversation_id=conv_a)
        a.send(expired)
        self.assertEqual(a.tick()['status'], 'ready')
        self.assertEqual(b.tick()['status'], 'ready')
        self.assertEqual(a.status(expired['id'], refresh=True)['status'], 'expired')
        b.store.set_dnd(conv_b, conv_b, 'bounce')
        bounced = dict(envelope(peer_b, conv_b, 'policy bounce'), sender_conversation_id=conv_a)
        a.send(bounced)
        self.assertEqual(a.tick()['status'], 'ready')
        self.assertEqual(b.tick()['status'], 'ready')
        self.assertEqual(a.status(bounced['id'], refresh=True)['outcome'],
                         {'status': 'bounced', 'reason': 'recipient_dnd'})
        self.assertEqual(len(effects), 3)
