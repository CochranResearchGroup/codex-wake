"""Exact-message receipt replay into Wake; the mailbox remains receipt authority."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from types import MappingProxyType

from .a2a_identity import Actor, BusError
from .a2a_mailbox import Mailbox, encoded
from .signals import (Degraded, Eq, Ingested, Invalid, Matched, NormalizedObservation,
                      SignalRequest, SourceAnchor, SourceCommit, SourceContract, Verification,
                      SourceInstanceReconcileResult, SourceReconcileResult)


class ReceiptSignalAdapter:
    def __init__(self, mailbox: Mailbox, actor: Actor, message_id: str):
        self.mailbox, self.actor, self.message_id = mailbox, actor, message_id
        with mailbox.transaction(actor) as database:
            mailbox._participant(mailbox._row(database, message_id), actor)
            database.execute('ROLLBACK')
        identity = encoded([str(mailbox.bus.root), mailbox.bus.bus_id, actor.key, message_id])
        self.source_instance = 'mailbox-' + hashlib.sha256(identity.encode()).hexdigest()[:32]
        self.subject = 'message:' + message_id

    def descriptor(self):
        return encoded(dict(version=1, bus_root=str(self.mailbox.bus.root),
            bus_id=self.mailbox.bus.bus_id, actor_key=self.actor.key,
            actor_id=self.actor.actor_id, actor_generation=self.actor.generation,
            message_id=self.message_id))

    def authorized(self):
        try:
            with self.mailbox.transaction(self.actor) as database:
                self.mailbox._participant(self.mailbox._row(database, self.message_id), self.actor)
                database.execute('ROLLBACK')
            return True
        except (BusError, OSError):
            return False

    def valid_arm(self, armed):
        try:
            return (armed.spec in [self.request(kind) for kind in
                    ('received', 'reply', 'accepted', 'declined', 'completed', 'failed')]
                and armed.anchor.source_anchor == 'a2a:' + self.source_instance
                and armed.anchor.recovery == 'source_replay'
                and dict(armed.anchor.baseline) == dict(sequence=0, descriptor=self.descriptor())
                and armed.anchor.local_after_sequence == 0)
        except (AttributeError, TypeError, ValueError):
            return False

    @classmethod
    def restore(cls, armed, mailbox, actor):
        # Supplied authority is checked independently of the untrusted descriptor.
        adapter = cls(mailbox, actor, armed.spec.subject.removeprefix('message:'))
        if not adapter.valid_arm(armed):
            raise BusError('receipt_anchor_invalid', 'receipt arm does not match supplied exact authority')
        return adapter

    def contract(self):
        return SourceContract('a2a.receipt', self.source_instance, frozenset({'receipt'}),
                              frozenset({self.subject}), MappingProxyType(dict(
                                  receipt_kind=str, receipt_id=str, message_id=str, sequence=int)),
                              max_clauses=1, max_attribute_bytes=1024,
                              occurrence_order_attribute='sequence')

    def request(self, condition='reply'):
        if condition not in ('received','reply','accepted','declined','completed','failed'):
            raise BusError('invalid_argument', 'unsupported recipient receipt condition')
        return SignalRequest(1, 'a2a.receipt', self.source_instance, 'occurrence', 'receipt',
                             self.subject, 'occurs', (Eq('receipt_kind', condition),), 'required')

    def establish_anchor(self, spec, now):
        if spec not in [self.request(kind) for kind in ('received','reply','accepted','declined','completed','failed')]:
            return Invalid(None, 'A2A_RECEIPT_NOT_ALLOWED', ('receipt selector is outside exact message',))
        try:
            with self.mailbox.transaction(self.actor) as database:
                self.mailbox._participant(self.mailbox._row(database, self.message_id), self.actor)
                database.execute('ROLLBACK')
        except BusError:
            return Degraded(None, 'A2A_AUTHORITY_UNAVAILABLE', None)
        # Replay includes receipts committed before the arm; an already-observed
        # response remains a valid answer to wait-for-reply.
        descriptor = self.descriptor()
        if len(descriptor.encode()) > 4096:
            return Invalid(None, 'A2A_ANCHOR_INVALID', ('receipt descriptor exceeds its bound',))
        return SourceAnchor(0, 'a2a:' + self.source_instance,
                            MappingProxyType(dict(sequence=0, descriptor=descriptor)), 'source_replay')

    def mirror(self, module, *, limit=100):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise BusError('invalid_argument', 'receipt replay is limited to one hundred rows')
        previous = module.source_checkpoint('a2a.receipt', self.source_instance)
        if isinstance(previous, (Invalid, Degraded)):
            return previous
        after = previous.checkpoint_order if isinstance(previous, SourceCommit) else 0
        try:
            with self.mailbox.transaction(self.actor) as database:
                original = self.mailbox._row(database, self.message_id)
                self.mailbox._participant(original, self.actor)
                rows = database.execute('''SELECT r.*,e.in_reply_to,e.sender_key,e.recipient_key,o.payload
                    FROM mail_receipts r JOIN mail_envelopes e USING(message_id)
                    JOIN mail_outbox o ON o.receipt_id=r.receipt_id AND o.kind='receipt_signal'
                    WHERE r.receipt_seq>? AND (e.message_id=? OR e.in_reply_to=?)
                    ORDER BY r.receipt_seq LIMIT ?''', (after, self.message_id, self.message_id, limit)).fetchall()
                observations = []
                for row in rows:
                    intent = json.loads(row['payload'])
                    if intent.get('receipt_id') != row['receipt_id'] or intent.get('message_id') != row['message_id'] or intent.get('bus_id') != self.mailbox.bus.bus_id:
                        raise BusError('receipt_corrupt', 'signal outbox does not match journal receipt')
                    if row['in_reply_to'] == self.message_id:
                        if row['sender_key'] != original['recipient_key'] or row['recipient_key'] != original['sender_key']:
                            raise BusError('receipt_corrupt', 'reply does not match pinned conversation participants')
                        kind = 'reply' if row['kind'] == 'admitted' else 'reply_' + row['kind']
                    else:
                        kind = row['kind']
                    occurred = datetime.fromtimestamp(row['created'], timezone.utc)
                    observations.append(NormalizedObservation('a2a.receipt', self.source_instance, 'receipt', self.subject,
                        'mailbox_receipt', row['receipt_id'], occurred, occurred,
                        dict(receipt_kind=kind,receipt_id=row['receipt_id'],message_id=row['message_id'],sequence=row['receipt_seq']),
                        Verification('verified','committed_mailbox_receipt'), 'a2a:' + row['receipt_id']))
                database.execute('ROLLBACK')
            if not rows:
                return dict(status='caught_up', checkpoint=after, mirrored=0)
            last = rows[-1]
            # Exact immutable IDs/timestamps make replay after interrupted
            # acknowledgement idempotent in the independent signal journal.
            return module.ingest(observations, SourceCommit('a2a.receipt', self.source_instance,
                last['receipt_id'], last['receipt_seq'], datetime.fromtimestamp(last['created'], timezone.utc)))
        except BusError:
            return Degraded(None, 'A2A_AUTHORITY_UNAVAILABLE', None)


class ReceiptSignalRunner:
    """Explicitly authorized restore seam; no automatic bus or actor discovery."""

    def __init__(self, adapter, armed_signals):
        from itertools import islice
        self.adapter = adapter
        self.arms = tuple(islice(armed_signals, 101))

    def handles(self, armed):
        return armed.spec.source == 'a2a.receipt' and armed.spec.source_instance == self.adapter.source_instance

    def reconcile(self, module, now, limits):
        code, observed, degraded = 'A2A_READY', 0, 0
        if type(limits.max_candidates) is not int or limits.max_candidates < 1 or len(self.arms) > min(limits.max_candidates, 100) or any(
                not self.adapter.valid_arm(arm) for arm in self.arms):
            code, degraded = 'A2A_ANCHOR_INVALID', 1
        else:
            outcome = self.adapter.mirror(module, limit=min(limits.max_candidates, 100))
            if isinstance(outcome, Ingested):
                observed = sum(not receipt.duplicate for receipt in outcome.receipts)
            elif isinstance(outcome, (Degraded, Invalid)):
                code, degraded = 'A2A_AUTHORITY_UNAVAILABLE', 1
        row = SourceInstanceReconcileResult('a2a.receipt', self.adapter.source_instance,
                    1, observed, degraded, code, now)
        return SourceReconcileResult('a2a.receipt', 1, observed, degraded, (row,))

    def evaluate(self, module, armed, now, limits):
        if not self.adapter.valid_arm(armed):
            return Invalid(armed.wake_id, 'A2A_ANCHOR_INVALID', ('receipt arm is invalid',))
        if not self.adapter.authorized():
            return Degraded(armed.wake_id, 'A2A_AUTHORITY_UNAVAILABLE', None)
        outcome = module.evaluate(armed.wake_id, armed, now, limits)
        if isinstance(outcome, Matched):
            if not self.adapter.authorized():
                return Degraded(armed.wake_id, 'A2A_AUTHORITY_UNAVAILABLE', None)
            if module.reconcile_match_publication(armed.wake_id) is not True:
                return Degraded(armed.wake_id, 'A2A_PUBLICATION_UNAVAILABLE', None)
        return outcome
