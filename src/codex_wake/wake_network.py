"""Persistent peer enrollment and recipient discovery for the Wake hub."""
from __future__ import annotations

from hashlib import sha256
from hmac import compare_digest
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator

from .controller_auth import AuthError
from .managed_inventory import InventoryError
from .message_policy import stable_micros
from .native_clock import snapshot
from .unified_connectors import check_action

LIST = 'network.recipients'
_IDENTIFIER = r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$'
_ID = {'type': 'string', 'pattern': _IDENTIFIER}
_QUERY = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'peer_id': _ID, 'conversation_id': _ID,
        'name': {'type': 'string', 'minLength': 1, 'maxLength': 256},
    },
}
TOOLS = {'wake_network_recipients': (LIST, _QUERY)}
_DIRECTORY = {
    'type': 'object', 'additionalProperties': False,
    'required': ['revision', 'recipients'],
    'properties': {
        'revision': {'type': 'integer', 'minimum': 1, 'maximum': 2**63 - 1},
        'recipients': {
            'type': 'array', 'maxItems': 256,
            'items': {
                'type': 'object', 'additionalProperties': False,
                'required': ['conversation_id', 'name'],
                'properties': {'conversation_id': _ID, 'name': _QUERY['properties']['name']},
            },
        },
    },
}


def validate(config):
    if not isinstance(config, dict) or set(config) != {'dsn_file', 'stale_seconds'}:
        raise ValueError('explicit Wake network configuration required')
    if (not isinstance(config['dsn_file'], str) or not Path(config['dsn_file']).is_absolute()
            or type(config['stale_seconds']) is not int or not 1 <= config['stale_seconds'] <= 3600):
        raise ValueError('invalid Wake network configuration')


def _check(schema, value):
    if not Draft202012Validator(schema).is_valid(value):
        raise InventoryError('invalid_argument', 'invalid network request')


