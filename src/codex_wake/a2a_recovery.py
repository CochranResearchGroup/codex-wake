"""Explicit gap-held recovery; original source artifacts are never discarded."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid

from .a2a_backup import MailBackup, MAX_BYTES, DEADLINE_SECONDS, _hash, _manifest, _sync_directory
from .a2a_bus import BusStore, default_bus_root, digest, local_filesystem, private_path, read_capability, write_capability
from .a2a_identity import BusError

SOURCE_FILES = ('mailbox.sqlite', 'mailbox.sqlite-wal', 'mailbox.sqlite-shm')
MARKER = '.recovery-in-progress.json'


def identity(path):
    private_path(path)
    info = path.stat()
    if info.st_size > MAX_BYTES:
        raise BusError('recovery_refused', 'recovery file exceeds one GiB limit')
    return dict(device=info.st_dev, inode=info.st_ino, bytes=info.st_size)


class MailRecovery:
    def __init__(self, root: Path, operator_capability: Path):
        root = Path(root).absolute()
        if root != root.resolve():
            raise BusError('ownership_mismatch', 'recovery root cannot traverse symlinks')
        private_path(root, directory=True)
        local_filesystem(root)
        capability = read_capability(operator_capability)
        if capability.get('role') != 'operator' or not isinstance(capability.get('bus_id'), str):
            raise BusError('authorization_denied', 'independent operator capability required')
        default_bus_root(capability['bus_id'])
        # No connection to the damaged journal. This authority is checked against
        # the independently pinned immutable snapshot before original files move.
        self.bus = BusStore.__new__(BusStore)
        self.bus.root, self.bus.path, self.bus.bus_id = root, root / 'mailbox.sqlite', capability['bus_id']
        self.operator_capability = operator_capability
        self.authorization_digest = digest(capability['secret'])
        self.marker = root / MARKER

    @staticmethod
    def _source_identity(path, deadline):
        value = identity(path)
        value['sha256'] = _hash(path, deadline)
        return value

    def _verify(self, snapshot, expected_sha256, deadline):
        if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
            raise BusError('invalid_argument', 'reviewed snapshot database SHA256 required')
        snapshot = Path(snapshot).absolute()
        path = snapshot / 'mailbox.sqlite'
        if snapshot != snapshot.resolve():
            raise BusError('ownership_mismatch', 'snapshot cannot traverse symlinks')
        private_path(snapshot, directory=True); private_path(path)
        identity(path)
        database = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True, isolation_level=None)
        try:
            database.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            checked = MailBackup(self.bus, self.operator_capability)._verify(snapshot, deadline, database)
            if checked['database_sha256'] != expected_sha256:
                raise BusError('recovery_refused', 'reviewed snapshot commitment differs; source untouched')
            return checked
        finally:
            database.close()

    def _current_authority(self):
        anchor = self.bus.root / '.recovery-authority.json'
        if anchor.exists() or anchor.is_symlink():
            private_path(anchor)
            if anchor.stat().st_size > 4096:
                raise BusError('authorization_denied', 'recovery authority anchor invalid')
            value = json.loads(anchor.read_text())
            if type(value) is not dict or value.get('format_version') != 1 or value.get('canonical_root') != str(self.bus.root) or value.get('bus_id') != self.bus.bus_id:
                raise BusError('authorization_denied', 'recovery authority anchor differs')
            expected = value.get('operator_digest')
        else:
            current = read_capability(self.bus.root / 'operator.json')
            if current.get('role') != 'operator' or current.get('bus_id') != self.bus.bus_id:
                raise BusError('authorization_denied', 'independent root operator identity differs')
            expected = digest(current['secret'])
        if not isinstance(expected, str) or not secrets.compare_digest(expected, self.authorization_digest):
            raise BusError('authorization_denied', 'current external recovery authority is required')

    def recover(self, snapshot, *, expected_sha256, acknowledge_gap=False):
        try:
            return self._recover(snapshot, expected_sha256=expected_sha256, acknowledge_gap=acknowledge_gap)
        except BusError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError):
            code = 'recovery_incomplete' if self.marker.exists() else 'recovery_refused'
            raise BusError(code, 'recovery preparation failed; preserve source and private artifacts') from None

    def _recover(self, snapshot, *, expected_sha256, acknowledge_gap=False):
        if acknowledge_gap is not True:
            raise BusError('recovery_refused', 'explicit acknowledgement of unbacked-state uncertainty required')
        with self.bus.lifecycle(exclusive=True):
            if self.marker.exists() or self.marker.is_symlink():
                raise BusError('recovery_incomplete', 'existing recovery intent requires explicit reconciliation')
            self._current_authority()
            deadline = time.monotonic() + DEADLINE_SECONDS
            checked = self._verify(snapshot, expected_sha256, deadline)
            source = {name: self._source_identity(self.bus.root / name, deadline) for name in SOURCE_FILES
                if (self.bus.root / name).exists() or (self.bus.root / name).is_symlink()}
            epoch = 'recovery_' + uuid.uuid4().hex
            receipt = 'receipt_' + uuid.uuid4().hex
            quarantine = self.bus.root / epoch
            quarantine.mkdir(mode=0o700, exist_ok=False)
            _sync_directory(self.bus.root)
            stage = quarantine / 'recovered.sqlite'
            descriptor = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            os.close(descriptor)
            new_operator = quarantine / 'operator.json'
            secret = secrets.token_urlsafe(32)
            write_capability(new_operator, dict(schema_version=1, role='operator', bus_id=self.bus.bus_id, secret=secret))
            snapshot_db = sqlite3.connect((Path(snapshot).absolute() / 'mailbox.sqlite').as_uri() + '?mode=ro&immutable=1', uri=True, isolation_level=None)
            prepared = sqlite3.connect(stage, isolation_level=None)
            try:
                def progress(status, remaining, total):
                    if time.monotonic() > deadline:
                        raise BusError('recovery_refused', 'recovery image preparation deadline exceeded')
                snapshot_db.backup(prepared, pages=256, progress=progress, sleep=0.01)
                prepared.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
                prepared.execute('PRAGMA foreign_keys=ON')
                prepared.execute('BEGIN IMMEDIATE')
                metadata = dict(schema_version=2, paused=True, recovery_hold=True, recovery_epoch=epoch,
                    recovery_gap_unknown=True, operator_digest=digest(secret))
                for key, value in metadata.items():
                    prepared.execute('INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, json.dumps(value)))
                for actor in prepared.execute('SELECT actor_id FROM actors').fetchall():
                    prepared.execute('UPDATE actors SET actor_id=?,revoked=1,generation=generation+1 WHERE actor_id=?',
                        ('actor_' + uuid.uuid4().hex, actor[0]))
                prepared.execute('UPDATE enrollments SET can_send=0,can_receive=0,can_notify=0')
                prepared.execute('DELETE FROM mail_leases')
                self.bus.event(prepared, 'operator-recovery', 'recovery_image_prepared',
                    dict(recovery_epoch=epoch, request_receipt_id=receipt, snapshot_id=checked['snapshot_id'],
                        database_sha256=expected_sha256, gap_unknown=True, activation_complete=False))
                prepared.execute('COMMIT')
                if prepared.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or prepared.execute('PRAGMA foreign_key_check').fetchone():
                    raise BusError('recovery_refused', 'prepared recovery integrity failed')
            finally:
                snapshot_db.close(); prepared.close()
            finalized = sqlite3.connect(stage, isolation_level=None, timeout=1)
            try:
                finalized.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
                if finalized.execute('PRAGMA journal_mode=WAL').fetchall() != [('wal',)]:
                    raise BusError('recovery_refused', 'recovery image WAL mode unavailable')
                checkpoint = finalized.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchall()
                if not checkpoint or checkpoint[0][0] != 0:
                    raise BusError('recovery_refused', 'recovery image checkpoint incomplete')
            finally:
                finalized.close()
            intent = dict(format_version=1, receipt_id=receipt, recovery_epoch=epoch,
                bus_id=self.bus.bus_id, canonical_root=str(self.bus.root), snapshot=str(Path(snapshot).absolute()),
                expected_sha256=expected_sha256, authorization_digest=self.authorization_digest, source=source, stage=identity(stage),
                stage_sha256=_hash(stage, deadline))
            _manifest(self.marker, intent)
            _sync_directory(self.bus.root)
            return self._complete(intent, deadline)

    def reconcile(self, *, expected_sha256):
        with self.bus.lifecycle(exclusive=True):
            if not (self.marker.exists() or self.marker.is_symlink()):
                raise BusError('no_recovery_in_progress', 'no pending recovery intent; no action performed')
            private_path(self.marker)
            try:
                if self.marker.stat().st_size > 16384:
                    raise ValueError('oversized')
                intent = json.loads(self.marker.read_text())
                required = {'format_version','receipt_id','recovery_epoch','bus_id','canonical_root','snapshot','expected_sha256','authorization_digest','source','stage','stage_sha256'}
                if (type(intent) is not dict or set(intent) != required or type(intent['format_version']) is not int or intent['format_version'] != 1 or
                    intent['canonical_root'] != str(self.bus.root) or intent['bus_id'] != self.bus.bus_id or
                    not re.fullmatch(r'recovery_[0-9a-f]{32}', intent['recovery_epoch']) or
                    not re.fullmatch(r'receipt_[0-9a-f]{32}', intent['receipt_id']) or
                    type(intent['source']) is not dict or not set(intent['source']).issubset(SOURCE_FILES)):
                    raise ValueError('invalid intent')
                for item, source in [(intent['stage'], False), *[(item, True) for item in intent['source'].values()]]:
                    fields = {'device','inode','bytes'} | ({'sha256'} if source else set())
                    if type(item) is not dict or set(item) != fields or any(type(item[key]) is not int or item[key] < 0 for key in ('device','inode','bytes')) or item['bytes'] > MAX_BYTES:
                        raise ValueError('invalid identity')
                    if source and (not isinstance(item['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])):
                        raise ValueError('invalid source commitment')
                if intent['authorization_digest'] != self.authorization_digest:
                    raise BusError('authorization_denied', 'pending recovery requires its original independent approval authority')
                if expected_sha256 != intent['expected_sha256']:
                    raise ValueError('wrong expected commitment')
                deadline = time.monotonic() + DEADLINE_SECONDS
                self._verify(intent['snapshot'], expected_sha256, deadline)
            except (OSError, ValueError, TypeError, KeyError):
                raise BusError('recovery_incomplete', 'recovery intent is not qualified; preserve all artifacts') from None
            return self._complete(intent, deadline)

    def _complete(self, intent, deadline):
        quarantine = self.bus.root / intent['recovery_epoch']
        stage = quarantine / 'recovered.sqlite'
        try:
            private_path(quarantine, directory=True)
            new_operator = quarantine / 'operator.json'
            capability = read_capability(new_operator)
            candidate = self.bus.path if self.bus.path.exists() and identity(self.bus.path) == intent['stage'] else stage
            if identity(candidate) != intent['stage'] or _hash(candidate, deadline) != intent['stage_sha256']:
                raise BusError('recovery_incomplete', 'prepared image commitment changed')
            database = sqlite3.connect(candidate.as_uri() + '?mode=ro&immutable=1', uri=True, isolation_level=None)
            try:
                database.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
                self.bus.operator(database, new_operator)
                if (self.bus.meta(database, 'schema_version') != 2 or self.bus.meta(database, 'canonical_root') != str(self.bus.root) or
                    self.bus.meta(database, 'bus_id') != self.bus.bus_id or self.bus.meta(database, 'recovery_epoch') != intent['recovery_epoch'] or
                    self.bus.meta(database, 'recovery_hold') is not True or self.bus.meta(database, 'recovery_gap_unknown') is not True or self.bus.meta(database, 'paused') is not True or
                    database.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or database.execute('PRAGMA foreign_key_check').fetchone() or
                    database.execute('SELECT 1 FROM actors WHERE revoked!=1 LIMIT 1').fetchone() or
                    database.execute('SELECT 1 FROM enrollments WHERE can_send!=0 OR can_receive!=0 OR can_notify!=0 LIMIT 1').fetchone() or
                    database.execute('SELECT 1 FROM mail_leases LIMIT 1').fetchone()):
                    raise BusError('recovery_incomplete', 'prepared image does not enforce held authority')
            finally:
                database.close()
            for name, original in intent['source'].items():
                path, preserved = self.bus.root / name, quarantine / name
                if preserved.exists() or preserved.is_symlink():
                    if self._source_identity(preserved, deadline) != original:
                        raise BusError('recovery_incomplete', 'quarantined source identity changed')
                    if path.exists() and not (name == 'mailbox.sqlite' and identity(path) == intent['stage']):
                        raise BusError('recovery_incomplete', 'conflicting canonical source appeared')
                else:
                    if self._source_identity(path, deadline) != original:
                        raise BusError('recovery_incomplete', 'source identity changed before quarantine')
                    os.replace(path, preserved)
                    _sync_directory(quarantine); _sync_directory(self.bus.root)
            for suffix in ('-wal', '-shm'):
                path = Path(str(self.bus.path) + suffix)
                if path.exists() or path.is_symlink():
                    raise BusError('recovery_incomplete', 'unqualified canonical sidecar appeared')
            if self.bus.path.exists():
                if identity(self.bus.path) != intent['stage']:
                    raise BusError('recovery_incomplete', 'unqualified canonical image appeared')
            else:
                os.replace(stage, self.bus.path)
                _sync_directory(quarantine); _sync_directory(self.bus.root)
            anchor = dict(format_version=1, bus_id=self.bus.bus_id, canonical_root=str(self.bus.root),
                operator_digest=digest(capability['secret']), recovery_epoch=intent['recovery_epoch'])
            anchor_path = self.bus.root / '.recovery-authority.json'
            if anchor_path.exists() or anchor_path.is_symlink():
                private_path(anchor_path)
                if anchor_path.stat().st_size > 4096:
                    raise BusError('recovery_incomplete', 'authority anchor oversized')
                previous = json.loads(anchor_path.read_text())
                if type(previous) is not dict or previous.get('operator_digest') not in (intent['authorization_digest'], anchor['operator_digest']) or previous.get('canonical_root') != str(self.bus.root) or previous.get('bus_id') != self.bus.bus_id:
                    raise BusError('recovery_incomplete', 'external authority changed during recovery')
            else:
                previous = None
            if previous != anchor:
                pending_anchor = quarantine / 'authority.json'
                if pending_anchor.exists() or pending_anchor.is_symlink():
                    private_path(pending_anchor)
                    if pending_anchor.stat().st_size > 4096 or json.loads(pending_anchor.read_text()) != anchor:
                        raise BusError('recovery_incomplete', 'prepared authority anchor differs')
                else:
                    _manifest(pending_anchor, anchor)
                    _sync_directory(quarantine)
                os.replace(pending_anchor, anchor_path)
                _sync_directory(quarantine); _sync_directory(self.bus.root)
            receipt = dict(format_version=1, receipt_id=intent['receipt_id'], recovery_epoch=intent['recovery_epoch'],
                bus_id=self.bus.bus_id, canonical_root=str(self.bus.root), snapshot_sha256=intent['expected_sha256'],
                completed=True, recovered=True, recovery_hold=True, gap_unknown=True)
            receipt_path = quarantine / 'receipt.json'
            if receipt_path.exists() or receipt_path.is_symlink():
                private_path(receipt_path)
                if receipt_path.stat().st_size > 4096 or json.loads(receipt_path.read_text()) != receipt:
                    raise BusError('recovery_incomplete', 'completion receipt differs; inspect preserved artifact')
            else:
                _manifest(receipt_path, receipt)
                _sync_directory(quarantine)
            self.marker.unlink()
            _sync_directory(self.bus.root)
            return dict(receipt, quarantine=str(quarantine), receipt_file=str(receipt_path), operator_capability_file=str(new_operator))
        except (OSError, sqlite3.Error, ValueError, TypeError, BusError):
            error = BusError('recovery_incomplete', 'recovery intent preserved; inspect artifacts and explicitly reconcile before retry')
            error.details = dict(receipt_id=intent['receipt_id'])
            raise error from None
