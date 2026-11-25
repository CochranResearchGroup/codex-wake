"""Durable message admission and effect receipts shared by Wake and A2A."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from decimal import Decimal
import math
import os
from typing import Callable

from .runtime_delivery import RuntimeSubmission


@dataclass(frozen=True)
class Message:
    identifier: str
    source: str
    scope: str
    recipient: str
    expires_at_micros: int
    payload: str = field(repr=False)
    sender: str | None = None
    in_reply_to: str | None = None
    not_before_micros: int | None = None

    def __post_init__(self):
        if self.source not in ('direct', 'wake'):
            raise ValueError('unsupported message source')
        for value in (self.identifier, self.scope, self.recipient):
            if not isinstance(value, str) or not value or len(value) > 1024:
                raise ValueError('invalid message identity')
        if type(self.expires_at_micros) is not int or not 0 < self.expires_at_micros < 2**63:
            raise ValueError('invalid message expiry')
        if self.not_before_micros is not None and (type(self.not_before_micros) is not int
                                                   or not 0 < self.not_before_micros < 2**63):
            raise ValueError('invalid message eligibility')
        if not isinstance(self.payload, str):
            raise ValueError('invalid message payload')


@dataclass(frozen=True)
class DeliveryReceipt:
    state: str
    receipt_id: str | None = None
    reason: str | None = None
    evidence_kind: str | None = None
    execution: str | None = None
    acknowledgment: str | None = None


_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS wake_messages_v1 (
       scope text NOT NULL, message_id text NOT NULL, source text NOT NULL,
       recipient text NOT NULL, expires_at_micros bigint NOT NULL CHECK (expires_at_micros > 0),
       payload text NOT NULL, sender text, in_reply_to text, not_before_micros bigint,
       PRIMARY KEY (scope, message_id))""",
    'ALTER TABLE wake_messages_v1 ADD COLUMN IF NOT EXISTS not_before_micros bigint',
    """CREATE TABLE IF NOT EXISTS wake_message_attempts_v1 (
       scope text NOT NULL, message_id text NOT NULL, attempt_id text NOT NULL,
       state text NOT NULL CHECK (state IN ('submitting','submitted','unsent','uncertain')),
       receipt_id text, reason text, evidence_kind text, execution text, acknowledgment text,
       PRIMARY KEY (scope, message_id, attempt_id),
       FOREIGN KEY (scope, message_id) REFERENCES wake_messages_v1 (scope, message_id))""",
)


