"""CLI and MCP presentation adapters for Wake-owned account operations."""
import json
import os
import socket
from pathlib import Path

from .controller_accounts import ControllerAccounts
from .controller_operations import ControllerOperations
from .managed_inventory import InventoryError


def execute(operation, arguments, root):
    if root is None:
        raise InventoryError('host_wake_root_required', 'host Wake root is required')
    try:
        host, environment = socket.gethostname(), os.environ.get('WSL_DISTRO_NAME') or os.name
        owner = ControllerAccounts(Path(root) / 'controller-accounts.toml', host=host, environment=environment)
        return ControllerOperations(None, host=host, environment=environment, accounts=owner).execute(operation, arguments)
    except InventoryError as error:
        return dict(schema_version=1, operation=operation, status='failed',
                    error=dict(code=error.code, message=str(error)))


def register_parser(subparsers):
    accounts = subparsers.add_parser('accounts', help='select existing isolated accounts')
    verbs = accounts.add_subparsers(dest='account_verb', required=True)
    for verb in ('list', 'resolve'):
        parser = verbs.add_parser(verb)
        parser.add_argument('--json', dest='as_json', action='store_true')
        if verb == 'resolve':
            parser.add_argument('selector')
            parser.add_argument('--expected-target', type=json.loads)
    configuration = subparsers.add_parser('configuration', help='explain effective account configuration')
    verbs = configuration.add_subparsers(dest='account_verb', required=True)
    parser = verbs.add_parser('explain')
    parser.add_argument('selector')
    parser.add_argument('--expected-target', type=json.loads)
    parser.add_argument('--json', dest='as_json', action='store_true')


def command(args, root):
    operation = args.command + '.' + args.account_verb
    arguments = {'selector': args.selector} if hasattr(args, 'selector') else {}
    if getattr(args, 'expected_target', None) is not None:
        arguments['expected_target'] = args.expected_target
    value = execute(operation, arguments, root)
    print(json.dumps(value, sort_keys=True))
    return 0 if value['status'] == 'completed' else 2
