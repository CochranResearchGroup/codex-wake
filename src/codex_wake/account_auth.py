"""Local human sign-in delegates credential handling to the registered native CLI."""
from contextlib import contextmanager, nullcontext
import fcntl
import os
from pathlib import Path
import stat
import subprocess

from codex_profiles.build_channels import BuildError, _home_ownership, _pinned_executable, load_build
from codex_profiles.config import account_environment
from .build_commands import owner_from_root
from .managed_inventory import InventoryError


@contextmanager
def _login_custody(home, channel):
    # Serialize with both private clients and Wake's native daemon manager.
    with _home_ownership(home, channel=channel) as client_lock:
        descriptor = os.open(home / '.wake-daemon.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                raise InventoryError('stale_target', 'account daemon lock is not private')
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise InventoryError('operation_busy', 'a scoped daemon operation is active; retry sign-in after it completes') from None
            if os.path.lexists(home / 'app-server-control/app-server-control.sock'):
                raise InventoryError('account_in_use', 'stop this account daemon explicitly before changing its authentication')
            yield (client_lock, descriptor)
        finally:
            os.close(descriptor)


def run(root, selector, verb, *, channel='modded', device_auth=False, with_api_key=False):
    if verb not in ('login', 'status') or (verb == 'status' and (device_auth or with_api_key)) or (device_auth and with_api_key):
        raise InventoryError('invalid_argument', 'select one supported local sign-in mode')
    builds = owner_from_root(root)
    try:
        account = builds.accounts.execute('accounts.resolve', {'selector': selector})['account']
    except InventoryError as error:
        if verb != 'login' or error.code != 'target_not_found':
            raise
        account = builds.accounts.execute('accounts.create', {'selector': selector})['account']
    home = Path(account['home'])
    build = load_build(builds.manifest, channel, home)
    if build.tenant_home is not None and build.tenant_home != str(home):
        raise BuildError('registered build belongs to another account')
    custody = _login_custody(home, channel) if verb == 'login' else nullcontext(())
    with custody as locks, _pinned_executable(build) as executable:
        builds.accounts.execute('accounts.resolve', dict(selector=selector, expected_target=account['target']))
        if load_build(builds.manifest, channel, home) != build:
            raise InventoryError('stale_target', 'registered authentication executable changed')
        arguments = ['-c', 'cli_auth_credentials_store="file"', 'login']
        if verb == 'status':
            arguments.append('status')
        elif device_auth:
            arguments.append('--device-auth')
        elif with_api_key:
            arguments.append('--with-api-key')
        # Inherit native stdio: browser/device instructions and stdin-only keys
        # never pass through Wake's JSON, logging or operation journal.
        try:
            return subprocess.run([f'/proc/self/fd/{executable}', *arguments],
                env=account_environment(home, account['id']), pass_fds=(executable, *locks),
                umask=0o077, check=False).returncode
        except KeyboardInterrupt:
            return 130
