"""Operator-delegated observation of explicitly listed senders' own requests."""
from contextlib import contextmanager
from dataclasses import asdict
import json
import os
import tempfile
from pathlib import Path

from .a2a_bus import BusStore, private_path
from .a2a_identity import Actor, BusError
from .a2a_mailbox import Mailbox
from .a2a_receipt_authority import _absolute_path, _unique_object, _unavailable
from .a2a_receipt_signals import ReceiptSignalAdapter


class SenderReceiptAuthority:
    """Independent bounded allowlist; an arm never supplies paths or authority."""
    def __init__(self, path, wake_root):
        self.path = Path(path)
        self.wake_root = Path(wake_root).resolve()

    def senders(self):
        try:
            if not self.path.is_absolute() or self.path != self.path.resolve():
                raise _unavailable()
            private_path(self.path)
            with self.path.open('rb') as stream:
                raw = stream.read(65537)
            config = json.loads(raw, object_pairs_hook=_unique_object)
            if (len(raw) > 65536 or type(config) is not dict
                    or set(config) != {'schema_version', 'wake_root', 'senders'}
                    or type(config['schema_version']) is not int or config['schema_version'] != 1
                    or _absolute_path(config['wake_root']) != self.wake_root
                    or type(config['senders']) is not list or not 1 <= len(config['senders']) <= 100):
                raise _unavailable()
            result = {}
            for grant in config['senders']:
                if type(grant) is not dict or set(grant) != {'bus_root', 'bus_id', 'operator_capability', 'actor'}:
                    raise _unavailable()
                _absolute_path(grant['bus_root'])
                _absolute_path(grant['operator_capability'])
                actor = Actor(**grant['actor'])
                _absolute_path(actor.root)
                if (actor.bus_id != grant['bus_id'] or type(actor.generation) is not int
                        or actor.generation < 1 or any(type(value) is not str or not value
                            or len(value.encode()) > 4096 for value in
                            (actor.bus_id, actor.namespace, actor.thread_id, actor.actor_id))):
                    raise _unavailable()
                key = (actor.bus_id, actor.key)
                if key in result:
                    raise _unavailable()
                result[key] = grant
            return result
        except (OSError, ValueError, TypeError, KeyError, RecursionError, BusError):
            raise _unavailable() from None

    def adapter(self, actor, message_id):
        try:
            grant = self.senders()[(actor.bus_id, actor.key)]
            if grant['actor'] != asdict(actor):
                raise _unavailable()
            bus = BusStore(Path(grant['bus_root']))
            if bus.bus_id != actor.bus_id:
                raise _unavailable()
            return ReceiptSignalAdapter(_SenderObserver(bus, self, grant, actor, message_id), actor, message_id)
        except (OSError, ValueError, TypeError, KeyError, BusError):
            raise _unavailable() from None

    def delegate(self, bus, operator_capability, actor):
        """Explicit operator action granting only this sender's receipt observation."""
        from .records import WakeLifecycleLock
        with bus.connection() as database:
            bus.operator(database, operator_capability)
            bus.validate_actor(database, actor, permission='send')
        if not self.path.is_absolute() or self.path != self.path.resolve():
            raise _unavailable()
        private_path(self.path.parent, directory=True)
        with WakeLifecycleLock(self.path.parent, 'sender-authority:' + str(self.path)):
            return self._delegate_unlocked(bus, operator_capability, actor)

    def _delegate_unlocked(self, bus, operator_capability, actor):
        with bus.connection() as database:
            bus.operator(database, operator_capability)
            row = bus.validate_actor(database, actor, permission='send')
            if not row['can_notify']:
                raise BusError('authorization_denied', 'sender receipt delegation requires notification enrollment')
        if not self.path.is_absolute() or self.path != self.path.resolve():
            raise _unavailable()
        private_path(self.path.parent, directory=True)
        grants = self.senders() if self.path.exists() or self.path.is_symlink() else {}
        if any(grant['bus_root'] != str(bus.root) or grant['operator_capability'] != str(operator_capability.resolve())
               for grant in grants.values()):
            raise BusError('authorization_denied', 'configuration belongs to a different explicit bus authority')
        key = (actor.bus_id, actor.key)
        if key not in grants and len(grants) >= 100:
            raise BusError('invalid_argument', 'sender delegation limit reached')
        grant = dict(bus_root=str(bus.root), bus_id=bus.bus_id,
                     operator_capability=str(operator_capability.resolve()), actor=asdict(actor))
        grants[key] = grant
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', dir=self.path.parent, prefix='.sender-receipts-', delete=False) as stream:
                temporary = Path(stream.name)
                os.chmod(temporary, 0o600)
                json.dump(dict(schema_version=1, wake_root=str(self.wake_root), senders=list(grants.values())), stream)
                stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            descriptor = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        if self.senders().get(key) != grant:
            raise _unavailable()
        return dict(actor_id=actor.actor_id, thread_id=actor.thread_id,
                    wake_root=str(self.wake_root), sender_receipt_authority=str(self.path))

    def resolve(self, armed):
        if (armed.spec.source != 'a2a.receipt'
                or not armed.spec.subject.startswith('message:')):
            raise _unavailable()
        message_id = armed.spec.subject.removeprefix('message:')
        for grant in self.senders().values():
            actor = Actor(**grant['actor'])
            try:
                adapter = self.adapter(actor, message_id)
                if adapter.source_instance == armed.spec.source_instance and adapter.valid_arm(armed):
                    return adapter.mailbox, actor
            except BusError:
                continue
        raise _unavailable()


class _SenderObserver(Mailbox):
    def __init__(self, bus, authority, grant, actor, message_id):
        self.authority, self.grant, self.actor, self.message_id = authority, grant, actor, message_id
        super().__init__(bus)

    @contextmanager
    def transaction(self, actor=None, *, permission='inspect'):
        if (actor != self.actor or permission != 'inspect'
                or self.authority.senders().get((actor.bus_id, actor.key)) != self.grant):
            raise _unavailable()
        with self.bus.connection(read_only=True) as database:
            database.execute('PRAGMA query_only=ON')
            database.execute('BEGIN')
            self._schema(database)
            self.bus.operator(database, Path(self.grant['operator_capability']))
            self.bus.validate_actor(database, actor)
            original = self._row(database, self.message_id)
            if original['sender_key'] != actor.key:
                raise _unavailable()
            yield database
