"""Exact local menu control and cooperative, global per-pane input custody.

This menu-only profile does not change Grok delivery adapter qualification.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import time
from uuid import uuid4

from .records import WakeError, WakeLifecycleLock
from .service import user_state_dir
from .session_permissions import PermissionStore, check_operation
from .grok_runtime import GENERATION_KEYS

BINARY_SHA256 = '92c997dfd109c0672d40d5ae6fbd15835d53ffaf12cf9ea124d22aaef3ff23fc'
_active = ContextVar('guarded_menu_input', default=None)


class MenuError(WakeError):
    pass


def pane_key(binding):
    return 'grok-pane-' + str(binding['socket']) + ':' + str(binding['pane'])


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _private(path, directory=False):
    info = path.lstat()
    if (info.st_uid != os.geteuid() or info.st_mode & 0o077
            or (not stat.S_ISDIR(info.st_mode) if directory else not stat.S_ISREG(info.st_mode))):
        raise MenuError('unsafe_menu_store')


def _directory(path):
    path = Path(path).absolute()
    if path != path.resolve():
        raise MenuError('menu_store_symlink')
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    _private(path, True)
    return path


def _read(path):
    _private(path)
    try:
        value = json.loads(path.read_text())
        if type(value) is not dict or value.get('version') != 1:
            raise ValueError()
        return value
    except (ValueError, OSError):
        raise MenuError('menu_state_unavailable') from None


def _write(path, value):
    _directory(path.parent)
    if path.exists() or path.is_symlink():
        _private(path)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.menu-')
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, sort_keys=True, allow_nan=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _fence_path(binding):
    directory = user_state_dir() / 'runtime-recipient-locks' / 'input-owners'
    return directory / (_digest(pane_key(binding)) + '.json')


def _owner(binding):
    path = _fence_path(binding)
    if not path.exists() and not path.is_symlink():
        # An enrollment marker makes removal of established authority fail closed.
        if path.with_suffix('.initialized').exists():
            raise MenuError('input_owner_state_missing')
        return dict(version=1, generation=1, owner='automation', history=[])
    value = _read(path)
    if (type(value.get('generation')) is not int or value['generation'] < 1
            or value.get('owner') not in ('human', 'automation') or type(value.get('history')) is not list):
        raise MenuError('input_owner_state_invalid')
    return value


def _save_owner(binding, value):
    path = _fence_path(binding)
    _write(path, value)
    marker = path.with_suffix('.initialized')
    if not marker.exists():
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)


def owner_token(binding, generation):
    return dict(pane=_digest(pane_key(binding)), generation=generation)


def assert_input_allowed(root, binding, owner_token=None):
    """Hook check; caller must use automated_input_guard through actual I/O."""
    state = _owner(binding)
    context = _active.get()
    token = owner_token if owner_token is not None else (context[1] if context and context[0] == pane_key(binding) else None)
    if state['owner'] != 'automation':
        raise MenuError('human_owns_input')
    if token is not None and token != globals()['owner_token'](binding, state['generation']):
        raise MenuError('stale_input_owner_generation')
    return state


@contextmanager
def automated_input_guard(root, binding, owner_token=None):
    """Global hook around each automated tmux input; nested menu input is reentrant."""
    key = pane_key(binding)
    active = _active.get()
    if active and active[0] == key:
        assert_input_allowed(root, binding, owner_token)
        yield
        return
    directory = _directory(user_state_dir() / 'runtime-recipient-locks')
    with WakeLifecycleLock(directory, 'input-fence-' + key):
        state = assert_input_allowed(root, binding, owner_token)
        token = _active.set((key, globals()['owner_token'](binding, state['generation'])))
        try:
            yield
        finally:
            _active.reset(token)


def _lines(frame):
    return [line.rstrip() for line in frame.splitlines() if line.strip()]


def _identity(host, binding):
    observed = host.snapshot(binding)
    if (any(observed.get(k) != binding.get(k) for k in GENERATION_KEYS)
            or observed['executable_sha256'] != BINARY_SHA256):
        raise MenuError('menu_identity_changed')
    # snapshot verifies argv UUID, executable, pid generation and exact pane pid.
    if str(Path('/proc', str(binding['pid']), 'cwd').resolve(strict=True)) != binding['cwd']:
        raise MenuError('menu_cwd_changed')
    lines = _lines(observed['frame'])
    versions = [x.strip() for x in lines if x.strip().startswith('Shell version:')]
    sessions = [x.strip() for x in lines if x.strip().startswith('Session ID:')]
    if (not versions or versions[-1] not in ('Shell version: 1.0.40', 'Shell version: 1.0.40 [stable]')
            or not sessions or sessions[-1] != 'Session ID: ' + binding['session_id']):
        raise MenuError('menu_session_identity_unavailable')
    return observed


def _empty(frame):
    lines = _lines(frame)
    return (len(lines) >= 3 and lines[-3].strip() == 'minimal · /help'
            and lines[-2] == '❯'
            and re.fullmatch(r'Grok 4\.[67] \(high\) · .+ · ctrl\+o transcript', lines[-1]) is not None)


def _palette(frame):
    lines = _lines(frame)
    return (any(x.strip() == 'Commands' for x in lines)
            and any(x.strip() == 'search:' for x in lines)
            and any('◆ New Session' in x for x in lines)
            and lines[-1].strip() == '↑/↓ nav  |  Enter select  |  Esc close')


class GuardedInteractions:
    def __init__(self, root, *, host=None):
        self.root = Path(root).absolute()
        self.directory = _directory(self.root / 'guarded-interactions')
        if host is None:
            from .grok_terminal import GrokTerminalHost
            host = GrokTerminalHost(root)
        self.host = host

    def _profile(self, name):
        if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', name):
            raise MenuError('invalid_menu_profile')
        path = self.directory / ('profile-' + name + '.json')
        if not path.exists():
            raise MenuError('menu_profile_unavailable')
        value = _read(path)
        if value.get('scope') != 'grok-palette-open-cancel' or not isinstance(value.get('binding'), dict):
            raise MenuError('menu_profile_invalid')
        return value

    def configure(self, name, binding, *, principal, reason):
        if principal.role != 'operator' or not reason:
            raise MenuError('operator_required')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', name):
            raise MenuError('invalid_menu_profile')
        selected = dict(binding)
        selected['cwd'] = str(Path(selected['cwd']).resolve(strict=True))
        observed = _identity(self.host, selected)
        if not _empty(observed['frame']):
            raise MenuError('menu_empty_composer_required')
        key = pane_key(selected)
        with WakeLifecycleLock(user_state_dir() / 'runtime-recipient-locks', key):
            with WakeLifecycleLock(user_state_dir() / 'runtime-recipient-locks', 'input-fence-' + key):
                state = _owner(selected)
                _save_owner(selected, state)
                value = dict(version=1, scope='grok-palette-open-cancel', binding=selected,
                             issuer=principal.subject, reason=reason, configured_at=time.time())
                _write(self.directory / ('profile-' + name + '.json'), value)
        return self.inspect(name)

    def inspect(self, name):
        profile = self._profile(name)
        binding = profile['binding']
        state = _owner(binding)
        return dict(profile=name, scope=profile['scope'], session_id=binding['session_id'],
                    ownership=state, token=owner_token(binding, state['generation']),
                    capability='menu_only', provider_delivery='not_qualified_by_this_profile')

    def _permission(self, action, principal, binding):
        if not PermissionStore(self.root).active():
            raise MenuError('common_permission_policy_required')
        return check_operation(self.root, action, principal, target=binding['session_id'])

    def change_owner(self, name, token, *, principal, human, reason):
        if principal.role != 'operator' or not reason or type(human) is not bool:
            raise MenuError('operator_required')
        binding = self._profile(name)['binding']
        with WakeLifecycleLock(user_state_dir() / 'runtime-recipient-locks', pane_key(binding)):
            with WakeLifecycleLock(user_state_dir() / 'runtime-recipient-locks', 'input-fence-' + pane_key(binding)):
                state = _owner(binding)
                if token != owner_token(binding, state['generation']):
                    raise MenuError('stale_input_owner_generation')
                self._permission('terminal.takeover' if human else 'terminal.return', principal, binding)
                if not human and not _empty(_identity(self.host, binding)['frame']):
                    raise MenuError('menu_empty_composer_required')
                state['generation'] += 1
                state['owner'] = 'human' if human else 'automation'
                state['history'].append(dict(actor=principal.subject, reason=reason, owner=state['owner'], generation=state['generation'], at=time.time()))
                _save_owner(binding, state)
        return self.inspect(name)

    def _operation_path(self, operation):
        if not isinstance(operation, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', operation):
            raise MenuError('invalid_menu_operation')
        return self.directory / ('operation-' + operation + '.json')

    def run(self, name, token, *, principal, operation):
        binding = self._profile(name)['binding']
        path = self._operation_path(operation)
        with WakeLifecycleLock(user_state_dir() / 'runtime-recipient-locks', pane_key(binding)):
            with automated_input_guard(self.root, binding, token):
                if path.exists():
                    return self.reconcile(name, operation)
                for existing in self.directory.glob('operation-*.json'):
                    row = _read(existing)
                    if row.get('pane') == _digest(pane_key(binding)) and row.get('state') == 'uncertain':
                        raise MenuError('unresolved_menu_effect')
                self._permission('terminal.menu', principal, binding)
                before = _identity(self.host, binding)
                if not _empty(before['frame']):
                    raise MenuError('menu_empty_composer_required')
                row = dict(version=1, operation=operation, profile=name, pane=_digest(pane_key(binding)),
                           token=token, state='admitted', pre_sha256=_digest(before['frame']), steps=[])
                _write(path, row)
                for key, expected in [('C-p', _palette), ('Escape', _empty)]:
                    # Recheck immediately before every distinct effect, never repeat.
                    self._permission('terminal.menu', principal, binding)
                    current = _identity(self.host, binding)
                    precondition = _empty if key == 'C-p' else _palette
                    if not precondition(current['frame']):
                        row.update(state='held', reason='menu_precondition_changed')
                        _write(path, row)
                        return row
                    row.update(state='uncertain', pending_key=key)
                    row['steps'].append(dict(key=key, state='uncertain', intent_at=time.time()))
                    _write(path, row)
                    try:
                        self.host._tmux(binding, 'send-keys', '-t', binding['pane'], key)
                        deadline = time.monotonic() + 2
                        while True:
                            after = _identity(self.host, binding)
                            if expected(after['frame']):
                                break
                            if time.monotonic() >= deadline:
                                raise MenuError('menu_post_state_unconfirmed')
                            time.sleep(.05)
                        if key == 'Escape' and _digest(after['frame']) != row['pre_sha256']:
                            raise MenuError('menu_post_frame_changed')
                    except Exception as exc:
                        row['reason'] = type(exc).__name__
                        _write(path, row)
                        return row
                    row['steps'][-1]['state'] = 'observed'
                    row['steps'][-1]['post_sha256'] = _digest(after['frame'])
                    row.update(state='between_steps' if key == 'C-p' else 'completed', pending_key=None)
                    _write(path, row)
                return row

    def reconcile(self, name, operation):
        """Read only: observations do not authorize another key or invent outcome."""
        row = _read(self._operation_path(operation))
        if row.get('profile') != name:
            raise MenuError('operation_profile_changed')
        try:
            frame = _identity(self.host, self._profile(name)['binding'])['frame']
            observed = 'palette' if _palette(frame) else ('empty_composer' if _empty(frame) else 'unknown')
        except Exception:
            observed = 'unknown'
        return dict(row, reconciliation_observation=observed, retry_allowed=False)
