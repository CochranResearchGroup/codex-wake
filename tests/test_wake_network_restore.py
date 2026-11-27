"""Older actual PostgreSQL backup plus authoritative spoke evidence."""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx2 as httpx
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.sql import Identifier, SQL

from codex_wake.external_connector import create_app
from codex_wake.message_delivery import DeliveryReceipt, PostgresMessages
from codex_wake.wake_network import WakeNetwork
from codex_wake.wake_network_messages import NetworkMessages
from codex_wake.wake_network_restore import main
from codex_wake.wake_network_spoke import NetworkSpoke
import test_external_oauth_connector
from test_wake_network_messages import envelope, private


@unittest.skipUnless(os.environ.get('CODEX_WAKE_TEST_RESTORE_DSN') and
                     os.environ.get('CODEX_WAKE_TEST_RESTORE_CONTAINER'), 'requires disposable PostgreSQL tools')
class NetworkRestoreTests(unittest.TestCase):
    def test_older_backup_preserves_exact_effect_and_holds(self):
        admin = os.environ['CODEX_WAKE_TEST_RESTORE_DSN']
        instance = os.environ['CODEX_WAKE_TEST_RESTORE_CONTAINER']
        user = conninfo_to_dict(admin).get('user', 'postgres')
        names = ['wake787_' + uuid4().hex[:12] for _ in range(3)]
        self.addCleanup(self.drop, admin, names)
        with psycopg.connect(admin, autocommit=True) as db:
            for name in names:
                db.execute(SQL('CREATE DATABASE {}').format(Identifier(name)))
        live, restored, local = [make_conninfo(admin, dbname=name) for name in names]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.exercise(root, instance, user, names, live, restored, local)

    def drop(self, admin, names):
        with psycopg.connect(admin, autocommit=True) as db:
            for name in names:
                db.execute(SQL('DROP DATABASE IF EXISTS {}').format(Identifier(name)))

    def exercise(self, root, instance, user, names, live, restored, local):
        epoch = 2_000_000_000

        def clock():
            return {'utc': {'status': 'network', 'sources': ['a', 'b'], 'lower': epoch, 'upper': epoch}}

        origin = 'https://wake.example'
        a, b, revoked = 'source-fixture', 'owner-fixture', 'revoked-fixture'
        sender, recipient = str(uuid4()), str(uuid4())
        keys = {peer: uuid4().hex for peer in (a, b, revoked)}
        auth = {peer: 'Bearer ' + key for peer, key in keys.items()}

        def network(dsn, name):
            target = dict(dsn_file=str(private(root/name, dsn)), stale_seconds=60)
            service = WakeNetwork(target, 'h', 'e', clock=clock)
            service.initialize()
            return target, service

        _, hub = network(live, 'live-dsn')
        custody = NetworkMessages(hub)
        custody.initialize()
        for peer in keys:
            hub.enroll(peer, keys[peer])
        for peer, conversation in ((a, sender), (b, recipient)):
            hub.publish(peer, auth[peer], dict(revision=1, recipients=[
                dict(conversation_id=conversation, name='fixture')]))
        driver_calls = []

        def driver(message):
            driver_calls.append(message.identifier)
            if message.identifier == uncertain['id']:
                return DeliveryReceipt('uncertain', reason='fixture_unknown')
            return DeliveryReceipt('submitted', 'native-' + message.identifier, evidence_kind='fixture_native')

        def exchange(verb, value):
            return getattr(custody, verb)(b, auth[b], value)

        state = root/'owner'
        state.mkdir(mode=0o700)
        worker = NetworkSpoke(state, b, PostgresMessages(local), exchange, {recipient: driver},
                              hub=origin + '/network/v1/peers/' + b, clock=clock)

        def send(value):
            return custody.peer_send(a, auth[a], dict(value, sender_conversation_id=sender))

        final, uncertain, deferred, unseen, after_backup = [
            envelope(b, recipient, label, due=due) for label, due in (
                ('delivered', None), ('unknown', None), ('deferred', epoch+20),
                ('not pulled', epoch+20), ('after backup', None))]
        for value in (final, uncertain, deferred):
            send(value)
        command = ['docker', 'exec', '-i', instance]
        backup = subprocess.check_output(command + ['pg_dump', '-U', user, '-Fc', '-d', names[0]])
        self.assertEqual(backup[:5], b'PGDMP')
        self.assertEqual(worker.tick()['status'], 'ready')
        self.assertEqual(set(driver_calls), {final['id'], uncertain['id']})
        send(after_backup)
        self.assertEqual(worker.tick()['status'], 'ready')
        send(unseen)
        with hub.connect() as db:
            db.execute('UPDATE wake_network_peers_v1 SET enabled=false WHERE peer_id=%s', (revoked,))
        self.assertEqual(len(driver_calls), 2)
        subprocess.run(command + ['pg_restore', '-U', user, '--exit-on-error', '-d', names[1]],
                       input=backup, check=True, capture_output=True)
        with sqlite3.connect(state/'work.sqlite') as db:
            # Simulate interruption after the original receipt committed on
            # the owner but before its final local journal write.
            saved = json.loads(db.execute('SELECT outcome FROM transfers WHERE id=?',
                                         (final['id'],)).fetchone()[0])
            db.execute('UPDATE transfers SET outcome=? WHERE id=?',
                       (json.dumps({'status': 'submitting', 'attempt_id': saved['attempt_id']}), final['id']))
        settings, recovered = network(restored, 'restored-dsn')
        current = NetworkMessages(recovered)
        expected = current.peer_status(a, auth[a], {'id': final['id']})
        self.assertEqual(expected['outcome']['status'], 'hub_accepted')
        config_path = root/'restore.json'
        args = ['--config', str(config_path), '--quiesced-restored-hub']
        private(config_path, json.dumps(dict(network=settings, hub=origin,
            owners=[dict(peer_id=b, journal=str(state/'unavailable.sqlite'))])))
        self.assertEqual(main(args), 0)
        with recovered.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM wake_network_restore_holds_v1').fetchone()[0], 3)
            self.assertEqual(db.execute('SELECT count(*) FROM wake_network_peers_v1 WHERE enabled').fetchone()[0], 0)
        private(config_path, json.dumps(dict(network=settings, hub=origin,
            owners=[dict(peer_id=b, journal=str(state/'work.sqlite'),
                         owner_dsn_file=str(private(root/'owner-dsn', local)))])))
        self.assertEqual(main(args), 0)
        custody = current

        fixture = test_external_oauth_connector.ExternalConnectorTests()
        app_config = dict(fixture.config(), wake_network=settings)
        with patch('codex_wake.wake_network.snapshot', clock):
            app = create_app(app_config, root/'app', identify=lambda _: 'operator',
                             operations=fixture.operations(root/'app'))

        async def verify():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=origin) as client:
                async def post(peer, action, value):
                    return await client.post('/network/v1/peers/' + peer + '/messages/' + action,
                        headers={'Authorization': auth[peer]}, json=value)

                for peer in (a, b, revoked):
                    self.assertEqual((await post(peer, 'pull', {})).status_code, 401)
                for peer in (a, b):
                    keys[peer] = uuid4().hex
                    auth[peer] = 'Bearer ' + keys[peer]
                    recovered.enroll(peer, keys[peer])
                self.assertEqual((await post(revoked, 'pull', {})).status_code, 401)
                self.assertEqual((await post(b, 'pull', {})).json()['error'], 'restore_held')
                pull = (await post(b, 'pull', {'restore_allowlist': True})).json()
                self.assertEqual(pull, {'deliveries': [], 'restore_allowlist': True})
                for value, status in ((final, 'submitted'), (uncertain, 'uncertain'), (deferred, 'restore_held')):
                    result = (await post(a, 'status', {'id': value['id']})).json()
                    self.assertEqual(result['outcome']['status'], status)
                    self.assertEqual(result['expires_at_micros'], value['expires_at_micros'])
                    if status == 'submitted':
                        self.assertEqual(result['outcome']['receipt_id'], 'native-' + value['id'])
                resend = dict(after_backup, sender_conversation_id=sender)
                self.assertEqual((await post(a, 'send', resend)).json()['error'], 'restore_held')

        asyncio.run(verify())
        epoch += 30
        worker.tick()
        self.assertEqual(set(driver_calls), {final['id'], uncertain['id']})
        self.assertEqual(len(driver_calls), 2)
        self.assertEqual(worker.status(deferred['id'], inbound=True)['status'], 'waiting_for_time')
        self.assertEqual(worker.status(unseen['id'], inbound=True)['status'], 'not_found')
        with sqlite3.connect(state/'work.sqlite') as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM transfers').fetchone()[0], 4)
