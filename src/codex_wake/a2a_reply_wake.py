"""Durable sender reply arms; delivery reuses the correlated mailbox outbox."""
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
import uuid
import json

from .a2a_identity import BusError
from .a2a_time import mailbox_time
from .a2a_sender_receipts import SenderReceiptAuthority
from .event_wake import EventWake
from .signal_records import WakeRecordPublisher, signal_journal_path
from .signal_store import SQLiteSignalModule
from .signals import Resume, WakeIntent, Invalid, Degraded


def arm_reply(actor, message_id, wake_root, authority_path, idempotency_key, expires_at):
    try:
        expiry = datetime.fromisoformat(expires_at)
        if (wake_root is None or authority_path is None or expiry.tzinfo is None
                or expiry.utcoffset() is None or not idempotency_key
                or len(idempotency_key.encode()) > 256):
            raise ValueError()
    except (TypeError, ValueError):
        raise BusError('invalid_argument', 'reply arm requires delegated wake root, key and timezone-aware expiry') from None
    root = Path(wake_root).resolve()
    adapter = SenderReceiptAuthority(authority_path, root).adapter(actor, message_id)
    module = SQLiteSignalModule(signal_journal_path(root),
        record_publisher=WakeRecordPublisher.for_managed_reader(root),
        lease_clock=lambda: mailbox_time(adapter.mailbox, upper=True))
    outcome = EventWake(module, adapters=[adapter], clock=lambda: mailbox_time(adapter.mailbox, upper=True),
        id_factory=lambda: 'wake_' + uuid.uuid4().hex).register(
            WakeIntent(adapter.request('reply'), Resume('Read the correlated mailbox reply.', Path(actor.root),
                dict(transport='owning_client_receipt', namespace=actor.namespace,
                     thread_id=actor.thread_id, bus_id=actor.bus_id,
                     request_message_id=message_id)), expires_at=expiry), idempotency_key=idempotency_key)
    if isinstance(outcome, (Invalid, Degraded)):
        raise BusError(outcome.code, 'reply arm registration unavailable; reconcile the same key before retry')
    return dict(wake_id=outcome.wake_id, arm_id=outcome.arm_id, source_instance=outcome.source_instance,
                status='registered', recovery=outcome.recovery, delivery='owning_client_receipt_candidate')


