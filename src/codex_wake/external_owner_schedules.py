"""External OAuth admission into an explicitly configured Windows MessageOwner."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import UUID

from .controller_auth import AuthError
from .managed_inventory import InventoryError
from .unified_connectors import check_action


SCHEDULE = 'wakes.messages.schedule'
STATUS = 'wakes.messages.status'
_SCOPES = {SCHEDULE: 'control', STATUS: 'observe'}
_FIELDS = {'host', 'environment', 'presentation', 'conversation_id', 'namespace', 'authority', 'generation'}
_UUID = {'type': 'string', 'pattern': r'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'}
_TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 128}


def _schema(fields):
    return dict(type='object', properties=fields, required=list(fields), additionalProperties=False)


_COMMON = dict(message_id=_UUID, expected_target=_schema(dict.fromkeys(_FIELDS, _TEXT)))
TOOLS = {
    'wake_wakes_messages_schedule': (SCHEDULE, _schema(dict(
        _COMMON, body={'type': 'string', 'minLength': 1, 'maxLength': 32768}, due_at=_TEXT, expires_at=_TEXT))),
    'wake_wakes_messages_status': (STATUS, _schema(_COMMON)),
}
DESCRIPTIONS = {
    SCHEDULE: 'Retain a timed message for an explicitly granted Windows psmux conversation. The owning worker restores and delivers it.',
    STATUS: 'Read this grant’s timed Windows psmux message receipt, without reading its body or starting the recipient.',
}


def _target(value, host, environment):
    if (not isinstance(value, dict) or set(value) != _FIELDS
            or value['host'] != host or value['environment'] != environment
            or value['presentation'] != 'psmux'
            or any(not isinstance(x, str) or not 1 <= len(x) <= 128 or any(ord(c) < 32 for c in x)
                   for x in value.values())
            or str(UUID(value['conversation_id'])) != value['conversation_id']):
        raise ValueError('exact local and destination owner target required')
    return value


def validate(config, host, environment):
    if not isinstance(config, dict) or set(config) != {'owner_config', 'targets'}:
        raise ValueError('explicit Windows MessageOwner routing configuration required')
    if not isinstance(config['owner_config'], str) or not Path(config['owner_config']).is_absolute():
        raise ValueError('absolute private MessageOwner config path required')
    if not isinstance(config['targets'], list) or not 1 <= len(config['targets']) <= 64:
        raise ValueError('explicit bounded Windows schedule targets required')
    targets = [_target(item, host, environment) for item in config['targets']]
    if len({item['conversation_id'] for item in targets}) != len(targets):
        raise ValueError('ambiguous Windows schedule targets')


def _micros(value):
    from .network_wakes import precise_deadline

    elapsed = precise_deadline(value) - datetime(1970, 1, 1, tzinfo=UTC)
    return (elapsed.days * 86400 + elapsed.seconds) * 1_000_000 + elapsed.microseconds


class OwnerSchedules:
    def __init__(self, config, host, environment):
        validate(config, host, environment)
        self.config = config

    def policy(self, operation):
        return _SCOPES.get(operation)

    def visible(self, actor, operation):
        return self.policy(operation) in actor.scopes and any(target in actor.targets for target in self.config['targets'])

    def _authorize(self, actor, operation, target):
        check_action(actor, operation)
        if (self.policy(operation) not in actor.scopes or target not in self.config['targets']
                or target not in actor.targets):
            raise AuthError('insufficient_scope')

    def execute(self, verify, token, operation, arguments):
        from .controller_runtime import identity
        from .message_owner import _worker

        actor = verify(token)
        target = arguments['expected_target']
        self._authorize(actor, operation, target)
        try:
            identifier = str(UUID(arguments['message_id']))
            if identifier != arguments['message_id']:
                raise ValueError('canonical message UUID required')
            if operation == SCHEDULE:
                due, expiry = _micros(arguments['due_at']), _micros(arguments['expires_at'])
                if not 0 < due < expiry:
                    raise ValueError('original due time must precede expiry')
        except (KeyError, TypeError, ValueError, OverflowError):
            raise InventoryError('invalid_argument', 'exact message identity and original delivery window required') from None

        try:
            owner, _, _ = _worker(Path(self.config['owner_config']))
        except (AttributeError, KeyError, OSError, sqlite3.Error, TypeError, ValueError):
            raise InventoryError('owner_unavailable', 'configured MessageOwner is unavailable') from None
        observed = dict(host=owner.local['host'], namespace=owner.peer['environment'],
                        authority=owner.peer['authority'], generation=owner.peer['generation'])
        if owner.kind != 'wsl' or owner.peer_kind != 'windows' or any(target[key] != value for key, value in observed.items()):
            raise InventoryError('stale_target', 'registered Windows MessageOwner generation changed')
        origin = hashlib.sha256(json.dumps(identity(actor), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self._authorize(verify(token), operation, target)
        try:
            if operation == SCHEDULE:
                owner.send(identifier, target['conversation_id'], arguments['body'],
                           expires=expiry, due=due, origin=origin)
            value = owner.status(identifier, 'out', recipient=target['conversation_id'], origin=origin)
        except ValueError:
            raise InventoryError('admission_rejected', 'message conflicts with a retained request or invalid body') from None
        except (OSError, sqlite3.Error):
            raise InventoryError('owner_unavailable', 'configured MessageOwner journal is unavailable') from None
        self._authorize(verify(token), operation, target)
        return dict(schema_version=1, operation=operation, status='completed', result=value)
