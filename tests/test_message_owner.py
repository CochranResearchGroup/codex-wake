"""Public handoff, ownership and restore journey against disposable PostgreSQL."""
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from codex_wake.controller_hosts import HostRegistry
from codex_wake.message_owner import add_arguments, command


DSN = os.environ.get('CODEX_WAKE_TEST_MESSAGE_DB_DSN')


@unittest.skipUnless(DSN, 'requires disposable PostgreSQL')
class MessageOwnerTests(unittest.TestCase):
    def test_bidirectional_message_custody_settings_revision_and_restore(self):
        import psycopg

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = HostRegistry(root / 'hosts.sqlite3')
            windows, wsl = (
                registry.register('fixture', kind, kind=kind, authority='normal-' + kind,
                                  destination='localhost', operator=True)['target']
                for kind in ('windows', 'wsl'))
            to_windows, to_wsl = str(uuid4()), str(uuid4())
            effects = root / 'effects.txt'
            adapter = root / 'owner_adapter.py'
            adapter.write_text(
                "import json,sys\nfrom pathlib import Path\n"
                "msg=json.load(sys.stdin)\n"
                "with Path(sys.argv[1]).open('a') as log: log.write(msg['identifier']+'\\n')\n"
                "if msg['payload']=='lost reply': sys.exit(9)\n"
                "print(json.dumps(dict(id=msg['identifier'],recipient=msg['recipient'],"
                "expires_at_micros=msg['expires_at_micros'],status='submitted',"
                "receipt_id='exact-'+msg['identifier'])))\n")
            configs = {}
            for local, peer, recipient in ((windows, wsl, to_windows), (wsl, windows, to_wsl)):
                name = local['environment']
                state = root / name
                state.mkdir(mode=0o700)
                config = root / (name + '.json')
                config.write_text(json.dumps(dict(root=str(state), registry=str(registry.path),
                    owner=local, peer=peer, bindings={recipient: [sys.executable, str(adapter), str(effects)]})))
                config.chmod(0o600)
                configs[name] = config
            parser = argparse.ArgumentParser()
            add_arguments(parser)
            now = 2_000_000_000

            def cli(owner, verb, *extra, request=None, dsn=DSN, expect=0):
                args = ['--config', str(configs[owner]), verb, *extra]
                if request is not None:
                    path = root / 'request.json'
                    path.write_text(json.dumps(request))
                    args.extend(['--request', str(path)])
                output = io.StringIO()
                clock = lambda: dict(utc=dict(status='network', sources=['test-a', 'test-b'],
                                               lower=now, upper=now))
                with patch.dict(os.environ, {'CODEX_WAKE_OWNER_DB_DSN': dsn}), redirect_stdout(output):
                    self.assertEqual(command(parser.parse_args(args), clock=clock), expect, output.getvalue())
                return json.loads(output.getvalue())

            identifier, reply, lost, stale, expired = (str(uuid4()) for _ in range(5))
            expiration = (now + 60) * 1_000_000
            original = dict(identifier=identifier, recipient=to_wsl, body='original', expires=expiration)
            self.assertEqual(cli('windows', 'send', request=original)['status'], 'waiting_for_database')
            self.assertEqual(cli('windows', 'tick'), dict(status='ready', shared_ingress=True))
            self.assertEqual(cli('windows', 'status', identifier)['status'], 'waiting_for_wsl')
            self.assertFalse(effects.exists())
            self.assertEqual(cli('wsl', 'tick')['status'], 'ready')
            self.assertEqual(cli('wsl', 'status', identifier, '--inbound')['status'], 'held_policy')
            self.assertEqual(cli('wsl', 'set-local', request=dict(recipient=to_wsl, revision=0, dnd=False))['revision'], 1)
            self.assertEqual(cli('wsl', 'tick')['status'], 'ready')
            self.assertEqual(cli('windows', 'send', request=original)['status'], 'waiting_for_wsl')
            self.assertEqual(cli('windows', 'tick')['status'], 'ready')
            self.assertEqual(cli('windows', 'status', identifier)['receipt_id'], 'exact-' + identifier)
            self.assertEqual(cli('wsl', 'tick')['status'], 'ready')

            self.assertEqual(cli('windows', 'set-local', request=dict(recipient=to_windows, revision=0, dnd=False))['revision'], 1)
            cli('wsl', 'send', request=dict(identifier=reply, recipient=to_windows, body='reply',
                                            expires=expiration, in_reply_to=identifier))
            self.assertEqual(cli('wsl', 'tick')['status'], 'ready')
            self.assertEqual(cli('wsl', 'status', reply)['status'], 'waiting_for_windows')
            self.assertEqual(cli('windows', 'tick')['status'], 'ready')
            cli('wsl', 'tick')
            self.assertEqual(cli('wsl', 'status', reply)['receipt_id'], 'exact-' + reply)
            with psycopg.connect(DSN) as conn:
                self.assertEqual(conn.execute("""SELECT in_reply_to,expires_at_micros FROM wake_messages_v1
                    WHERE message_id=%s""", (reply,)).fetchone(), (identifier, expiration))

            # A recipient can change its local policy while shared ingress is down.
            self.assertFalse(cli('windows', 'tick', dsn='')['shared_ingress'])
            self.assertEqual(cli('wsl', 'set-local', dsn='', request=dict(recipient=to_wsl, revision=1, dnd=True))['revision'], 2)
            cli('windows', 'request-setting', dsn='', request=dict(
                identifier=stale, recipient=to_wsl, revision=1, dnd=False))
            cli('windows', 'send', dsn='', request=dict(
                identifier=expired, recipient=to_wsl, body='expired', expires=(now+1)*1_000_000))
            now += 2
            cli('windows', 'tick')
            cli('wsl', 'tick')
            cli('windows', 'tick')
            self.assertEqual(cli('windows', 'status', stale),
                             dict(id=stale, status='revision_conflict', revision=2, dnd=True))
            self.assertEqual(cli('windows', 'status', expired)['status'], 'expired')
            self.assertEqual(cli('wsl', 'settings', to_wsl)['revision'], 2)
            cli('wsl', 'set-local', request=dict(recipient=to_wsl, revision=2, dnd=False))

            cli('windows', 'send', request=dict(identifier=lost, recipient=to_wsl, body='lost reply', expires=expiration))
            cli('windows', 'tick')
            cli('wsl', 'tick')
            self.assertEqual(cli('wsl', 'status', lost, '--inbound')['status'], 'uncertain')
            cli('windows', 'tick')
            self.assertEqual(cli('windows', 'status', lost)['status'], 'uncertain')
            self.assertEqual(effects.read_text().splitlines(), [identifier, reply, lost])

            # Simulate a restored shared image missing this test pair's journal.
            ids = [identifier, reply, lost, stale, expired]
            with psycopg.connect(DSN) as conn:
                scopes = [row[0] for row in conn.execute(
                    'SELECT DISTINCT destination FROM wake_owner_handoffs_v1 WHERE id=ANY(%s)', (ids,))]
                conn.execute('DELETE FROM wake_owner_handoffs_v1 WHERE id=ANY(%s)', (ids,))
                conn.execute('DELETE FROM wake_message_attempts_v1 WHERE message_id=ANY(%s)', (ids,))
                conn.execute('DELETE FROM wake_messages_v1 WHERE message_id=ANY(%s)', (ids,))
                conn.execute('DELETE FROM wake_owner_settings_v1 WHERE owner=ANY(%s)', (scopes,))
            for owner in ('windows', 'wsl', 'windows'):
                self.assertEqual(cli(owner, 'tick')['status'], 'ready')
            self.assertEqual(effects.read_text().splitlines(), [identifier, reply, lost])
            with psycopg.connect(DSN) as conn:
                states = dict(conn.execute("""SELECT message_id,state FROM wake_message_attempts_v1
                    WHERE message_id=ANY(%s)""", (ids,)).fetchall())
            self.assertEqual(states, {identifier: 'submitted', reply: 'submitted', lost: 'uncertain'})
