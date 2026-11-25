"""Portable owner service CLI, including native Windows without POSIX imports."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import subprocess
import sys
import time
from uuid import UUID

from .message_delivery import DeliveryReceipt
from .message_handoff import MessageHandoff


def _private(path, *, directory=False):
    path = Path(path)
    if not path.is_absolute() or path != path.resolve(strict=True):
        raise ValueError('owner paths must be absolute and canonical')
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
        raise ValueError('owner path is not a private file or directory')
    if os.name == 'nt':
        from .controller_client_windows import check_private_file
        check_private_file(path)
    elif info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('owner paths require current-user private permissions')
    return path


def _object(path):
    with path.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('owner input exceeds the bounded frame')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('owner input must be an object')
    return value


def _driver(argv, recipient, clock):
    if (not isinstance(argv, list) or not 1 <= len(argv) <= 16
            or any(type(x) is not str or not 0 < len(x) <= 4096 or '\x00' in x for x in argv)
            or not Path(argv[0]).is_absolute()):
        raise ValueError('owner transport requires explicit absolute argv')
    if Path(argv[0]).suffix.lower() in ('.bat', '.cmd', '.ps1'):
        raise ValueError('owner transport requires an executable without shell interpretation')

    def send(message):
        if message.recipient != recipient:
            return DeliveryReceipt('unsent', reason='recipient_binding_unavailable')
        # Refresh the original window at the owner before invoking the transport.
        if MessageHandoff._window(message, clock()) != 'eligible':
            return DeliveryReceipt('unsent', reason='recipient_deadline_unverified')
        env = dict(os.environ)
        # The owning adapter receives exactly one message, never PostgreSQL access.
        for key in ('CODEX_WAKE_OWNER_DB_DSN', 'CODEX_WAKE_MESSAGE_DB_DSN', 'CODEX_WAKE_CUTOVER_DB_DSN',
                    'TMUX', 'TMUX_PANE', 'CODEX_THREAD_ID'):
            env.pop(key, None)
        try:
            result = subprocess.run(argv, input=json.dumps(asdict(message)), text=True, encoding='utf-8',
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=Path(argv[0]).parent,
                                    timeout=15, env=env, check=False)
        except FileNotFoundError:
            return DeliveryReceipt('unsent', reason='recipient_binding_unavailable')
        except (OSError, subprocess.SubprocessError):
            return DeliveryReceipt('uncertain', reason='owner_transport_outcome_unverified')
        try:
            if result.returncode or len(result.stdout) > 4096:
                raise ValueError
            reply = json.loads(result.stdout)
            if (reply['id'] != message.identifier or reply['recipient'] != recipient
                    or reply['expires_at_micros'] != message.expires_at_micros):
                raise ValueError
            if reply['status'] == 'unsent' and reply.get('reason') in ('busy', 'offline', 'expired'):
                return DeliveryReceipt('unsent', reason=reply['reason'])
            if reply['status'] == 'submitted' and isinstance(reply['receipt_id'], str) and 0 < len(reply['receipt_id']) <= 256:
                return DeliveryReceipt('submitted', reply['receipt_id'], evidence_kind='pinned_owner_transport')
        except (ValueError, TypeError, KeyError):
            pass
        return DeliveryReceipt('uncertain', reason='owner_transport_outcome_unverified')

    return send


def _activate_wsl(setting, peer):
    if not isinstance(setting, dict) or set(setting) != {'environment', 'distribution', 'python', 'config'}:
        raise ValueError('explicit WSL owner startup settings are required')
    distro = setting['distribution']
    if (setting['environment'] != peer['environment'] or not isinstance(distro, str)
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', distro)):
        raise ValueError('WSL auto-start must be pinned to the registered peer')
    for name in ('python', 'config'):
        if (not isinstance(setting[name], str) or not PurePosixPath(setting[name]).is_absolute()
                or any(ord(c) < 32 for c in setting[name])):
            raise ValueError('WSL owner startup requires bounded absolute paths')

    next_activation = 0.0
    process = None

    def start():
        nonlocal next_activation, process
        if os.name != 'nt':
            return 'native_windows_required'
        if process is not None and process.poll() is None:
            return 'activation_running'
        now = time.monotonic()
        if now < next_activation:
            return 'activation_check_deferred'
        next_activation = now + 30
        wsl = str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'wsl.exe')
        try:
            process = subprocess.Popen(
                [wsl, '--distribution', distro, '--exec', setting['python'], '-m',
                 'codex_wake.message_owner', '--config', setting['config'], 'run'],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
        except OSError:
            return 'distribution_activation_unavailable'
        # WSL still has to verify its pins, reconcile and acknowledge custody.
        return 'activation_requested'

    return start


def _worker(config_path, *, clock=None):
    config = _object(_private(config_path))
    if not {'root', 'registry', 'owner', 'peer'} <= set(config) or set(config) - {
            'root', 'registry', 'owner', 'peer', 'bindings', 'wsl_auto_start', 'db_dsn_file'}:
        raise ValueError('invalid message owner configuration')
    root = _private(config['root'], directory=True)
    registry = _private(config['registry'])
    if os.name == 'nt':
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin() != 0:
            raise ValueError('native Windows message owner requires a normal Windows execution account')
    for name in ('message-owner.sqlite3', 'message-owner-pump.sqlite3', 'message-owner-service.sqlite3'):
        file = root / name
        if file.exists() or file.is_symlink():
            _private(file)
        else:
            try:
                handle = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(handle)
            except FileExistsError:
                _private(file)
    options = {'clock': clock} if clock is not None else {}
    dsn = os.environ.get('CODEX_WAKE_OWNER_DB_DSN')
    if 'db_dsn_file' in config:
        with _private(config['db_dsn_file']).open(encoding='utf-8-sig') as stream:
            text = stream.read(16385)
        if len(text) > 16384 or not text.strip():
            raise ValueError('owner database configuration is empty or oversized')
        dsn = text.strip()
    worker = MessageHandoff(root, registry, config['owner'], config['peer'], dsn, **options)
    if os.name == 'nt' and worker.kind != 'windows':
        raise ValueError('the WSL owner must execute inside its registered Linux environment')
    bindings = {}
    for recipient, command in config.get('bindings', {}).items():
        key = str(UUID(recipient))
        if key in bindings:
            raise ValueError('ambiguous owner transport binding')
        bindings[key] = _driver(command, key, worker.clock)

    def dispatch(message):
        binding = bindings.get(message.recipient)
        if binding is None:
            return DeliveryReceipt('unsent', reason='recipient_binding_unavailable')
        return binding(message)

    activate = None
    if config.get('wsl_auto_start') is not None:
        if worker.kind != 'windows':
            raise ValueError('only Windows may own optional WSL activation')
        activate = _activate_wsl(config['wsl_auto_start'], config['peer'])
    return worker, dispatch if bindings else None, activate


def add_arguments(parser):
    parser.add_argument('--config', required=True, type=Path)
    verbs = parser.add_subparsers(dest='owner_verb', required=True)
    for verb in ('send', 'set-local', 'request-setting'):
        item = verbs.add_parser(verb)
        item.add_argument('--request', type=Path, required=True, help='JSON request file; bodies stay off argv')
    status = verbs.add_parser('status')
    status.add_argument('id', type=UUID)
    status.add_argument('--inbound', action='store_true')
    settings = verbs.add_parser('settings')
    settings.add_argument('recipient', type=UUID)
    verbs.add_parser('tick')
    service = verbs.add_parser('run')
    service.add_argument('--interval', type=float, default=2.0)


def register_parser(subparsers):
    add_arguments(subparsers.add_parser('message-owner', help='Operate one pinned Windows/WSL message owner'))


def command(args, *, clock=None):
    try:
        owner, driver, activate = _worker(args.config, clock=clock)
        verb = args.owner_verb
        if verb == 'send':
            result = owner.send(**_object(args.request))
        elif verb == 'set-local':
            result = owner.set_local(**_object(args.request))
        elif verb == 'request-setting':
            result = owner.request_setting(**_object(args.request))
        elif verb == 'status':
            result = owner.status(str(args.id), 'in' if args.inbound else 'out')
        elif verb == 'settings':
            result = owner.settings(str(args.recipient))
        elif verb == 'tick':
            result = owner.tick(driver, activate)
        else:
            if not math.isfinite(args.interval) or not .25 <= args.interval <= 60:
                raise ValueError('owner poll interval must be between 0.25 and 60 seconds')
            with owner.service_lock() as service:
                try:
                    service.execute('BEGIN EXCLUSIVE')
                except sqlite3.OperationalError:
                    print(json.dumps(dict(status='owner_already_running', shared_ingress=False)))
                    return 0
                previous = None
                while True:
                    current = owner.tick(driver, activate)
                    if current != previous:
                        print(json.dumps(current, sort_keys=True), flush=True)
                        previous = current
                    time.sleep(args.interval)
        print(json.dumps(result, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        return 0
    except (AttributeError, KeyError, OSError, sqlite3.Error, TypeError, ValueError):
        # Some exceptions can expose the private DSN or the message body.
        print(json.dumps(dict(status='error', reason='owner_configuration_or_state_invalid')))
        return 2


def main(argv=None):
    parser = argparse.ArgumentParser(prog='codex-wake message-owner')
    add_arguments(parser)
    return command(parser.parse_args(argv))


if __name__ == '__main__':
    sys.exit(main())
