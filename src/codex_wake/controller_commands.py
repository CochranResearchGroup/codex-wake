"""Local CLI/MCP adapters for the shared controller operation service."""
from __future__ import annotations

import json
import os
import socket

from .controller_operations import ControllerOperations
from .managed_inventory import ManagedInventory, InventoryError


def execute(verb, arguments, root):
    if root is None:
        raise InventoryError('host_wake_root_required', 'host Wake root is required')
    service = ControllerOperations(ManagedInventory(root), host=socket.gethostname(),
        environment=os.environ.get('WSL_DISTRO_NAME') or os.name)
    try:
        return service.execute('inventory.' + verb, arguments)
    except InventoryError as error:
        return {'schema_version': 1, 'operation': 'inventory.' + verb, 'status': 'failed',
                'error': {'code': error.code, 'message': str(error)}}


def register_parser(subparsers):
    parser = subparsers.add_parser('controller', help='inspect scoped controller resources')
    commands = parser.add_subparsers(dest='controller_command', required=True)
    for verb in ('list', 'resolve'):
        command = commands.add_parser(verb)
        command.add_argument('--json', dest='as_json', action='store_true')
        if verb == 'list':
            command.add_argument('--query', default='')
        else:
            command.add_argument('selector')
            command.add_argument('--expected-target', type=json.loads)


def command(args):
    arguments = ({'query': args.query} if args.controller_command == 'list'
                 else {'selector': args.selector})
    if getattr(args, 'expected_target', None) is not None:
        arguments['expected_target'] = args.expected_target
    value = execute(args.controller_command, arguments, args.wake_root)
    print(json.dumps(value, sort_keys=True))
    return 0 if value['status'] == 'completed' else 2
