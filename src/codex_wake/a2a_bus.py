"""Owner-only A2A bus identity, enrollment and capability authority.

Capabilities are an auditable API boundary inside one OS user's trust domain;
filesystem permissions do not isolate a malicious process with the same UID.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import time
from time import monotonic as lifecycle_monotonic
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import uuid

from .a2a_identity import Actor, BusError, RuntimeIdentity

SCHEMA_VERSION = 1
LOCAL_FILESYSTEMS = frozenset({'ext2', 'ext3', 'ext4', 'btrfs', 'xfs', 'zfs', 'tmpfs', 'ramfs', 'overlay', 'f2fs'})


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def default_bus_root(bus_id: str = 'local') -> Path:
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', bus_id):
        raise BusError('invalid_argument', 'invalid bus identifier')
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'codex-wake/a2a' / bus_id


def private_path(path: Path, *, directory: bool = False) -> None:
    try:
        info = path.lstat()
    except OSError:
        raise BusError('store_unavailable', 'private bus path is unavailable') from None
    expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not expected or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600):
        raise BusError('ownership_mismatch', 'bus paths must be owned and private without symlinks')


def local_filesystem(path: Path) -> None:
    best = None
    try:
        for line in Path('/proc/self/mountinfo').read_text().splitlines():
            before, after = line.split(' - ', 1)
            mount = Path(re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), before.split()[4]))
            if path.is_relative_to(mount) and (best is None or len(str(mount)) > best[0]):
                best = len(str(mount)), after.split()[0]
    except (OSError, ValueError, IndexError):
        raise BusError('filesystem_unsupported', 'cannot qualify local bus filesystem') from None
    if best is None or best[1] not in LOCAL_FILESYSTEMS:
        raise BusError('filesystem_unsupported', 'bus requires a qualified local filesystem')


def write_capability(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(value, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        # Preserve interrupted bootstrap state for explicit recovery, never reset.
        raise BusError('store_unavailable', 'capability publication failed; inspect bus state') from None


def read_capability(path: Path) -> dict:
    private_path(path)
    try:
        if path.stat().st_size > 4096:
            raise ValueError('oversized')
        value = json.loads(path.read_text())
        if not isinstance(value, dict) or not isinstance(value.get('secret'), str):
            raise ValueError('invalid')
        return value
    except (OSError, ValueError):
        raise BusError('authorization_denied', 'invalid capability file') from None


class BusStore:
    def __init__(self, root: Path):
        self.root = Path(root).absolute()
        if self.root != self.root.resolve():
            raise BusError('ownership_mismatch', 'bus root cannot traverse symlinks')
        self.path = self.root / 'mailbox.sqlite'
        private_path(self.root, directory=True)
        local_filesystem(self.root)
        private_path(self.path)
        with self.connection() as database:
            self.bus_id = self.meta(database, 'bus_id')

    @classmethod
    def configure(cls, root: Path, *, bus_id: str = 'local', allow_cross_root: bool = False) -> tuple[BusStore, Path]:
        default_bus_root(bus_id)  # Validate without selecting a different location.
        root = Path(root).absolute()
        if root != root.resolve():
            raise BusError('ownership_mismatch', 'bus root cannot traverse symlinks')
        local_filesystem(root)
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        private_path(root, directory=True)
        path = root / 'mailbox.sqlite'
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.close(descriptor)
        except FileExistsError:
            raise BusError('already_configured', 'bus already exists; no state was reset') from None
        secret = secrets.token_urlsafe(32)
        bootstrap_receipt = 'receipt_' + uuid.uuid4().hex
        database = sqlite3.connect(path, isolation_level=None)
        try:
            database.execute('PRAGMA journal_mode=WAL')
            database.execute('PRAGMA foreign_keys=ON')
            database.executescript('''
                BEGIN IMMEDIATE;
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE enrollments (root TEXT PRIMARY KEY, can_send INTEGER NOT NULL,
                    can_receive INTEGER NOT NULL, can_notify INTEGER NOT NULL);
                CREATE TABLE actors (actor_id TEXT UNIQUE NOT NULL, namespace TEXT NOT NULL,
                    thread_id TEXT NOT NULL, root TEXT NOT NULL REFERENCES enrollments(root),
                    token_digest TEXT NOT NULL, generation INTEGER NOT NULL, revoked INTEGER NOT NULL,
                    PRIMARY KEY(namespace, thread_id));
                CREATE TABLE events (receipt_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                    actor TEXT NOT NULL, action TEXT NOT NULL, subject TEXT NOT NULL);
            ''')
            for key, value in dict(schema_version=SCHEMA_VERSION, bus_id=bus_id, canonical_root=str(root),
                                   operator_digest=digest(secret), allow_cross_root=bool(allow_cross_root),
                                   paused=True, bootstrap_receipt=bootstrap_receipt).items():
                database.execute('INSERT INTO meta VALUES (?,?)', (key, json.dumps(value)))
            database.execute('INSERT INTO events VALUES (?,?,?,?,?)',
                             (bootstrap_receipt, timestamp(), 'operator-bootstrap', 'configure',
                              json.dumps(dict(bus_id=bus_id, canonical_root=str(root), allow_cross_root=bool(allow_cross_root)))))
            capability = root / 'operator.json'
            write_capability(capability, dict(schema_version=1, bus_id=bus_id, secret=secret, role='operator'))
            database.execute('COMMIT')
        except sqlite3.Error:
            raise BusError('store_unavailable', 'bus bootstrap failed; existing state is preserved') from None
        finally:
            database.close()
        return cls(root), capability

    @staticmethod
    def meta(database, key: str):
        row = database.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        if row is None:
            raise BusError('store_unavailable', 'required bus metadata is missing')
        return json.loads(row[0])

    @contextmanager
    def lifecycle(self, *, exclusive=False):
        """Cooperative connection fencing; old/raw SQLite clients are not covered."""
        private_path(self.root, directory=True)
        path = self.root / '.lifecycle.lock'
        if path.exists() or path.is_symlink():
            private_path(path)
        try:
            descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        except OSError:
            raise BusError('store_unavailable', 'lifecycle lock unavailable') from None
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
                raise BusError('ownership_mismatch', 'lifecycle lock must be owner-only')
            deadline = lifecycle_monotonic() + 1
            while True:
                try:
                    fcntl.flock(descriptor, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if lifecycle_monotonic() >= deadline:
                        raise BusError('bus_busy', 'participating bus connections prevent lifecycle maintenance') from None
                    time.sleep(0.01)
            yield
        finally:
            os.close(descriptor)

    @contextmanager
    def connection(self, *, read_only: bool = False):
        with self.lifecycle():
            with self._connection(read_only=read_only) as database:
                yield database

    @contextmanager
    def maintenance_connection(self):
        with self.lifecycle(exclusive=True):
            with self._connection() as database:
                yield database

    @contextmanager
    def _connection(self, *, read_only: bool = False):
        private_path(self.root, directory=True)
        private_path(self.path)
        for suffix in ('-wal', '-shm'):
            sidecar = Path(str(self.path) + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                private_path(sidecar)
        database = None
        try:
            mode = 'ro' if read_only else 'rw'
            database = sqlite3.connect(self.path.as_uri() + '?mode=' + mode,
                                       uri=True, isolation_level=None, timeout=1)
            database.row_factory = sqlite3.Row
            database.execute('PRAGMA foreign_keys=ON')
            version = self.meta(database, 'schema_version')
            if type(version) is not int or version != SCHEMA_VERSION:
                raise BusError('unsupported_schema', 'unsupported bus schema; no downgrade attempted')
            if self.meta(database, 'canonical_root') != str(self.root):
                raise BusError('bus_identity_mismatch', 'copied bus root cannot become another active writer')
            yield database
        except BusError:
            raise
        except (sqlite3.Error, ValueError, TypeError, KeyError, IndexError):
            raise BusError('store_unavailable', 'bus journal unavailable; no automatic repair attempted') from None
        finally:
            if database is not None:
                database.close()

    def operator(self, database, capability: Path) -> None:
        value = read_capability(capability)
        if value.get('bus_id') != self.meta(database, 'bus_id') or not secrets.compare_digest(digest(value['secret']), self.meta(database, 'operator_digest')):
            raise BusError('authorization_denied', 'operator capability is required')

    def event(self, database, actor: str, action: str, subject: dict) -> str:
        identifier = 'receipt_' + uuid.uuid4().hex
        database.execute('INSERT INTO events VALUES (?,?,?,?,?)',
                         (identifier, timestamp(), actor, action, json.dumps(subject, sort_keys=True)))
        return identifier

    def enroll(self, root: Path, operator_capability: Path, *, send: bool = True,
               receive: bool = True, notify: bool = False) -> str:
        root = root.resolve(strict=True)
        if not root.is_dir():
            raise BusError('invalid_argument', 'enrollment root must be a directory')
        with self.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            self.operator(database, operator_capability)
            database.execute('INSERT INTO enrollments VALUES (?,?,?,?) ON CONFLICT(root) DO UPDATE SET can_send=excluded.can_send,can_receive=excluded.can_receive,can_notify=excluded.can_notify',
                             (str(root), int(send), int(receive), int(notify)))
            receipt = self.event(database, 'operator', 'enroll', dict(root=str(root), send=send, receive=receive, notify=notify))
            database.execute('COMMIT')
            return receipt

    def issue_actor(self, identity: RuntimeIdentity, root: Path, operator_capability: Path) -> tuple[Path, str]:
        root = root.resolve(strict=True)
        if not Path(identity.cwd).is_relative_to(root):
            raise BusError('authorization_denied', 'thread is outside the selected enrollment root')
        secret, actor_id = secrets.token_urlsafe(32), 'actor_' + uuid.uuid4().hex
        with self.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            self.operator(database, operator_capability)
            if database.execute('SELECT root FROM enrollments WHERE root=?', (str(root),)).fetchone() is None:
                raise BusError('authorization_denied', 'root is not enrolled')
            if database.execute('SELECT actor_id FROM actors WHERE namespace=? AND thread_id=?', (identity.namespace, identity.thread_id)).fetchone():
                raise BusError('already_authorized', 'thread already has a capability; rotation must be explicit')
            database.execute('INSERT INTO actors VALUES (?,?,?,?,?,?,0)',
                             (actor_id, identity.namespace, identity.thread_id, str(root), digest(secret), 1))
            receipt = self.event(database, 'operator', 'issue_actor', dict(namespace=identity.namespace, thread_id=identity.thread_id, root=str(root), actor_id=actor_id))
            directory = self.root / 'capabilities'
            directory.mkdir(mode=0o700, exist_ok=True)
            private_path(directory, directory=True)
            capability = directory / (actor_id + '.json')
            write_capability(capability, dict(schema_version=1, bus_id=self.bus_id, actor_id=actor_id, secret=secret))
            database.execute('COMMIT')
            return capability, receipt

    def rotate_actor(self, actor_id: str, operator_capability: Path) -> tuple[Path, str]:
        secret = secrets.token_urlsafe(32)
        with self.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            self.operator(database, operator_capability)
            row = database.execute('SELECT * FROM actors WHERE actor_id=?', (actor_id,)).fetchone()
            if row is None:
                raise BusError('not_found', 'actor not found')
            generation = row['generation'] + 1
            directory = self.root / 'capabilities'
            private_path(directory, directory=True)
            capability = directory / (actor_id + '_g' + str(generation) + '.json')
            write_capability(capability, dict(schema_version=1, bus_id=self.bus_id, actor_id=actor_id, secret=secret))
            database.execute('UPDATE actors SET token_digest=?,generation=?,revoked=0 WHERE actor_id=?',
                             (digest(secret), generation, actor_id))
            receipt = self.event(database, 'operator', 'rotate_actor', dict(actor_id=actor_id, generation=generation))
            database.execute('COMMIT')
            return capability, receipt

    def authenticate(self, capability: Path, identity: RuntimeIdentity, *, invoking_cwd: Path) -> Actor:
        value = read_capability(capability)
        with self.connection() as database:
            row = database.execute('SELECT * FROM actors WHERE actor_id=?', (value.get('actor_id'),)).fetchone()
            if (row is None or value.get('bus_id') != self.bus_id or row['revoked'] or
                not secrets.compare_digest(row['token_digest'], digest(value['secret'])) or
                row['namespace'] != identity.namespace or row['thread_id'] != identity.thread_id or
                not Path(identity.cwd).is_relative_to(row['root']) or
                not invoking_cwd.resolve().is_relative_to(row['root'])):
                raise BusError('authorization_denied', 'capability and runtime context do not match')
            return Actor(self.bus_id, row['namespace'], row['thread_id'], row['root'], row['generation'], row['actor_id'])

    def revoke_actor(self, actor_id: str, operator_capability: Path) -> str:
        with self.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            self.operator(database, operator_capability)
            changed = database.execute('UPDATE actors SET revoked=1,generation=generation+1 WHERE actor_id=? AND revoked=0', (actor_id,)).rowcount
            if changed != 1:
                raise BusError('not_found', 'active actor capability not found')
            receipt = self.event(database, 'operator', 'revoke_actor', dict(actor_id=actor_id))
            database.execute('COMMIT')
            return receipt

    def validate_actor(self, database, actor: Actor, *, permission: str = 'inspect'):
        row = database.execute('SELECT a.*, e.can_send,e.can_receive,e.can_notify FROM actors a JOIN enrollments e ON a.root=e.root WHERE a.actor_id=?', (actor.actor_id,)).fetchone()
        if (row is None or actor.bus_id != self.bus_id or row['revoked'] or
            row['namespace'] != actor.namespace or row['thread_id'] != actor.thread_id or
            row['root'] != actor.root or row['generation'] != actor.generation):
            raise BusError('authorization_denied', 'actor authority is stale or revoked')
        if permission == 'send' and not row['can_send']:
            raise BusError('authorization_denied', 'enrollment does not permit sending')
        if permission == 'receive' and not row['can_receive']:
            raise BusError('authorization_denied', 'enrollment does not permit receiving')
        if permission == 'inspect' and not (row['can_send'] or row['can_receive']):
            raise BusError('authorization_denied', 'enrollment is disabled')
        return row

    def authorize_pair(self, database, sender: Actor, recipient: RuntimeIdentity) -> Actor:
        self.validate_actor(database, sender, permission='send')
        row = database.execute('SELECT * FROM actors WHERE namespace=? AND thread_id=?',
                               (recipient.namespace, recipient.thread_id)).fetchone()
        if row is None or row['revoked'] or not Path(recipient.cwd).is_relative_to(row['root']):
            raise BusError('authorization_denied', 'recipient has no matching active enrollment capability')
        target = Actor(self.bus_id, row['namespace'], row['thread_id'], row['root'], row['generation'], row['actor_id'])
        self.validate_actor(database, target, permission='receive')
        if sender.key == target.key:
            raise BusError('self_send_denied', 'self messaging is unsupported in this version')
        if sender.root != target.root and not self.meta(database, 'allow_cross_root'):
            raise BusError('cross_root_denied', 'cross-root messaging requires explicit bus permission')
        return target

    def set_paused(self, paused: bool, operator_capability: Path) -> str:
        with self.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            self.operator(database, operator_capability)
            database.execute("UPDATE meta SET value=? WHERE key='paused'", (json.dumps(bool(paused)),))
            receipt = self.event(database, 'operator', 'pause' if paused else 'resume', dict(paused=bool(paused)))
            database.execute('COMMIT')
            return receipt

    def status(self) -> dict:
        with self.connection() as database:
            return dict(schema_version=1, bus_id=self.bus_id, store_schema=SCHEMA_VERSION,
                        paused=self.meta(database, 'paused'),
                        allow_cross_root=self.meta(database, 'allow_cross_root'),
                        enrolled_roots=database.execute('SELECT count(*) FROM enrollments').fetchone()[0],
                        active_actors=database.execute('SELECT count(*) FROM actors WHERE revoked=0').fetchone()[0],
                        notification_capability='unqualified', same_uid_isolation=False)
