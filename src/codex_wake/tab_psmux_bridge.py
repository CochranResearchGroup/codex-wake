"""Finite Windows psmux bridge for a WSL-owned Wake controller.

The host fixes the executable, namespace, session and server birth in its bridge
command. Requests contain typed presentation actions, never shell or argv. This
module is stdlib-only so the same installed artifact runs under native Windows
Python without creating a second Wake execution owner.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


class BridgeError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def process_birth(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        raise BridgeError('attachment_unavailable', 'native presentation process is unavailable')
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *[ctypes.byref(value) for value in times]):
            raise BridgeError('attachment_unavailable', 'native process generation is unavailable')
        return (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
    finally:
        kernel.CloseHandle(handle)


def process_image(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        value = ctypes.create_unicode_buffer(size.value)
        return value.value if kernel.QueryFullProcessImageNameW(handle, 0, value, ctypes.byref(size)) else None
    finally:
        kernel.CloseHandle(handle)


def pane_processes(roots):
    """One bounded native snapshot, returning only selected pane descendants.

    No command-line/private environment reads and no PowerShell/WMI process loop.
    Image identity can classify a harness; it cannot attest its conversation,
    turn activity, stock/modded registration or exact TUI-loop health.
    """
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    class Entry(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t),
                    ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG),
                    ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260)]
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ('Process32FirstW', 'Process32NextW'):
        getattr(kernel, name).argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
        getattr(kernel, name).restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        return {}, False
    deadline = time.monotonic() + .5
    children, parents, count, complete = {}, {}, 0, True
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(entry)
        found = kernel.Process32FirstW(handle, ctypes.byref(entry))
        while found:
            count += 1
            if count > 4096 or time.monotonic() >= deadline:
                complete = False
                break
            pid, parent = int(entry.th32ProcessID), int(entry.th32ParentProcessID)
            children.setdefault(parent, []).append(pid)
            parents[pid] = parent
            found = kernel.Process32NextW(handle, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(handle)
    result = {}
    for root in roots:
        pending, seen, rows = [root], set(), []
        while pending:
            pid = pending.pop(0)
            if pid in seen:
                continue
            if len(seen) >= 256 or time.monotonic() >= deadline:
                complete = False
                break
            seen.add(pid)
            try:
                birth = process_birth(pid)
                image = process_image(pid)
                if process_birth(pid) != birth:
                    complete = False
                    continue
                rows.append(dict(pid=pid, parent_pid=parents.get(pid), creation_filetime=birth,
                                 executable=image, platform='windows'))
            except BridgeError:
                complete = False
            pending.extend(children.get(pid, []))
        result[root] = rows
    return result, complete


class PsmuxHost:
    ACTIONS = {'snapshot', 'discover', 'capture', 'visible_screen', 'swap', 'lifecycle'}

    def __init__(self, *, namespace, session, server_pid=None, server_birth=None):
        if os.name != 'nt':
            raise BridgeError('unsupported_target', 'this presentation bridge requires native Windows Python')
        if not isinstance(namespace, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', namespace):
            raise BridgeError('invalid_argument', 'host must configure a bounded exact namespace')
        self.namespace = namespace
        self.session = self._text(session, 'session')
        self.binary = Path(os.environ['LOCALAPPDATA']) / 'Microsoft/WinGet/Links/psmux.exe'
        self.server_pid, self.server_birth = server_pid, server_birth
        self.identity = self.describe()
        if server_pid is not None and (self.identity['pid'] != server_pid or self.identity['creation_filetime'] != server_birth):
            raise BridgeError('stale_target', 'psmux server generation changed')
        self.generation = hashlib.sha256(json.dumps(self.identity, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _text(value, field):
        if not isinstance(value, str) or not value or len(value.encode()) > 256 or any(ord(c) < 32 for c in value):
            raise BridgeError('invalid_argument', field + ' must be bounded single-line text')
        return value

    def command(self, *argv):
        try:
            reply = subprocess.run([str(self.binary), '-L', self.namespace, *argv],
                text=True, capture_output=True, timeout=4, check=True)
        except (OSError, subprocess.SubprocessError):
            raise BridgeError('attachment_unavailable', 'native psmux command failed; reconcile effects before retry') from None
        if len(reply.stdout.encode()) > 1048576:
            raise BridgeError('capacity', 'native presentation exceeds bounded output')
        return reply.stdout

    def describe(self):
        pid = int(self.command('display-message', '-p', '-t', self.session + ':', '#{pid}').strip())
        return dict(platform='windows', namespace=self.namespace, pid=pid,
                    session=self.session, creation_filetime=process_birth(pid),
                    executable_sha256=hashlib.sha256(self.binary.read_bytes()).hexdigest())

    def _current(self):
        if process_birth(self.identity['pid']) != self.identity['creation_filetime']:
            raise BridgeError('stale_target', 'native psmux process generation changed')
        pid = int(self.command('display-message', '-p', '-t', self.session + ':', '#{pid}').strip())
        if pid != self.identity['pid']:
            raise BridgeError('stale_target', 'native psmux server was replaced')

    def _rows(self):
        fields = ('session_id', 'session_name', 'window_id', 'window_index', 'window_name',
                  'window_active', 'pane_id', 'pane_index', 'pane_pid', 'pane_current_path')
        output = self.command('list-panes', '-a', '-F', '\t'.join('#{' + field + '}' for field in fields))
        lines = output.splitlines()
        if len(lines) > 4096:
            raise BridgeError('capacity', 'native pane inventory exceeds bound')
        rows = []
        for line in lines:
            values = line.split('\t')
            if len(values) != len(fields):
                raise BridgeError('attachment_unavailable', 'ambiguous native presentation metadata')
            row = dict(zip(fields, values))
            if not re.fullmatch(r'@[0-9]+', row['window_id']) or not re.fullmatch(r'%[0-9]+', row['pane_id']):
                raise BridgeError('attachment_unavailable', 'invalid native presentation identities')
            rows.append(row)
        return rows

    def _snapshot(self, rows, session=None):
        session = session or self.session
        selected = [row for row in rows if session in (row['session_id'], row['session_name'])]
        identities = {row['session_id'] for row in selected}
        if len(identities) != 1:
            raise BridgeError('attachment_unavailable', 'exact psmux session is unavailable or ambiguous')
        native_processes, complete = pane_processes({int(row['pane_pid']) for row in selected})
        windows = {}
        for row in selected:
            window = windows.setdefault(row['window_id'], dict(window_id=row['window_id'], index=int(row['window_index']),
                name=row['window_name'], focused=row['window_active'] == '1',
                linked=False, panes=[]))
            pid = int(row['pane_pid'])
            window['panes'].append(dict(pane_id=row['pane_id'], pane_index=int(row['pane_index']), pid=pid, platform='windows',
                windows_creation_filetime=process_birth(pid), windows_executable=process_image(pid), cwd=row['pane_current_path'],
                windows_processes=native_processes.get(pid, []), windows_processes_complete=complete))
        return dict(server=str(self.identity['pid']), session_id=next(iter(identities)),
                    socket_identity=[self.identity['pid'], self.identity['creation_filetime']],
                    windows=sorted(windows.values(), key=lambda w: w['index']),
                    server_identity=self.identity, windows_server=self.identity)

    def execute(self, request):
        if not isinstance(request, dict) or set(request) != {'action', 'arguments'}:
            raise BridgeError('invalid_argument', 'finite action and arguments required')
        action, args = request['action'], request['arguments']
        if action not in self.ACTIONS or not isinstance(args, dict):
            raise BridgeError('unsupported_operation', 'unsupported finite presentation operation')
        self._current()
        rows = self._rows()
        if action == 'discover':
            if args:
                raise BridgeError('invalid_argument', 'discovery accepts no arguments')
            sessions = {row['session_id']: row['session_name'] for row in rows}
            result = dict(sessions=[dict(session_id=k, name=v) for k, v in sorted(sessions.items())],
                          server_identity=self.identity, capabilities=sorted(self.ACTIONS))
        else:
            snapshot = self._snapshot(rows)
            windows = {w['window_id']: w for w in snapshot['windows']}
            panes = {p['pane_id'] for w in windows.values() for p in w['panes']}
            if action == 'snapshot':
                if args:
                    raise BridgeError('invalid_argument', 'snapshot accepts no arguments')
                result = snapshot
            elif action in ('capture', 'visible_screen'):
                allowed = {'pane', 'lines'} if action == 'capture' else {'pane'}
                if set(args) != allowed or args.get('pane') not in panes:
                    raise BridgeError('stale_target', 'exact current pane is required')
                row = next(r for r in rows if r['session_id'] == snapshot['session_id'] and r['pane_id'] == args['pane'])
                exact_pane = self.session + ':' + row['window_index'] + '.' + row['pane_index']
                command = ['capture-pane', '-p', '-t', exact_pane]
                if action == 'capture':
                    lines = args['lines']
                    if type(lines) is not int or not 1 <= lines <= 200:
                        raise BridgeError('invalid_argument', 'capture supports 1 through 200 lines')
                    command += ['-S', '-' + str(lines)]
                result = self.command(*command)[-32768:]
            elif action == 'swap':
                if set(args) != {'first', 'second'} or args.get('first') not in windows or args.get('second') not in windows:
                    raise BridgeError('stale_target', 'exact current windows required')
                focused = next(w['window_id'] for w in windows.values() if w['focused'])
                self.command('swap-window', '-d', '-s', self.session + ':' + args['first'], '-t', self.session + ':' + args['second'])
                self.command('select-window', '-t', self.session + ':' + focused)
                result = {}
            else:
                result = self._lifecycle(args, snapshot, rows)
        if not (action == 'lifecycle' and args.get('action') == 'close'
                and result.get('workspace_state') == 'removed'):
            self._current()
        return dict(generation=self.generation, result=result)

    def _lifecycle(self, args, snapshot, rows):
        allowed = {
            'create': {'name', 'cwd'}, 'rename': {'window', 'name'}, 'focus': {'window'}, 'close': {'window'},
            'move': {'window', 'destination_session', 'index'}, 'park': {'window', 'destination_session', 'index'},
            'restore': {'window', 'destination_session', 'index'},
        }
        action = args.get('action')
        if action not in allowed or set(args) - allowed[action] - {'action'}:
            raise BridgeError('unsupported_operation', 'unsupported finite lifecycle operation')
        windows = {w['window_id']: w for w in snapshot['windows']}
        wid = args.get('window')
        if action != 'create' and wid not in windows:
            raise BridgeError('stale_target', 'exact current source window is required')
        destination = snapshot['session_id']
        if action in ('create', 'rename'):
            name = self._text(args.get('name'), 'name')
            if any(w['name'] == name and w['window_id'] != wid for w in windows.values()):
                raise BridgeError('name_conflict', 'destination already has that tab name')
        if action == 'create':
            command = ['new-window', '-d', '-P', '-F', '#{window_id}', '-t', destination + ':', '-n', name]
            cwd_value = args.get('cwd', os.environ['USERPROFILE'])
            if cwd_value is not None:
                cwd = self._text(cwd_value, 'cwd')
                if not Path(cwd).is_absolute() or not Path(cwd).is_dir():
                    raise BridgeError('invalid_argument', 'native working directory must exist and be absolute')
                command += ['-c', cwd]
            # Shell selection belongs to this host adapter, never to requests.
            wid = self.command(*command, '--', 'cmd.exe', '/d', '/k').strip()
        elif action == 'rename':
            self.command('rename-window', '-t', self.session + ':' + wid, name)
        elif action == 'focus':
            self.command('select-window', '-t', self.session + ':' + wid)
        elif action == 'close':
            self.command('kill-window', '-t', self.session + ':' + wid)
        else:
            destination = args.get('destination_session')
            target = self._snapshot(rows, destination)
            if target['session_id'] == snapshot['session_id']:
                raise BridgeError('invalid_argument', 'destination must differ from source')
            # Native psmux sessions have separate servers and repeat @/% IDs.
            # join-pane would be a different operation and must not be substituted.
            raise BridgeError('unsupported_target', 'psmux whole-window cross-session movement is unsupported; source preserved')
        after_rows = self._rows()
        present = any(row['session_id'] == destination for row in after_rows)
        after = self._snapshot(after_rows, destination) if present else None
        if action == 'close':
            if any(row['session_id'] == snapshot['session_id'] and row['window_id'] == wid for row in after_rows):
                raise BridgeError('effect_uncertain', 'closed tab remains visible')
        elif after is None or not any(w['window_id'] == wid for w in after['windows']):
            raise BridgeError('effect_uncertain', 'destination attachment was not observed')
        return dict(window_id=wid, workspace_state='present' if present else 'removed', snapshot=after)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--server-pid', type=int)
    parser.add_argument('--server-birth', type=int)
    parser.add_argument('--describe', action='store_true')
    args = parser.parse_args(argv)
    host = None
    try:
        host = PsmuxHost(namespace=args.namespace, session=args.session,
                         server_pid=args.server_pid, server_birth=args.server_birth)
        if args.describe:
            value = dict(generation=host.generation, identity=host.identity,
                         capabilities=sorted(host.ACTIONS))
        else:
            raw = sys.stdin.buffer.read(65537)
            if len(raw) > 65536:
                raise BridgeError('capacity', 'finite bridge input exceeds bound')
            value = host.execute(json.loads(raw))
        print(json.dumps(value))
        return 0
    except (BridgeError, ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps(dict(generation=host.generation if host else None,
            error=dict(code=getattr(error, 'code', 'attachment_unavailable'), message=str(error)))))
        return 0 if host else 2


if __name__ == '__main__':
    raise SystemExit(main())
