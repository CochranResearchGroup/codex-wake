"""Explicit retention of unknown recovery history; release never resumes work."""
import json
import re
from pathlib import Path

from .a2a_bus import private_path
from .a2a_identity import BusError


class RecoveryDisposition:
    def __init__(self, bus, operator_capability):
        self.bus, self.operator = bus, operator_capability

    def _context(self, database):
        self.bus.operator(database, self.operator)
        if self.bus.meta(database, 'schema_version') not in (2, 3):
            raise BusError('recovery_refused', 'this bus has no recovered authority epoch')
        epoch = self.bus.meta(database, 'recovery_epoch')
        receipt = self.bus.root / epoch / 'receipt.json'
        private_path(receipt)
        try:
            if receipt.stat().st_size > 4096:
                raise ValueError()
            recovery = json.loads(receipt.read_text())
            if (recovery.get('recovery_epoch') != epoch or recovery.get('bus_id') != self.bus.bus_id
                    or recovery.get('canonical_root') != str(self.bus.root)
                    or recovery.get('completed') is not True or recovery.get('gap_unknown') is not True
                    or not re.fullmatch(r'[0-9a-f]{64}', recovery.get('snapshot_sha256', ''))):
                raise ValueError()
        except (OSError, ValueError, TypeError):
            raise BusError('recovery_refused', 'original completed recovery commitment is unavailable') from None
        row = database.execute("SELECT value FROM meta WHERE key='recovery_disposition'").fetchone()
        disposition = json.loads(row[0]) if row else None
        value = dict(epoch=epoch, snapshot_sha256=recovery['snapshot_sha256'],
                     hold=self.bus.recovery_held(database), gap_unknown=True,
                     disposition='retain-unknown' if disposition else None,
                     disposition_receipt=disposition['receipt_id'] if disposition else None)
        value['legacy_through_sequence'] = disposition['legacy_through_sequence'] if disposition else None
        value['legacy_message_count'] = database.execute(
            'SELECT count(*) FROM mail_metadata WHERE global_seq<=?',
            (value['legacy_through_sequence'],)).fetchone()[0] if disposition else None
        value['revoked_actors'] = [dict(row) for row in database.execute(
            'SELECT actor_id,namespace,thread_id,root,generation FROM actors WHERE revoked=1 ORDER BY actor_id LIMIT 100')]
        value['revoked_actors_truncated'] = database.execute('SELECT count(*) FROM actors WHERE revoked=1').fetchone()[0] > 100
        return value, disposition

    def status(self):
        with self.bus.connection(read_only=True) as database:
            value, _ = self._context(database)
            return value

    @staticmethod
    def _pin(value, epoch, sha256):
        if epoch != value['epoch'] or sha256 != value['snapshot_sha256']:
            raise BusError('recovery_refused', 'exact recovery epoch and reviewed snapshot SHA256 required')

    def dispose(self, *, epoch, sha256, key, reason, accept_unknown=False):
        if (accept_unknown is not True or not isinstance(key, str) or not key or len(key.encode()) > 256
                or not isinstance(reason, str) or not reason.strip() or len(reason.encode()) > 1024):
            raise BusError('invalid_argument', 'explicit unknown-state acceptance, bounded key and nonsecret reason required')
        with self.bus.maintenance_connection() as database:
            database.execute('BEGIN IMMEDIATE')
            value, previous = self._context(database)
            self._pin(value, epoch, sha256)
            intent = dict(epoch=epoch, sha256=sha256, key=key, reason=reason, disposition='retain-unknown')
            if previous:
                if previous['intent'] != intent:
                    raise BusError('idempotency_conflict', 'recovery disposition already identifies a different intent')
                database.execute('ROLLBACK')
                return dict(recovery=value, receipt_id=previous['receipt_id'], deduplicated=True)
            if not value['hold'] or self.bus.meta(database, 'paused') is not True:
                raise BusError('recovery_refused', 'disposition requires the original paused recovery hold')
            boundary = database.execute('SELECT coalesce(max(global_seq),0) FROM mail_metadata').fetchone()[0]
            database.execute("UPDATE mail_outbox SET status='recovery_held',owner=NULL,lease_until=NULL "
                             "WHERE status IN ('pending','published','deferred','dispatching')")
            receipt = self.bus.event(database, 'operator', 'recovery_disposition',
                                     dict(intent, legacy_through_sequence=boundary, gap_unknown=True))
            database.execute('INSERT INTO meta VALUES (?,?)',
                             ('recovery_disposition', json.dumps(dict(intent=intent, receipt_id=receipt, legacy_through_sequence=boundary))))
            database.execute("UPDATE meta SET value='3' WHERE key='schema_version'")
            database.execute('COMMIT')
            value.update(disposition='retain-unknown', disposition_receipt=receipt, legacy_through_sequence=boundary)
            return dict(recovery=value, receipt_id=receipt, deduplicated=False)

    def release(self, *, epoch, sha256, receipt_id):
        with self.bus.maintenance_connection() as database:
            database.execute('BEGIN IMMEDIATE')
            value, disposition = self._context(database)
            self._pin(value, epoch, sha256)
            if not disposition or receipt_id != disposition['receipt_id']:
                raise BusError('recovery_refused', 'committed retained-unknown disposition receipt required')
            if database.execute("SELECT 1 FROM mail_outbox o JOIN mail_metadata e USING(message_id) "
                                "WHERE e.global_seq<=? AND o.status IN ('pending','published','deferred','dispatching') LIMIT 1",
                                (disposition['legacy_through_sequence'],)).fetchone():
                raise BusError('recovery_refused', 'legacy outbox is not fenced; preserve the recovery hold')
            if self.bus.meta(database, 'paused') is not True:
                raise BusError('pause_required', 'release leaves the bus paused; pause it before reconciliation')
            if not value['hold']:
                release = self.bus.meta(database, 'recovery_release')
                if release.get('epoch') != epoch or release.get('disposition_receipt') != receipt_id:
                    raise BusError('recovery_refused', 'original release receipt is unavailable')
                database.execute('ROLLBACK')
                return dict(recovery=value, receipt_id=release['receipt_id'], deduplicated=True)
            receipt = self.bus.event(database, 'operator', 'recovery_hold_released',
                                     dict(epoch=epoch, disposition_receipt=receipt_id, gap_unknown=True, paused=True))
            database.execute('INSERT INTO meta VALUES (?,?)', ('recovery_release',
                json.dumps(dict(epoch=epoch, disposition_receipt=receipt_id, receipt_id=receipt))))
            database.execute("UPDATE meta SET value='false' WHERE key='recovery_hold'")
            database.execute('COMMIT')
            value['hold'] = False
            return dict(recovery=value, receipt_id=receipt, deduplicated=False)
