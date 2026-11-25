"""Durable, pinned Windows/WSL forwarding custody and owner reconciliation."""
from __future__ import annotations

from contextlib import closing
from dataclasses import asdict
from hashlib import sha256
import json
from decimal import Decimal
import math
import re
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4

from .message_delivery import DeliveryReceipt, Message, PostgresMessages, deliver
from .message_owner_registry import resolve_owner_pair
from .native_clock import snapshot, valid_utc


_FINAL = {'submitted', 'uncertain', 'expired', 'applied', 'revision_conflict'}
_WAITING = {'owner_admitted', 'held_dnd', 'held_policy', 'held_recipient', 'waiting_for_time'}
_SCHEMA = """CREATE TABLE IF NOT EXISTS wake_owner_handoffs_v1 (
    source text NOT NULL, destination text NOT NULL, id text NOT NULL,
    request jsonb NOT NULL, outcome jsonb,
    PRIMARY KEY (source,destination,id))"""


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _owner_key(target):
    return 'owner:' + sha256(_encode(target).encode()).hexdigest()


def _state(status, **evidence):
    return dict(status=status, **evidence)


class MessageHandoff:
    """Only the destination owns dispatch and settings. SQLite survives a stale PG restore."""

    def __init__(self, root, registry, local, peer, dsn, *, clock=snapshot):
        self.root = Path(root)
        self.registry, self.local, self.peer = registry, local, peer
        self.kind, self.peer_kind = resolve_owner_pair(registry, local, peer)
        self.local_key, self.peer_key = _owner_key(local), _owner_key(peer)
        self.store = PostgresMessages(dsn) if dsn else None
        self.clock = clock
        self._schema_ready = False
        with self._journal() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS transfers (
                    id text NOT NULL, direction text NOT NULL, request text NOT NULL,
                    outcome text NOT NULL, PRIMARY KEY(id,direction));
                CREATE TABLE IF NOT EXISTS settings (
                    recipient text PRIMARY KEY, revision integer NOT NULL, dnd integer NOT NULL);
                CREATE TABLE IF NOT EXISTS owner_pins (
                    singleton integer PRIMARY KEY CHECK(singleton=1), local text NOT NULL, peer text NOT NULL);
            """)
            with db:
                db.execute('INSERT OR IGNORE INTO owner_pins VALUES (1,?,?)', (self.local_key, self.peer_key))
                pins = db.execute('SELECT local,peer FROM owner_pins').fetchone()
                if pins != (self.local_key, self.peer_key):
                    raise ValueError('local journal belongs to a different owner pair')

    def _database(self, name):
        return closing(sqlite3.connect(self.root / name, timeout=1))

    def _journal(self):
        return self._database('message-owner.sqlite3')

    def service_lock(self):
        return self._database('message-owner-service.sqlite3')

    def _check_pins(self):
        resolve_owner_pair(self.registry, self.local, self.peer)

    def initialize(self):
        if self.store is None:
            raise OSError('shared message store is not configured')
        self.store.initialize()
        with self.store._connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('wake_owner_handoffs_v1'))")
            conn.execute(_SCHEMA)
            conn.execute("""CREATE TABLE IF NOT EXISTS wake_owner_settings_v1 (
                owner text NOT NULL, recipient text NOT NULL, revision bigint NOT NULL, dnd boolean NOT NULL,
                PRIMARY KEY (owner,recipient))""")
            conn.execute("""CREATE INDEX IF NOT EXISTS wake_owner_handoffs_destination_v1
                ON wake_owner_handoffs_v1(destination,source,id)""")

    def send(self, identifier, recipient, body, *, expires, due=None, in_reply_to=None, origin=None):
        identifier = str(UUID(identifier))
        recipient = str(UUID(recipient))
        if in_reply_to is not None:
            in_reply_to = str(UUID(in_reply_to))
        if not isinstance(body, str) or len(body.encode()) > 65536 or not body.strip() or '\x00' in body:
            raise ValueError('handoff body requires 1–65536 UTF-8 bytes')
        message = Message(identifier, 'direct', self.peer_key, recipient, expires, body,
                          self.local_key, in_reply_to, due)
        envelope = {key: getattr(message, key) for key in (
            'identifier', 'source', 'scope', 'recipient', 'expires_at_micros',
            'payload', 'sender', 'in_reply_to', 'not_before_micros')}
        request = dict(message=envelope)
        if origin is not None:
            if not isinstance(origin, str) or not re.fullmatch(r'[0-9a-f]{64}', origin):
                raise ValueError('invalid message admission origin')
            request['origin'] = origin
        return self._request(identifier, request)

    def request_setting(self, identifier, recipient, *, revision, dnd):
        identifier, recipient = str(UUID(identifier)), str(UUID(recipient))
        if type(revision) is not int or revision < 0 or type(dnd) is not bool:
            raise ValueError('remote settings require the original owner revision and a Boolean value')
        return self._request(identifier, dict(setting=dict(recipient=recipient, revision=revision, dnd=dnd)))

    def _request(self, identifier, request):
        self._check_pins()
        with self._journal() as db, db:
            self._put(db, identifier, 'out', request, _state('waiting_for_database'))
        return self.status(identifier, 'out')

    def status(self, identifier, direction, *, recipient=None, origin=None):
        with self._journal() as db:
            row = db.execute('SELECT request,outcome FROM transfers WHERE id=? AND direction=?',
                             (identifier, direction)).fetchone()
        if row is None:
            return dict(id=identifier, status='not_found')
        outcome = json.loads(row[1])
        if recipient is not None or origin is not None:
            request = json.loads(row[0])
            message = request.get('message', {})
            if (origin is None or request.get('origin') != origin
                    or recipient is None or message.get('recipient') != recipient):
                return dict(id=identifier, status='not_found')
            outcome = {key: outcome[key] for key in (
                'status', 'attempt_id', 'receipt_id', 'reason', 'evidence_kind', 'execution', 'acknowledgment')
                if key in outcome}
            outcome.update(not_before_micros=message['not_before_micros'],
                           expires_at_micros=message['expires_at_micros'])
        return dict(id=identifier, **outcome)

    def settings(self, recipient):
        recipient = str(UUID(recipient))
        with self._journal() as db:
            row = db.execute('SELECT revision,dnd FROM settings WHERE recipient=?', (recipient,)).fetchone()
        return dict(recipient=recipient, revision=row[0], dnd=bool(row[1])) if row else dict(recipient=recipient, revision=0)

    def set_local(self, recipient, *, revision, dnd):
        self._check_pins()
        recipient = str(UUID(recipient))
        if type(revision) is not int or revision < 0 or type(dnd) is not bool:
            raise ValueError('settings require the original owner revision and a Boolean value')
        with self._journal() as db, db:
            db.execute('BEGIN IMMEDIATE')
            return self._set(db, recipient, revision, dnd)

    @staticmethod
    def _set(db, recipient, revision, dnd):
        row = db.execute('SELECT revision,dnd FROM settings WHERE recipient=?', (recipient,)).fetchone()
        current = row[0] if row else 0
        if current != revision:
            return _state('revision_conflict', revision=current, dnd=bool(row[1]) if row else None)
        db.execute("""INSERT INTO settings VALUES (?,?,?) ON CONFLICT(recipient) DO UPDATE SET
                      revision=excluded.revision,dnd=excluded.dnd""", (recipient, current + 1, int(dnd)))
        return _state('applied', revision=current + 1, dnd=dnd)

    @staticmethod
    def _put(db, identifier, direction, request, outcome):
        value = _encode(request)
        db.execute('INSERT OR IGNORE INTO transfers VALUES (?,?,?,?)',
                   (identifier, direction, value, _encode(outcome)))
        row = db.execute('SELECT request,outcome FROM transfers WHERE id=? AND direction=?',
                         (identifier, direction)).fetchone()
        if row[0] != value:
            raise ValueError('original handoff identity conflicts with another request')
        return json.loads(row[1])

    @staticmethod
    def _save(db, identifier, direction, outcome):
        db.execute('UPDATE transfers SET outcome=? WHERE id=? AND direction=?',
                   (_encode(outcome), identifier, direction))

    def _publish(self, conn, identifier, source, destination, request):
        from psycopg.types.json import Jsonb

        if 'message' in request:
            message = Message(**request['message'])
            if (message.scope, message.sender, message.identifier) != (destination, source, identifier):
                raise ValueError('handoff message does not match its pinned owners and identity')
            self.store._admit(conn, message)
        conn.execute('''INSERT INTO wake_owner_handoffs_v1(source,destination,id,request)
                        VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                     (source, destination, identifier, Jsonb(request)))
        old, outcome = conn.execute('''SELECT request,outcome FROM wake_owner_handoffs_v1
            WHERE source=%s AND destination=%s AND id=%s FOR UPDATE''',
                                    (source, destination, identifier)).fetchone()
        if old != request:
            raise ValueError('shared handoff identity conflicts with another request')
        return outcome

    def _publish_owner(self, conn, identifier, request, outcome):
        old = self._publish(conn, identifier, self.peer_key, self.local_key, request)
        if old and old['status'] in _FINAL:
            if old != outcome:
                raise ValueError('shared outcome conflicts with the original owner receipt')
        if outcome.get('attempt_id'):
            # Rebuild the exact effect fence from local journal evidence after restore.
            message = Message(**request['message'])
            attempt = outcome['attempt_id']
            key = (message.scope, message.identifier, attempt)
            previous = self._attempt(conn, key)
            if outcome['status'] == 'uncertain' and previous is not None:
                if previous[0] == 'unsent':
                    outcome = _state('held_recipient', reason=previous[2])
                    self._publish_disposition(conn, identifier, outcome)
                    return outcome
                if previous[0] in ('submitted', 'uncertain'):
                    outcome = self._outcome(attempt, DeliveryReceipt(*previous))
            expected = (outcome['status'], outcome.get('receipt_id'), outcome.get('reason'),
                        outcome.get('evidence_kind'), outcome.get('execution'), outcome.get('acknowledgment'))
            conn.execute("""INSERT INTO wake_message_attempts_v1
                (scope,message_id,attempt_id,state,receipt_id,reason,evidence_kind,execution,acknowledgment)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (scope,message_id,attempt_id) DO UPDATE SET
                  state=excluded.state, receipt_id=excluded.receipt_id, reason=excluded.reason,
                  evidence_kind=excluded.evidence_kind, execution=excluded.execution,
                  acknowledgment=excluded.acknowledgment
                WHERE wake_message_attempts_v1.state='submitting'""", (*key, *expected))
            actual = self._attempt(conn, key)
            if actual != expected:
                raise ValueError('shared attempt conflicts with original local owner evidence')
        self._publish_disposition(conn, identifier, outcome)
        return outcome

    @staticmethod
    def _attempt(conn, key):
        return conn.execute("""SELECT state,receipt_id,reason,evidence_kind,execution,acknowledgment
            FROM wake_message_attempts_v1 WHERE scope=%s AND message_id=%s AND attempt_id=%s""", key).fetchone()

    def _publish_disposition(self, conn, identifier, outcome):
        from psycopg.types.json import Jsonb

        conn.execute("""UPDATE wake_owner_handoffs_v1 SET outcome=%s
            WHERE source=%s AND destination=%s AND id=%s""",
                     (Jsonb(outcome), self.peer_key, self.local_key, identifier))

    def _publish_settings(self, db):
        local = {recipient: (revision, bool(dnd))
                 for recipient, revision, dnd in db.execute('SELECT recipient,revision,dnd FROM settings')}
        with self.store._connect() as conn:
            shared = conn.execute('SELECT recipient,revision,dnd FROM wake_owner_settings_v1 WHERE owner=%s',
                                  (self.local_key,)).fetchall()
            for recipient, revision, dnd in shared:
                current = local.get(recipient)
                if current is None or current[0] < revision or current[0] == revision and current[1] != dnd:
                    raise ValueError('local owner settings journal conflicts with shared settings')
            for recipient, (revision, dnd) in local.items():
                conn.execute("""INSERT INTO wake_owner_settings_v1 VALUES (%s,%s,%s,%s)
                    ON CONFLICT(owner,recipient) DO UPDATE SET revision=excluded.revision,dnd=excluded.dnd
                    WHERE wake_owner_settings_v1.revision < excluded.revision""",
                             (self.local_key, recipient, revision, dnd))

    def _sync(self):
        """Project all local facts before admitting new work in a restored database."""
        kicks = []
        with self._journal() as db:
            self._publish_settings(db)
            for identifier, raw, saved in db.execute(
                    "SELECT id,request,outcome FROM transfers WHERE direction='in' ORDER BY id"):
                request, outcome = json.loads(raw), json.loads(saved)
                with self.store._connect() as conn:
                    if outcome['status'] == 'submitting':
                        outcome = self._recover_attempt(conn, identifier, outcome)
                    outcome = self._publish_owner(conn, identifier, request, outcome)
                with db:
                    self._save(db, identifier, 'in', outcome)

            for identifier, raw, saved in db.execute(
                    "SELECT id,request,outcome FROM transfers WHERE direction='out' ORDER BY id"):
                request = json.loads(raw)
                with self.store._connect() as conn:
                    remote = self._publish(conn, identifier, self.local_key, self.peer_key, request)
                saved = json.loads(saved)
                if remote is None and saved['status'] not in {'waiting_for_database', 'waiting_for_' + self.peer_kind}:
                    # Retain an already observed receipt during PG restore.
                    continue
                outcome = remote or _state('waiting_for_' + self.peer_kind)
                with db:
                    self._save(db, identifier, 'out', outcome)
                if remote is None and 'message' in request:
                    kicks.append(Message(**request['message']))

            with self.store._connect() as conn:
                incoming = conn.execute("""SELECT id,request,outcome FROM wake_owner_handoffs_v1
                    WHERE source=%s AND destination=%s ORDER BY id""",
                                        (self.peer_key, self.local_key)).fetchall()
            for identifier, request, remote in incoming:
                with db:
                    outcome = self._put(db, identifier, 'in', request, remote or _state('owner_admitted'))
                with self.store._connect() as conn:
                    outcome = self._publish_owner(conn, identifier, request, outcome)
                with db:
                    self._save(db, identifier, 'in', outcome)
        return kicks

    def _recover_attempt(self, conn, identifier, submitting):
        attempt = submitting['attempt_id']
        row = self._attempt(conn, (self.local_key, identifier, attempt))
        if row and row[0] in ('submitted', 'uncertain'):
            return self._outcome(attempt, DeliveryReceipt(*row))
        if row and row[0] == 'unsent':
            return _state('held_recipient', reason=row[2])
        # The local begin is durable before any I/O. Absence does not establish
        # a negative result if the shared database could have been restored.
        return _state('uncertain', attempt_id=attempt, reason='local_attempt_requires_reconciliation')

    @staticmethod
    def _outcome(attempt, receipt):
        evidence = asdict(receipt)
        state = evidence.pop('state')
        return _state(state, attempt_id=attempt,
                      **{key: value for key, value in evidence.items() if value is not None})

    @staticmethod
    def _window(message, clock):
        utc = clock.get('utc')
        if not valid_utc(utc):
            return 'waiting_for_time'
        lower = math.floor(Decimal(str(utc['lower'])) * 1_000_000)
        upper = math.ceil(Decimal(str(utc['upper'])) * 1_000_000)
        if lower >= message.expires_at_micros:
            return 'expired'
        if upper >= message.expires_at_micros:
            return 'waiting_for_time'
        if message.not_before_micros is not None and lower < message.not_before_micros:
            return 'waiting_for_time'
        return 'eligible'

    def _execute(self, db, identifier, request, driver):
        if 'setting' in request:
            with db:
                db.execute('BEGIN IMMEDIATE')
                outcome = self._set(db, **request['setting'])
                self._save(db, identifier, 'in', outcome)
            self._publish_settings(db)
            return outcome

        message = Message(**request['message'])
        self._check_pins()
        clock = self.clock()
        window = self._window(message, clock)
        if window != 'eligible':
            return _state(window)
        with db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT dnd FROM settings WHERE recipient=?', (message.recipient,)).fetchone()
            if row is None:
                return _state('held_policy')
            if row[0]:
                return _state('held_dnd')
            if driver is None:
                return _state('held_recipient')
            attempt = str(uuid4())
            self._save(db, identifier, 'in', _state('submitting', attempt_id=attempt))

        receipt = deliver(self.store, message, attempt, lambda: driver(message), clock=lambda: clock)
        if receipt.state == 'unsent':
            return _state('held_recipient', reason=receipt.reason)
        if receipt.state == 'submitted' and not receipt.receipt_id:
            return _state('uncertain', attempt_id=attempt, reason='owner_receipt_unverified')
        return self._outcome(attempt, receipt)

    def tick(self, driver=None, activate=None):
        """Process one owning worker pass. Locks survive concurrent CLI calls and crashes."""
        self._check_pins()
        if self.store is None:
            return _state('waiting_for_database', shared_ingress=False)
        try:
            from psycopg import Error
        except ImportError:
            return _state('waiting_for_database', shared_ingress=False,
                          reason='postgres_dependency_unavailable')
        with self._database('message-owner-pump.sqlite3') as lock:
            try:
                lock.execute('BEGIN EXCLUSIVE')
            except sqlite3.OperationalError:
                return _state('owner_busy')
            try:
                self._initialize_if_needed()
                kicks = self._sync()
                with self._journal() as db:
                    for identifier, raw, result in db.execute(
                            "SELECT id,request,outcome FROM transfers WHERE direction='in' ORDER BY id"):
                        saved = json.loads(result)
                        if saved['status'] not in _WAITING:
                            continue
                        request = json.loads(raw)
                        outcome = self._execute(db, identifier, request, driver)
                        with db:
                            self._save(db, identifier, 'in', outcome)
                        with self.store._connect() as conn:
                            outcome = self._publish_owner(conn, identifier, request, outcome)
                        with db:
                            self._save(db, identifier, 'in', outcome)
            except (Error, OSError):
                self._schema_ready = False
                return _state('waiting_for_database', shared_ingress=False)
            if activate is not None and self.kind == 'windows':
                clock = self.clock() if kicks else {}
                if any(self._window(message, clock) == 'eligible' for message in kicks):
                    status = activate()
                    return _state('ready', shared_ingress=True, peer_activation=status)
            return _state('ready', shared_ingress=True)

    def _initialize_if_needed(self):
        if not self._schema_ready:
            # The handoff tables can survive an upgrade of the common Message
            # tables. Always initialize both on first contact or reconnection.
            self.initialize()
            self._schema_ready = True
