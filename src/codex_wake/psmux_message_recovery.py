"""Normal Windows owning adapter for an exact saved Codex presentation."""
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import stat
import subprocess
import sys
import time
from uuid import UUID, uuid4

from .message_delivery import Message
from .message_handoff import MessageHandoff
from .native_clock import snapshot as stable_time
from .windows_scope import ScopeError, executor_enabled, require_elevated_path, require_scope, scope_identity, set_created_owner
from .tab_psmux_bridge import (
    PsmuxHost, check_private_manifest, current_sid, process_birth, process_image,
)


_ENV = 'CODEX_WAKE_PSMUX_TOKEN'
_NAMESPACE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}\Z')
_SESSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')
_FIELDS = {'thread', 'namespace', 'session', 'title', 'index', 'cwd', 'home',
           'codex', 'port', 'server_pid', 'token_file'}
_WINDOWS_TIMEOUT = 4


class Unavailable(ValueError):
    pass


class Unsupported(Unavailable):
    pass


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _file_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _same_path(a, b):
    return bool(a and b and os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b)))


def _absolute(value, *, directory=False, private=False):
    path = Path(value)
    if not path.is_absolute():
        raise Unavailable('restore_absolute_path_required')
    info = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
        raise Unavailable('restore_expected_local_path')
    if private:
        check_private_manifest(path)
    return path.resolve(strict=True)


def _read(path):
    with Path(path).open('rb') as stream:
        value = stream.read(65537)
    if len(value) > 65536:
        raise Unavailable('restore_input_size')
    result = json.loads(value)
    if not isinstance(result, dict):
        raise Unavailable('restore_object_required')
    return result


def _write(path, value, *, identity=None):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(_json(value))
        stream.flush()
        os.fsync(stream.fileno())
    set_created_owner(path, identity)


def _binary():
    return Path(os.environ['LOCALAPPDATA']) / 'Microsoft/WinGet/Links/psmux.exe'


def _token(path):
    path = _absolute(path, private=True)
    with path.open(encoding='utf-8') as stream:
        token = stream.read(257).strip()
    if not re.fullmatch(r'[A-Za-z0-9._~-]{32,256}', token):
        raise Unavailable('restore_app_server_token_invalid')
    return token


def _loopback_listener(port):
    """Read the exact IPv4 loopback listener's owning process."""
    from ctypes import wintypes

    class Row(ctypes.Structure):
        _fields_ = [(name, wintypes.DWORD) for name in (
            'state', 'address', 'port', 'remote_address', 'remote_port', 'pid')]

    read = ctypes.WinDLL('iphlpapi').GetExtendedTcpTable
    read.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
                     wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
    read.restype = wintypes.DWORD
    size = wintypes.DWORD()
    if read(None, ctypes.byref(size), False, socket.AF_INET, 3, 0) != 122 or not 4 <= size.value <= 1048576:
        raise Unavailable('restore_tcp_owner_unavailable')
    buffer = ctypes.create_string_buffer(size.value)
    if read(buffer, ctypes.byref(size), False, socket.AF_INET, 3, 0) != 0:
        raise Unavailable('restore_tcp_owner_unavailable')
    count = wintypes.DWORD.from_buffer(buffer).value
    if count > (len(buffer) - 4) // ctypes.sizeof(Row):
        raise Unavailable('restore_tcp_owner_unavailable')
    rows = (Row * count).from_buffer(buffer, 4)
    loopback = int.from_bytes(socket.inet_aton('127.0.0.1'), 'little')
    owners = [row.pid for row in rows if row.state == 2 and row.address == loopback
              and socket.ntohs(row.port & 0xFFFF) == port]
    if len(owners) != 1:
        raise Unavailable('restore_tcp_owner_unavailable')
    return owners[0]


