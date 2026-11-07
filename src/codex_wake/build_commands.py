"""CLI and MCP adapter for Wake build operations; no caller-supplied host paths."""
import json


def execute(owner, operation, arguments):
    return owner.execute('builds.' + operation, arguments)


def register_parser(subparsers):
    parser = subparsers.add_parser('builds')
    commands = parser.add_subparsers(dest='build_command', required=True)
    for verb in ('list', 'launch', 'stage', 'select', 'rollback', 'prepare', 'status', 'build', 'resume', 'qualify', 'cleanup', 'run'):
        item = commands.add_parser(verb)
        item.add_argument('--arguments', type=json.loads, default=None)
        if verb in ('prepare', 'status', 'build', 'resume', 'qualify', 'cleanup', 'run'):
            for flag in ('recipe', 'upstream', 'mod-revision', 'run-id', 'expected-cache'):
                item.add_argument('--' + flag)
            item.add_argument('--jobs', type=int)
            item.add_argument('--output', choices=('compact','json','progress','diagnostics'), default=None)
            item.add_argument('--json', dest='output', action='store_const', const='json')
            item.add_argument('--max-items', type=int)
            item.add_argument('--confirm', action='store_true', default=None)
            continue
        if verb == 'stage':
            item.add_argument('--recipe')
        else:
            item.add_argument('--account')
        if verb not in ('list', 'stage'):
            item.add_argument('--channel', choices=('stock', 'modded'))
            item.add_argument('--expected-target', type=json.loads)
        if verb == 'select':
            item.add_argument('--identifier')
        if verb == 'launch':
            native = item.add_mutually_exclusive_group()
            native.add_argument('--arg', action='append', dest='native_args', help='Repeat for each native client argument; use --arg=--flag for options.')
            native.add_argument('--args', type=json.loads, dest='native_args_json', help='Native client arguments as a JSON array of strings.')
    return parser


def command(args, owner):
    from .managed_inventory import InventoryError
    try:
        arguments = {} if args.arguments is None else args.arguments
        if not isinstance(arguments, dict):
            raise InventoryError('invalid_argument', '--arguments must be a JSON object')
        arguments = dict(arguments)
        typed = {key: getattr(args, key) for key in ('account', 'channel', 'expected_target', 'recipe', 'identifier', 'upstream', 'mod_revision', 'run_id', 'jobs', 'output', 'max_items', 'confirm', 'expected_cache')
                 if getattr(args, key, None) is not None}
        native = getattr(args, 'native_args', None)
        native_json = getattr(args, 'native_args_json', None)
        if native is not None or native_json is not None:
            typed['args'] = native if native is not None else native_json
        if typed and args.arguments is None and args.build_command in ('launch', 'select', 'rollback'):
            typed.setdefault('channel', 'modded')
        for key, value in typed.items():
            if key in arguments and arguments[key] != value:
                raise InventoryError('invalid_argument', 'named flag conflicts with --arguments field: ' + key)
            arguments[key] = value
        result = execute(owner, args.build_command, arguments)
    except (ValueError, OSError) as error:
        print(json.dumps({'schema_version': 1, 'operation': 'builds.' + args.build_command,
                          'status': 'failed', 'error': {'code': getattr(error, 'code', 'build_held'), 'message': str(error)}}, sort_keys=True))
        return 2
    print(json.dumps({'schema_version': 1, 'operation': 'builds.' + args.build_command,
                      'status': 'completed', 'result': result}, sort_keys=True))
    return 0


def owner_from_root(root):
    """Read the fixed host registry; callers cannot choose manifest or recipes."""
    import os
    import socket
    import tomllib
    from pathlib import Path
    from .controller_accounts import ControllerAccounts
    from .controller_builds import ControllerBuilds
    from .managed_inventory import InventoryError
    if root is None:
        raise InventoryError('host_wake_root_required', 'host Wake root is required')
    from .controller_registry import resolve_registry
    path = resolve_registry(Path(root) / 'controller-accounts.toml', root=root)
    try:
        config = tomllib.loads(path.read_text())
        builds = config['builds']
        manifest = Path(builds['manifest'])
        recipes = builds.get('recipes', {})
        if not manifest.is_absolute() or not isinstance(recipes, dict):
            raise ValueError('host manifest and recipes require absolute paths')
        if any(not isinstance(value, str) or not Path(value).is_absolute() for value in recipes.values()):
            raise ValueError('host recipe paths must be absolute')
        accounts = ControllerAccounts(path, host=socket.gethostname(),
            environment=os.environ.get('WSL_DISTRO_NAME') or os.name)
        return ControllerBuilds(manifest, accounts, recipes=recipes)
    except (OSError, KeyError, ValueError, TypeError) as error:
        raise InventoryError('configuration_unavailable', 'host build configuration is unavailable') from error


def protected_execute(operation, arguments, root):
    """Native MCP uses a fixed host grant through the same protected operation gate."""
    from types import SimpleNamespace
    from .operation_commands import local_actor
    from .controller_http import ProtectedOperations
    from .controller_operations import ControllerOperations
    from .managed_inventory import ManagedInventory
    builds = owner_from_root(root)
    authority = SimpleNamespace(authenticate=lambda unused: local_actor(root))
    operations = ControllerOperations(ManagedInventory(root), host=builds.accounts.host,
        environment=builds.accounts.environment, accounts=builds.accounts, builds=builds)
    return ProtectedOperations(authority, operations).execute('host-local-grant', operation, arguments)
