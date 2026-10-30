"""Presentation adapters for explicitly scoped migration preview/qualification."""
import json
import os
from pathlib import Path
import socket

from .controller_migration import ControllerMigration
from .managed_inventory import InventoryError


def owner_from_root(root, *, writer_probe=None):
    if root is None:
        raise InventoryError('host_wake_root_required', 'host Wake root is required')
    return ControllerMigration(Path(root) / 'controller-accounts.toml', root=root,
        host=socket.gethostname(), environment=os.environ.get('WSL_DISTRO_NAME') or os.name,
        writer_probe=writer_probe)


def protected_execute(operation, arguments, root, *, writer_probe=None):
    from types import SimpleNamespace
    from .operation_commands import local_actor
    from .controller_http import ProtectedOperations
    from .controller_operations import ControllerOperations
    from .managed_inventory import ManagedInventory
    owner = owner_from_root(root, writer_probe=writer_probe)
    authority = SimpleNamespace(authenticate=lambda unused: local_actor(root))
    service = ControllerOperations(ManagedInventory(root), host=owner.host, environment=owner.environment,
                                   migration=owner)
    return ProtectedOperations(authority, service).execute('host-local-grant', operation, arguments)


def register_parser(subparsers):
    parser = subparsers.add_parser('migration', help='preview legacy dependencies; qualify reversible cutover only in disposable scope')
    verbs = parser.add_subparsers(dest='migration_verb', required=True)
    for verb in ('preview', 'apply', 'rollback'):
        item = verbs.add_parser(verb)
        item.add_argument('--arguments', type=json.loads, default={})
        item.add_argument('--json', dest='as_json', action='store_true')


def command(args, root, *, writer_probe=None):
    try:
        value = protected_execute('migration.' + args.migration_verb, args.arguments, root, writer_probe=writer_probe)
    except (ValueError, OSError, InventoryError) as error:
        value = dict(schema_version=1, operation='migration.' + args.migration_verb, status='failed',
                     error=dict(code=getattr(error, 'code', 'migration_unavailable'), message=str(error)))
    print(json.dumps(value, sort_keys=True))
    return 0 if value.get('status') == 'completed' else 2


def tool_specs():
    return {
        'wake_controller_migration_preview': ('controller-migration', 'migration.preview',
            'Read explicitly configured legacy link/writer/native-owner inventory. No production activation.', {}, [], True),
        'wake_controller_migration_apply': ('controller-migration', 'migration.apply',
            'Qualify one pinned migration only inside an operator-designated disposable fixture; durable admin admission required.',
            {'expected_target': {'type': 'object'}, '_request': {'type': 'object'}}, ['expected_target', '_request'], False),
        'wake_controller_migration_rollback': ('controller-migration', 'migration.rollback',
            'Roll back an attributable unchanged disposable cutover; preserve changed targets and uncertain effects.',
            {'expected_target': {'type': 'object'}, 'receipt_id': {'type': 'string'}, '_request': {'type': 'object'}},
            ['expected_target', 'receipt_id', '_request'], False),
    }
