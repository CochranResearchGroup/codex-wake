"""Read official Grok sessions without exposing credentials in public status.

The private bearer method is consumed only by the command-auth broker. Presence
is deliberately separate from entitlement and inference qualification.
"""
from datetime import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import stat


class GrokSession:
    def __init__(self, auth_path):
        self.auth_path = Path(auth_path)

    def _read(self):
        fd = os.open(self.auth_path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd) as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('insecure_native_auth')
            if info.st_size > 1024 * 1024:
                raise ValueError('invalid_native_auth')
            try:
                data = json.load(stream)
            except (ValueError, UnicodeError):
                raise ValueError('invalid_native_auth') from None
        if not isinstance(data, dict):
            raise ValueError('invalid_native_auth')
        sessions = [value for value in data.values() if isinstance(value, dict)
                    and value.get('auth_mode') in ('web_login', 'grok', 'oidc', 'external')
                    and isinstance(value.get('key'), str) and value['key']]
        if len(sessions) != 1:
            raise ValueError('native_session_missing_or_ambiguous')
        return sessions[0]

    def status(self):
        try:
            self._read()
            authentication = 'present'
        except FileNotFoundError:
            authentication = 'logged_out'
        except (OSError, ValueError):
            authentication = 'unavailable'
        return dict(authentication=authentication, entitlement='unverified', inference='unverified')

    def bearer(self, qualified_upper):
        """Return a private token only before its expiry's conservative boundary.

        Caller supplies a qualified StableTime upper bound, never guest wall time.
        Rotation remains owned by official Grok until refresh is qualified.
        """
        if (type(qualified_upper) not in (int, float)
                or not math.isfinite(qualified_upper)):
            raise ValueError('qualified_time_required')
        lock_path = self.auth_path.with_name(self.auth_path.name + '.lock')
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'r+') as lock:
            info = os.fstat(lock.fileno())
            if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISREG(info.st_mode):
                raise ValueError('insecure_native_lock')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('native_auth_busy') from None
            current = os.stat(lock_path, follow_symlinks=False)
            if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
                raise ValueError('native_lock_replaced')
            session = self._read()
            try:
                expiry = datetime.fromisoformat(session['expires_at'].replace('Z', '+00:00'))
                if expiry.tzinfo is None:
                    raise ValueError()
                expires_at = expiry.timestamp()
            except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
                raise ValueError('native_expiry_unknown') from None
            if qualified_upper + 30 >= expires_at:
                raise ValueError('native_refresh_required')
            return session['key']


def register_parser(commands):
    parser = commands.add_parser('auth', help='official Grok session status and private native command auth')
    verbs = parser.add_subparsers(dest='grok_auth_command', required=True)
    for verb in ('status', 'token'):
        command = verbs.add_parser(verb)
        command.add_argument('--auth-path', type=Path, required=True,
                             help='operator-selected official Grok credential store')


def command(args, root):
    """Local operator boundary; token is intentionally absent from MCP tools."""
    import sys
    session = GrokSession(args.auth_path)
    if args.grok_auth_command == 'status':
        print(json.dumps(session.status(), sort_keys=True))
        return 0
    if sys.stdout.isatty():
        print('private_channel_required', file=sys.stderr)
        return 3
    from .time_inspection import stable_time_config
    from .stable_time import service_time_decision
    from .time_provider import require_time_decision
    config = stable_time_config()
    try:
        decision = service_time_decision(config) if config else None
        upper = require_time_decision(decision).upper if decision else None
        token = session.bearer(upper)
    except (OSError, ValueError):
        # Native Codex includes command stderr in its own diagnostics. Never emit
        # provider exceptions, native login output, paths or credential contents.
        print('grok_auth_unavailable', file=sys.stderr)
        return 3
    sys.stdout.write(token)
    return 0
