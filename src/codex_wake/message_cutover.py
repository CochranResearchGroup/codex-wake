"""Owner-scoped migration of an idle legacy message and Wake pair."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .a2a_bus import BusStore, private_path
from .a2a_identity import BusError
from .message_delivery import PostgresMessages, direct_message, wake_message
from .monitor_ownership import MonitorOwnership
from .records import ACTIVE_STATUS_DIRS, WakeError, all_records
from .recurring_schedules import ScheduleStore
from .runtime_delivery import original_submission_expiry
from .wake_policy import _read, _write


POINTER = 'message-cutover-scope.json'
ACTIVATION = 'message-cutover-activation.json'
_ENV = 'CODEX_WAKE_CUTOVER_DB_DSN'


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _root(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise WakeError('message cutover requires a canonical absolute root')
    private_path(path, directory=True)
    return path


def activated_store(root):
    """Resolve only an explicitly activated scope. A prepared pointer is inert."""
    root = Path(root).resolve()
    try:
        pointer = _read(root / POINTER)
    except FileNotFoundError:
        return None
    if not isinstance(pointer, dict) or set(pointer) != {'version', 'wake_root', 'cutover_id'} or pointer['version'] != 1:
        raise WakeError('message cutover pointer is invalid')
    wake = _root(pointer['wake_root'])
    try:
        active = _read(wake / ACTIVATION)
    except FileNotFoundError:
        return None
    if (not isinstance(active, dict) or active.get('version') != 1
            or active.get('cutover_id') != pointer['cutover_id']
            or active.get('wake_root') != str(wake)
            or str(root) not in (active.get('wake_root'), active.get('bus_root'))):
        raise WakeError('message cutover activation does not match this root')
    dsn = os.environ.get(_ENV)
    if not dsn:
        raise WakeError('activated message scope requires its PostgreSQL configuration')
    return PostgresMessages(dsn, cutover_id=active['cutover_id'])


def _mail_snapshot(db):
    def rows(query):
        return [dict(row) for row in db.execute(query)]

    return {
        'mail': rows("""SELECT e.*,s.admission,s.notification,s.recipient,s.recipient_seq,
                           s.read_receipt,s.claim_receipt,s.claim_generation,
                           s.terminal_receipt,s.terminal_at,b.body
                    FROM mail_metadata e JOIN mail_state s USING(message_id)
                    LEFT JOIN mail_bodies b USING(message_id) ORDER BY e.global_seq"""),
        'receipts': rows('SELECT * FROM mail_receipts ORDER BY receipt_seq'),
        'attempts': rows('SELECT * FROM mail_attempts ORDER BY attempt_id'),
        'outbox': rows('SELECT * FROM mail_outbox ORDER BY outbox_id'),
    }


def _snapshot(wake, bus, db):
    records = all_records(wake, include_archive=True)
    expected_paths = {path for status in (*ACTIVE_STATUS_DIRS, 'archive')
                      for path in (wake / status).glob('*.json')}
    if expected_paths != {item.path for item in records}:
        raise BusError('invalid_legacy_wake', 'a legacy Wake record is unreadable')
    return {
        'wake_root': str(wake),
        'bus_root': str(bus.root),
        'wakes': [item.record for item in records],
        'schedules': ScheduleStore(wake).records(),
        **_mail_snapshot(db),
    }


def _summary(source):
    counts = {name: len(source[name]) for name in ('wakes', 'schedules', 'mail', 'receipts', 'attempts', 'outbox')}
    return dict(status='previewed', source_digest=_digest(source), counts=counts)


def _project(source, wake):
    """Keep original effects fenced. Rows with unavailable bodies stay history-only."""
    messages = {}
    attempts = {}
    for row in source['mail']:
        if row['body'] is None:
            if row['notification'] in ('pending', 'published', 'deferred', 'dispatching'):
                raise WakeError('active legacy message has no retained body')
            continue
        message = direct_message(json.loads(row['envelope']), row['body'])
        messages[message.identifier] = message
    for row in source['attempts']:
        evidence = json.loads(row['evidence'])
        for identifier in json.loads(row['message_ids']):
            if identifier not in messages:
                continue
            state = row['state']
            receipt = evidence.get('receipt_id')
            state = ('submitted' if state == 'submitted' and receipt else
                     'unsent' if state == 'unsent' else 'uncertain')
            attempts[identifier, row['attempt_id']] = (state, receipt, evidence.get('reason'),
                evidence.get('evidence_kind'), evidence.get('execution'), evidence.get('acknowledgment'))
    for row in source['mail']:
        identifier = row['message_id']
        if (identifier in messages and row['notification'] in ('dispatching', 'submitted', 'uncertain')
                and not any(mid == identifier and state[0] != 'unsent' for (mid, _), state in attempts.items())):
            attempts[identifier, 'legacy-disposition:' + identifier] = (
                'uncertain', None, 'original_notification_requires_reconciliation', None, None, None)
    for record in source['wakes']:
        if record.get('target', {}).get('transport') != 'native':
            continue
        delivery = record.get('native_delivery') or {}
        possible = bool(delivery) or record.get('status') in ('firing', 'submitted')
        try:
            expiry = original_submission_expiry(record)
        except (WakeError, KeyError, TypeError, ValueError):
            if possible:
                raise WakeError('original native effect lacks qualified expiry')
            continue
        message = wake_message(wake, record, expiry)
        if message.identifier in messages:
            raise WakeError('legacy message identity is ambiguous')
        messages[message.identifier] = message
        if possible:
            evidence = delivery.get('evidence') or {}
            queue = delivery.get('queue_id') or evidence.get('queue_id')
            receipt = queue or delivery.get('turn_id') or evidence.get('turn_id')
            state = 'submitted' if delivery.get('state') == 'accepted' and receipt else 'uncertain'
            attempt = delivery.get('submission_id') or 'legacy-disposition:' + message.identifier
            attempts[message.identifier, attempt] = (
                state, receipt, None if state == 'submitted' else 'original_wake_requires_reconciliation',
                ('native_queue_acceptance' if queue else 'native_turn_acceptance') if receipt else None,
                delivery.get('execution'), delivery.get('acknowledgment'))
    terminal = {row['message_id'] for row in source['mail']
                if row['admission'] != 'accepted' or row['notification'] in ('suppressed', 'failed')}
    terminal.update(record['id'] for record in source['wakes']
                    if record['status'] in ('cancelled', 'expired', 'failed', 'archived'))
    return messages, attempts, terminal


def _import_verified(store, source, wake, digest, cutover):
    from psycopg.types.json import Jsonb

    messages, attempts, terminal = _project(source, wake)
    with store._connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('wake_message_cutovers_v1'))")
        conn.execute("""CREATE TABLE IF NOT EXISTS wake_message_cutovers_v1 (
            cutover_id text PRIMARY KEY, source_digest text NOT NULL, snapshot jsonb NOT NULL)""")
        conn.execute("""INSERT INTO wake_message_cutovers_v1 VALUES (%s,%s,%s)
                        ON CONFLICT DO NOTHING""", (cutover, digest, Jsonb(source)))
        for message in messages.values():
            store._admit(conn, message)
            if message.identifier in terminal:
                conn.execute('UPDATE wake_messages_v1 SET local_terminal=true WHERE scope=%s AND message_id=%s',
                             (message.scope, message.identifier))
        for (identifier, attempt), expected in attempts.items():
            message = messages[identifier]
            key = (message.scope, message.identifier, attempt)
            conn.execute("""INSERT INTO wake_message_attempts_v1
                (scope,message_id,attempt_id,state,receipt_id,reason,evidence_kind,execution,acknowledgment)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""", (*key, *expected))
            actual = conn.execute("""SELECT state,receipt_id,reason,evidence_kind,execution,acknowledgment
                FROM wake_message_attempts_v1 WHERE scope=%s AND message_id=%s AND attempt_id=%s""", key).fetchone()
            if actual != expected:
                raise WakeError('original effect conflicts with stored PostgreSQL evidence')
        archived = conn.execute('SELECT source_digest,snapshot FROM wake_message_cutovers_v1 WHERE cutover_id=%s',
                                (cutover,)).fetchone()
        if not archived or archived[0] != digest or _digest(archived[1]) != digest:
            raise WakeError('PostgreSQL source snapshot failed verification')
    return len(messages), sum(state[0] == 'uncertain' for state in attempts.values())


def cutover(wake_root, bus_root, isolated_root, operator_capability, *, expected_source=None):
    isolated = _root(isolated_root)
    wake, bus_path = _root(wake_root), _root(bus_root)
    if wake == bus_path or any(path == isolated or not path.is_relative_to(isolated)
                              for path in (wake, bus_path)):
        raise BusError('message_cutover_refused', 'cutover requires distinct wake and bus roots inside the isolated scope')
    if wake.is_relative_to(bus_path) or bus_path.is_relative_to(wake):
        raise BusError('message_cutover_refused', 'cutover wake and bus roots must be disjoint')
    bus = BusStore(bus_path)
    with MonitorOwnership(wake) as owner, bus.maintenance_connection() as db:
        if not owner.acquired:
            raise BusError('message_cutover_refused', 'stop the isolated Wake monitor before cutover')
        bus.operator(db, Path(operator_capability))
        if not bus.meta(db, 'paused'):
            raise BusError('message_cutover_refused', 'pause the isolated mailbox before cutover')
        if any(not Path(row[0]).is_relative_to(isolated)
               for row in db.execute('SELECT root FROM enrollments')):
            raise BusError('message_cutover_refused', 'mailbox enrollment extends beyond the isolated scope')
        source = _snapshot(wake, bus, db)
        result = _summary(source)
        if expected_source is None:
            return result
        if result['source_digest'] != expected_source:
            raise BusError('message_cutover_refused', 'legacy scope changed since preview')
        dsn = os.environ.get(_ENV)
        if not dsn or os.environ.get('CODEX_WAKE_MESSAGE_DB_DSN'):
            raise BusError('message_cutover_refused', 'configure the isolated cutover database without the unscoped fixture override')
        cutover_id = 'cutover_' + expected_source
        pointer = dict(version=1, wake_root=str(wake), cutover_id=cutover_id)
        active = dict(pointer, bus_root=str(bus.root))
        for path, value in ((wake / POINTER, pointer), (bus.root / POINTER, pointer),
                            (wake / ACTIVATION, active)):
            try:
                previous = _read(path)
            except FileNotFoundError:
                continue
            if previous != value:
                raise BusError('message_cutover_refused', 'another cutover already owns the selected scope')
        store = PostgresMessages(dsn)
        store.initialize()
        messages, uncertain = _import_verified(store, source, wake, expected_source, cutover_id)
        if _digest(_snapshot(wake, bus, db)) != expected_source:
            raise BusError('message_cutover_refused', 'legacy scope changed during PostgreSQL verification')
        # Both pointers remain inert until one authoritative marker is committed.
        _write(wake / POINTER, pointer)
        _write(bus.root / POINTER, pointer)
        _write(wake / ACTIVATION, active)
        return dict(result, status='activated', cutover_id=cutover_id,
                    imported_messages=messages, uncertain_effects=uncertain)
