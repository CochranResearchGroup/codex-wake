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
        if operation == 'accounts.status':
            from .account_observation import execute as observe
            return observe(root, arguments)
        host, environment = socket.gethostname(), os.environ.get('WSL_DISTRO_NAME') or os.name
        owner = ControllerAccounts(Path(root) / 'controller-accounts.toml', host=host, environment=environment)
        if operation == 'accounts.readiness':
            from .profile_operations import readiness
            return readiness(root, arguments, accounts=owner)
        return ControllerOperations(None, host=host, environment=environment, accounts=owner).execute(operation, arguments)
    except InventoryError as error:
        return dict(schema_version=1, operation=operation, status='failed',
                    error=dict(code=error.code, message=str(error)))


def register_parser(subparsers):
    accounts = subparsers.add_parser('accounts', help='create and select isolated accounts')
    verbs = accounts.add_subparsers(dest='account_verb', required=True)
    initialize = verbs.add_parser('init', help='initialize a new isolated account registry')
    initialize.add_argument('--json', dest='as_json', action='store_true')
    create = verbs.add_parser('create', help='create a private account home without credentials')
    create.add_argument('selector')
    create.add_argument('--alias')
    create.add_argument('--mode', choices=('independent',))
    create.add_argument('--source')
    create.add_argument('--json', dest='as_json', action='store_true')
    for verb in ('login', 'status'):
        item = verbs.add_parser(verb, help='sign in or inspect native authentication for a named account')
        item.add_argument('selector')
        item.add_argument('--channel', choices=('stock', 'modded'), default='modded')
        if verb == 'status':
            item.add_argument('--json', dest='as_json', action='store_true', help='show sanitized local cached identity; no provider check or refresh')
            item.add_argument('--expected-target', type=json.loads, help='require this exact account generation; selects structured cached status')
        if verb == 'login':
            modes = item.add_mutually_exclusive_group()
            modes.add_argument('--device-auth', action='store_true')
            modes.add_argument('--with-api-key', action='store_true')
    for verb in ('list', 'resolve'):
        parser = verbs.add_parser(verb)
        parser.add_argument('--json', dest='as_json', action='store_true')
        if verb == 'resolve':
            parser.add_argument('selector')
            parser.add_argument('--expected-target', type=json.loads)
    readiness = verbs.add_parser('readiness', help='inspect selected profile readiness without runtime effects')
    readiness.add_argument('selector')
    readiness.add_argument('--expected-target', type=json.loads)
    readiness.add_argument('--manifest')
    readiness.add_argument('--launcher')
    readiness.add_argument('--json', dest='as_json', action='store_true')
    stores = subparsers.add_parser('stores', help='register and inspect the stable stock configuration/history store')
    store_verbs = stores.add_subparsers(dest='account_verb', required=True)
    for verb in ('register', 'resolve', 'list'):
        item = store_verbs.add_parser(verb)
        if verb != 'list':
            item.add_argument('selector')
        if verb == 'register':
            item.add_argument('--home', required=True)
        item.add_argument('--json', dest='as_json', action='store_true')
    configuration = subparsers.add_parser('configuration', help='explain effective account configuration')
    verbs = configuration.add_subparsers(dest='account_verb', required=True)
    parser = verbs.add_parser('explain')
    parser.add_argument('selector')
    parser.add_argument('--expected-target', type=json.loads)
    parser.add_argument('--json', dest='as_json', action='store_true')

    sync = verbs.add_parser('sync', help='preview or apply explicit directional configuration sync')
    sync_verbs = sync.add_subparsers(dest='sync_verb', required=True)
    for verb in ('preview', 'apply'):
        item = sync_verbs.add_parser(verb)
        item.add_argument('--source', required=True)
        item.add_argument('--destination', dest='destinations', action='append', required=True)
        item.add_argument('--category', dest='categories', action='append', choices=('settings', 'mcp', 'hooks', 'skills', 'rules'), required=True)
        item.add_argument('--operation-id', required=True)
        if verb == 'apply':
            item.add_argument('--expected-snapshot', required=True)
        item.add_argument('--propagate-deletions', action='store_true', default=None)
        item.add_argument('--reload', action='store_true', default=None)
        item.add_argument('--json', dest='as_json', action='store_true')


def command(args, root):
    if args.command == 'accounts' and args.account_verb in ('login', 'status') and not getattr(args, 'as_json', False) and getattr(args, 'expected_target', None) is None:
        from .account_auth import run
        try:
            return run(root, args.selector, args.account_verb, channel=args.channel,
                device_auth=getattr(args, 'device_auth', False), with_api_key=getattr(args, 'with_api_key', False))
        except (ValueError, OSError) as error:
            import sys
            print('Account sign-in unavailable: ' + str(error), file=sys.stderr)
            return 2
    operation = args.command + '.' + args.account_verb
    if getattr(args, 'sync_verb', None):
        operation += '.' + args.sync_verb
    arguments = {'selector': args.selector} if hasattr(args, 'selector') else {}
    if getattr(args, 'alias', None) is not None:
        arguments['alias'] = args.alias
    if getattr(args, 'expected_target', None) is not None:
        arguments['expected_target'] = args.expected_target
    for key in ('mode', 'source', 'home', 'manifest', 'launcher', 'destinations', 'categories', 'operation_id', 'expected_snapshot', 'propagate_deletions', 'reload'):
        if getattr(args, key, None) is not None:
            arguments[key] = getattr(args, key)
    value = execute(operation, arguments, root)
    print(json.dumps(value, sort_keys=True))
    return 0 if value['status'] == 'completed' else 2