class PostgresMessages:
    """The owner commits before external I/O and cannot replay uncertain effects."""

    def __init__(self, dsn: str):
        self._dsn = dsn

    def _connect(self):
        import psycopg

        return psycopg.connect(self._dsn, connect_timeout=3,
                               options='-c statement_timeout=3000 -c lock_timeout=2000')

    def initialize(self):
        with self._connect() as conn:
            # Concurrent process startup can otherwise race on CREATE IF NOT EXISTS.
            conn.execute('SELECT pg_advisory_xact_lock(%s)', (80499432601277,))
            for statement in _SCHEMA:
                conn.execute(statement)

    @staticmethod
    def _identity(message):
        return message.scope, message.identifier

    def admit(self, message: Message):
        with self._connect() as conn:
            self._admit(conn, message)

    def _admit(self, conn, message):
        identity = self._identity(message)
        values = (message.source, message.recipient, message.expires_at_micros,
                  message.payload, message.sender, message.in_reply_to, message.not_before_micros)
        conn.execute(
            """INSERT INTO wake_messages_v1
               (scope,message_id,source,recipient,expires_at_micros,payload,sender,in_reply_to,not_before_micros)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (*identity, *values))
        original = conn.execute(
            """SELECT source,recipient,expires_at_micros,payload,sender,in_reply_to,not_before_micros
               FROM wake_messages_v1 WHERE scope=%s AND message_id=%s FOR UPDATE""",
            identity).fetchone()
        if original != values:
            raise ValueError('message identity already binds a different envelope')

    def prepare(self, message: Message, attempt_id: str) -> DeliveryReceipt | None:
        identity = self._identity(message)
        with self._connect() as conn:
            self._admit(conn, message)
            for saved_attempt, *columns in conn.execute(
                    """SELECT attempt_id,state,receipt_id,reason,evidence_kind,execution,acknowledgment
                       FROM wake_message_attempts_v1 WHERE scope=%s AND message_id=%s""",
                    identity):
                saved = DeliveryReceipt(*columns)
                if saved_attempt == attempt_id and saved.state in ('submitted', 'unsent'):
                    return saved
                if saved.state != 'unsent':
                    return DeliveryReceipt('uncertain', reason='original_message_effect_requires_reconciliation')
            conn.execute(
                """INSERT INTO wake_message_attempts_v1(scope,message_id,attempt_id,state)
                   VALUES (%s,%s,%s,'submitting')""", (*identity, attempt_id))
        return None

    def finish(self, message: Message, attempt_id: str, receipt: DeliveryReceipt):
        with self._connect() as conn:
            cursor = conn.execute(
                """UPDATE wake_message_attempts_v1
                   SET state=%s,receipt_id=%s,reason=%s,evidence_kind=%s,execution=%s,acknowledgment=%s
                   WHERE scope=%s AND message_id=%s AND attempt_id=%s AND state='submitting'""",
                (receipt.state, receipt.receipt_id, receipt.reason, receipt.evidence_kind,
                 receipt.execution, receipt.acknowledgment, *self._identity(message), attempt_id))
            if cursor.rowcount != 1:
                raise ValueError('message delivery attempt changed')


def configured_store() -> PostgresMessages | None:
    dsn = os.environ.get('CODEX_WAKE_MESSAGE_DB_DSN')
    return PostgresMessages(dsn) if dsn else None


def deliver(store: PostgresMessages, message: Message, attempt_id: str,
            effect: Callable[[], DeliveryReceipt], *, clock=None) -> DeliveryReceipt:
    """Persist a single effect intent and retain exact transport evidence."""
    from psycopg import Error
    from .native_clock import snapshot
    from .native_intents import valid_utc

    try:
        cached = store.prepare(message, attempt_id)
    except (Error, OSError):
        return DeliveryReceipt('unsent', reason='message_store_unavailable')
    except ValueError:
        return DeliveryReceipt('uncertain', reason='message_identity_conflict')
    if cached is not None:
        return cached

    try:
        utc = (clock or snapshot)().get('utc')
        if not valid_utc(utc):
            result = DeliveryReceipt('unsent', reason='message_delivery_time_unavailable')
        elif math.ceil(utc['upper'] * 1_000_000) >= message.expires_at_micros:
            result = DeliveryReceipt('unsent', reason='message_dispatch_window_closed')
        elif (message.not_before_micros is not None
              and math.floor(utc['lower'] * 1_000_000) < message.not_before_micros):
            result = DeliveryReceipt('unsent', reason='message_eligibility_unverified')
        else:
            result = effect()
            if result.state not in ('submitted', 'unsent', 'uncertain'):
                result = DeliveryReceipt('uncertain', reason='message_effect_outcome_unverified')
    except Exception:
        result = DeliveryReceipt('uncertain', reason='message_effect_outcome_unverified')
    try:
        store.finish(message, attempt_id, result)
    except (Error, OSError, ValueError):
        return DeliveryReceipt('uncertain', reason='message_receipt_commit_unverified')
    return result


def wake_message(root, record, expires_at_micros):
    # The legacy record ID is retained across both stores. A digest scopes it
    # to the original local owner without publishing its filesystem path.
    scope = 'wake:' + hashlib.sha256(str(root.resolve()).encode()).hexdigest()
    due = record.get('predicate', {}).get('due_at')
    if due:
        from .network_wakes import precise_deadline
        from datetime import UTC, datetime

        delta = precise_deadline(due) - datetime(1970, 1, 1, tzinfo=UTC)
        not_before = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    else:
        not_before = None
    return Message(record['id'], 'wake', scope, record['target']['thread_id'],
                   expires_at_micros, record['prompt'], not_before_micros=not_before)


def direct_message(envelope, payload):
    recipient = envelope['recipient']
    exact = json.dumps([recipient['namespace'], recipient['thread_id']], separators=(',', ':'))
    sender = envelope['sender']
    return Message(envelope['message_id'], 'direct', 'a2a:' + envelope['bus_id'], exact,
                   int(Decimal(str(envelope['expires_at'])) * 1_000_000), payload,
                   json.dumps([sender['namespace'], sender['thread_id']], separators=(',', ':')),
                   envelope.get('in_reply_to'))


def admission_status(store, message):
    from psycopg import Error
    try:
        store.admit(message)
    except (Error, OSError):
        return 'pending_shared_store'
    except ValueError:
        return 'identity_conflict'
    return 'recorded'


def submit_native_message(store, message, attempt_id, submit, *, clock=None):
    if store is None:
        return submit()
    original = None

    def effect():
        nonlocal original
        original = submit()
        state = 'uncertain'
        if original.state == 'accepted':
            state = 'submitted'
        elif original.state == 'not_sent' and original.pre_io:
            state = 'unsent'
        return DeliveryReceipt(state, original.receipt_id, original.reason, original.evidence_kind)

    receipt = deliver(store, message, attempt_id, effect, clock=clock)
    if original is not None and receipt.state in ('submitted', 'unsent'):
        return original
    if receipt.state == 'submitted':
        return RuntimeSubmission('accepted', receipt_id=receipt.receipt_id,
                                 evidence_kind=receipt.evidence_kind or 'none')
    if receipt.state == 'unsent':
        return RuntimeSubmission('not_sent', reason=receipt.reason, pre_io=True)
    return RuntimeSubmission('uncertain', reason=receipt.reason)
