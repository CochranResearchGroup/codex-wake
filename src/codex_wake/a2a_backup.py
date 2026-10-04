"""Private versioned snapshots. Verification is never restore activation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
import uuid

from .a2a_bus import BusStore, SCHEMA_VERSION, local_filesystem, private_path
from .a2a_identity import BusError
from .a2a_mailbox import Mailbox, MAILBOX_SCHEMA

FORMAT = 1
MAX_BYTES = 1024 ** 3
DEADLINE_SECONDS = 10
FIELDS = frozenset({'format_version', 'snapshot_id', 'bus_id', 'canonical_root',
    'bus_schema', 'mailbox_schema', 'database_bytes', 'database_sha256', 'request_receipt_id'})


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _hash(path, deadline):
    if path.stat().st_size > MAX_BYTES:
        raise BusError('backup_invalid', 'backup exceeds the one GiB limit')
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            if time.monotonic() > deadline:
                raise BusError('backup_invalid', 'backup verification deadline exceeded')
            value.update(chunk)
    return value.hexdigest()


def _manifest(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


class MailBackup:
    def __init__(self, bus: BusStore, operator_capability: Path):
        self.bus, self.operator_capability = bus, operator_capability

    def create(self, directory: Path):
        """Publish manifest last; interrupted directories remain explicit evidence."""
        directory = Path(directory).absolute()
        if directory != directory.resolve() or directory.is_relative_to(self.bus.root):
            raise BusError('invalid_argument', 'snapshot requires a separate unsymlinked directory')
        private_path(directory.parent, directory=True)
        local_filesystem(directory.parent)
        request = None
        try:
            # Audit the request before filesystem effects. No credentials exported.
            with self.bus.connection() as source:
                source.execute('BEGIN IMMEDIATE')
                self.bus.operator(source, self.operator_capability)
                Mailbox._schema(source)
                if self.bus.meta(source, 'paused') is not True:
                    raise BusError('pause_required', 'pause the bus before snapshot creation')
                if source.execute('PRAGMA page_count').fetchone()[0] * source.execute('PRAGMA page_size').fetchone()[0] > MAX_BYTES:
                    raise BusError('backup_invalid', 'source exceeds the one GiB limit')
                request = self.bus.event(source, 'operator', 'backup_requested', dict(directory=str(directory)))
                source.execute('COMMIT')
                directory.mkdir(mode=0o700, exist_ok=False)
                _sync_directory(directory.parent)
                database_path = directory / 'mailbox.sqlite'
                descriptor = os.open(database_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                os.close(descriptor)
                deadline = time.monotonic() + DEADLINE_SECONDS
                source.execute('BEGIN')
                # Fix one read snapshot, including pause/authority/schema and request.
                self.bus.operator(source, self.operator_capability)
                Mailbox._schema(source)
                if self.bus.meta(source, 'paused') is not True:
                    raise BusError('pause_required', 'source resumed before snapshot boundary')
                page_size = source.execute('PRAGMA page_size').fetchone()[0]
                target = sqlite3.connect(database_path, isolation_level=None)
                try:
                    def progress(status, remaining, total):
                        if time.monotonic() > deadline or total * page_size > MAX_BYTES:
                            raise BusError('backup_invalid', 'snapshot copy deadline or size exceeded')
                    source.backup(target, pages=256, progress=progress, sleep=0.01)
                    target.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
                    target.execute('PRAGMA journal_mode=DELETE')
                    if target.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or target.execute('PRAGMA foreign_key_check').fetchone():
                        raise BusError('backup_invalid', 'snapshot integrity or foreign keys failed')
                finally:
                    target.close()
                source.execute('ROLLBACK')
            with database_path.open('rb') as stream:
                os.fsync(stream.fileno())
            manifest = dict(format_version=FORMAT, snapshot_id='snapshot_' + uuid.uuid4().hex,
                bus_id=self.bus.bus_id, canonical_root=str(self.bus.root), bus_schema=SCHEMA_VERSION,
                mailbox_schema=MAILBOX_SCHEMA, database_bytes=database_path.stat().st_size,
                database_sha256=_hash(database_path, deadline), request_receipt_id=request)
            _manifest(directory / 'manifest.json', manifest)
            _sync_directory(directory)
            # Verification checks actual contents before declaring publication complete.
            checked = self._verify(directory, deadline)
            with self.bus.connection() as source:
                source.execute('BEGIN IMMEDIATE')
                self.bus.operator(source, self.operator_capability)
                receipt = self.bus.event(source, 'operator', 'backup_completed',
                    dict(snapshot_id=manifest['snapshot_id'], database_sha256=manifest['database_sha256'], request_receipt_id=request))
                source.execute('COMMIT')
            return dict(checked, receipt_id=receipt, request_receipt_id=request)
        except (OSError, sqlite3.Error, BusError) as exc:
            if request is None:
                if isinstance(exc, BusError):
                    raise
                raise BusError('backup_invalid', 'snapshot preflight failed; source preserved') from None
            error = BusError('backup_incomplete', 'snapshot request committed; inspect preserved directory and audit before retry')
            error.details = dict(receipt_id=request)
            raise error from None

    def verify(self, directory: Path):
        """Read-only validation against current independently supplied authority."""
        return self._verify(directory, time.monotonic() + DEADLINE_SECONDS)

    def _verify(self, directory: Path, deadline):
        directory = Path(directory).absolute()
        if directory != directory.resolve():
            raise BusError('ownership_mismatch', 'snapshot path cannot traverse symlinks')
        private_path(directory, directory=True)
        local_filesystem(directory)
        path, manifest_path = directory / 'mailbox.sqlite', directory / 'manifest.json'
        private_path(path)
        private_path(manifest_path)
        try:
            if manifest_path.stat().st_size > 4096 or set(p.name for p in directory.iterdir()) != {'mailbox.sqlite', 'manifest.json'}:
                raise ValueError('incomplete or unexpected artifacts')
            manifest = json.loads(manifest_path.read_text())
            if not isinstance(manifest, dict) or set(manifest) != FIELDS:
                raise ValueError('manifest fields')
            if any(type(manifest[key]) is not int for key in ('format_version', 'bus_schema', 'mailbox_schema', 'database_bytes')):
                raise ValueError('manifest types')
            if any(not isinstance(manifest[key], str) or not manifest[key] for key in FIELDS - {'format_version', 'bus_schema', 'mailbox_schema', 'database_bytes'}):
                raise ValueError('manifest strings')
            if (manifest['format_version'], manifest['bus_schema'], manifest['mailbox_schema']) != (FORMAT, SCHEMA_VERSION, MAILBOX_SCHEMA):
                raise ValueError('unsupported versions')
            if manifest['bus_id'] != self.bus.bus_id or manifest['canonical_root'] != str(self.bus.root):
                raise BusError('bus_identity_mismatch', 'backup belongs to a different canonical bus')
            with self.bus.connection(read_only=True) as live:
                self.bus.operator(live, self.operator_capability)
                current_operator = self.bus.meta(live, 'operator_digest')
            if path.stat().st_size != manifest['database_bytes'] or _hash(path, deadline) != manifest['database_sha256']:
                raise ValueError('snapshot digest or length')
            database = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True, isolation_level=None)
            try:
                database.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
                if database.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or database.execute('PRAGMA foreign_key_check').fetchone():
                    raise ValueError('snapshot integrity')
                version = self.bus.meta(database, 'schema_version')
                if type(version) is not int or version != SCHEMA_VERSION:
                    raise ValueError('bus schema')
                Mailbox._schema(database)
                if self.bus.meta(database, 'bus_id') != self.bus.bus_id or self.bus.meta(database, 'canonical_root') != str(self.bus.root):
                    raise BusError('bus_identity_mismatch', 'snapshot content identity differs')
                self.bus.operator(database, self.operator_capability)
                if not secrets.compare_digest(self.bus.meta(database, 'operator_digest'), current_operator):
                    raise BusError('authorization_denied', 'snapshot operator authority differs from current bus')
                if self.bus.meta(database, 'paused') is not True:
                    raise ValueError('unpaused snapshot')
                request = database.execute('SELECT action FROM events WHERE receipt_id=?', (manifest['request_receipt_id'],)).fetchone()
                if request is None or request[0] != 'backup_requested':
                    raise ValueError('snapshot request provenance')
                counts = {name: database.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                    for name in ('actors', 'events', 'mail_identities', 'mail_receipts', 'mail_attempts')}
            finally:
                database.close()
            return dict(verified=True, activation_qualified=False, snapshot_id=manifest['snapshot_id'],
                bus_id=self.bus.bus_id, mailbox_schema=MAILBOX_SCHEMA, database_sha256=manifest['database_sha256'],
                database_bytes=manifest['database_bytes'], counts=counts)
        except BusError:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError):
            raise BusError('backup_invalid', 'backup format, integrity or commitment is invalid; no activation attempted') from None
