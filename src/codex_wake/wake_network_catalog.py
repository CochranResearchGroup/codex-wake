"""Authorized controller contracts for the live Wake network."""
from dataclasses import replace
from functools import lru_cache
from json import dumps
from hashlib import sha256

from .controller_auth import AuthError
from .controller_http import ProtectedOperations, TOOLS
from .unified_connectors import check_action, delegated_content_scope, permits
from .unified_contract import canonical
from .wake_network import _ID, _check


CATALOG = 'network.management.catalog'
EXECUTE = 'network.management.execute'
ADDRESS = dict(peer_id=_ID, conversation_id=_ID)
EXECUTE_FIELDS = dict(ADDRESS, operation=_ID, arguments={'type': 'object'}, contract=_ID)


def object_schema(fields):
    return dict(type='object', properties=fields, required=list(fields), additionalProperties=False)


TOOLS_PUBLIC = {
    'wake_network_management_catalog': (CATALOG, object_schema(ADDRESS)),
    'wake_network_management_execute': (EXECUTE, object_schema(EXECUTE_FIELDS)),
}
ENTRY = object_schema(dict(operation=_ID, fixed=dict(type='array', maxItems=100, uniqueItems=True, items=_ID),
                           contract=_ID))
ADVERTISEMENT = dict(type='object', maxProperties=100, propertyNames=_ID,
                     additionalProperties=dict(type='array', maxItems=256, items=ENTRY))
PULL = dict(type='object', properties={'catalog': ADVERTISEMENT}, additionalProperties=False)


@lru_cache(maxsize=1)
def registered():
    return {canonical(operation): (operation, schema)
            for operation, schema in TOOLS.values()}


def scopes(operation):
    required = ProtectedOperations.READ_POLICIES.get(operation, (None,))[0]
    return frozenset(filter(None, (required, delegated_content_scope(operation))))


def authorized(actor, operation):
    check_action(actor, operation)
    required = scopes(operation)
    if not required or not required <= actor.scopes:
        raise AuthError('insufficient_scope')


def contract(name, fixed):
    operation, schema = registered()[name]
    properties = schema.get('properties', {})
    if not set(fixed) <= properties.keys():
        raise ValueError('fixed arguments must be part of the controller schema')
    public = dict(schema, properties={k: v for k, v in properties.items() if k not in fixed},
                  required=[k for k in schema.get('required', []) if k not in fixed])
    digest = sha256(dumps([name, sorted(fixed), schema], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return operation, public, digest


def local_binding(actor, name, binding, owner):
    operation, public, digest = contract(name, binding['fixed'])
    authorized(actor, operation)
    target = binding['target']
    if (not isinstance(target, dict) or target.get('host') != owner.host
            or target.get('environment') != owner.environment or not permits(actor, target)):
        raise AuthError('insufficient_scope')
    return replace(actor, actions=frozenset({canonical(operation)}), targets=[dict(target)]), public, digest


def advertised(entries):
    """Resolve peer announcements against this deploy's known controller schemas."""
    result = {}
    for entry in entries:
        name = entry['operation']
        try:
            operation, schema, digest = contract(name, entry['fixed'])
        except (KeyError, ValueError):
            continue
        if digest == entry['contract']:
            result[name] = (operation, schema, digest)
    return result


def validate_address(arguments, execute=False):
    _check(object_schema(EXECUTE_FIELDS if execute else ADDRESS), arguments)
