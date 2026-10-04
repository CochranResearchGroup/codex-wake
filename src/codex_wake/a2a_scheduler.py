"""Journal-fenced notification jobs. Derived projections never grant authority."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import uuid

from .a2a_identity import BusError
from .a2a_mailbox import Mailbox, encoded


@dataclass(frozen=True)
class Lease:
    name: str
    owner: str
    generation: int
    until: float


class MailScheduler:
    def __init__(self, mailbox: Mailbox, operator_capability: Path, *, owner=None, lease_seconds=30):
        if not 5 <= lease_seconds <= 60:
            raise BusError('invalid_argument', 'lease duration must be between five and sixty seconds')
        self.mailbox = mailbox
        self.operator_capability = operator_capability
        self.owner = owner or 'scheduler_' + uuid.uuid4().hex
        self.lease_seconds = lease_seconds
        with mailbox.transaction() as database:
            mailbox.bus.operator(database, operator_capability)
            database.execute('ROLLBACK')

    def _operator(self, database):
        self.mailbox.bus.operator(database, self.operator_capability)
        if self.mailbox.bus.recovery_held(database):
            raise BusError('recovery_hold', 'scheduler is held pending recovery gap reconciliation')

    def acquire(self, name='dispatcher'):
        with self.mailbox.transaction() as database:
            self._operator(database)
            now = self.mailbox._now(database)
            row = database.execute('SELECT * FROM mail_leases WHERE name=?', (name,)).fetchone()
            if row and row['lease_until'] > now:
                if row['owner'] != self.owner:
                    database.execute('ROLLBACK')
                    return None
                lease = Lease(name, self.owner, row['generation'], now + self.lease_seconds)
            else:
                lease = Lease(name, self.owner, row['generation'] + 1 if row else 1, now + self.lease_seconds)
            database.execute('INSERT INTO mail_leases VALUES (?,?,?,?) ON CONFLICT(name) DO UPDATE SET owner=excluded.owner,generation=excluded.generation,lease_until=excluded.lease_until',
                             (lease.name, lease.owner, lease.generation, lease.until))
            database.execute('COMMIT')
            return lease

    def _fence(self, database, lease, now):
        row = database.execute('SELECT * FROM mail_leases WHERE name=?', (lease.name,)).fetchone()
        if lease.owner != self.owner or not row or row['owner'] != lease.owner or row['generation'] != lease.generation or row['lease_until'] <= now:
            raise BusError('stale_lease', 'scheduler ownership expired or changed')

    def release(self, lease):
        with self.mailbox.transaction() as database:
            self._operator(database)
            now = self.mailbox._now(database)
            self._fence(database, lease, now)
            database.execute('UPDATE mail_leases SET lease_until=? WHERE name=?', (now, lease.name))
            database.execute('COMMIT')

    def jobs(self, lease, *, limit=100):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise BusError('invalid_argument', 'scheduler scan is limited to one hundred intents')
        with self.mailbox.transaction() as database:
            self._operator(database)
            now = self.mailbox._now(database)
            self._fence(database, lease, now)
            rows = database.execute("SELECT o.*,e.global_seq FROM mail_outbox o JOIN mail_envelopes e USING(message_id) WHERE o.kind='notification' AND o.status IN ('pending','published','deferred') AND o.next_attempt<=? ORDER BY e.global_seq LIMIT ?", (now, limit)).fetchall()
            jobs = []
            for intent in rows:
                row = self.mailbox._expire(database, self.mailbox._row(database, intent['message_id']), now)
                if row['admission'] != 'accepted':
                    continue
                jobs.append(dict(schema_version=1, job_id=intent['outbox_id'], bus_id=self.mailbox.bus.bus_id,
                                 message_id=row['message_id'], recipient_key=row['recipient_key'],
                                 expires_at=row['expires'], kind='a2a.notification'))
            database.execute('COMMIT')
            return jobs

    def publish(self, lease, projection_root: Path, *, limit=100):
        jobs = self.jobs(lease, limit=limit)
        published = []
        for job in jobs:
            # Publication is deliberately outside SQLite; reconcile exact bytes
            # if interrupted before the journal acknowledgement.
            path = publish_job(projection_root, job)
            with self.mailbox.transaction() as database:
                self._operator(database)
                now = self.mailbox._now(database)
                self._fence(database, lease, now)
                intent = database.execute('SELECT * FROM mail_outbox WHERE outbox_id=?', (job['job_id'],)).fetchone()
                row = self.mailbox._expire(database, self.mailbox._row(database, job['message_id']), now)
                if row['admission'] == 'accepted' and intent['status'] in ('pending','published','deferred'):
                    if intent['status'] == 'pending':
                        database.execute("UPDATE mail_outbox SET status='published' WHERE outbox_id=?", (job['job_id'],))
                        self.mailbox._record(database, job['message_id'], 'job_published', 'scheduler', now,
                                             dict(job_id=job['job_id']))
                    published.append(dict(job_id=job['job_id'], path=str(path)))
                database.execute('COMMIT')
        return published

    def _authorized(self, database, row):
        # Recheck grants; an immutable envelope does not preserve revoked rights.
        for key, permission in [(row['sender_key'], 'send'), (row['recipient_key'], 'receive')]:
            namespace, thread_id = json.loads(key)
            actor = database.execute('SELECT a.*,e.can_send,e.can_receive,e.can_notify FROM actors a JOIN enrollments e ON a.root=e.root WHERE a.namespace=? AND a.thread_id=?', (namespace, thread_id)).fetchone()
            if not actor or actor['revoked'] or not actor['can_' + permission]:
                return False
            if permission == 'receive' and not actor['can_notify']:
                return False
        return True

    def defer(self, lease, job_id, reason, *, seconds=5):
        if reason not in {'paused','busy','offline','capability_unavailable','rate_limit','authorization_denied'} or not 1 <= seconds <= 300:
            raise BusError('invalid_argument', 'unsupported bounded deferral')
        with self.mailbox.transaction() as database:
            self._operator(database)
            now = self.mailbox._now(database)
            self._fence(database, lease, now)
            intent = database.execute("SELECT * FROM mail_outbox WHERE outbox_id=? AND kind='notification'", (job_id,)).fetchone()
            if not intent or intent['status'] not in ('pending','published','deferred'):
                raise BusError('not_processable', 'notification is not available for deferral')
            row = self.mailbox._expire(database, self.mailbox._row(database, intent['message_id']), now)
            if row['admission'] == 'accepted':
                database.execute("UPDATE mail_outbox SET status='deferred',next_attempt=? WHERE outbox_id=?", (now + seconds, job_id))
                database.execute("UPDATE mail_state SET notification='deferred' WHERE message_id=?", (row['message_id'],))
                # Backoff and rate-capped event metadata: no repeated receipt per polling tick.
                previous = database.execute("SELECT details FROM mail_receipts WHERE message_id=? AND kind='deferred' ORDER BY receipt_seq DESC LIMIT 1", (row['message_id'],)).fetchone()
                if not previous or json.loads(previous['details']).get('reason') != reason:
                    self.mailbox._record(database, row['message_id'], 'deferred', 'scheduler', now, dict(reason=reason))
            database.execute('COMMIT')

    def claim(self, dispatcher, recipient_lease, job_ids):
        if not isinstance(job_ids, list) or not 1 <= len(job_ids) <= 20 or len(set(job_ids)) != len(job_ids):
            raise BusError('invalid_argument', 'notification batch requires one to twenty distinct intent IDs')
        with self.mailbox.transaction() as database:
            self._operator(database)
            now = self.mailbox._now(database)
            self._fence(database, dispatcher, now)
            self._fence(database, recipient_lease, now)
            if self.mailbox.bus.meta(database, 'paused'):
                raise BusError('paused', 'notification dispatch is paused')
            rows = []
            for identifier in job_ids:
                intent = database.execute("SELECT * FROM mail_outbox WHERE outbox_id=? AND kind='notification'", (identifier,)).fetchone()
                if not intent or intent['status'] not in ('pending','published','deferred') or intent['next_attempt'] > now:
                    raise BusError('not_processable', 'notification intent cannot be dispatched')
                row = self.mailbox._expire(database, self.mailbox._row(database, intent['message_id']), now)
                if row['admission'] != 'accepted' or row['notification'] not in ('pending','deferred'):
                    raise BusError('not_processable', 'message no longer authorizes notification')
                if recipient_lease.name != 'recipient:' + row['recipient_key'] or not self._authorized(database, row):
                    raise BusError('authorization_denied', 'exact enrolled recipient is not authorized for notification')
                if intent['attempts'] >= 3:
                    raise BusError('attempt_limit', 'actual notification attempt limit reached')
                rows.append((intent, row))
            recipient_key = rows[0][1]['recipient_key']
            count = database.execute('SELECT count(*) FROM mail_attempts WHERE recipient_key=? AND created>?', (recipient_key, now - 3600)).fetchone()[0]
            if count >= 10:
                raise BusError('rate_limit', 'recipient notification hourly limit reached')
            # Prevent overtaking any earlier still-pending message to this recipient.
            earlier = database.execute("SELECT o.outbox_id FROM mail_outbox o JOIN mail_envelopes e USING(message_id) JOIN mail_state s USING(message_id) WHERE o.kind='notification' AND e.recipient_key=? AND s.admission='accepted' AND o.status IN ('pending','published','deferred','dispatching','uncertain') ORDER BY e.global_seq LIMIT ?", (recipient_key, len(job_ids))).fetchall()
            if [r[0] for r in earlier] != job_ids:
                raise BusError('fifo_conflict', 'notification batch would overtake earlier intent')
            attempt = 'attempt_' + uuid.uuid4().hex
            database.execute('INSERT INTO mail_attempts VALUES (?,?,?,?,?,?,?,?)', (attempt, recipient_key, encoded([r['message_id'] for _, r in rows]), self.owner, recipient_lease.generation, now, 'dispatching', encoded(dict(dispatcher_generation=dispatcher.generation))))
            for intent, row in rows:
                database.execute("UPDATE mail_outbox SET status='dispatching',owner=?,generation=?,lease_until=?,attempts=attempts+1 WHERE outbox_id=?", (self.owner, recipient_lease.generation, recipient_lease.until, intent['outbox_id']))
                database.execute("UPDATE mail_state SET notification='dispatching' WHERE message_id=?", (row['message_id'],))
                self.mailbox._record(database, row['message_id'], 'dispatch_claimed', 'scheduler', now, dict(attempt_id=attempt, generation=recipient_lease.generation))
            self.mailbox._finish(database)
            return dict(attempt_id=attempt, recipient_key=recipient_key, message_ids=[r['message_id'] for _, r in rows])

    def finish(self, dispatcher, recipient_lease, attempt_id, *, outcome, evidence):
        if outcome not in ('submitted','unsent','uncertain') or not isinstance(evidence, dict) or len(encoded(evidence).encode()) > 4096:
            raise BusError('invalid_argument', 'bounded typed transport outcome required')
        if any(key not in {'transport','receipt_id','reason','exact_thread_id','daemon_generation'} or not isinstance(value, (str, int, bool)) or len(str(value)) > 1024 for key, value in evidence.items()):
            raise BusError('invalid_argument', 'transport evidence contains unsupported fields')
        with self.mailbox.transaction() as database:
            self._operator(database)
            now = self.mailbox._now(database)
            self._fence(database, dispatcher, now)
            self._fence(database, recipient_lease, now)
            attempt = database.execute('SELECT * FROM mail_attempts WHERE attempt_id=?', (attempt_id,)).fetchone()
            if not attempt or attempt['owner'] != self.owner or attempt['generation'] != recipient_lease.generation or recipient_lease.name != 'recipient:' + attempt['recipient_key'] or attempt['state'] != 'dispatching':
                raise BusError('stale_attempt', 'attempt ownership or state changed')
            exact_thread = json.loads(attempt['recipient_key'])[1]
            if outcome == 'submitted' and (evidence.get('exact_thread_id') != exact_thread or
                    not isinstance(evidence.get('transport'), str) or not evidence['transport'] or
                    not isinstance(evidence.get('receipt_id'), str) or not evidence['receipt_id']):
                raise BusError('transport_evidence_invalid', 'submission requires an exact-thread transport receipt')
            if outcome == 'unsent' and evidence.get('reason') not in {'pre_io_failure','explicit_not_sent','fixture_pre_io'}:
                raise BusError('transport_evidence_invalid', 'only qualified provably-unsent evidence permits retry')
            database.execute('UPDATE mail_attempts SET state=?,evidence=? WHERE attempt_id=?', (outcome, encoded(evidence), attempt_id))
            for message_id in json.loads(attempt['message_ids']):
                intent = database.execute("SELECT * FROM mail_outbox WHERE message_id=? AND kind='notification'", (message_id,)).fetchone()
                if outcome == 'unsent':
                    state = 'failed' if intent['attempts'] >= 3 else 'deferred'
                    next_attempt = now + (5, 30, 120)[intent['attempts'] - 1]
                else:
                    state, next_attempt = outcome, 0
                database.execute('UPDATE mail_outbox SET status=?,next_attempt=?,lease_until=NULL WHERE outbox_id=?', (state, next_attempt, intent['outbox_id']))
                database.execute('UPDATE mail_state SET notification=? WHERE message_id=?', (state, message_id))
                self.mailbox._record(database, message_id, 'notification_' + state, 'scheduler', now, dict(attempt_id=attempt_id, evidence=evidence))
            self.mailbox._finish(database)

    def recover(self, dispatcher, *, limit=100):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise BusError('invalid_argument', 'recovery scan is limited to one hundred intents')
        with self.mailbox.transaction() as database:
            self._operator(database)
            now = self.mailbox._now(database)
            self._fence(database, dispatcher, now)
            rows = database.execute("SELECT * FROM mail_outbox WHERE kind='notification' AND status='dispatching' AND lease_until<=? LIMIT ?", (now, limit)).fetchall()
            for row in rows:
                database.execute("UPDATE mail_outbox SET status='uncertain' WHERE outbox_id=?", (row['outbox_id'],))
                database.execute("UPDATE mail_state SET notification='uncertain' WHERE message_id=?", (row['message_id'],))
                self.mailbox._record(database, row['message_id'], 'notification_uncertain', 'scheduler', now, dict(reason='dispatch_lease_expired'))
            # An attempt remains uncertain as a whole if any constituent send is unknown.
            for attempt in database.execute("SELECT * FROM mail_attempts WHERE state='dispatching' ORDER BY created LIMIT 100").fetchall():
                if any(row['message_id'] in json.loads(attempt['message_ids']) for row in rows):
                    database.execute("UPDATE mail_attempts SET state='uncertain' WHERE attempt_id=?", (attempt['attempt_id'],))
            database.execute('COMMIT')
            return len(rows)


def publish_job(root: Path, job: dict):
    """Atomic private projection, reconciled by deterministic bytes and exact ID."""
    if not root.is_absolute() or root.is_symlink() or root.resolve() != root:
        raise BusError('projection_denied', 'projection root must be canonical and private')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise BusError('projection_denied', 'projection root is not owner-only')
    identifier = job.get('job_id')
    if not isinstance(identifier, str) or not identifier.startswith('notify_msg_') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in identifier):
        raise BusError('projection_denied', 'unsafe job identity')
    target = root / (identifier + '.json')
    payload = (encoded(job) + '\n').encode()
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.stat().st_uid != os.getuid() or target.stat().st_mode & 0o077 or target.read_bytes() != payload:
            raise BusError('projection_conflict', 'existing projection differs from journal intent')
        return target
    temporary = root / ('.' + identifier + '_' + uuid.uuid4().hex)
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.is_symlink() or target.read_bytes() != payload:
                raise BusError('projection_conflict', 'concurrent projection differs')
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
        return target
    finally:
        temporary.unlink(missing_ok=True)