class Runtime:
    """Pinned stock Codex endpoint with same-home/thread/account checks."""

    def __init__(self, spec):
        self.spec = spec
        self.endpoint = 'ws://127.0.0.1:' + str(spec['port'])
        require_elevated_path(spec['token_file'], spec.get('execution_scope'), no_read_up=True)
        self.token = _token(spec['token_file'])

    def identify_process(self):
        pid = self.spec['server_pid']
        if _loopback_listener(self.spec['port']) != pid or not _same_path(process_image(pid), self.spec['codex']):
            raise Unavailable('restore_app_server_image_changed')
        if 'execution_scope' in self.spec:
            _authorize_scope(self.spec, pid=pid)
        return process_birth(pid)

    @contextmanager
    def connect(self):
        from websockets.sync.client import connect

        with connect(self.endpoint, additional_headers={'Authorization': 'Bearer ' + self.token},
                     open_timeout=2, close_timeout=.25, compression=None, proxy=None,
                     max_size=4 * 1024 * 1024) as stream:
            sequence = 0

            def rpc(method, params):
                nonlocal sequence
                sequence += 1
                stream.send(_json({'id': sequence, 'method': method, 'params': params}))
                deadline = time.monotonic() + 2
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise Unavailable('restore_runtime_readback_unavailable')
                    value = json.loads(stream.recv(timeout=remaining))
                    if value.get('id') != sequence:
                        continue
                    error = value.get('error')
                    if isinstance(error, dict) and error.get('code') == -32601:
                        raise Unsupported('restore_native_method_unavailable')
                    if 'error' in value or 'result' not in value:
                        raise Unavailable('restore_runtime_observation_unavailable')
                    return value['result']

            info = rpc('initialize', {'clientInfo': {'name': 'codex_wake_psmux', 'version': '1'},
                                      'capabilities': {'experimentalApi': True}})
            stream.send(_json({'method': 'initialized'}))
            if not _same_path(info.get('codexHome'), self.spec['home']):
                raise Unavailable('restore_app_server_home_changed')
            yield rpc

    def inspect(self, rpc):
        birth = self.identify_process()
        account = rpc('account/read', {'refreshToken': False})
        selected = rpc('thread/read', {'threadId': self.spec['thread'], 'includeTurns': False})['thread']
        if (birth != self.identify_process() or selected['id'] != self.spec['thread']
                or not _same_path(selected.get('cwd'), self.spec['cwd']) or not selected.get('modelProvider')):
            raise Unavailable('restore_original_conversation_unverified')
        status = selected['status']
        if not isinstance(status, dict) or status.get('type') not in ('idle', 'notLoaded', 'active'):
            raise Unavailable('restore_thread_status_unverified')
        return dict(provider=selected['modelProvider'], account=_digest(account), server_birth=birth), status

    def observe(self):
        with self.connect() as rpc:
            return self.inspect(rpc)

    def queue(self, rpc, message):
        # Stock's own queue client uses this native operation. Stdin/file-sized
        # bodies stay off Windows argv and retain the original client UUID.
        content = [{'type': 'text', 'text': message.payload, 'text_elements': []}]
        result = rpc('thread/queue/add', {
            'threadId': self.spec['thread'], 'clientUserMessageId': str(UUID(message.identifier)),
            'input': content, 'responsesapiClientMetadata': None})
        queued = result['queuedSubmission']
        if queued['clientUserMessageId'] != message.identifier or queued['input'] != content:
            raise Unavailable('restore_native_queue_receipt_unverified')
        return str(UUID(queued['id']))

    def environment(self):
        env = dict(os.environ)
        for key in ('CODEX_THREAD_ID', 'TMUX', 'TMUX_PANE', 'CODEX_WAKE_OWNER_DB_DSN',
                    'CODEX_WAKE_MESSAGE_DB_DSN', 'CODEX_WAKE_CUTOVER_DB_DSN'):
            env.pop(key, None)
        env['CODEX_HOME'] = self.spec['home']
        env[_ENV] = self.token
        return env


