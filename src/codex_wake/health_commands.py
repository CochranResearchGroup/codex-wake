"""Read-only health CLI and shared public API/MCP schema adapters."""
import json
from pathlib import Path

from .controller_health import ControllerHealth
from .managed_inventory import InventoryError
from .records import WakeError

_TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 4096}
TARGET_SCHEMA = {'type': 'object', 'properties': {
    **{key: _TEXT for key in ('host', 'environment', 'runtime', 'namespace', 'build_sha256',
        'conversation_id', 'home', 'provider', 'backend_id', 'channel', 'connection_generation')},
    'process': {'type': 'object', 'properties': {'pid': {'type': 'integer', 'minimum': 1},
        'start_ticks': _TEXT, 'boot_id': _TEXT}, 'required': ['pid', 'start_ticks', 'boot_id'],
        'additionalProperties': False}},
    'required': ['host', 'environment', 'runtime', 'namespace', 'build_sha256', 'conversation_id',
        'home', 'provider', 'backend_id', 'channel', 'process', 'connection_generation'],
    'additionalProperties': False}
INPUT_SCHEMA = {'type': 'object', 'properties': {'expected_target': TARGET_SCHEMA,
    'timeout': {'type': 'number', 'minimum': .05, 'maximum': 5}},
    'required': ['expected_target'], 'additionalProperties': False}


def owner(root):
    if root is None: raise InventoryError('host_wake_root_required', 'host Wake root required')
    return ControllerHealth(Path(root))


def execute(operation, arguments, root):
    try:
        return dict(schema_version=1, operation=operation, status='completed',
                    result=owner(root).execute(operation, arguments))
    except (WakeError, ValueError, OSError, TypeError, KeyError) as error:
        return dict(schema_version=1, operation=operation, status='failed',
            error=dict(code=getattr(error, 'code', 'invalid_argument'), message=str(error)))


def register_parser(subparsers):
    parser = subparsers.add_parser('health', help='observe the exact controlling native TUI loop without recovery')
    verbs = parser.add_subparsers(dest='health_verb', required=True)
    observe = verbs.add_parser('observe')
    observe.add_argument('--expected-target', type=json.loads, required=True)
    observe.add_argument('--timeout', type=float, default=1)
    observe.add_argument('--json', dest='as_json', action='store_true')


def command(args, root=None):
    value = execute('health.' + args.health_verb,
        dict(expected_target=args.expected_target, timeout=args.timeout), root or args.wake_root)
    print(json.dumps(value, sort_keys=True))
    return 0 if value['status'] == 'completed' else 2


def tool_specs():
    # Shared authenticated dispatch owns capability admission for API/OAuth/native MCP.
    return {'wake_controller_health': ('controller-health', 'observe',
        'Read-only fresh challenge to the exact controlling native TUI loop. Unknown/unsupported never grants recovery.',
        INPUT_SCHEMA['properties'], INPUT_SCHEMA['required'], True)}


def protected_observe(actor, arguments, root, *, authorize):
    from .controller_runtime import ControllerRuntime
    from .controller_auth import AuthError
    from .controller_health import _TARGET_FIELDS
    target = arguments.get('expected_target') if isinstance(arguments, dict) else None
    if not isinstance(target, dict) or not isinstance(target.get('process'), dict):
        raise InventoryError('invalid_argument', 'complete pinned native target required')
    process = target['process']
    flat = {key:value for key,value in target.items() if key != 'process'}
    flat.update(process_pid=str(process.get('pid')), process_start_ticks=process.get('start_ticks'), process_boot_id=process.get('boot_id'))
    required = (_TARGET_FIELDS - {'process'}) | {'process_pid','process_start_ticks','process_boot_id'}
    if not any(required <= scope.keys() and all(flat.get(key)==value for key,value in scope.items()) for scope in actor.targets):
        raise AuthError('insufficient_scope')
    runtime = ControllerRuntime(root)
    runtime.check_authority(actor, flat, 'observe', authorize=authorize)
    value = execute('health.observe', arguments, root)
    runtime.check_authority(actor, flat, 'observe', authorize=authorize)
    return value


def protected_execute(operation, arguments, root):
    from types import SimpleNamespace
    from .operation_commands import local_actor
    from .controller_http import ProtectedOperations
    from .controller_operations import ControllerOperations
    from .managed_inventory import ManagedInventory
    authority = SimpleNamespace(authenticate=lambda unused: local_actor(root))
    operations = ControllerOperations(ManagedInventory(root), host='host-authorized', environment='host-authorized')
    return ProtectedOperations(authority, operations).execute('host-local-grant', operation, arguments)
