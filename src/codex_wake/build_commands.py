"""CLI and MCP adapter for Wake build operations; no caller-supplied host paths."""
import json


def execute(owner, operation, arguments):
    return owner.execute('builds.' + operation, arguments)


def register_parser(subparsers):
    parser = subparsers.add_parser('builds')
    commands = parser.add_subparsers(dest='build_command', required=True)
    for verb in ('list', 'launch', 'stage', 'select', 'rollback'):
        item = commands.add_parser(verb)
        item.add_argument('--arguments', type=json.loads, default={})
    return parser


def command(args, owner):
    result = execute(owner, args.build_command, args.arguments)
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
