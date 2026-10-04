"""Explicit bounded mailbox maintenance. Bodies never enter operator diagnostics."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .a2a_identity import BusError
from .a2a_mailbox import Mailbox, TERMINAL, encoded


class MailOperations:
    def __init__(self, mailbox: Mailbox, operator_capability: Path):
        self.mailbox, self.operator_capability = mailbox, operator_capability

    def _pins(self, database, row, now):
        pins = []
        if row['notification'] in ('dispatching','uncertain'):
            pins.append('uncertain_notification')
        if row['recipient'] == 'accepted':
            pins.append('open_processing_claim')
        pending = database.execute("SELECT 1 FROM mail_outbox WHERE message_id=? AND kind='receipt_signal' AND status!='published' LIMIT 1", (row['message_id'],)).fetchone()
        if pending:
            pins.append('unprojected_receipt_signal')
        envelope = json.loads(row['envelope'])
        root = envelope['lineage'][0] if envelope['lineage'] else row['message_id']
        conversation = database.execute('''WITH RECURSIVE members(message_id) AS (
            SELECT message_id FROM mail_envelopes WHERE message_id=?
            UNION ALL SELECT e.message_id FROM mail_envelopes e JOIN members m ON e.in_reply_to=m.message_id
            LIMIT 1001)
            SELECT e.message_id,e.expires,s.admission,s.recipient,s.notification FROM members m
            JOIN mail_envelopes e USING(message_id) JOIN mail_state s USING(message_id)''', (root,)).fetchall()
        if len(conversation) > 1000:
            pins.append('conversation_scan_limit')
        elif any(item['recipient'] == 'accepted' or item['notification'] in ('dispatching','uncertain') or
                 (item['admission'] == 'accepted' and item['expires'] > now and item['recipient'] not in TERMINAL)
                 for item in conversation):
            pins.append('active_conversation')
        return sorted(set(pins))

    def _preview(self, database, now, cursor, limit):
        rows = database.execute('''SELECT e.message_id,e.global_seq FROM mail_envelopes e
            JOIN mail_state s USING(message_id) JOIN mail_bodies b USING(message_id)
            WHERE e.global_seq>? AND s.terminal_at IS NOT NULL AND s.terminal_at<=?
            ORDER BY e.global_seq LIMIT ?''', (cursor, now - 30 * 86400, limit + 1)).fetchall()
        candidates = []
        for item in rows[:limit]:
            row = self.mailbox._row(database, item['message_id'])
            candidates.append(dict(message_id=row['message_id'], terminal_at=row['terminal_at'],
                body_digest=json.loads(row['envelope'])['body_digest'], pins=self._pins(database, row, now)))
        value = dict(schema_version=1,bus_id=self.mailbox.bus.bus_id,cursor=cursor,limit=limit,
                     candidates=candidates,eligible=[item['message_id'] for item in candidates if not item['pins']],
                     next_cursor=rows[limit - 1]['global_seq'] if len(rows) > limit else None,
                     retention_days=30,metadata_retention='preserved',dedup_horizon_days=90)
        value['fingerprint'] = hashlib.sha256(encoded(value).encode()).hexdigest()
        return value

    def retention(self, *, cursor=0, limit=100, apply_fingerprint=None):
        if type(cursor) is not int or cursor < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise BusError('invalid_argument', 'retention requires a nonnegative cursor and limit one to one hundred')
        with self.mailbox.transaction() as database:
            self.mailbox.bus.operator(database, self.operator_capability)
            now = self.mailbox._now(database)
            preview = self._preview(database, now, cursor, limit)
            action = 'preview_retention'
            if apply_fingerprint is not None:
                if apply_fingerprint != preview['fingerprint']:
                    raise BusError('retention_preview_stale', 'retention eligibility changed; generate a fresh preview')
                for identifier in preview['eligible']:
                    database.execute('DELETE FROM mail_bodies WHERE message_id=?', (identifier,))
                action = 'apply_retention'
            receipt = self.mailbox.bus.event(database, 'operator', action, dict(
                fingerprint=preview['fingerprint'], pruned=preview['eligible'] if apply_fingerprint is not None else [],
                candidates=len(preview['candidates'])))
            self.mailbox._finish(database, receipt_id=receipt)
            return dict(preview,receipt_id=receipt,applied=apply_fingerprint is not None,
                        pruned=len(preview['eligible']) if apply_fingerprint is not None else 0)

    def acknowledge_projections(self, wake_root, receipt_authority, source_instance, *, limit=100):
        from .a2a_receipt_authority import ConfiguredReceiptAuthority
        from .signal_records import signal_journal_path
        from .signal_store import SQLiteSignalModule
        from .signals import Degraded
        if type(limit) is not int or not 1 <= limit <= 100:
            raise BusError('invalid_argument', 'projection acknowledgement is limited to one hundred rows')
        with self.mailbox.transaction() as database:
            # Writer authority is independent of the observer's read-only delegation.
            self.mailbox.bus.operator(database, self.operator_capability)
            adapter = ConfiguredReceiptAuthority(receipt_authority, wake_root).adapter(source_instance)
            if (adapter.mailbox.bus.root != self.mailbox.bus.root
                    or adapter.mailbox.bus.bus_id != self.mailbox.bus.bus_id):
                raise BusError('authorization_denied', 'receipt grant belongs to a different bus')
            original = self.mailbox._row(database, adapter.message_id)
            self.mailbox._participant(original, adapter.actor)
            rows = database.execute("""SELECT r.*,e.in_reply_to,e.sender_key,e.recipient_key,o.payload,o.outbox_id
                FROM mail_receipts r JOIN mail_envelopes e USING(message_id)
                JOIN mail_outbox o ON o.receipt_id=r.receipt_id AND o.kind='receipt_signal'
                WHERE o.status!='published' AND (e.message_id=? OR e.in_reply_to=?)
                ORDER BY r.receipt_seq LIMIT ?""", (adapter.message_id, adapter.message_id, limit)).fetchall()
            expected = {row['receipt_id']: adapter.observation(row, original) for row in rows}
            proof = SQLiteSignalModule.read_committed_occurrences(signal_journal_path(wake_root),
                'a2a.receipt', source_instance, 'mailbox_receipt', list(expected))
            if isinstance(proof, Degraded):
                raise BusError('projection_proof_unavailable', 'committed receipt proof is unavailable')
            journal_uuid, observations = proof
            acknowledged = []
            for row in rows:
                identifier = row['receipt_id']
                if identifier not in observations:
                    continue
                if observations[identifier] != expected[identifier]:
                    raise BusError('projection_proof_mismatch', 'committed occurrence does not match mailbox receipt')
                database.execute("UPDATE mail_outbox SET status='published' WHERE outbox_id=?", (row['outbox_id'],))
                acknowledged.append(identifier)
            if not adapter.authorized():
                raise BusError('authorization_denied', 'receipt grant is no longer available')
            receipt = self.mailbox.bus.event(database, 'operator', 'acknowledge_receipt_projections',
                dict(source_instance=source_instance, journal_uuid=journal_uuid, receipt_ids=acknowledged))
            self.mailbox._finish(database, receipt_id=receipt)
            return dict(acknowledged=len(acknowledged), scanned=len(rows), receipt_id=receipt,
                        source_instance=source_instance, journal_uuid=journal_uuid)

    def diagnostics(self):
        with self.mailbox.transaction() as database:
            self.mailbox.bus.operator(database, self.operator_capability)
            now = self.mailbox._now(database)
            axes = {axis:dict(database.execute('SELECT ' + axis + ',count(*) FROM mail_state GROUP BY ' + axis).fetchall())
                    for axis in ('admission','notification','recipient')}
            outbox = [dict(kind=row['kind'],status=row['status'],count=row['count']) for row in
                      database.execute('SELECT kind,status,count(*) AS count FROM mail_outbox GROUP BY kind,status')]
            oldest = database.execute("SELECT min(e.created) FROM mail_envelopes e JOIN mail_state s USING(message_id) WHERE s.admission='accepted' AND s.recipient NOT IN ('declined','completed','failed') AND e.expires>?", (now,)).fetchone()[0]
            leases = [dict(name=row['name'],generation=row['generation'],expired=row['lease_until']<=now)
                      for row in database.execute('SELECT * FROM mail_leases ORDER BY name LIMIT 100')]
            receipt = self.mailbox.bus.event(database,'operator','inspect_mailbox',dict(bus_id=self.mailbox.bus.bus_id))
            database.execute('COMMIT')
        return dict(schema_version=1,bus_id=self.mailbox.bus.bus_id,states=axes,outbox=outbox,
                    backlog_oldest_age_seconds=max(0,now-oldest) if oldest is not None else None,
                    leases=leases,notification_capability='unqualified',receipt_id=receipt,
                    store_bytes=sum(p.stat().st_size for p in self.mailbox.bus.root.glob('mailbox.sqlite*') if p.is_file()),
                    observer_descriptors=len(list(Path('/proc/self/fd').iterdir())),
                    observer_pid=os.getpid(),metadata_only=True)