class ReplyWakeGate:
    """Match a real reply arm before releasing its existing notification job."""
    def __init__(self, scheduler, wake_root, authority_path):
        self.scheduler = scheduler
        self.root = Path(wake_root).resolve()
        self.authority = SenderReceiptAuthority(authority_path, self.root)

    def tick(self):
        from .daemon import default_signal_runners, poll_once, poll_result_dict
        from .a2a_receipt_family import receipt_source_registration
        from .source_registry import BuiltinSourceRegistry
        from .signal_records import current_reader_capability
        from .monitor import write_monitor_health
        current = mailbox_time(self.scheduler.mailbox)
        # This bounded worker is the actual managed reader for its explicit root.
        write_monitor_health(wake_root=self.root, source='a2a-worker', mode='notification')
        self.runtime = SQLiteSignalModule(signal_journal_path(self.root),
            record_publisher=WakeRecordPublisher(self.root, current_reader_capability(self.root)),
            lease_clock=lambda: mailbox_time(self.scheduler.mailbox, upper=True))
        runners = default_signal_runners(self.root, self.runtime,
            source_registry=BuiltinSourceRegistry((receipt_source_registration(self.authority.resolve),)))
        result = poll_once(self.root, now=current, dispatch=False, signal_runtime=self.runtime, signal_runners=runners)
        self.reconcile_submitted()
        write_monitor_health(wake_root=self.root, source='a2a-worker', mode='notification',
                             poll_result=poll_result_dict(result))
        return poll_result_dict(result)

    @contextmanager
    def guard(self, job):
        from .records import iter_records, find_record, WakeLifecycleLock
        with self.scheduler.mailbox.transaction() as database:
            self.scheduler._operator(database)
            row = self.scheduler.mailbox._row(database, job['message_id'])
            parent = row['in_reply_to']
            database.execute('ROLLBACK')
        if parent is None:
            yield None
            return
        # A reply job never substitutes for a missing, cancelled or expired arm.
        for found in iter_records(self.root):
            target = found.record.get('target', {})
            if (found.record.get('status') != 'firing'
                    or target.get('transport') != 'owning_client_receipt'
                    or target.get('request_message_id') != parent
                    or target.get('bus_id') != self.scheduler.mailbox.bus.bus_id
                    or json_key(target) != job['recipient_key']):
                continue
            with WakeLifecycleLock(self.root, found.record['id']):
                current = find_record(self.root, found.record['id'])
                if not self.runtime.authorize_firing_record(current.record):
                    continue
                armed = self.runtime.load_armed_signal(current.record['id'])
                try:
                    observer, actor = self.authority.resolve(armed)
                    if observer.bus.root != self.scheduler.mailbox.bus.root or actor.key != job['recipient_key']:
                        continue
                    if armed.expires_at is not None and armed.expires_at <= mailbox_time(observer, upper=True):
                        continue
                    # Revalidate independent authority immediately before transport.
                    with observer.transaction(actor) as database:
                        database.execute('ROLLBACK')
                except (BusError, AttributeError):
                    continue
                yield current
                return
        yield False

    def reconcile_submitted(self):
        """Finish only bookkeeping when a crash follows the mailbox send receipt."""
        from itertools import islice
        from .records import iter_records, find_record, WakeLifecycleLock
        for found in islice(iter_records(self.root), 100):
            target = found.record.get('target', {})
            if (found.record.get('status') != 'firing'
                    or target.get('transport') != 'owning_client_receipt'
                    or target.get('bus_id') != self.scheduler.mailbox.bus.bus_id):
                continue
            with WakeLifecycleLock(self.root, found.record['id']):
                current = find_record(self.root, found.record['id'])
                if not self.runtime.authorize_firing_record(current.record):
                    continue
                with self.scheduler.mailbox.transaction() as database:
                    self.scheduler._operator(database)
                    rows = database.execute('''SELECT e.message_id,a.attempt_id,a.evidence
                        FROM mail_envelopes e JOIN mail_outbox o USING(message_id)
                        JOIN mail_attempts a ON a.recipient_key=e.recipient_key
                        WHERE e.in_reply_to=? AND e.recipient_key=?
                        AND o.kind='notification' AND o.status='submitted' AND a.state='submitted'
                        ORDER BY e.global_seq LIMIT 100''',
                        (target.get('request_message_id'), json_key(target))).fetchall()
                    reconciled = None
                    for row in rows:
                        attempt = database.execute('SELECT message_ids FROM mail_attempts WHERE attempt_id=?',
                                                   (row['attempt_id'],)).fetchone()
                        evidence = json.loads(row['evidence'])
                        if (row['message_id'] in json.loads(attempt['message_ids'])
                                and evidence.get('transport') in ('owning_client_v1', 'tmux_notification_v1')
                                and evidence.get('exact_thread_id') == target.get('thread_id')
                                and isinstance(evidence.get('receipt_id'), str) and evidence['receipt_id']):
                            reconciled = (row['message_id'], row['attempt_id'], evidence['receipt_id'], evidence['transport'])
                            break
                    database.execute('ROLLBACK')
                if reconciled:
                    message_id, attempt_id, receipt_id, transport = reconciled
                    self.submitted(current, dict(message_id=message_id), attempt_id, receipt_id, transport=transport)

    def submitted(self, found, job, attempt_id, receipt_id, *, transport='owning_client_v1'):
        from .records import replace_record, append_event, format_utc
        if found is None:
            return
        now = mailbox_time(self.scheduler.mailbox, upper=True)
        record = dict(found.record)
        record.update(status='submitted', updated_at=format_utc(now),
                      transport_receipt=dict(message_id=job['message_id'], attempt_id=attempt_id,
                                             receipt_id=receipt_id, transport=transport))
        record = append_event(record, 'submitted', 'Correlated reply notification submitted to bound client', now)
        replace_record(self.root, found, record)


def json_key(target):
    from .a2a_mailbox import encoded
    return encoded([target.get('namespace'), target.get('thread_id')])
