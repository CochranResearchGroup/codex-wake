"""Durable caller-owned operation admission, correlation and result custody.

Effect owners remain authoritative. This journal never retries an admitted effect.
Mailbox and supervised-command adapters retain their own execution/cancellation
contracts; caller wait deadlines and disconnects do not cancel target work.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

from .controller_auth import Actor, AuthError
from .managed_inventory import InventoryError


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def bounded_id(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200 or any(ord(c) < 32 for c in value):
        raise InventoryError('invalid_argument', 'explicit bounded operation/correlation/binding identity required')
    return value


def identity(actor):
    return {key: getattr(actor, key) for key in ('issuer', 'resource', 'subject', 'client_id', 'grant_id')}


class ControllerRuntime:
    def __init__(self, root, *, adapter=None, now=time.time):
        self.root, self.adapter, self.now = Path(root), adapter, now
        directory = self.root / 'controller-operations'
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = directory / 'operations.sqlite'
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600); os.close(fd)
        os.chmod(self.path, 0o600)
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS operations (
                id TEXT PRIMARY KEY, intent_key TEXT UNIQUE, fingerprint TEXT, record TEXT);
                CREATE TABLE IF NOT EXISTS events (operation_id TEXT, sequence INTEGER,
                event_key TEXT, payload TEXT, PRIMARY KEY(operation_id,event_key));''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def _authorize(self, actor, target, capability, authorize=None):
        if not isinstance(actor, Actor) or actor.expires_at <= self.now() or capability not in actor.scopes:
            raise AuthError('insufficient_scope')
        if not isinstance(target, dict) or not {'host', 'environment'} <= target.keys():
            raise InventoryError('invalid_argument', 'pinned host/environment target required')
        if not any({'host', 'environment'} <= scope.keys() and all(target.get(k) == v for k, v in scope.items()) for scope in actor.targets):
            raise AuthError('insufficient_scope')
        if authorize is not None:
            current = authorize()
            if not isinstance(current, Actor) or identity(current) != identity(actor) or current.scopes != actor.scopes or current.targets != actor.targets or current.expires_at <= self.now():
                raise AuthError()
        return actor

    def _save(self, record):
        with self.connect() as db:
            db.execute('UPDATE operations SET record=? WHERE id=?', (encoded(record), record['operation_id']))

    def _event(self, record, key, value):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM events WHERE operation_id=? AND event_key=?', (record['operation_id'], key)).fetchone(): return
            sequence = db.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE operation_id=?', (record['operation_id'],)).fetchone()[0]
            db.execute('INSERT INTO events VALUES(?,?,?,?)', (record['operation_id'], sequence, key, encoded(dict(sequence=sequence, **value))))

    def _load(self, operation_id):
        bounded_id(operation_id)
        with self.connect() as db:
            row = db.execute('SELECT record FROM operations WHERE id=?', (operation_id,)).fetchone()
        if not row: raise InventoryError('operation_not_found', 'operation handle is not retained')
        return json.loads(row[0])

    def _owned(self, actor, record, authorize=None, *, capability='observe'):
        self._authorize(actor, record['target'], capability, authorize)
        if identity(actor) not in [record['principal'], *record.get('successors', [])]: raise AuthError('insufficient_scope')
        return record

    @staticmethod
    def projection(record):
        return {k: v for k, v in record.items() if k not in ('payload', 'principal', 'successors', 'authorization', 'fingerprint')}

    def envelope(self, operation, record, **extra):
        return dict(schema_version=1, operation=operation, status='completed',
            result=dict(operation=self.projection(record), **extra))

    def execute(self, actor, operation, arguments, *, authorize, dispatch):
        if not isinstance(arguments, dict) or not isinstance(arguments.get('_request'), dict):
            raise InventoryError('intent_required', 'explicit _request operation/idempotency/correlation/binding/target metadata required')
        meta = arguments['_request']
        if set(meta) != {'operation_id', 'idempotency_key', 'correlation_id', 'binding', 'target'}:
            raise InventoryError('invalid_argument', 'unsupported request metadata; caller identity is authenticated separately')
        for key in ('operation_id', 'idempotency_key', 'correlation_id', 'binding'): bounded_id(meta[key])
        payload = {k: v for k, v in arguments.items() if k != '_request'}
        target = meta['target']
        if 'expected_target' in payload and payload['expected_target'] != target:
            raise InventoryError('stale_target', 'request target differs from pinned owner target')
        capability = 'admin' if operation == 'builds.stage' else 'control'
        self._authorize(actor, target, capability, authorize)
        intent = dict(operation=operation, payload=payload, correlation_id=meta['correlation_id'], binding=meta['binding'], target=target)
        raw = encoded(intent)
        if len(raw.encode()) > 262144: raise InventoryError('invalid_argument', 'operation intent exceeds bounded capacity')
        fingerprint = hashlib.sha256(raw.encode()).hexdigest()
        intent_key = hashlib.sha256(encoded(dict(principal=identity(actor), key=meta['idempotency_key'])).encode()).hexdigest()
        record = dict(schema_version=1, operation_id=meta['operation_id'], operation=operation,
            correlation_id=meta['correlation_id'], binding=meta['binding'], original_binding=meta['binding'], target=target,
            principal=identity(actor), authorization=dict(scopes=sorted(actor.scopes), targets=actor.targets),
            payload=payload, payload_sha256=hashlib.sha256(encoded(payload).encode()).hexdigest(),
            created_at=self.now(), submission='admitted', execution='unknown', delivery='uncertain', acceptance='unknown',
            phase='dispatching', reason='dispatch_in_progress_or_interrupted', result=None, cancellation='not_requested')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT fingerprint,record FROM operations WHERE intent_key=?', (intent_key,)).fetchone()
            if previous:
                if previous[0] != fingerprint: raise InventoryError('idempotency_conflict', 'intent key already binds different immutable inputs')
                old = json.loads(previous[1]); self._owned(actor, old, authorize, capability=capability)
                return self.envelope(operation, old)
            if db.execute('SELECT COUNT(*) FROM operations').fetchone()[0] >= 10000:
                raise InventoryError('capacity', 'retained operation capacity reached')
            try: db.execute('INSERT INTO operations VALUES(?,?,?,?)', (meta['operation_id'], intent_key, fingerprint, encoded(record)))
            except sqlite3.IntegrityError: raise InventoryError('idempotency_conflict', 'operation ID already names another immutable intent')
        self._event(record, 'admitted', {'kind': 'admitted', 'operation_id': record['operation_id'], 'correlation_id': record['correlation_id']})
        dispatched = False
        try:
            self._authorize(actor, target, capability, authorize)
            dispatched = True
            value = dispatch(operation, payload)
            if len(encoded(value).encode()) > 262144: raise ValueError('effect result exceeds retained bound')
            if isinstance(value, dict) and value.get('_pending') is True:
                record.update(execution='queued', delivery='submitted', acceptance='pending', phase='waiting', reason=None, result=value['handle'])
            else:
                record.update(execution='completed', delivery='retained', acceptance='owner_reported', phase='terminal', reason=None, result=value)
            self._event(record, 'submitted' if record['phase'] == 'waiting' else 'completed', {'kind': record['phase'], 'operation_id': record['operation_id']})
        except Exception as error:
            record.update(execution='unknown' if dispatched else 'not_started', delivery='uncertain' if dispatched else 'not_submitted',
                reason=getattr(error, 'code', 'effect_uncertain'), phase='uncertain' if dispatched else 'terminal')
        self._save(record)
        # Grant loss can prevent delivery, never erase effect admission/result custody.
        self._authorize(actor, target, capability, authorize)
        return self.envelope(operation, record)

    def operation(self, actor, operation, arguments, *, authorize):
        if operation not in ('operations.result',): raise InventoryError('unsupported_operation', 'unsupported runtime operation')
        if not isinstance(arguments, dict) or set(arguments) != {'operation_id'}:
            raise InventoryError('invalid_argument', 'operation ID required')
        record = self._owned(actor, self._load(arguments['operation_id']), authorize)
        return self.envelope(operation, record)
