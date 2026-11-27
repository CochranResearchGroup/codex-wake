"""Durable hub custody for exact Message envelopes and owner receipts."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from uuid import UUID

from .controller_auth import AuthError
from .managed_inventory import InventoryError
from .message_delivery import Message, PostgresMessages
from .unified_connectors import check_action
from .wake_network import _ID, _check


SEND = 'network.messages.send'
STATUS = 'network.messages.status'
POLICIES = {
    SEND: ('control', 'Send a retained message to an exact Wake network recipient.', False),
    STATUS: ('observe', 'Read a Wake network message and its correlated replies.', True),
}

_UUID = {'type': 'string', 'pattern': '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'}
_MICROS = {'type': 'integer', 'minimum': 1, 'maximum': 2**63 - 1}
_BODY = {'type': 'string', 'minLength': 1, 'maxLength': 65536}


def _schema(properties, required=()):
    return dict(type='object', properties=properties, required=list(required), additionalProperties=False)


def _optional(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


_SEND_FIELDS = dict(id=_UUID, peer_id=_optional(_ID), conversation_id=_optional(_ID), body=_BODY,
                    not_before_micros=_optional(_MICROS), expires_at_micros=_MICROS, in_reply_to=_optional(_UUID))
_SEND = _schema(_SEND_FIELDS, ('id', 'peer_id', 'conversation_id', 'body', 'expires_at_micros'))
_PEER_SEND = _schema(dict(_SEND_FIELDS, sender_conversation_id=_ID),
                     ('id', 'peer_id', 'conversation_id', 'body', 'expires_at_micros', 'sender_conversation_id'))
_STATUS = _schema(dict(id=_UUID), ('id',))
TOOLS = {'wake_network_send': (SEND, _SEND), 'wake_network_message_status': (STATUS, _STATUS)}
_TERMINAL = {'submitted', 'uncertain', 'expired', 'bounced'}
_WAITING = {'owner_admitted', 'held_dnd', 'held_policy', 'held_recipient', 'waiting_for_time'}
_RECEIPT = _schema(dict(
    id=_UUID, conversation_id=_ID, expires_at_micros=_MICROS, not_before_micros=_optional(_MICROS),
    in_reply_to=_optional(_UUID), outcome=_schema(dict(
        status={'enum': sorted(_TERMINAL | _WAITING)}, attempt_id=_UUID,
        receipt_id={'type': 'string', 'minLength': 1, 'maxLength': 256},
        reason={'type': 'string', 'minLength': 1, 'maxLength': 256},
        evidence_kind={'type': 'string', 'minLength': 1, 'maxLength': 256},
        execution={'type': 'string', 'minLength': 1, 'maxLength': 256},
        acknowledgment={'type': 'string', 'minLength': 1, 'maxLength': 256}), ('status',))),
    ('id', 'conversation_id', 'expires_at_micros', 'not_before_micros', 'in_reply_to', 'outcome'))
_PULL = _schema(dict(limit={'type': 'integer', 'minimum': 1, 'maximum': 64},
                     after={'type': 'integer', 'minimum': 0, 'maximum': 2**63-1},
                     restore_allowlist={'const': True}))
_SELECT = """SELECT ordinal,id,source,source_conversation,destination,conversation,
                     envelope,outcome FROM wake_network_messages_v1"""


def _principal(actor):
    # Stable across access-token rotation, and distinct for independently granted clients.
    material = json.dumps([actor.issuer, actor.client_id, actor.subject, actor.grant_id], separators=(',', ':'))
    return 'client:' + hashlib.sha256(material.encode()).hexdigest()


def _peer(peer):
    return 'peer:' + peer


def _error(code, reason):
    return InventoryError(code, reason)


class NetworkMessages:
    def __init__(self, network):
        self.network = network
        self.messages = PostgresMessages(network.dsn)

    @contextmanager
    def _connect(self):
        from psycopg import Error

        try:
            with self.network.connect() as db:
                yield db
        except Error as exc:
            raise _error('network_store_unavailable', 'network message custody is unavailable') from exc

    def initialize(self):
        self.messages.initialize()
        with self._connect() as db:
            db.execute('SELECT pg_advisory_xact_lock(%s)', (783000785,))
            db.execute('''CREATE TABLE IF NOT EXISTS wake_network_messages_v1 (
                ordinal bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                id text NOT NULL UNIQUE, source text NOT NULL, source_conversation text,
                destination text NOT NULL, conversation text NOT NULL,
                envelope jsonb NOT NULL, outcome jsonb,
                in_reply_to text REFERENCES wake_network_messages_v1(id))''')
            db.execute('CREATE TABLE IF NOT EXISTS wake_network_restore_holds_v1 (id text PRIMARY KEY)')
            db.execute('CREATE TABLE IF NOT EXISTS wake_network_restore_mode_v1 (singleton boolean PRIMARY KEY CHECK (singleton))')
            db.execute('''CREATE INDEX IF NOT EXISTS wake_network_message_pull_v1
                ON wake_network_messages_v1(destination,ordinal)''')
            db.execute('''CREATE INDEX IF NOT EXISTS wake_network_message_replies_v1
                ON wake_network_messages_v1(in_reply_to,ordinal)''')

    def _authorize_client(self, actor, op, peer, conversation):
        check_action(actor, op)
        target = dict(host=self.network.host, environment=self.network.environment,
                      peer_id=peer, conversation_id=conversation)
        if POLICIES[op][0] not in actor.scopes or not any(
                scope.get('peer_id') == peer and isinstance(peer, str)
                and all(target.get(key) == value for key, value in scope.items()) for scope in actor.targets):
            raise AuthError('insufficient_scope')

    @staticmethod
    def _directory_target(db, peer, conversation):
        if not isinstance(peer, str) or not isinstance(conversation, str):
            raise _error('invalid_argument', 'exact destination required')
        row = db.execute('SELECT directory FROM wake_network_peers_v1 WHERE peer_id=%s FOR SHARE',
                         (peer,)).fetchone()
        if not row or not any(item['conversation_id'] == conversation for item in row[0]):
            raise _error('unknown_recipient', 'recipient is not in the pinned peer directory')

    @staticmethod
    def _summary(row, *, include_body=False):
        _, identifier, source, origin, destination, conversation, envelope, outcome = row
        target = destination[5:] if destination.startswith('peer:') else None
        value = dict(id=identifier, peer_id=target, conversation_id=conversation if target else None,
                     sender_peer_id=source[5:] if source.startswith('peer:') else None,
                     sender_conversation_id=origin, not_before_micros=envelope['not_before_micros'],
                     expires_at_micros=envelope['expires_at_micros'], in_reply_to=envelope['in_reply_to'],
                     outcome=outcome or {'status': 'hub_accepted'})
        if include_body:
            value['body'] = envelope['payload']
        return value

    @staticmethod
    def _row(db, identifier):
        return db.execute(_SELECT + ' WHERE id=%s', (identifier,)).fetchone()

    @staticmethod
    def _restore_view(db, row):
        if db.execute('SELECT 1 FROM wake_network_restore_holds_v1 WHERE id=%s', (row[1],)).fetchone():
            return (*row[:-1], {'status': 'restore_held', 'reason': 'owner_receipt_requires_reconciliation'})
        return row

    def _admit(self, db, source, sender, value):
        from psycopg.types.json import Jsonb

        identifier = value['id']
        body = value['body']
        lower, expiry = value.get('not_before_micros'), value['expires_at_micros']
        reply = value.get('in_reply_to')
        peer, conversation = value['peer_id'], value['conversation_id']
        if str(UUID(identifier)) != identifier or not body.strip() or '\x00' in body or len(body.encode()) > 65536:
            raise _error('invalid_argument', 'invalid message body or identity')
        if lower is not None and lower >= expiry:
            raise _error('invalid_argument', 'message eligibility must precede expiry')
        destination = _peer(peer) if peer is not None else None
        if reply is not None:
            original = self._row(db, reply)
            if not original or original[4] != source or original[5] != (sender or source):
                raise AuthError('insufficient_scope')
            if original[2].startswith('client:'):
                if destination is not None or conversation is not None:
                    raise _error('invalid_argument', 'reply must return to the original client')
                destination = conversation = original[2]
            elif (destination, conversation) != (original[2], original[3]):
                raise _error('invalid_argument', 'reply must return to the original peer conversation')
        if destination is None or conversation is None:
            raise _error('invalid_argument', 'exact destination required')
        msg = Message(identifier, 'direct', destination, conversation, expiry, body,
                      json.dumps([source, sender], separators=(',', ':')), reply, lower)
        envelope = {k: getattr(msg, k) for k in ('identifier', 'source', 'scope', 'recipient',
                    'expires_at_micros', 'payload', 'sender', 'in_reply_to', 'not_before_micros')}
        # Immutable retries retain acceptance even if directory visibility changes.
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,%s))', (identifier, 785))
        previous = self._row(db, identifier)
        if previous is not None:
            if previous[2:7] != (source, sender, destination, conversation, envelope):
                raise _error('message_conflict', 'message identity already has a different owner or envelope')
            return self._summary(self._restore_view(db, previous))
        if db.execute('SELECT 1 FROM wake_network_restore_holds_v1 WHERE id=%s', (identifier,)).fetchone():
            raise _error('restore_held', 'original admission is held for recovery')
        if peer is not None:
            self._directory_target(db, peer, conversation)
        if sender is not None:
            self._directory_target(db, source[5:], sender)
        self.messages._admit(db, msg)
        initial = Jsonb({'status': 'reply_available'}) if peer is None else None
        row = db.execute('''INSERT INTO wake_network_messages_v1
            (id,source,source_conversation,destination,conversation,envelope,outcome,in_reply_to)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING ordinal,id,source,source_conversation,destination,conversation,envelope,outcome''',
            (identifier, source, sender, destination, conversation, Jsonb(envelope), initial, reply)).fetchone()
        return self._summary(row)

    def client_send(self, actor, value):
        _check(_SEND, value)
        self._authorize_client(actor, SEND, value['peer_id'], value['conversation_id'])
        with self._connect() as db:
            return self._admit(db, _principal(actor), None, value)

    def client_status(self, actor, value):
        _check(_STATUS, value)
        source = _principal(actor)
        with self._connect() as db:
            row = self._row(db, value['id'])
            if not row or row[2] != source or not row[4].startswith('peer:'):
                raise AuthError('insufficient_scope')
            self._authorize_client(actor, STATUS, row[4][5:], row[5])
            replies = db.execute(_SELECT + ''' WHERE in_reply_to=%s AND destination=%s
                                              ORDER BY ordinal LIMIT 128''', (row[1], source)).fetchall()
            row = self._restore_view(db, row)
            availability = self.network.peer_availability(db, row[4][5:])
        return dict(self._summary(row), recipient_availability=availability,
                    replies=[self._summary(item, include_body='content.observe' in actor.scopes)
                             for item in replies])

    def peer_send(self, peer, authorization, value):
        _check(_PEER_SEND, value)
        with self._connect() as db:
            self.network.authorize_peer(db, peer, authorization)
            return self._admit(db, _peer(peer), value['sender_conversation_id'], value)

    def peer_status(self, peer, authorization, value):
        _check(_STATUS, value)
        with self._connect() as db:
            self.network.authorize_peer(db, peer, authorization)
            row = self._row(db, value['id'])
            if not row or row[2] != _peer(peer):
                raise AuthError('insufficient_scope')
            replies = db.execute(_SELECT + ''' WHERE in_reply_to=%s AND destination=%s
                                              ORDER BY ordinal LIMIT 128''', (row[1], _peer(peer))).fetchall()
            row = self._restore_view(db, row)
            availability = self.network.peer_availability(db, row[4][5:]) if row[4].startswith('peer:') else 'current'
        return dict(self._summary(row), recipient_availability=availability,
                    replies=[self._summary(item) for item in replies])

    def pull(self, peer, authorization, value):
        _check(_PULL, value)
        with self._connect() as db:
            self.network.authorize_peer(db, peer, authorization)
            restored = db.execute('SELECT 1 FROM wake_network_restore_mode_v1').fetchone()
            if restored and value.get('restore_allowlist') is not True:
                raise _error('restore_held', 'spoke does not enforce restored custody')
            rows = db.execute(_SELECT + """ WHERE destination=%s AND ordinal>%s
                AND NOT EXISTS (SELECT 1 FROM wake_network_restore_holds_v1 h
                                WHERE h.id=wake_network_messages_v1.id)
                AND coalesce(outcome->>'status','') <> ALL(%s)
                ORDER BY ordinal LIMIT %s""", (_peer(peer), value.get('after', 0), sorted(_TERMINAL), value.get('limit', 16))).fetchall()
        result = dict(deliveries=[dict(sequence=row[0], message=row[6], sender=self._summary(row))
                                  for row in rows])
        if restored:
            result['restore_allowlist'] = True
        return result

    def receipt(self, peer, authorization, value):
        from psycopg.types.json import Jsonb

        _check(_RECEIPT, value)
        outcome = value['outcome']
        state = outcome['status']
        if (state in {'submitted', 'uncertain'} and 'attempt_id' not in outcome
                or state == 'submitted' and 'receipt_id' not in outcome
                or state != 'submitted' and 'receipt_id' in outcome
                or state in _WAITING | {'expired', 'bounced'} and 'attempt_id' in outcome
                or state == 'bounced' and outcome.get('reason') not in {'recipient_dnd', 'recipient_busy'}):
            raise _error('invalid_argument', 'receipt lacks exact effect evidence')
        with self._connect() as db:
            self.network.authorize_peer(db, peer, authorization)
            row = db.execute(_SELECT + ' WHERE id=%s FOR UPDATE', (value['id'],)).fetchone()
            if not row or row[4] != _peer(peer):
                raise AuthError('insufficient_scope')
            if db.execute('SELECT 1 FROM wake_network_restore_holds_v1 WHERE id=%s', (row[1],)).fetchone():
                raise _error('restore_held', 'original owner journal must resolve restored custody')
            expected = self._summary(row)
            if any(value[key] != expected[key] for key in (
                    'conversation_id', 'expires_at_micros', 'not_before_micros', 'in_reply_to')):
                raise _error('message_conflict', 'receipt does not match original envelope')
            old = row[-1]
            if old is not None and old['status'] in _TERMINAL and old != outcome:
                raise _error('message_conflict', 'original owner receipt is already final')
            db.execute('UPDATE wake_network_messages_v1 SET outcome=%s WHERE id=%s', (Jsonb(outcome), row[1]))
        return dict(expected, outcome=outcome)
