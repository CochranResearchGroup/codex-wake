"""Protected account setup uses the existing owner and durable operation journal."""
import hashlib
from pathlib import Path

from .controller_auth import AuthError
from .managed_inventory import InventoryError


def registry_target(accounts):
    path = accounts.path.absolute()
    if path.is_symlink() or path != path.resolve():
        raise InventoryError('stale_target', 'fixed account registry required')
    raw = path.read_bytes() if path.exists() else b''
    return dict(host=accounts.host, environment=accounts.environment, registry=str(path),
                registry_revision=hashlib.sha256(raw).hexdigest() if path.exists() else 'absent')


def execute(root, operation, arguments, actor, authorize, accounts):
    from .controller_runtime import ControllerRuntime
    if operation not in ('accounts.init', 'accounts.create') or not isinstance(arguments, dict):
        raise InventoryError('invalid_argument', 'account setup operation required')
    target = arguments.get('_request', {}).get('target')
    if not isinstance(target, dict) or set(target) != {'host', 'environment', 'registry', 'registry_revision'}:
        raise InventoryError('stale_target', 'pinned host registry target required')
    if 'admin' not in actor.scopes or not any(scope == target for scope in actor.targets):
        raise AuthError('insufficient_scope')
    def dispatch(op, payload):
        if registry_target(accounts) != target:
            raise InventoryError('stale_target', 'account registry changed before setup')
        current = authorize()
        if current != actor:
            raise AuthError()
        return accounts.execute(op, payload)
    return ControllerRuntime(root).execute(actor, operation, arguments, authorize=authorize,
                                           dispatch=dispatch, required_capability='admin')


def tool_specs():
    request = {'type': 'object'}
    return {
        'wake_controller_account_init': ('controller-account-management', 'accounts.init',
            'Initialize a new isolated host registry under an exact admin grant; preserve existing registries.',
            {'_request': request}, ['_request'], False),
        'wake_controller_account_create': ('controller-account-management', 'accounts.create',
            'Create a private account without credentials under a pinned registry admin grant.',
            {'selector': {'type': 'string'}, 'alias': {'type': 'string'}, '_request': request}, ['selector', '_request'], False),
    }


def protected_execute(operation, arguments, root):
    import os
    import socket
    from .controller_accounts import ControllerAccounts
    from .operation_commands import local_actor
    accounts = ControllerAccounts(Path(root) / 'controller-accounts.toml', host=socket.gethostname(),
                                   environment=os.environ.get('WSL_DISTRO_NAME') or os.name)
    return execute(root, operation, arguments, local_actor(root), lambda: local_actor(root), accounts)