def _spec(raw):
    if not _FIELDS <= set(raw) <= _FIELDS | {'execution_scope', 'executor_activation'} or str(UUID(raw['thread'])) != raw['thread']:
        raise Unavailable('restore_exact_binding_required')
    identity = raw.get('execution_scope')
    if identity is not None:
        scope_identity(identity)
    if 'executor_activation' in raw and (not identity or not identity['elevated']
                                         or not Path(raw['executor_activation']).is_absolute()):
        raise Unavailable('restore_invalid_elevated_activation_path')
    if (not _NAMESPACE.fullmatch(raw['namespace']) or not _SESSION.fullmatch(raw['session'])
            or not isinstance(raw['title'], str) or not 0 < len(raw['title'].encode()) <= 192
            or any(ord(c) < 32 for c in raw['title'])
            or any(type(raw[k]) is not int for k in ('index', 'port', 'server_pid'))
            or not 0 <= raw['index'] <= 2**31-1 or not 1 <= raw['port'] <= 65535 or raw['server_pid'] <= 0):
        raise Unavailable('restore_invalid_binding_fields')
    return dict(raw, codex=str(_absolute(raw['codex'])), token_file=str(_absolute(raw['token_file'], private=True)),
                cwd=str(_absolute(raw['cwd'], directory=True)), home=str(_absolute(raw['home'], directory=True)))


def _authorize_scope(spec, *, execute=False, pid=None):
    identity = spec.get('execution_scope')
    try:
        actual = require_scope(identity, pid=pid)
        if execute and not executor_enabled(spec.get('executor_activation'), identity):
            raise Unavailable('restore_elevated_executor_disabled')
    except ScopeError as exc:
        raise Unavailable(str(exc)) from None
    return actual


def _pins(spec):
    _authorize_scope(spec)
    identity = spec.get('execution_scope')
    require_elevated_path(spec['token_file'], identity, no_read_up=True)
    home = Path(spec['home'])
    require_elevated_path(home, identity)
    check_private_manifest(home)
    st = home.stat()
    return dict(sid=_digest(current_sid()), home_identity=[st.st_dev, st.st_ino],
                codex_sha256=_file_digest(spec['codex']), psmux_sha256=_file_digest(_binary()))


def enroll(binding, request):
    spec = _spec(_read(request))
    _authorize_scope(spec)
    identity = spec.get('execution_scope')
    require_elevated_path(binding.parent, identity)
    require_elevated_path(request, identity)
    runtime, readiness = Runtime(spec).observe()
    if readiness['type'] not in ('idle', 'notLoaded'):
        raise Unavailable('restore_binding_requires_idle_thread')
    _write(binding, {'version': 1, 'spec': spec, 'pins': _pins(spec), 'runtime': runtime},
           identity=spec.get('execution_scope'))
    return {'status': 'bound', 'thread': spec['thread'], 'namespace': spec['namespace'],
            'session': spec['session'], 'index': spec['index']}


