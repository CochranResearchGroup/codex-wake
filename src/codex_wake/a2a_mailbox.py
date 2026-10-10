"""Transactional mailbox authority; notification and consumption are independent."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
import threading
import uuid

from .a2a_bus import BusStore
from .a2a_identity import Actor, BusError, RuntimeIdentity

MAILBOX_SCHEMA = 2
NETWORK_MAILBOX_SCHEMA = 3
TERMINAL = frozenset({'declined', 'completed', 'failed'})


def encoded(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def retired_key_digest(sender_key: str, key: str) -> str:
    return hashlib.sha256(encoded([sender_key, key]).encode()).hexdigest()


def thread_key(identity: RuntimeIdentity) -> str:
    return encoded([identity.namespace, identity.thread_id])


class Mailbox:
    def __init__(self, bus: BusStore, *, clock=time.time, monotonic=time.monotonic,
                 fault=None, time_provider=None, max_open=1000, max_messages=100000, max_bytes=1024**3, rate_limit=10):
        self.bus, self.clock, self.monotonic, self.fault = bus, clock, monotonic, fault
        self.time_provider = time_provider
        self._time_context = threading.local()
        self.max_open, self.max_messages, self.max_bytes, self.rate_limit = max_open, max_messages, max_bytes, rate_limit
        self.boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        with bus.connection() as database:
            self._schema(database)

    def pending_thread_work(self, thread_id: str) -> list[dict]:
        """Inspect lifecycle blockers without reading message bodies or expiring work."""
        with self.bus.connection(read_only=True) as database:
            rows = database.execute(
                "SELECT e.message_id, e.recipient_key, 'message' AS kind "
                "FROM mail_metadata e JOIN mail_state s USING(message_id) "
                "WHERE s.admission='accepted' AND s.recipient NOT IN ('declined','completed','failed') "
                "UNION SELECT message_id, recipient_key, kind FROM mail_outbox "
                "WHERE kind='notification' AND status IN ('pending','published','deferred','dispatching','uncertain')"
            ).fetchall()
        result = []
        for row in rows:
            try:
                identity = json.loads(row['recipient_key'])
                if (not isinstance(identity, list) or len(identity) != 2
                        or any(not isinstance(part, str) or not part for part in identity)):
                    raise ValueError()
            except (ValueError, TypeError):
                raise BusError('inventory_unavailable', 'pending mailbox attribution is unavailable') from None
            if identity[1] == thread_id:
                result.append(dict(message_id=row['message_id'], kind=row['kind']))
        return result

    @staticmethod
    def _schema(database):
        row = database.execute("SELECT value FROM meta WHERE key='mailbox_schema'").fetchone()
        version = json.loads(row[0]) if row else None
        if type(version) is not int or version not in (MAILBOX_SCHEMA, NETWORK_MAILBOX_SCHEMA):
            raise BusError('unsupported_mailbox_schema', 'mailbox domain requires an explicit supported migration')
        if version == NETWORK_MAILBOX_SCHEMA:
            policy = database.execute("SELECT value FROM meta WHERE key='mail_time_policy'").fetchone()
            if not policy or json.loads(policy[0]) != dict(version=1,mode='network-first',authentication='plain-ntp-explicit-opt-in'):
                raise BusError('unsupported_time_policy','network time policy is missing or unsupported')

    @classmethod
    def migrate(cls, bus: BusStore, operator_capability: Path) -> str:
        with bus.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            bus.operator(database, operator_capability)
            previous = database.execute("SELECT value FROM meta WHERE key='mailbox_schema'").fetchone()
            if previous:
                version = json.loads(previous[0])
                if type(version) is int and version == 1:
                    cls._migrate_identity(database)
                    database.execute("UPDATE meta SET value=? WHERE key='mailbox_schema'", (encoded(MAILBOX_SCHEMA),))
                    receipt = bus.event(database, 'operator', 'migrate_mailbox', dict(from_version=1, to_version=MAILBOX_SCHEMA))
                    database.execute('COMMIT')
                    return receipt
                cls._schema(database)
                database.execute('ROLLBACK')
                return 'already_current'
            statements = [
                '''CREATE TABLE mail_envelopes (global_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE NOT NULL, sender_key TEXT NOT NULL, recipient_key TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, created REAL NOT NULL,
                    expires REAL NOT NULL, envelope TEXT NOT NULL, in_reply_to TEXT REFERENCES mail_envelopes(message_id), UNIQUE(sender_key,idempotency_key))''',
                '''CREATE TABLE mail_bodies (message_id TEXT PRIMARY KEY REFERENCES mail_envelopes(message_id), body TEXT NOT NULL)''',
                '''CREATE TABLE mail_state (message_id TEXT PRIMARY KEY REFERENCES mail_envelopes(message_id),
                    recipient_seq INTEGER NOT NULL, admission TEXT NOT NULL, notification TEXT NOT NULL,
                    recipient TEXT NOT NULL, read_receipt TEXT, claim_receipt TEXT, claim_generation INTEGER,
                    terminal_receipt TEXT, terminal_at REAL)''',
                '''CREATE TABLE mail_sequences (recipient_key TEXT PRIMARY KEY, next_sequence INTEGER NOT NULL)''',
                '''CREATE TABLE mail_receipts (receipt_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id TEXT UNIQUE NOT NULL REFERENCES events(receipt_id),
                    message_id TEXT NOT NULL REFERENCES mail_envelopes(message_id), kind TEXT NOT NULL,
                    actor_key TEXT NOT NULL, created REAL NOT NULL, details TEXT NOT NULL)''',
                '''CREATE TABLE mail_outbox (outbox_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    message_id TEXT NOT NULL REFERENCES mail_envelopes(message_id), receipt_id TEXT,
                    recipient_key TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
                    generation INTEGER NOT NULL DEFAULT 0, owner TEXT, lease_until REAL,
                    attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0)''',
                '''CREATE TABLE mail_leases (name TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    generation INTEGER NOT NULL, lease_until REAL NOT NULL)''',
                '''CREATE TABLE mail_attempts (attempt_id TEXT PRIMARY KEY, recipient_key TEXT NOT NULL,
                    message_ids TEXT NOT NULL, owner TEXT NOT NULL, generation INTEGER NOT NULL,
                    created REAL NOT NULL, state TEXT NOT NULL, evidence TEXT NOT NULL)''',
                'CREATE INDEX mail_recipient ON mail_envelopes(recipient_key,global_seq)',
                'CREATE INDEX mail_sender ON mail_envelopes(sender_key,global_seq)',
                'CREATE INDEX mail_replies ON mail_envelopes(in_reply_to,global_seq)',
                'CREATE INDEX mail_pending ON mail_outbox(kind,status,next_attempt)',
                '''CREATE TRIGGER mail_envelope_immutable BEFORE UPDATE ON mail_envelopes BEGIN SELECT RAISE(ABORT,'immutable envelope'); END''',
                '''CREATE TRIGGER mail_body_immutable BEFORE UPDATE ON mail_bodies BEGIN SELECT RAISE(ABORT,'immutable body'); END''',
                '''CREATE TRIGGER mail_receipt_immutable BEFORE UPDATE ON mail_receipts BEGIN SELECT RAISE(ABORT,'immutable receipt'); END''',
            ]
            for statement in statements:
                database.execute(statement)
            cls._migrate_identity(database)
            database.execute('INSERT INTO meta VALUES (?,?)', ('mailbox_schema', encoded(MAILBOX_SCHEMA)))
            receipt = bus.event(database, 'operator', 'migrate_mailbox', dict(from_version=0, to_version=MAILBOX_SCHEMA))
            database.execute('COMMIT')
            return receipt

    @classmethod
    def activate_network_time(cls, bus, operator_capability, *, provider=None):
        """Explicit schema migration; never resets an anomalous legacy checkpoint."""
        mailbox = cls(bus, time_provider=provider)
        with mailbox.transaction() as database:
            bus.operator(database, operator_capability)
            if bus.recovery_held(database):
                raise BusError('recovery_hold','time-policy migration is held during recovery')
            if mailbox._network_mode(database):
                database.execute('ROLLBACK')
                return 'already_current'
            decision = mailbox._accepted_time()
            if database.execute("SELECT 1 FROM mail_leases WHERE lease_until>?",(decision.lower,)).fetchone() or database.execute("SELECT 1 FROM mail_attempts WHERE state IN ('dispatching','uncertain')").fetchone():
                raise BusError('migration_busy','quiescent mailbox required for time-policy migration')
            if decision.status != 'network':
                raise BusError('time_uncertain','network consensus required to establish the time policy')
            previous = database.execute("SELECT value FROM meta WHERE key='mail_clock'").fetchone()
            if previous:
                legacy_now = mailbox._now(database)
                if legacy_now < decision.lower-1 or legacy_now > decision.upper+1:
                    raise BusError('clock_anomaly','legacy clock and network consensus disagree; checkpoint retained')
                database.execute('INSERT INTO meta VALUES (?,?)',('mail_clock_before_network',previous[0]))
            ddl = database.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='mail_receipts'").fetchone()[0]
            triggers = database.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND tbl_name='mail_receipts'").fetchall()
            database.execute(ddl.replace('CREATE TABLE "mail_receipts"','CREATE TABLE network_receipts',1).replace('CREATE TABLE mail_receipts','CREATE TABLE network_receipts',1).replace('created REAL NOT NULL','created REAL',1))
            database.execute('INSERT INTO network_receipts SELECT * FROM mail_receipts')
            database.execute('DROP TABLE mail_receipts')
            database.execute('ALTER TABLE network_receipts RENAME TO mail_receipts')
            for trigger in triggers:
                database.execute(trigger[0])
            database.execute("UPDATE meta SET value=? WHERE key='mailbox_schema'",(encoded(NETWORK_MAILBOX_SCHEMA),))
            database.execute('INSERT INTO meta VALUES (?,?)',('mail_time_policy',encoded(dict(version=1,mode='network-first',authentication='plain-ntp-explicit-opt-in'))))
            database.execute('INSERT INTO meta VALUES (?,?)',('mail_network_clock',encoded(dict(lower=decision.lower,upper=decision.upper,sources=decision.sources,status=decision.status))))
            receipt = bus.event(database,'operator','activate_network_time',dict(from_version=MAILBOX_SCHEMA,to_version=NETWORK_MAILBOX_SCHEMA,previous_checkpoint_preserved=bool(previous)))
            if database.execute('PRAGMA foreign_key_check').fetchone():
                raise BusError('store_unavailable','time-policy migration failed foreign-key proof')
            mailbox._finish(database,receipt_id=receipt)
            return receipt

    @staticmethod
    def _network_mode(database):
        row = database.execute("SELECT value FROM meta WHERE key='mailbox_schema'").fetchone()
        return bool(row and json.loads(row[0]) == NETWORK_MAILBOX_SCHEMA)

    def _accepted_time(self):
        from .time_inspection import network_time_decision
        from .time_provider import require_time_decision
        try:
            decision = require_time_decision((self.time_provider or network_time_decision)())
        except (OSError,ValueError,TypeError) as error:
            raise BusError('time_uncertain','bounded time unavailable; retry original intent') from error
        self._time_context.decision = decision
        return decision

    @staticmethod
    def _migrate_identity(database):
        # Keep the envelope sequence generator intact. Only dependent foreign
        # keys move; an identity remains valid after its envelope is compacted.
        database.execute('CREATE TABLE mail_identities (message_id TEXT PRIMARY KEY)')
        database.execute('INSERT INTO mail_identities SELECT message_id FROM mail_envelopes')
        for table in ('mail_bodies', 'mail_state', 'mail_receipts', 'mail_outbox'):
            ddl = database.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
            triggers = database.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)).fetchall()
            indexes = database.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table,)).fetchall()
            replacement = table + '_identity_migration'
            database.execute(ddl.replace('CREATE TABLE ' + table, 'CREATE TABLE ' + replacement, 1)
                .replace('REFERENCES mail_envelopes(message_id)', 'REFERENCES mail_identities(message_id)'))
            database.execute('INSERT INTO ' + replacement + ' SELECT * FROM ' + table)
            database.execute('DROP TABLE ' + table)
            database.execute('ALTER TABLE ' + replacement + ' RENAME TO ' + table)
            for row in list(triggers) + list(indexes):
                database.execute(row[0])
        database.execute("""CREATE TABLE mail_tombstones (
            global_seq INTEGER PRIMARY KEY, message_id TEXT UNIQUE NOT NULL REFERENCES mail_identities(message_id),
            sender_key TEXT NOT NULL, recipient_key TEXT NOT NULL, idempotency_key TEXT NOT NULL,
            fingerprint TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL,
            envelope TEXT NOT NULL, in_reply_to TEXT, UNIQUE(sender_key,idempotency_key))""")
        database.execute("""CREATE TRIGGER mail_tombstone_immutable BEFORE UPDATE ON mail_tombstones
            BEGIN SELECT RAISE(ABORT,'immutable tombstone'); END""")
        for name, column in (('recipient', 'recipient_key'), ('sender', 'sender_key'), ('replies', 'in_reply_to')):
            database.execute('CREATE INDEX mail_tombstone_' + name + ' ON mail_tombstones(' + column + ',global_seq)')
        database.execute('CREATE INDEX mail_attempt_lifecycle ON mail_attempts(state,created)')
        database.execute('CREATE TABLE mail_retired_keys (key_digest TEXT PRIMARY KEY, retired_at REAL NOT NULL)')
        database.execute("CREATE TRIGGER mail_retired_key_immutable BEFORE UPDATE ON mail_retired_keys BEGIN SELECT RAISE(ABORT,'immutable retired key'); END")
        database.execute('CREATE VIEW mail_metadata AS SELECT * FROM mail_envelopes UNION ALL SELECT * FROM mail_tombstones')
        if database.execute('PRAGMA foreign_key_check').fetchone():
            raise BusError('store_unavailable', 'mailbox migration failed its foreign-key proof')

    @contextmanager
    def transaction(self, actor: Actor | None = None, *, permission='inspect'):
        try:
            with self.bus.connection() as database:
                self._schema(database)
                if self._network_mode(database):
                    # A competing transaction may be acquiring host time (25s
                    # collector bound). Wait once for its commit, without retrying
                    # an admission/effect; legacy stores retain their 1s bound.
                    database.execute('PRAGMA busy_timeout=30000')
                database.execute('BEGIN IMMEDIATE')
                if actor is not None:
                    self.bus.validate_actor(database, actor, permission=permission)
                yield database
        except BusError as error:
            if actor is not None and error.code in ('capacity','rate_limit','body_limit','lineage_limit','not_processable'):
                try:
                    with self.bus.connection() as database:
                        database.execute('BEGIN IMMEDIATE')
                        self.bus.validate_actor(database, actor)
                        cutoff = datetime.fromtimestamp(time.time() - 60, timezone.utc).isoformat()
                        count = database.execute("SELECT count(*) FROM events WHERE actor=? AND action='message_rejected' AND created_at>?", (actor.key, cutoff)).fetchone()[0]
                        size = sum(path.stat().st_size for path in self.bus.root.glob('mailbox.sqlite*') if path.is_file())
                        if count < 10 and size + 4096 < self.max_bytes:
                            receipt = self.bus.event(database, actor.key, 'message_rejected', dict(code=error.code))
                            database.execute('COMMIT')
                            error.details = dict(getattr(error, 'details', {}), rejection_receipt_id=receipt)
                except (BusError, OSError):
                    pass  # Preserve the original failure; no admission or effect retry.
            raise

    @staticmethod
    def _check_network_checkpoint(database, decision):
        previous = database.execute("SELECT value FROM meta WHERE key='mail_network_clock'").fetchone()
        if previous:
            from .time_provider import TimeDecision, require_time_decision
            try:
                last = json.loads(previous[0])
                require_time_decision(TimeDecision(last['status'],tuple(last['sources']),last['lower'],last['upper']))
                regressed = decision.lower < last['lower']-1
            except (KeyError,TypeError,ValueError):
                raise BusError('clock_anomaly','persisted network checkpoint is invalid') from None
            if regressed:
                raise BusError('clock_anomaly','network time regressed; no checkpoint reset authorized')

    def _now(self, database) -> float:
        if self._network_mode(database):
            decision = self._accepted_time()
            self._check_network_checkpoint(database, decision)
            database.execute('INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                             ('mail_network_clock',encoded(dict(lower=decision.lower,upper=decision.upper,sources=decision.sources,status=decision.status))))
            return decision.lower
        now, monotonic = float(self.clock()), float(self.monotonic())
        if not math.isfinite(now) or not math.isfinite(monotonic) or now <= 0:
            raise BusError('clock_anomaly', 'invalid clock observation')
        previous = database.execute("SELECT value FROM meta WHERE key='mail_clock'").fetchone()
        if previous:
            last = json.loads(previous[0])
            if not isinstance(last, dict) or not all(key in last for key in ('wall','monotonic','boot_id')):
                raise BusError('clock_anomaly', 'persisted clock checkpoint is invalid')
            if not all(isinstance(last[key], (int,float)) and not isinstance(last[key], bool) and math.isfinite(last[key]) for key in ('wall','monotonic')):
                raise BusError('clock_anomaly', 'persisted clock checkpoint is invalid')
            if now < last['wall'] - 1 or (last['boot_id'] == self.boot_id and
                    abs((now - last['wall']) - (monotonic - last['monotonic'])) > 300):
                raise BusError('clock_anomaly', 'clock continuity is uncertain; no effect authorized')
        database.execute('INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                         ('mail_clock', encoded(dict(wall=now, monotonic=monotonic, boot_id=self.boot_id))))
        return now

    def _finish(self, database, *, message_id=None, idempotency_key=None, receipt_id=None):
        if self.fault:
            self.fault('before_commit')
        database.execute('COMMIT')
        if self.fault:
            try:
                self.fault('after_commit')
            except Exception:
                error = BusError('effect_uncertain', 'commit may be accepted; reconcile the original intent')
                error.details = dict(message_id=message_id, idempotency_key=idempotency_key, receipt_id=receipt_id)
                raise error from None

    def _record(self, database, message_id, kind, actor_key, now, details=None, *, signal=True):
        details = details or {}
        receipt = self.bus.event(database, actor_key, 'message_' + kind, dict(message_id=message_id, **details))
        database.execute('INSERT INTO mail_receipts(receipt_id,message_id,kind,actor_key,created,details) VALUES (?,?,?,?,?,?)',
                         (receipt, message_id, kind, actor_key, now, encoded(details)))
        if signal:
            payload = dict(schema_version=1, bus_id=self.bus.bus_id, message_id=message_id,
                           receipt_id=receipt, kind=kind, actor_key=actor_key, observed_at=now)
            database.execute('INSERT INTO mail_outbox(outbox_id,kind,message_id,receipt_id,recipient_key,payload,status) VALUES (?,?,?,?,?,?,?)',
                             ('signal_' + receipt, 'receipt_signal', message_id, receipt, actor_key, encoded(payload), 'pending'))
        return receipt

    def _row(self, database, identifier):
        row = database.execute('SELECT e.*,s.recipient_seq,s.admission,s.notification,s.recipient,s.read_receipt,s.claim_receipt,s.claim_generation,s.terminal_receipt,s.terminal_at FROM mail_metadata e JOIN mail_state s USING(message_id) WHERE message_id=?', (identifier,)).fetchone()
        if row is None:
            raise BusError('not_found', 'message not found')
        return row

    def _participant(self, row, actor):
        if actor.key not in (row['sender_key'], row['recipient_key']):
            raise BusError('authorization_denied', 'message belongs to another mailbox')

    def _legacy_recovery(self, database, row):
        boundary = self.bus.recovery_legacy_boundary(database)
        return boundary is not None and row['global_seq'] <= boundary

    def _require_current_work(self, database, row):
        if self._legacy_recovery(database, row):
            raise BusError('recovery_legacy_held', 'snapshot-era work stays unknown; inspect as operator, never process or replay')

    def _time_upper(self, database, now):
        return self._time_context.decision.upper if self._network_mode(database) else now

    def _deadline_clear(self, database, row, now):
        if self._network_mode(database) and row['admission'] == 'accepted' and now < row['expires'] <= self._time_upper(database,now):
            raise BusError('time_uncertain','deadline lies inside the accepted interval; no delivery authorized')

    def _expire(self, database, row, now):
        if self._legacy_recovery(database, row):
            return row
        if json.loads(row['envelope']).get('compacted'):
            return row
        if row['admission'] == 'accepted' and now >= row['expires']:
            notification = 'suppressed' if row['notification'] in ('pending', 'deferred') else row['notification']
            terminal_at = None if row['recipient'] == 'accepted' else row['terminal_at'] or now
            database.execute('UPDATE mail_state SET admission=?,notification=?,terminal_at=? WHERE message_id=?',
                             ('expired', notification, terminal_at, row['message_id']))
            database.execute("UPDATE mail_outbox SET status='suppressed' WHERE message_id=? AND kind='notification' AND status IN ('pending','published','deferred')", (row['message_id'],))
            self._record(database, row['message_id'], 'expired', 'scheduler', now)
            return self._row(database, row['message_id'])
        return row

    def _projection(self, database, row):
        value = json.loads(row['envelope'])
        if self._legacy_recovery(database, row):
            value['recovery'] = dict(epoch=self.bus.meta(database, 'recovery_epoch'),
                                     legacy=True, disposition='retain-unknown', gap_unknown=True)
        value['recipient_sequence'] = row['recipient_seq']
        value['state'] = dict(admission=row['admission'], notification=row['notification'], recipient=row['recipient'])
        value['received_receipt_id'] = row['read_receipt']
        value['claim_receipt_id'] = row['claim_receipt']
        value['terminal_receipt_id'] = row['terminal_receipt']
        value['body_retained'] = database.execute('SELECT 1 FROM mail_bodies WHERE message_id=?', (row['message_id'],)).fetchone() is not None
        value['receipts'] = [dict(receipt_id=r['receipt_id'], kind=r['kind'], actor_key=r['actor_key'],
                                  created_at=r['created'], details=json.loads(r['details']))
                             for r in database.execute('SELECT * FROM mail_receipts WHERE message_id=? ORDER BY receipt_seq LIMIT 100', (row['message_id'],))]
        count = database.execute('SELECT count(*) FROM mail_receipts WHERE message_id=?', (row['message_id'],)).fetchone()[0]
        value['receipts_truncated'] = count > 100
        return value

    def _parameters(self, body, kind, ttl, key, delivery, subject, selector, correlation):
        if not isinstance(body, str):
            raise BusError('invalid_argument', 'body must be UTF-8 text')
        try:
            raw = body.encode('utf-8')
        except UnicodeError:
            raise BusError('invalid_argument', 'body must be valid UTF-8') from None
        if len(raw) > 32768 or not raw:
            raise BusError('body_limit', 'body must contain 1 to 32768 UTF-8 bytes')
        if kind not in ('notice', 'request', 'result') or delivery not in ('inbox', 'notify'):
            raise BusError('invalid_argument', 'unsupported kind or delivery mode')
        if not isinstance(key, str) or not 1 <= len(key) <= 200:
            raise BusError('invalid_argument', 'explicit bounded idempotency key is required')
        if not math.isfinite(ttl) or not 0 < ttl <= 7 * 86400:
            raise BusError('invalid_argument', 'TTL must be positive and at most seven days')
        if subject is not None and (not isinstance(subject, str) or len(subject) > 200):
            raise BusError('invalid_argument', 'subject is limited to 200 characters')
        if correlation is not None and (not isinstance(correlation, str) or len(correlation) > 200):
            raise BusError('invalid_argument', 'correlation is limited to 200 characters')
        if not isinstance(selector, dict) or len(encoded(selector).encode()) > 8192:
            raise BusError('invalid_argument', 'selector observation must be a bounded object')
        return hashlib.sha256(raw).hexdigest()

    def _admit(self, database, actor, recipient, *, body, kind, ttl, key, delivery,
               subject, selector, now, original=None, correlation=None, acknowledgement=None,
               resume_missing=False):
        if type(resume_missing) is not bool or (resume_missing and delivery != 'notify'):
            raise BusError('invalid_argument', 'explicit reopening requires notification delivery')
        body_digest = self._parameters(body, kind, ttl, key, delivery, subject, selector, correlation)
        recipient_key = thread_key(recipient)
        parent_id = original['message_id'] if original else None
        parameters = dict(recipient=recipient_key, body_digest=body_digest,
            kind=kind, ttl=ttl, delivery=delivery, subject=subject, in_reply_to=parent_id,
            correlation=correlation, acknowledgement=acknowledgement)
        if resume_missing:
            parameters['resume_policy'] = 'same_thread'
        fingerprint = hashlib.sha256(encoded(parameters).encode()).hexdigest()
        existing = database.execute('SELECT message_id,fingerprint,created FROM mail_metadata WHERE sender_key=? AND idempotency_key=?', (actor.key, key)).fetchone()
        if existing:
            if now - existing['created'] > 90 * 86400:
                raise BusError('idempotency_horizon', 'old intent requires an explicitly new idempotency key')
            if existing['fingerprint'] != fingerprint:
                raise BusError('idempotency_conflict', 'key already identifies a different immutable request')
            row = self._expire(database, self._row(database, existing['message_id']), now)
            projection = self._projection(database, row)
            receipt = next(item['receipt_id'] for item in projection['receipts'] if item['kind'] == 'admitted')
            return dict(message=projection, deduplicated=True, receipt_id=receipt)
        if database.execute('SELECT 1 FROM mail_retired_keys WHERE key_digest=?',
                (retired_key_digest(actor.key, key),)).fetchone():
            raise BusError('idempotency_horizon', 'retired intent requires an explicitly new idempotency key')
        if original is not None and json.loads(original['envelope']).get('compacted'):
            raise BusError('message_compacted', 'new replies require a retained full envelope')
        target = self.bus.authorize_pair(database, actor, recipient)
        parent = json.loads(original['envelope']) if original else None
        hop = parent['hop_count'] + 1 if parent else 0
        if hop > 8:
            raise BusError('lineage_limit', 'conversation hop bound exceeded')
        if database.execute('SELECT (SELECT count(*) FROM mail_metadata)+(SELECT count(*) FROM mail_retired_keys)').fetchone()[0] >= self.max_messages:
            raise BusError('capacity', 'retained message capacity reached')
        if database.execute("SELECT count(*) FROM mail_envelopes e JOIN mail_state s USING(message_id) WHERE e.recipient_key=? AND e.expires>? AND e.global_seq>? AND s.admission='accepted' AND s.recipient NOT IN ('declined','completed','failed')", (recipient_key, now, self.bus.recovery_legacy_boundary(database) or 0)).fetchone()[0] >= self.max_open:
            raise BusError('capacity', 'recipient open-message capacity reached')
        if database.execute('SELECT count(*) FROM mail_envelopes WHERE sender_key=? AND created>?', (actor.key, now - 60)).fetchone()[0] >= self.rate_limit:
            raise BusError('rate_limit', 'sender minute limit reached')
        size = sum(path.stat().st_size for path in self.bus.root.glob('mailbox.sqlite*') if path.is_file())
        if size + len(body.encode()) + 65536 > self.max_bytes:
            raise BusError('capacity', 'bus storage capacity reached')
        sequence = database.execute('SELECT next_sequence FROM mail_sequences WHERE recipient_key=?', (recipient_key,)).fetchone()
        sequence = sequence[0] if sequence else 1
        database.execute('INSERT INTO mail_sequences VALUES (?,?) ON CONFLICT(recipient_key) DO UPDATE SET next_sequence=excluded.next_sequence', (recipient_key, sequence + 1))
        identifier = 'msg_' + uuid.uuid4().hex
        created = self._time_upper(database,now)
        envelope = dict(schema_version=1, bus_id=self.bus.bus_id, message_id=identifier,
            conversation_id=parent['conversation_id'] if parent else 'conversation_' + uuid.uuid4().hex,
            sender=dict(namespace=actor.namespace, thread_id=actor.thread_id, root=actor.root),
            recipient=dict(namespace=target.namespace, thread_id=target.thread_id, root=target.root),
            kind=kind, subject=subject, body_digest=body_digest, created_at=created, expires_at=created + ttl,
            idempotency_key=key, in_reply_to=parent_id, correlation=parent['correlation'] if parent else correlation,
            lineage=(parent['lineage'] + [parent_id]) if parent else [], hop_count=hop,
            selector_observation=selector, delivery=delivery)
        if resume_missing:
            envelope['resume_policy'] = 'same_thread'
            envelope['notification_authority'] = dict(
                sender=dict(actor_id=actor.actor_id, generation=actor.generation, root=actor.root),
                recipient=dict(actor_id=target.actor_id, generation=target.generation, root=target.root))
        database.execute('INSERT INTO mail_identities VALUES (?)', (identifier,))
        database.execute('INSERT INTO mail_envelopes(message_id,sender_key,recipient_key,idempotency_key,fingerprint,created,expires,envelope,in_reply_to) VALUES (?,?,?,?,?,?,?,?,?)',
                         (identifier, actor.key, recipient_key, key, fingerprint, created, created + ttl, encoded(envelope), parent_id))
        database.execute('INSERT INTO mail_bodies VALUES (?,?)', (identifier, body))
        database.execute('INSERT INTO mail_state(message_id,recipient_seq,admission,notification,recipient) VALUES (?,?,?,?,?)',
                         (identifier, sequence, 'accepted', 'pending' if delivery == 'notify' else 'suppressed', 'unread'))
        receipt = self._record(database, identifier, 'admitted', actor.key, now)
        if delivery == 'notify':
            database.execute('INSERT INTO mail_outbox(outbox_id,kind,message_id,recipient_key,payload,status) VALUES (?,?,?,?,?,?)',
                ('notify_' + identifier, 'notification', identifier, recipient_key,
                 encoded(dict(schema_version=1, bus_id=self.bus.bus_id, message_ids=[identifier], recipient_key=recipient_key)), 'pending'))
        return dict(message=self._projection(database, self._row(database, identifier)), deduplicated=False, receipt_id=receipt)

    def send(self, actor, recipient, *, body, idempotency_key, kind='request', ttl=86400,
             delivery='notify', subject=None, selector=None, correlation=None, resume_missing=False):
        with self.transaction(actor, permission='send') as database:
            now = self._now(database)
            value = self._admit(database, actor, recipient, body=body, kind=kind, ttl=float(ttl),
                                key=idempotency_key, delivery=delivery, subject=subject,
                                selector=selector or {}, correlation=correlation, now=now,
                                resume_missing=resume_missing)
            self._finish(database, message_id=value['message']['message_id'], idempotency_key=idempotency_key,
                         receipt_id=value.get('receipt_id'))
            return value

    def show(self, actor, identifier):
        with self.transaction(actor) as database:
            row = self._row(database, identifier)
            self._participant(row, actor)
            if not self._network_mode(database):
                row = self._expire(database, row, self._now(database))
            value = self._projection(database, row)
            database.execute('COMMIT')
            return value

    def read(self, actor, identifier):
        with self.transaction(actor) as database:
            row = self._row(database, identifier)
            self._participant(row, actor)
            self._require_current_work(database, row)
            recipient = actor.key == row['recipient_key']
            if recipient:
                self.bus.validate_actor(database, actor, permission='receive')
            now = self._now(database)
            row = self._expire(database, row, now)
            self._deadline_clear(database,row,now)
            stored = database.execute('SELECT body FROM mail_bodies WHERE message_id=?', (identifier,)).fetchone()
            if stored is None:
                raise BusError('body_unavailable', 'body was retained as metadata only')
            body = stored['body']
            if hashlib.sha256(body.encode()).hexdigest() != json.loads(row['envelope'])['body_digest']:
                raise BusError('store_unavailable', 'body digest mismatch; no receipt fabricated')
            if recipient and not row['read_receipt']:
                receipt = self._record(database, identifier, 'received', actor.key, now)
                database.execute("UPDATE mail_state SET read_receipt=?,recipient=CASE WHEN recipient='unread' THEN 'received' ELSE recipient END WHERE message_id=?", (receipt, identifier))
                row = self._row(database, identifier)
            value = dict(message=self._projection(database, row), body=body, peer_content_trust='untrusted',
                         receipt_id=row['read_receipt'] if recipient else None)
            self._finish(database, message_id=identifier, receipt_id=value['receipt_id'])
            return value

    def _ack(self, database, actor, row, outcome, evidence, now):
        if actor.key != row['recipient_key']:
            raise BusError('authorization_denied', 'only the exact recipient may acknowledge')
        self.bus.validate_actor(database, actor, permission='receive')
        if outcome not in ('accepted', 'declined', 'completed', 'failed'):
            raise BusError('invalid_argument', 'unsupported recipient outcome')
        if evidence is not None and (not isinstance(evidence, str) or len(evidence) > 2048):
            raise BusError('invalid_argument', 'evidence must be a bounded pointer')
        if row['recipient'] == outcome or (outcome == 'accepted' and row['claim_receipt']):
            if row['claim_receipt'] and row['claim_generation'] != actor.generation:
                raise BusError('claim_fenced', 'claim generation requires explicit recovery')
            receipt = row['claim_receipt'] if outcome == 'accepted' else row['terminal_receipt']
            prior = database.execute('SELECT details FROM mail_receipts WHERE receipt_id=?', (receipt,)).fetchone()
            if prior and json.loads(prior['details']).get('evidence') != evidence:
                raise BusError('receipt_conflict', 'outcome already has different evidence')
            return dict(receipt_id=receipt, claimed=False, deduplicated=True)
        if json.loads(row['envelope']).get('compacted'):
            raise BusError('message_compacted', 'compacted recipient state cannot acquire new outcomes')
        if row['recipient'] in TERMINAL:
            raise BusError('terminal_conflict', 'recipient outcome is already terminal')
        if outcome == 'accepted' and (row['admission'] != 'accepted' or now >= row['expires']):
            raise BusError('not_processable', 'cancelled or expired message cannot acquire a first work claim')
        if outcome in ('completed', 'failed') and not row['claim_receipt']:
            raise BusError('claim_required', 'terminal processing outcome requires an accepted work claim')
        if row['claim_receipt'] and row['claim_generation'] != actor.generation:
            raise BusError('claim_fenced', 'claim generation requires explicit recovery')
        receipt = self._record(database, row['message_id'], outcome, actor.key, now, dict(evidence=evidence, generation=actor.generation))
        if outcome == 'accepted':
            database.execute('UPDATE mail_state SET recipient=?,claim_receipt=?,claim_generation=? WHERE message_id=?',
                             (outcome, receipt, actor.generation, row['message_id']))
        else:
            database.execute('UPDATE mail_state SET recipient=?,terminal_receipt=?,terminal_at=? WHERE message_id=?',
                             (outcome, receipt, now, row['message_id']))
        return dict(receipt_id=receipt, claimed=outcome == 'accepted', deduplicated=False)

    def ack(self, actor, identifier, *, outcome, evidence=None):
        with self.transaction(actor, permission='receive') as database:
            row = self._row(database, identifier)
            self._participant(row, actor)
            self._require_current_work(database, row)
            now = self._now(database)
            row = self._expire(database, row, now)
            self._deadline_clear(database,row,now)
            value = self._ack(database, actor, row, outcome, evidence, now)
            value['message'] = self._projection(database, self._row(database, identifier))
            self._finish(database, message_id=identifier, receipt_id=value['receipt_id'])
            return value

    def reply(self, actor, identifier, *, body, idempotency_key, kind='result', ttl=86400,
              delivery='notify', subject=None, outcome=None, evidence=None, resume_missing=False):
        with self.transaction(actor, permission='send') as database:
            original = self._row(database, identifier)
            self._require_current_work(database, original)
            if actor.key != original['recipient_key']:
                raise BusError('authorization_denied', 'only the original recipient may reply')
            now = self._now(database)
            original = self._expire(database, original, now)
            self._deadline_clear(database,original,now)
            sender = json.loads(original['envelope'])['sender']
            recipient = RuntimeIdentity(sender['namespace'], sender['thread_id'], sender['root'])
            value = self._admit(database, actor, recipient, body=body, kind=kind, ttl=float(ttl), key=idempotency_key,
                                delivery=delivery, subject=subject, selector=dict(reply_to=identifier),
                                now=now, original=original,
                                acknowledgement=dict(outcome=outcome, evidence=evidence) if outcome else None,
                                resume_missing=resume_missing)
            if outcome:
                value['acknowledgement'] = self._ack(database, actor, original, outcome, evidence, now)
            self._finish(database, message_id=value['message']['message_id'], idempotency_key=idempotency_key,
                         receipt_id=value.get('receipt_id'))
            return value

    def cancel(self, actor, identifier):
        with self.transaction(actor) as database:
            row = self._row(database, identifier)
            self._require_current_work(database, row)
            if actor.key != row['sender_key']:
                raise BusError('authorization_denied', 'only the sender may cancel')
            try:
                now = self._now(database)
            except BusError as error:
                if not self._network_mode(database) or error.code != 'time_uncertain':
                    raise
                now = None
            if now is not None:
                row = self._expire(database, row, now)
            if row['admission'] == 'cancelled':
                value = dict(message=self._projection(database, row), deduplicated=True)
            else:
                if row['notification'] == 'uncertain':
                    raise BusError('effect_uncertain', 'notification effect must be reconciled before cancellation')
                if row['notification'] in ('dispatching', 'submitted') or row['recipient'] != 'unread':
                    raise BusError('too_late', 'prompt or work may already be consumed; cancellation cannot retract it')
                if row['admission'] != 'accepted':
                    raise BusError('not_processable', 'message admission is already terminal')
                database.execute("UPDATE mail_state SET admission='cancelled',notification='suppressed',terminal_at=? WHERE message_id=?", (now, identifier))
                database.execute("UPDATE mail_outbox SET status='suppressed' WHERE message_id=? AND kind='notification'", (identifier,))
                receipt = self._record(database, identifier, 'cancelled', actor.key, now,
                                       dict(time_status='uncertain') if now is None else {}, signal=now is not None)
                value = dict(message=self._projection(database, self._row(database, identifier)), receipt_id=receipt, deduplicated=False)
            self._finish(database, message_id=identifier, receipt_id=value.get('receipt_id'))
            return value

    def list(self, actor, *, outbox=False, cursor=0, limit=100, state=None):
        if type(cursor) is not int or cursor < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise BusError('invalid_argument', 'page size must be 1 to 100 and cursor a nonnegative integer')
        if state is not None and state not in ('unread','received','accepted','declined','completed','failed','cancelled','expired'):
            raise BusError('invalid_argument', 'unsupported mailbox state filter')
        with self.transaction(actor) as database:
            now = None if self._network_mode(database) else self._now(database)
            column = 'sender_key' if outbox else 'recipient_key'
            rows = database.execute('SELECT message_id,global_seq FROM mail_metadata WHERE ' + column + '=? AND global_seq>? ORDER BY global_seq LIMIT ?', (actor.key, cursor, limit + 1)).fetchall()
            values = []
            for row in rows[:limit]:
                current = self._row(database, row['message_id'])
                if now is not None:
                    current = self._expire(database,current,now)
                if state is None or state == current['admission' if state in ('cancelled','expired') else 'recipient']:
                    values.append(self._projection(database, current))
            next_cursor = rows[limit - 1]['global_seq'] if len(rows) > limit else None
            database.execute('COMMIT')
            return dict(messages=values, next_cursor=next_cursor)

    def disposition_receipt(self, actor, identifier, condition):
        """Find historical recipient evidence without relying on display limits."""
        if condition not in ('received', 'accepted', 'declined', 'completed', 'failed'):
            raise BusError('invalid_argument', 'unsupported recipient receipt condition')
        with self.transaction(actor) as database:
            row = self._row(database, identifier)
            self._participant(row, actor)
            receipt = database.execute(
                'SELECT receipt_id,kind,created FROM mail_receipts '
                'WHERE message_id=? AND kind=? AND actor_key=? ORDER BY receipt_seq LIMIT 1',
                (identifier, condition, row['recipient_key'])).fetchone()
            database.execute('ROLLBACK')
            return dict(receipt) if receipt else None

    def replies(self, actor, identifier):
        with self.transaction(actor) as database:
            original = self._row(database, identifier)
            self._participant(original, actor)
            now = None if self._network_mode(database) else self._now(database)
            candidates = database.execute('SELECT message_id,envelope FROM mail_metadata WHERE recipient_key=? AND sender_key=? AND in_reply_to=? ORDER BY global_seq LIMIT 100', (original['sender_key'], original['recipient_key'], identifier)).fetchall()
            values = [self._projection(database, self._row(database, row['message_id']) if now is None else self._expire(database, self._row(database, row['message_id']), now))
                      for row in candidates if json.loads(row['envelope'])['in_reply_to'] == identifier]
            database.execute('COMMIT')
            return values

    def operator_inspect(self, capability, identifier, *, body=False):
        with self.transaction() as database:
            self.bus.operator(database, capability)
            network = self._network_mode(database)
            row = self._row(database,identifier)
            if not network:
                row = self._expire(database,row,self._now(database))
            receipt = self._record(database, identifier, 'operator_inspected', 'operator', None if network else float(self.clock()), dict(body_requested=bool(body),time_status='not_observed' if network else 'legacy'), signal=False)
            value = dict(message=self._projection(database, row), receipt_id=receipt)
            if body:
                stored = database.execute('SELECT body FROM mail_bodies WHERE message_id=?', (identifier,)).fetchone()
                if stored and hashlib.sha256(stored['body'].encode()).hexdigest() != json.loads(row['envelope'])['body_digest']:
                    raise BusError('store_unavailable', 'body digest mismatch; inspection cannot certify it')
                value['body'] = stored['body'] if stored else None
            database.execute('COMMIT')
            return value
