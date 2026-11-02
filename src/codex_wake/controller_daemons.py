"""Account-scoped lifecycle over the native daemon manager and existing build owner."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess

from codex_profiles.build_channels import (
    BuildError, _pinned_executable, _process_start_ticks, load_build, validate_history,
)
from codex_profiles.config import account_environment
from .controller_accounts import launch_overrides
from .managed_inventory import InventoryError


class ControllerDaemons:
    def __init__(self, builds):
        self.builds = builds
        self.accounts = builds.accounts

    def _selection(self, account, channel):
        row = self.accounts.execute('accounts.resolve', {'selector': account})['account']
        home = Path(row['home'])
        build = load_build(self.builds.manifest, channel, home)
        target = dict(row['target'], build_channel=channel, build_sha256=build.sha256,
                      build_revision=build.revision, executable=str(build.executable))
        return row, home, build, target

    def _observe(self, account, channel):
        row, home, build, target = self._selection(account, channel)
        control = home / 'app-server-control/app-server-control.sock'
        result = dict(account=row['id'], channel=channel, target=dict(target, process=None, socket_generation=None),
                      endpoint=None, state='unavailable', account_identity='unverified')
        if not os.path.lexists(control):
            return result
        try:
            physical = control.resolve(strict=True)
            info, parent = physical.lstat(), physical.parent.stat()
            if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid()
                    or parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700):
                raise InventoryError('stale_target', 'daemon endpoint is not private and owned')
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
                peer.settimeout(3)
                peer.connect(str(physical))
                pid, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            process = dict(pid=pid, start_ticks=_process_start_ticks(pid),
                           boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
            if uid != os.getuid() or not process['start_ticks']:
                raise InventoryError('stale_target', 'daemon peer generation is unavailable')
            with Path(f'/proc/{pid}/exe').open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if ('CODEX_HOME=' + str(home)).encode() not in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'):
                raise InventoryError('stale_target', 'daemon peer belongs to another account home')
            if process['start_ticks'] != _process_start_ticks(pid):
                raise InventoryError('stale_target', 'daemon peer was replaced during observation')
            result.update(state='running', endpoint='unix://' + str(physical), running_sha256=digest,
                          selected_build_running=digest == build.sha256)
            result['target'].update(process=process, socket_generation=f'{info.st_dev}:{info.st_ino}')
            return result
        except InventoryError:
            raise
        except (OSError, ValueError):
            raise InventoryError('daemon_unavailable', 'daemon endpoint exists but its exact owner cannot be verified') from None

    def execute(self, operation, arguments):
        verbs = ('list', 'status', 'start', 'restart', 'update', 'stop')
        if operation not in {'daemons.' + verb for verb in verbs}:
            raise InventoryError('unsupported_operation', 'unsupported daemon operation')
        if not isinstance(arguments, dict):
            raise InventoryError('invalid_argument', 'daemon arguments must be an object')
        allowed = {'channel'} if operation == 'daemons.list' else {'account', 'channel'}
        if operation not in ('daemons.list', 'daemons.status'):
            allowed |= {'expected_target', 'confirm'}
        if set(arguments) - allowed:
            raise InventoryError('invalid_argument', 'unsupported daemon arguments')
        channel = arguments.get('channel', 'modded')
        try:
            if operation == 'daemons.list':
                rows = self.accounts.execute('accounts.list', {})['accounts']
                return dict(owner='codex-wake', daemons=[self._observe(row['id'], channel) for row in rows])
            account = arguments.get('account')
            current = self._observe(account, channel)
            if operation == 'daemons.status':
                return dict(daemon=current)
            if arguments.get('expected_target') != current['target']:
                raise InventoryError('stale_target', 'exact observed account/build/process target required')
            if operation in ('daemons.restart', 'daemons.update', 'daemons.stop') and arguments.get('confirm') is not True:
                raise InventoryError('confirmation_required', 'explicit confirmation of this scoped interruption is required')
            row, home, build, target = self._selection(account, channel)
            if build.backend != 'managed':
                raise InventoryError('unsupported_target', 'selected build is registered for private clients, not managed daemons')
            validate_history(build, home)
            lock = os.open(home / '.wake-daemon.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(lock)
                if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
                    raise InventoryError('stale_target', 'daemon operation lock is not private')
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise InventoryError('operation_busy', 'another scoped daemon operation is active') from None
                if self._observe(account, channel)['target'] != current['target']:
                    raise InventoryError('stale_target', 'daemon changed before lifecycle dispatch')
                view = self.accounts.execute('configuration.explain', {'selector': row['id'], 'expected_target': row['target']})
                overrides = launch_overrides(view)
                env = account_environment(home, row['id'])
                with _pinned_executable(build) as executable:
                    def native(verb, *args):
                        try:
                            p = subprocess.run([f'/proc/self/fd/{executable}', *overrides, 'app-server', 'daemon', verb, *args],
                                env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                pass_fds=(executable,), timeout=100)
                        except subprocess.TimeoutExpired:
                            raise InventoryError('effect_uncertain', 'native lifecycle timed out; reconcile retained intent before retry') from None
                        if p.returncode:
                            raise InventoryError('daemon_held', 'native daemon manager refused the scoped operation: ' + p.stderr[:1000] + ('\n...\n' if len(p.stderr) > 2000 else '') + p.stderr[-1000:])
                        try:
                            value = json.loads(p.stdout)
                            if not isinstance(value, dict):
                                raise ValueError
                            return value
                        except ValueError:
                            raise InventoryError('effect_uncertain', 'native lifecycle result was not valid JSON') from None
                    verb = operation.split('.')[1]
                    if verb == 'start':
                        selected = home / 'packages/app-server-daemon/current/bin/codex'
                        if selected.exists():
                            with selected.open('rb') as stream:
                                if hashlib.file_digest(stream, 'sha256').hexdigest() != build.sha256:
                                    raise InventoryError('stale_target', 'native package differs; use explicit daemon update')
                        else:
                            if os.path.lexists(selected) or current['state'] == 'running':
                                raise InventoryError('stale_target', 'incomplete native package selection requires reconciliation')
                            native('start')
                            native('update', '--from-cli', '--yes')
                        outcome = native('start')
                    elif verb == 'update':
                        outcome = native('update', '--from-cli', '--yes')
                    else:
                        if current['state'] != 'running' or not current['selected_build_running']:
                            raise InventoryError('stale_target', 'only the verified selected running build can be interrupted')
                        outcome = native(verb)
                after = self._observe(account, channel)
                activation = 'running'
                if verb == 'update' and current['state'] == 'unavailable':
                    selected = home / 'packages/app-server-daemon/current/bin/codex'
                    with selected.open('rb') as stream:
                        if hashlib.file_digest(stream, 'sha256').hexdigest() != build.sha256:
                            raise InventoryError('effect_uncertain', 'native update did not select the requested package')
                    activation = 'future_start'
                elif verb != 'stop' and (after['state'] != 'running' or not after['selected_build_running']):
                    raise InventoryError('effect_uncertain', 'native result did not establish the selected running build')
                return dict(daemon=after, previous=current, native=outcome, activation=activation)
            finally:
                os.close(lock)
        except InventoryError:
            raise
        except (BuildError, OSError, ValueError) as error:
            raise InventoryError('daemon_held', str(error)) from error
