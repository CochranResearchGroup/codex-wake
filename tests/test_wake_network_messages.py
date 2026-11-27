"""Two independent Wake owners using public HTTPS and OAuth MCP custody."""
import asyncio
import base64
import contextlib
from datetime import UTC, datetime
import io
import json
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
from codex_wake.wake_network import WakeNetwork, enroll_main
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
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
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

        enrollment = WakeNetwork(config['wake_network'], 'h', 'e', clock=clock)
        enrollment.initialize()
        credentials = []
        for peer in (peer_a, peer_b):
            token = uuid4().hex
            enrollment.enroll(peer, token)
            credentials.append(private(root/(peer + '.key'), token))

        def start_hub():
            with patch('codex_wake.wake_network.snapshot', clock):
                app = create_app(config, root, identify=lambda request: 'operator', operations=fixture.operations(root))
            sock = socket.socket()
            self.addCleanup(sock.close)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', port))
            server = uvicorn.Server(uvicorn.Config(app, log_level='error', ssl_certfile=str(cert),
                                                   ssl_keyfile=str(key), lifespan='on'))
            thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
            thread.start()

            def stop():
                server.should_exit = True
                thread.join(7)
                self.assertFalse(thread.is_alive())
            self.addCleanup(stop)
            deadline = time.monotonic() + 8
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(server.started)
            return stop

        stop_hub = start_hub()

        effects = []
        losses = set()
        unsent = set()

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
                if (peer, verb) in unsent:
                    unsent.remove((peer, verb))
                    raise ExchangeUnavailable('fixture_lost_request')
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

        b.store.set_dnd(conv_b, conv_b, 'clear')
        pending = dict(envelope(peer_b, conv_b, 'kept through revoked peer', due=now+8),
                       sender_conversation_id=conv_a)
        unreported = dict(envelope(peer_b, conv_b, 'unreported owner receipt'), sender_conversation_id=conv_a)
        a.send(unreported)
        a.send(pending)
        self.assertEqual(a.tick()['status'], 'ready')
        unsent.add((peer_b, 'receipt'))
        self.assertEqual(b.tick()['failures']['receipt'], 'fixture_lost_request')
        local_receipt = b.status(unreported['id'], inbound=True)
        self.assertEqual(local_receipt['status'], 'submitted')
        self.assertEqual(b.status(pending['id'], inbound=True)['status'], 'waiting_for_time')
        self.assertEqual(a.status(unreported['id'], refresh=True)['status'], 'hub_accepted')
        self.assertEqual(len(effects), 4)

        stop_hub()
        elapsed = dict(envelope(peer_b, conv_b, 'expiry during outage', expiry=now+3),
                       sender_conversation_id=conv_a)
        a.send(elapsed)
        now += 9
        self.assertEqual(a.tick()['peer_access'], 'unavailable')
        self.assertEqual(a.status(elapsed['id'])['status'], 'waiting_for_hub')
        self.assertEqual(b.tick()['peer_access'], 'unavailable')
        self.assertEqual(b.status(pending['id'], inbound=True)['status'], 'waiting_for_time')
        self.assertEqual(len(effects), 4)
        self.local_wake_during_outage(root, dsns[2], clock, now)

        enrollment_args = ['--dsn-file', config['wake_network']['dsn_file'], '--peer-id', peer_b]
        data = io.StringIO()
        with contextlib.redirect_stdout(data):
            self.assertEqual(enroll_main(enrollment_args + ['--revoke']), 0)
        self.assertEqual(json.loads(data.getvalue()), {'peer_id': peer_b, 'status': 'revoked'})
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as rejected:
            enroll_main(enrollment_args + ['--credential-file', str(credentials[1])])
        self.assertEqual(rejected.exception.code, 2)
        with self.assertRaisesRegex(ValueError, 'different peer'):
            enrollment.enroll(peer_a, credentials[1].read_text())

        start_hub()
        self.assertEqual(b.tick()['peer_access'], 'authorization_denied')
        self.assertEqual(len(effects), 4)
        blocked = a.status(pending['id'], refresh=True)
        self.assertEqual((blocked['recipient_availability'], blocked['expires_at_micros']),
                         ('offline', pending['expires_at_micros']))
        with self.assertRaisesRegex(ExchangeUnavailable, 'invalid_token'):
            PeerHTTPS(origin, peer_b, credentials[0], ca_file=str(cert))('pull', {})
        self.assertTrue(all(delivery['message']['identifier'] != pending['id']
                            for delivery in a.exchange('pull', {})['deliveries']))
        self.assertEqual(a.tick()['status'], 'ready')
        self.assertEqual(a.status(elapsed['id'])['status'], 'hub_accepted')

        replacement = private(root/'rotated-key', uuid4().hex)
        self.assertEqual(enroll_main(enrollment_args + ['--credential-file', str(replacement)]), 0)
        self.assertEqual(a.status(pending['id'], refresh=True)['recipient_availability'], 'stale')
        self.assertEqual(b.tick()['peer_access'], 'authorization_denied')
        os.replace(replacement, credentials[1])
        directory = dict(revision=1, recipients=[dict(conversation_id=conv_b, name='Pilot '+peer_b)])
        self.assertEqual(b.tick(directory), {'status': 'ready', 'failures': {}})
        self.assertEqual(b.tick(), {'status': 'ready', 'failures': {}})
        self.assertEqual(a.tick(), {'status': 'ready', 'failures': {}})
        recovered = a.status(pending['id'], refresh=True)
        self.assertEqual((recovered['status'], recovered['recipient_availability'], recovered['not_before_micros'],
                          recovered['expires_at_micros']),
                         ('submitted', 'current', pending['not_before_micros'], pending['expires_at_micros']))
        self.assertEqual(a.status(elapsed['id'], refresh=True)['status'], 'expired')
        original = a.status(unreported['id'], refresh=True)
        self.assertEqual(original['outcome']['receipt_id'], local_receipt['receipt_id'])
        self.assertEqual(original['outcome']['attempt_id'], local_receipt['attempt_id'])
        self.assertEqual([message.identifier for _,message in effects].count(unreported['id']), 1)
        self.assertEqual([message.identifier for _,message in effects].count(pending['id']), 1)
        self.assertEqual(len(effects), 5)

    def local_wake_during_outage(self, root, dsn, clock, now):
        from codex_wake.cli import run
        from codex_wake.daemon import poll_once
        from codex_wake.records import all_records
        from codex_wake.time_provider import TimeDecision

        local_root = root/'independent-local'
        local_root.mkdir()
        codex = local_root/'codex'
        calls = local_root/'effects'
        thread, receipt = str(uuid4()), str(uuid4())
        codex.write_text(f"""#!/bin/sh
test "$1" = queue || exit 2
printf 'submitted\n' >> '{calls}'
printf 'Queued message {receipt} for thread {thread}.\n'
""")
        codex.chmod(0o700)
        due = datetime.fromtimestamp(now, UTC)
        observation = lambda: TimeDecision('network', ('test-a', 'test-b'), now, now)
        wake_root = local_root/'wake'
        output = io.StringIO()
        with patch.dict(os.environ, {'CODEX_WAKE_MESSAGE_DB_DSN': dsn}), patch(
                'codex_wake.native_clock.snapshot', clock), patch(
                'codex_wake.native_delivery.read_native_thread',
                return_value={'id': thread, 'status': {'type': 'idle'}}):
            with contextlib.redirect_stdout(output):
                self.assertEqual(run(['--wake-root', str(wake_root), 'native', 'at', '--json',
                                      '--codex-path', str(codex), '--ttl', '10m', thread,
                                      due.strftime('%Y-%m-%dT%H:%M:%SZ'), '--', 'local during hub outage']), 0)
            admitted = json.loads(output.getvalue())
            self.assertEqual(admitted['shared_admission'], 'recorded')
            poll_once(wake_root, due, time_provider=observation)
            poll_once(wake_root, due, time_provider=observation)
        record, = all_records(wake_root)
        self.assertEqual((record.record['id'], record.record['status']), (admitted['id'], 'submitted'))
        self.assertEqual(calls.read_text().splitlines(), ['submitted'])