class Presentation:
    def __init__(self, binding, value):
        self.binding, self.value, self.spec = binding, value, value['spec']
        self.state_path = binding.with_suffix('.sqlite3')

    def _state_file(self, path):
        identity = self.spec.get('execution_scope')
        if identity and identity['elevated']:
            try:
                with path.open('xb'):
                    pass
                set_created_owner(path, identity)
            except FileExistsError:
                pass
        if path.exists() or path.is_symlink():
            _absolute(path, private=True)
            require_elevated_path(path, identity)

    @contextmanager
    def custody(self):
        self._state_file(self.state_path)
        with closing(sqlite3.connect(self.state_path, timeout=1, isolation_level=None)) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS placement(
                id integer PRIMARY KEY CHECK(id=1), binding text NOT NULL, creation text)''')
            db.execute('INSERT OR IGNORE INTO placement VALUES (1,?,NULL)', (_digest(self.value),))
            row = db.execute('SELECT binding,creation FROM placement').fetchone()
            if row[0] != _digest(self.value):
                raise Unavailable('restore_binding_changed')
            # A second database owns the OS-backed exclusive lock while
            # placement state commits independently before terminal commands.
            control = self.state_path.with_suffix('.lock.sqlite3')
            self._state_file(control)
            with closing(sqlite3.connect(control, timeout=.5)) as lock:
                lock.execute('BEGIN EXCLUSIVE')
                creation = db.execute('SELECT creation FROM placement WHERE id=1').fetchone()[0]
                yield db, json.loads(creation) if creation else None

    def _command(self, *args):
        return subprocess.run([str(_binary()), '-L', self.spec['namespace'], *args],
                              timeout=_WINDOWS_TIMEOUT, capture_output=True, text=True, encoding='utf-8')

    def _host(self):
        reply = self._command('list-sessions', '-F', '#{session_name}')
        if reply.returncode:
            if reply.returncode == 1 and not reply.stdout.strip() and (
                    reply.stderr.strip().endswith('(-L ' + self.spec['namespace'] + ')')
                    and reply.stderr.startswith('psmux: no server running on ')):
                return None
            raise Unavailable('restore_psmux_discovery_unverified')
        if self.spec['session'] not in reply.stdout.splitlines():
            return None
        host = PsmuxHost(namespace=self.spec['namespace'], session=self.spec['session'])
        if host.identity['executable_sha256'] != self.value['pins']['psmux_sha256']:
            raise Unavailable('restore_psmux_executable_changed')
        if 'execution_scope' in self.spec:
            _authorize_scope(self.spec, pid=host.identity['pid'])
        return host

    @staticmethod
    def _windows(host):
        host._current()
        return host._snapshot(host._rows())['windows']

    def _marker(self, nonce):
        return self.binding.parent / (self.binding.stem + '.pane-' + nonce + '.json')

    def _find(self, windows, creation):
        try:
            marker_path = _absolute(self._marker(creation['nonce']), private=True)
            require_elevated_path(marker_path, self.spec.get('execution_scope'))
            marker = _read(marker_path)
        except FileNotFoundError:
            return None
        if marker['nonce'] != creation['nonce'] or marker['thread'] != self.spec['thread']:
            raise Unavailable('restore_launch_receipt_changed')
        matches = []
        for window in windows:
            if window['linked'] or len(window['panes']) != 1:
                continue
            pane = window['panes'][0]
            found = any(row['pid'] == marker['pid'] and row['creation_filetime'] == marker['birth']
                        and _same_path(row['executable'], self.spec['codex'])
                        for row in pane['windows_processes'])
            if found:
                matches.append(window)
        if len(matches) > 1:
            raise Unavailable('restore_duplicate_presentation')
        return matches[0] if matches else None

    @staticmethod
    def _window_identity(window):
        return [[p['pane_id'], p['pid'], p['windows_creation_filetime']] for p in window['panes']]

    def _placeholder(self, windows):
        for window in windows:
            if (window['index'] != self.spec['index'] or window['name'] != self.spec['title']
                    or window['linked'] or len(window['panes']) != 1):
                continue
            pane = window['panes'][0]
            if (pane['windows_processes_complete'] and len(pane['windows_processes']) == 1
                    and Path(pane['windows_executable'] or '').name.lower() in ('cmd.exe', 'powershell.exe', 'pwsh.exe')
                    and _same_path(pane['cwd'], self.spec['cwd'])):
                return window
        return None

    def open(self):
        _authorize_scope(self.spec, execute=True)
        with self.custody() as (db, existing):
            host = self._host()
            windows = self._windows(host) if host else []
            if existing:
                previous = self._find(windows, existing)
                if previous:
                    return self._confirm(db, host, windows, previous, existing)
                if existing['pending'] and (not host or existing['generation'] in (None, host.generation)):
                    if not host or any(item['name'] == existing['name'] for item in windows):
                        return None
            # A name collision alone grants no custody over that tab.
            placeholder = self._placeholder(windows)
            occupied = {item['index'] for item in windows}
            chosen = self.spec['index'] if self.spec['index'] not in occupied else max(occupied) + 1
            if chosen > 2**31 - 1:
                chosen = next(index for index in range(len(occupied) + 1) if index not in occupied)
            title = self.spec['title']
            titles = {item['name'] for item in windows}
            for suffix in range(1, len(titles)+2):
                if title not in titles:
                    break
                title = self.spec['title'] + '-restored' + ('' if suffix == 1 else '-' + str(suffix))
            nonce = uuid4().hex
            unaffected = {item['window_id']: [item['index'], item['name'], item['focused'], self._window_identity(item)]
                          for item in windows if not placeholder or item['window_id'] != placeholder['window_id']}
            creation = dict(nonce=nonce, name=title, index=chosen, pending=True,
                            generation=host.generation if host else None, placeholder=placeholder,
                            unaffected=unaffected)
            _authorize_scope(self.spec, execute=True)
            db.execute('UPDATE placement SET creation=? WHERE id=1', (_json(creation),))
            launch = self._launch_argv(nonce)
            if host is None:
                result = self._command('new-session', '-d', '-s', self.spec['session'], '-n', title,
                                       '-c', self.spec['cwd'], *launch)
                if result.returncode:
                    raise Unavailable('restore_native_session_launch_unverified')
                host = self._host()
                if host is None:
                    raise Unavailable('restore_native_session_launch_unverified')
            else:
                host._current()
                host.command('new-window', '-d', '-t', self.spec['session'] + ':' + str(chosen),
                             '-n', title, '-c', self.spec['cwd'], *launch)
            creation['generation'] = host.generation
            db.execute('UPDATE placement SET creation=? WHERE id=1', (_json(creation),))
            windows = self._windows(host)
            opening = self._find(windows, creation)
            return self._confirm(db, host, windows, opening, creation) if opening else None

    def _launch_argv(self, nonce):
        # Use the exact installed module path even if the already-running
        # psmux server's Python environment differs from the owner worker's.
        return ['--', sys.executable, str(Path(__file__).with_name('psmux_message_launch.py').resolve()),
                str(self.binding), nonce]

    def _swap_preserving_focus(self, host, windows, first, second):
        _authorize_scope(self.spec, execute=True)
        focused = next((item for item in windows if item['focused']), None)
        host._current()
        host.command('swap-window', '-d', '-s', self.spec['session'] + ':' + first,
                     '-t', self.spec['session'] + ':' + second)
        after = self._windows(host)
        if focused is not None:
            selected = next((item for item in after if item['focused']), None)
            original = next((item for item in after if item['window_id'] == focused['window_id']), None)
            # psmux can focus a swap participant even with -d. Restore only
            # the previous exact pane, and leave an unrelated focus change alone.
            if (selected and selected['window_id'] in (first, second) and original
                    and not original['focused']
                    and self._window_identity(original) == self._window_identity(focused)):
                host._current()
                host.command('select-window', '-t', self.spec['session'] + ':' + original['window_id'])
                after = self._windows(host)
        return after

    def _confirm(self, db, host, windows, current, creation):
        placeholder = creation.get('placeholder')
        window = current['window_id']
        if creation['pending'] and placeholder:
            live = self._placeholder(windows)
            if live and self._window_identity(live) == self._window_identity(placeholder):
                windows = self._swap_preserving_focus(host, windows, window, live['window_id'])
                current = next(item for item in windows if item['window_id'] == window)
        expected = self.spec['index'] if placeholder else creation['index']
        if creation['pending'] and current['index'] != expected and not placeholder:
            if expected in {item['index'] for item in windows if item['window_id'] != window}:
                raise Unavailable('restore_target_slot_changed')
            _authorize_scope(self.spec, execute=True)
            host._current()
            host.command('move-window', '-d', '-s', self.spec['session'] + ':' + window,
                         '-t', self.spec['session'] + ':' + str(expected))
            current = next(item for item in self._windows(host) if item['window_id'] == window)
        if creation['pending'] and current['index'] != expected:
            raise Unavailable('restore_placement_readback_mismatch')
        if creation['pending']:
            observed = {item['window_id']: [item['index'], item['name'], item['focused'], self._window_identity(item)]
                        for item in self._windows(host)}
            if placeholder and observed.get(placeholder['window_id']) != [
                    creation['index'], placeholder['name'], placeholder['focused'], self._window_identity(placeholder)]:
                raise Unavailable('restore_idle_placeholder_changed')
            if any(observed.get(identifier) != saved for identifier, saved in creation['unaffected'].items()):
                raise Unavailable('restore_unrelated_placement_changed')
        creation['pending'] = False
        db.execute('UPDATE placement SET creation=? WHERE id=1', (_json(creation),))
        return self._placement(host, current)

    def _placement(self, host, window):
        return {'status': 'placed', 'namespace': self.spec['namespace'], 'session': self.spec['session'],
                'thread': self.spec['thread'], 'index': window['index'], 'title': window['name'],
                'window': window['window_id'], 'pane': window['panes'][0]['pane_id'],
                'server_birth': host.identity['creation_filetime'],
                **({'execution_scope': self.spec['execution_scope']} if 'execution_scope' in self.spec else {})}

    def status(self):
        with self.custody() as (_, creation):
            host = self._host()
            current = self._find(self._windows(host), creation) if host and creation else None
            if current is None or creation['pending']:
                return {'status': 'opening' if creation and creation['pending'] else 'absent',
                        'thread': self.spec['thread']}
            return self._placement(host, current)


def _load(binding):
    value = _read(_absolute(binding, private=True))
    identity = value['spec'].get('execution_scope')
    _authorize_scope(value['spec'])
    require_elevated_path(binding.parent, identity)
    require_elevated_path(binding, identity)
    if value.get('version') != 1 or _pins(value['spec']) != value['pins']:
        raise Unavailable('restore_original_account_or_harness_changed')
    return value


def _delivery(binding, message):
    result = dict(id=message.identifier, recipient=message.recipient,
                  expires_at_micros=message.expires_at_micros)
    entered = False
    try:
        value = _load(binding)
        spec = value['spec']
        _authorize_scope(spec, execute=True)
        if message.recipient != spec['thread']:
            raise Unavailable('restore_recipient_changed')
        if MessageHandoff._window(message, stable_time()) != 'eligible':
            return dict(result, status='unsent', reason='expired')
        runtime = Runtime(spec)
        pin, status = runtime.observe()
        if pin != value['runtime']:
            raise Unavailable('restore_native_runtime_changed')
        if status.get('type') not in ('idle', 'notLoaded') or status.get('activeFlags'):
            return dict(result, status='unsent', reason='busy')
        if not Presentation(binding, value).open():
            return dict(result, status='unsent', reason='offline')
        with runtime.connect() as rpc:
            pin, status = runtime.inspect(rpc)
            if pin != value['runtime'] or status['type'] != 'idle' or status.get('activeFlags'):
                return dict(result, status='unsent', reason='busy')
            if MessageHandoff._window(message, stable_time()) != 'eligible':
                return dict(result, status='unsent', reason='expired')
            _authorize_scope(spec, execute=True)
            entered = True
            receipt = runtime.queue(rpc, message)
        return dict(result, status='submitted', receipt_id=receipt)
    except Unsupported:
        return dict(result, status='unsent', reason='offline')
    except Exception:
        # An ambiguous transport invocation remains fenced by the owner.
        return dict(result, status='uncertain' if entered else 'unsent', reason='offline')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', type=Path, required=True)
    operation = parser.add_subparsers(dest='verb', required=True)
    register = operation.add_parser('enroll')
    register.add_argument('--request', type=Path, required=True)
    operation.add_parser('present')
    operation.add_parser('status')
    operation.add_parser('deliver')
    args = parser.parse_args(argv)
    try:
        if os.name != 'nt':
            raise Unavailable('native_windows_executor_required')
        root = _absolute(args.binding.parent, directory=True, private=True)
        binding = root / args.binding.name
        if args.verb == 'enroll':
            result = enroll(binding, args.request)
        elif args.verb == 'status':
            result = Presentation(binding, _load(binding)).status()
        elif args.verb == 'present':
            value = _load(binding)
            _authorize_scope(value['spec'], execute=True)
            pin, status = Runtime(value['spec']).observe()
            if pin != value['runtime'] or status['type'] not in ('idle', 'notLoaded') or status.get('activeFlags'):
                raise Unavailable('restore_original_recipient_not_idle')
            result = Presentation(binding, value).open() or {'status': 'opening'}
        else:
            payload = sys.stdin.buffer.read(524289)
            if len(payload) > 524288:
                raise Unavailable('restore_message_frame_too_large')
            result = _delivery(binding, Message(**json.loads(payload)))
        print(_json(result))
        return 0
    except Exception as error:
        reason = str(error) if isinstance(error, (Unavailable, ScopeError)) else 'restore_owner_unavailable'
        print(_json({'status': 'held', 'reason': reason}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
