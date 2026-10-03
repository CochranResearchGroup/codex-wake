"""Explicit operator-delegated receipt inspection, never actor impersonation."""
from contextlib import contextmanager
import json
from pathlib import Path
import re

from .a2a_bus import BusStore, private_path
from .a2a_identity import Actor, BusError
from .a2a_mailbox import Mailbox


def _unavailable():
    return BusError('receipt_authority_unavailable', 'configured receipt authority is unavailable')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate configuration member')
        result[key] = value
    return result


def _absolute_path(value):
    if type(value) is not str or not value or len(value.encode()) > 4096:
        raise _unavailable()
    path = Path(value)
    if not path.is_absolute() or path != path.resolve():
        raise _unavailable()
    return path


class ConfiguredReceiptAuthority:
    """Read private, independent grants for one explicitly selected wake root.

    The operator capability delegates inspection of the listed conversation to
    the daemon. An Actor value only pins whose conversation is being observed;
    it is not runtime authentication or permission to execute actor operations.
    """

    def __init__(self, path: Path, wake_root: Path):
        self.path = Path(path).absolute()
        self.wake_root = Path(wake_root).resolve()

    def grants(self):
        try:
            if self.path != self.path.resolve():
                raise _unavailable()
            private_path(self.path)
            with self.path.open('rb') as stream:
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise _unavailable()
            config = json.loads(raw, object_pairs_hook=_unique_object)
            if (type(config) is not dict or set(config) != {'schema_version', 'wake_root', 'grants'}
                    or type(config['schema_version']) is not int or config['schema_version'] != 1
                    or _absolute_path(config['wake_root']) != self.wake_root
                    or type(config['grants']) is not list or len(config['grants']) > 100):
                raise _unavailable()
            result = {}
            for grant in config['grants']:
                if (type(grant) is not dict or set(grant) != {
                        'source_instance', 'bus_root', 'bus_id', 'operator_capability', 'actor', 'message_id'}
                        or type(grant['source_instance']) is not str
                        or not re.fullmatch(r'mailbox-[0-9a-f]{32}', grant['source_instance'])
                        or grant['source_instance'] in result
                        or type(grant['message_id']) is not str
                        or not 1 <= len(grant['message_id'].encode()) <= 128
                        or type(grant['bus_id']) is not str
                        or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', grant['bus_id'])
                        or type(grant['actor']) is not dict):
                    raise _unavailable()
                _absolute_path(grant['bus_root'])
                _absolute_path(grant['operator_capability'])
                actor = Actor(**grant['actor'])
                if (actor.bus_id != grant['bus_id'] or type(actor.generation) is not int
                        or actor.generation < 1 or any(type(value) is not str or not value
                            or len(value.encode()) > 4096 for value in (
                                actor.bus_id, actor.namespace, actor.thread_id, actor.root, actor.actor_id))):
                    raise _unavailable()
                _absolute_path(actor.root)
                result[grant['source_instance']] = grant
            return result
        except (OSError, ValueError, TypeError, KeyError, RecursionError, BusError):
            raise _unavailable() from None

    def resolve(self, armed):
        # Only this independent allowlist supplies filesystem paths/authority.
        try:
            grant = self.grants()[armed.spec.source_instance]
            if (armed.spec.source != 'a2a.receipt'
                    or armed.spec.subject != 'message:' + grant['message_id']):
                raise _unavailable()
            actor = Actor(**grant['actor'])
            bus = BusStore(Path(grant['bus_root']))
            if bus.bus_id != grant['bus_id']:
                raise _unavailable()
            mailbox = _ObserverMailbox(bus, self, grant, actor)
            from .a2a_receipt_signals import ReceiptSignalAdapter
            adapter = ReceiptSignalAdapter.restore(armed, mailbox, actor)
            if adapter.message_id != grant['message_id'] or adapter.source_instance != grant['source_instance']:
                raise _unavailable()
            return mailbox, actor
        except (OSError, ValueError, TypeError, KeyError, AttributeError, BusError):
            raise _unavailable() from None


class _ObserverMailbox(Mailbox):
    def __init__(self, bus, authority, grant, actor):
        self.authority, self.grant, self.actor = authority, grant, actor
        super().__init__(bus)

    @contextmanager
    def transaction(self, actor=None, *, permission='inspect'):
        # Re-read every transaction so removal/replacement fences cached runners.
        if (actor != self.actor or permission != 'inspect'
                or self.authority.grants().get(self.grant['source_instance']) != self.grant):
            raise _unavailable()
        with self.bus.connection() as database:
            database.execute('PRAGMA query_only=ON')
            database.execute('BEGIN')
            self._schema(database)
            self.bus.operator(database, Path(self.grant['operator_capability']))
            self.bus.validate_actor(database, actor)
            yield database
