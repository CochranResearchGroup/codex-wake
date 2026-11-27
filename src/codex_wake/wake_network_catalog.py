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
                           contract=_ID, binding_revision=_ID))
ADVERTISEMENT = dict(type='object', maxProperties=100, propertyNames=_ID,
                     additionalProperties=dict(type='array', maxItems=256, items=ENTRY))
PULL = dict(type='object', properties={'catalog': ADVERTISEMENT}, additionalProperties=False)


@lru_cache(maxsize=1)
def registered():
    return {canonical(operation): (operation, schema)
            for operation, schema in TOOLS.values()}


def scopes(operation):
    required = ProtectedOperations.READ_POLICIES.get(operation, (None,))[0]
    if required is None:
        return frozenset()
    return frozenset(filter(None, (required, delegated_content_scope(operation))))


def authorized(actor, operation):
    check_action(actor, operation)
    required = scopes(operation)
    if not required or not required <= actor.scopes:
        raise AuthError('insufficient_scope')


def fingerprint(value):
    return sha256(dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def contract(name, fixed, binding_revision=None):
    operation, schema = registered()[name]
    properties = schema.get('properties', {})
    if not set(fixed) <= properties.keys():
        raise ValueError('fixed arguments must be part of the controller schema')
    public = without_fixed_requirements(schema, fixed)
    public.update(additionalProperties=False, properties={k: v for k, v in properties.items() if k not in fixed})
    digest = fingerprint([name, sorted(fixed), schema, binding_revision])
    return operation, public, digest


def without_fixed_requirements(schema, fixed):
    """Project object-level required branches onto the caller's unpinned fields."""
    projected = dict(schema)
    if 'required' in schema:
        projected['required'] = [name for name in schema['required'] if name not in fixed]
    for keyword in ('allOf', 'anyOf', 'oneOf'):
        if keyword in schema:
            projected[keyword] = [without_fixed_requirements(part, fixed) for part in schema[keyword]]
    if 'not' in schema:
        projected['not'] = without_fixed_requirements(schema['not'], fixed)
    return projected


def local_binding(actor, name, binding, owner):
    operation, public, digest = contract(name, binding['fixed'], fingerprint(binding))
    authorized(actor, operation)
    target = binding['target']
    if (not isinstance(target, dict) or target.get('host') != owner.host
            or target.get('environment') != owner.environment or not permits(actor, target)):
        raise AuthError('insufficient_scope')
    return replace(actor, actions=frozenset({canonical(operation)}), targets=[dict(target)]), public, digest


def attenuate(actor, scopes_from_hub, operation):
    actor = replace(actor, scopes=actor.scopes.intersection(scopes_from_hub), delegated=True)
    authorized(actor, operation)
    return actor


def advertised(entries):
    """Resolve peer announcements against this deploy's known controller schemas."""
    result = {}
    for entry in entries:
        name = entry['operation']
        try:
            operation, schema, digest = contract(name, entry['fixed'], entry['binding_revision'])
        except (KeyError, ValueError):
            continue
        if digest == entry['contract']:
            result[name] = (operation, schema, digest)
    return result


def validate_address(arguments, execute=False):
    _check(object_schema(EXECUTE_FIELDS if execute else ADDRESS), arguments)