class WakeNetwork:
    def __init__(self, config, host, environment, *, clock=None):
        from .a2a_bus import private_path

        validate(config)
        path = Path(config['dsn_file'])
        private_path(path)
        self.dsn = path.read_text().strip()
        if not self.dsn or len(self.dsn) > 16384:
            raise ValueError('invalid Wake network database configuration')
        self.host, self.environment = host, environment
        self.clock = clock or snapshot
        self.stale_micros = config['stale_seconds'] * 1_000_000

    def connect(self):
        import psycopg

        return psycopg.connect(self.dsn, connect_timeout=3,
                               options='-c statement_timeout=3000 -c lock_timeout=2000')

    def initialize(self):
        with self.connect() as db:
            db.execute('SELECT pg_advisory_xact_lock(%s)', (783000784,))
            db.execute('''CREATE TABLE IF NOT EXISTS wake_network_peers_v1 (
                peer_id text PRIMARY KEY, credential text NOT NULL, enabled boolean NOT NULL,
                revision bigint, directory jsonb NOT NULL DEFAULT '[]'::jsonb,
                verified_at bigint)''')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS wake_network_unique_peer_credential_v1 '
                       'ON wake_network_peers_v1(credential)')

    def enroll(self, peer_id, token):
        if (not isinstance(peer_id, str) or not re.fullmatch(_IDENTIFIER, peer_id)
                or not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', token)):
            raise ValueError('invalid peer ID or credential')
        from psycopg.errors import UniqueViolation

        try:
            with self.connect() as db:
                registered = db.execute("""
                    INSERT INTO wake_network_peers_v1 (peer_id,credential,enabled) VALUES (%s,%s,true)
                    ON CONFLICT (peer_id) DO UPDATE SET credential=excluded.credential, enabled=true
                    WHERE wake_network_peers_v1.enabled OR wake_network_peers_v1.credential<>excluded.credential
                    RETURNING peer_id""", (peer_id, sha256(token.encode()).hexdigest())).fetchone()
                if registered is None:
                    raise ValueError('a revoked peer requires a replacement credential')
        except UniqueViolation:
            raise ValueError('credential is enrolled to a different peer') from None

    def revoke(self, peer_id):
        if not isinstance(peer_id, str) or not re.fullmatch(_IDENTIFIER, peer_id):
            raise ValueError('invalid peer ID')
        with self.connect() as db:
            peer = db.execute("""UPDATE wake_network_peers_v1
                SET enabled=false, verified_at=NULL WHERE peer_id=%s RETURNING peer_id""",
                (peer_id,)).fetchone()
            if peer is None:
                raise ValueError('unknown Wake network peer')
        return {'peer_id': peer_id, 'status': 'revoked'}

    def availability(self, enabled, verified_at, *, now):
        if not enabled:
            return 'offline'
        if now is not None and verified_at is not None and 0 <= now - verified_at <= self.stale_micros:
            return 'current'
        return 'stale'

    def peer_availability(self, db, peer_id):
        row = db.execute('SELECT enabled,verified_at FROM wake_network_peers_v1 WHERE peer_id=%s',
                         (peer_id,)).fetchone()
        if row is None:
            return 'offline'
        return self.availability(*row, now=stable_micros(self.clock(), upper=True))

    def authorize_peer(self, db, peer_id, authorization):
        if not authorization or not authorization.startswith('Bearer '):
            raise AuthError()
        token = authorization[7:]
        if not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', token):
            raise AuthError()
        row = db.execute('''SELECT credential, enabled FROM wake_network_peers_v1
                            WHERE peer_id=%s FOR SHARE''', (peer_id,)).fetchone()
        if not row or not row[1] or not compare_digest(row[0], sha256(token.encode()).hexdigest()):
            raise AuthError()

    def publish(self, peer_id, authorization, value):
        _check(_DIRECTORY, value)
        directory = sorted(value['recipients'], key=lambda item: item['conversation_id'])
        if len({item['conversation_id'] for item in directory}) != len(directory):
            raise InventoryError('invalid_argument', 'duplicate conversation identity')
        now = stable_micros(self.clock())
        with self.connect() as db:
            # Serialize publishers before authenticating, without lock promotion.
            db.execute('SELECT peer_id FROM wake_network_peers_v1 WHERE peer_id=%s FOR UPDATE', (peer_id,))
            self.authorize_peer(db, peer_id, authorization)
            old_revision, old_directory = db.execute(
                'SELECT revision,directory FROM wake_network_peers_v1 WHERE peer_id=%s', (peer_id,)).fetchone()
            revision = value['revision']
            if old_revision is not None and (revision < old_revision or
                                             revision == old_revision and directory != old_directory):
                raise InventoryError('directory_conflict', 'directory revision conflicts with accepted state')
            if now is None:
                raise InventoryError('trusted_time_unavailable', 'cannot verify directory freshness')
            db.execute('''UPDATE wake_network_peers_v1 SET revision=%s,directory=%s::jsonb,
                          verified_at=greatest(verified_at,%s) WHERE peer_id=%s''',
                       (revision, json.dumps(directory), now, peer_id))
        return {'peer_id': peer_id, 'revision': revision, 'status': 'accepted'}

    def permits_recipient(self, actor, peer_id, conversation_id):
        target = dict(host=self.host, environment=self.environment,
                      peer_id=peer_id, conversation_id=conversation_id)
        return any(scope.get('peer_id') == peer_id and
                   all(target.get(key) == value for key, value in scope.items())
                   for scope in actor.targets)

    def discover(self, actor, arguments):
        check_action(actor, LIST)
        if 'observe' not in actor.scopes:
            raise AuthError('insufficient_scope')
        _check(_QUERY, arguments)
        now = stable_micros(self.clock(), upper=True)
        with self.connect() as db:
            peers = db.execute('''SELECT peer_id, enabled, directory, verified_at
                                  FROM wake_network_peers_v1 WHERE (%s::text IS NULL OR peer_id=%s)
                                  ORDER BY peer_id''', (arguments.get('peer_id'),) * 2).fetchall()
        result = []
        for peer, enabled, directory, verified_at in peers:
            for item in directory:
                if not self.permits_recipient(actor, peer, item['conversation_id']):
                    continue
                if 'conversation_id' in arguments and arguments['conversation_id'] != item['conversation_id']:
                    continue
                if 'name' in arguments and arguments['name'].casefold() not in item['name'].casefold():
                    continue
                status = self.availability(enabled, verified_at, now=now)
                result.append(dict(item, peer_id=peer, availability=status, verified_at_micros=verified_at))
        return {'status': 'ambiguous' if len(result) > 1 and arguments else 'ok', 'recipients': result}


def enroll_main(argv=None):
    import argparse

    from .a2a_bus import private_path

    parser = argparse.ArgumentParser(description='Enroll or revoke one operator-approved Wake network peer')
    parser.add_argument('--dsn-file', required=True, type=Path)
    parser.add_argument('--peer-id', required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--credential-file', type=Path)
    action.add_argument('--revoke', action='store_true')
    args = parser.parse_args(argv)
    try:
        network = WakeNetwork({'dsn_file': str(args.dsn_file), 'stale_seconds': 60}, '', '')
        network.initialize()
        if args.revoke:
            print(json.dumps(network.revoke(args.peer_id), sort_keys=True))
        else:
            private_path(args.credential_file)
            network.enroll(args.peer_id, args.credential_file.read_text().strip())
        return 0
    except ValueError as error:
        parser.exit(2, f'codex-wake network peer: {error}\n')


if __name__ == '__main__':
    raise SystemExit(enroll_main())
