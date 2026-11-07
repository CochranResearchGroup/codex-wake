"""Read-only selected-account readiness; registration never proves native operation.

Reuses account resolution and the build-channel owner. No processes, credentials,
watcher starts, grants, refreshes, or budget mutations occur in this inspection.
"""
from pathlib import Path
import os
import socket

from .controller_accounts import ControllerAccounts
from .managed_inventory import InventoryError


def execute(root, arguments, *, accounts=None):
    """Inspect selected launcher/registration, retaining explicit runtime gates."""
    if root is None:
        raise InventoryError('host_wake_root_required', 'host Wake root required')
    if (not isinstance(arguments, dict) or set(arguments) - {'selector', 'expected_target', 'manifest', 'launcher'}
            or not isinstance(arguments.get('selector'), str)):
        raise InventoryError('invalid_argument', 'selected account and optional manifest/launcher paths required')
    for key in ('manifest', 'launcher'):
        if key in arguments and (not isinstance(arguments[key], str) or not Path(arguments[key]).is_absolute()):
            raise InventoryError('invalid_argument', 'readiness paths must be absolute')
    accounts = accounts or ControllerAccounts(Path(root)/'controller-accounts.toml',
        host=socket.gethostname(), environment=os.environ.get('WSL_DISTRO_NAME') or os.name)
    selection = {key: arguments[key] for key in ('selector', 'expected_target') if key in arguments}
    account = accounts.execute('accounts.resolve', selection)['account']
    checks = {}
    launcher = arguments.get('launcher')
    checks['launcher'] = dict(state='unknown', remedy='Select the installed profile launcher path for inspection.')
    if launcher:
        path = Path(launcher)
        available = path.is_file() and os.access(path, os.X_OK)
        checks['launcher'] = dict(state='present' if available else 'blocked', path=str(path),
            remedy='Qualify this launcher with the selected native profile; presence does not prove its routing.' if available
            else 'Repair or install only the selected profile launcher; preserve stock and peer launchers.')
    checks['build'] = dict(state='missing', remedy='Supply the existing build-channel manifest for the selected profile.')
    if arguments.get('manifest'):
        from codex_profiles.build_channels import load_build, BuildError, _pinned_executable
        try:
            build = load_build(Path(arguments['manifest']), 'modded', Path(account['home']))
            with _pinned_executable(build):
                pass
            checks['build'] = dict(state='registered_bytes_verified', executable=str(build.executable),
                sha256=build.sha256, backend=build.backend,
                remedy='Qualify native initialization and selected home/backend identity in isolation.')
        except (BuildError, OSError):
            checks['build'] = dict(state='blocked', remedy='Repair the selected tenant build registration and digest using the existing build-channel owner; re-inspect before launch.')
    for name, remedy in (
        ('backend', 'Observe native initialization and selected home/backend identity using isolated native qualification.'),
        ('watcher', 'Inspect the existing selected limit-watcher owner; explicitly authorize any selected watcher start.'),
        ('limits', 'Exercise voluntary limits through the existing self-limit owner on the selected real profile; retain cumulative usage.'),
        ('refresh', 'Qualify scoped refresh through the existing refresh owner on the selected real profile; preserve stock, peers and budgets.')):
        checks[name] = dict(state='not_qualified', remedy=remedy)
    accounts.execute('accounts.resolve', dict(selector=arguments['selector'], expected_target=account['target']))
    return dict(schema_version=1, operation='accounts.readiness', status='completed',
        result=dict(account=account, status='incomplete', checks=checks,
                    native_qualified=False, effects='none'))
