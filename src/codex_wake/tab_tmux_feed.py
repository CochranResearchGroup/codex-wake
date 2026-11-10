"""One bounded, metadata-only stock tmux control client per session.

No pane output, terminal input, layout mutation or server lifetime is owned here.
The public snapshot shape is the existing TmuxTransport snapshot contract.
"""
import collections
import os
from pathlib import Path
import re
import selectors
import shlex
import subprocess
import time
import uuid

from .tab_organization import TabError, TmuxTransport


class TmuxMetadataFeed:
    MAX_BYTES = 1048576
    MAX_PANES = 4096
    FORMAT = '\t'.join('#{' + name + '}' for name in (
        'pid', 'session_id', 'window_id', 'window_index', 'window_name',
        'window_active', 'pane_id', 'pane_pid', 'pane_title', 'pane_current_path', 'pane_tty'))
    CHANGES = frozenset(('%window-add', '%window-close', '%window-renamed',
        '%unlinked-window-add', '%unlinked-window-close', '%unlinked-window-renamed',
        '%layout-change', '%session-window-changed', '%sessions-changed',
        '%session-changed', '%subscription-changed', '%pane-mode-changed'))

    def __init__(self, socket_path, session_id, *, clock=time.time,
                 monotonic=time.monotonic, timeout=2):
        self.socket, self.session = str(socket_path), session_id
        self.clock, self.monotonic = clock, monotonic
        self.timeout = min(10., max(.05, float(timeout)))
        self.source_id = 'tmux:' + self.socket + ':' + self.session
        self.epoch, self.sequence = '', 0
        self.process = None
        self.selector = None
        self.buffer = b''
        self.pending = collections.deque()
        self.frame = None
        self.dirty = False
        self.snapshot = None
        self.identity = None
        self.state, self.reason = 'disconnected', None
        self.retry_at = 0.
        self.closed = False
        self.started_at = None
        self.startup_seconds = None

    def _event(self, kind, data):
        self.sequence += 1
        return dict(source_id=self.source_id, source_kind='tmux', epoch=self.epoch,
                    sequence=self.sequence, kind=kind, observed_at=self.clock(), data=data)

    def _dispose(self):
        if self.selector is not None:
            self.selector.close()
            self.selector = None
        if self.process is not None:
            process, self.process = self.process, None
            for stream in (process.stdin, process.stdout):
                if stream:
                    stream.close()
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=.2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=.2)
        self.buffer = b''
        self.pending.clear()
        self.frame = None

    def _lost(self, reason):
        was_connected = self.process is not None
        self._dispose()
        self.state, self.reason = 'disconnected', reason
        self.retry_at = self.monotonic() + 1
        self.dirty = False
        return [self._event('unavailable', dict(reason=reason))] if was_connected else []

    def _send(self, kind, *parts):
        command = ' '.join(shlex.quote(str(p)) for p in parts) + '\n'
        # Only fixed metadata commands reach this method; labels are output only.
        self.process.stdin.write(command.encode())
        self.process.stdin.flush()
        self.pending.append((kind, self.monotonic()))

    def _request_snapshot(self):
        self._send('snapshot', 'list-panes', '-a', '-F', self.FORMAT)
        self.dirty = False

    def _connect(self):
        transport = TmuxTransport(self.socket, self.session)
        self.identity = transport.socket_identity
        self.epoch, self.sequence = uuid.uuid4().hex, 0
        self.snapshot = None
        self.started_at = self.monotonic()
        self.process = subprocess.Popen(['tmux', '-S', self.socket, '-C',
            'attach-session', '-f', 'no-output,ignore-size,read-only', '-t', self.session],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            bufsize=0, env={**os.environ, 'TMUX': ''})
        os.set_blocking(self.process.stdout.fileno(), False)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.pending.append(('attach', self.monotonic()))
        self.state, self.reason = 'connecting', None

    def _snapshot(self, lines):
        if not lines or len(lines) > self.MAX_PANES:
            raise ValueError('empty_or_oversized_inventory')
        rows = []
        for line in lines:
            values = line.split('\t')
            if len(values) != 11:
                raise ValueError('ambiguous_inventory_metadata')
            server, session, window, index, name, active, pane, pid, title, path, tty = values
            if not (server.isdecimal() and re.fullmatch(r'\$\d+', session)
                    and re.fullmatch(r'@\d+', window) and re.fullmatch(r'%\d+', pane)
                    and index.isdecimal() and pid.isdecimal() and active in ('0', '1')):
                raise ValueError('invalid_inventory_metadata')
            rows.append((server, session, window, int(index), name, active, pane, int(pid), title, path, tty))
        selected = [row for row in rows if row[1] == self.session]
        if not selected:
            raise ValueError('session_unavailable')
        windows = {}
        for server, session, window, index, name, active, pane, pid, title, path, tty in selected:
            item = windows.setdefault(window, dict(window_id=window, index=index,
                name=name, focused=active == '1',
                linked=len({r[1] for r in rows if r[2] == window}) > 1, panes=[]))
            item['panes'].append(dict(pane_id=pane, pid=pid, pane_title=title,
                                      pane_current_path=path, pane_tty=tty))
        return dict(server=selected[0][0], session_id=self.session,
                    socket_identity=self.identity,
                    windows=sorted(windows.values(), key=lambda w: w['index']))

    def _line(self, line):
        if line.startswith('%begin '):
            if self.frame is not None or not self.pending:
                raise ValueError('control_frame_gap')
            kind, sent = self.pending.popleft()
            self.frame = [line.split()[2], kind, [], sent, 0]
        elif line.startswith(('%end ', '%error ')):
            if self.frame is None or line.split()[2] != self.frame[0]:
                raise ValueError('control_frame_gap')
            _, kind, lines, _, _ = self.frame
            self.frame = None
            if line.startswith('%error '):
                raise ValueError('metadata_command_failed')
            if kind == 'attach':
                self._request_snapshot()
            elif kind == 'snapshot':
                snapshot = self._snapshot(lines)
                first = self.snapshot is None
                changed = snapshot != self.snapshot
                self.snapshot = snapshot
                self.state = 'available'
                if first:
                    self.startup_seconds = self.monotonic() - self.started_at
                    self._send('subscription', 'refresh-client', '-B',
                               'wake-windows:@*:#{window_id} #{window_index} #{window_name} #{window_active}')
                    self._send('subscription', 'refresh-client', '-B',
                               'wake-panes:%*:#{pane_id} #{pane_pid} #{pane_title} #{pane_current_path} #{pane_tty}')
                return [self._event('baseline' if first else 'update', dict(snapshot=snapshot))] if changed else []
        elif line.startswith('%exit'):
            raise ValueError('control_disconnected')
        elif line.startswith('%'):
            if line.split(' ', 1)[0] in self.CHANGES:
                self.dirty = True
            # Includes ignored pane-output messages; never retain their contents.
        elif self.frame is not None:
            self.frame[4] += len(line.encode('utf-8')) + 1
            self.frame[2].append(line)
            if len(self.frame[2]) > self.MAX_PANES or self.frame[4] > self.MAX_BYTES:
                raise ValueError('inventory_limit')
        return []

    def poll(self, timeout=0.0):
        if self.closed:
            return []
        now = self.monotonic()
        end = now + max(0., min(float(timeout), 10.))
        events = []
        try:
            if self.process is None:
                if now < self.retry_at:
                    return []
                self._connect()
                end = max(end, now + self.timeout)
            info = Path(self.socket).lstat()
            if [info.st_dev, info.st_ino] != self.identity:
                return self._lost('socket_generation_changed')
            read_bytes = 0
            while True:
                pending_at = self.frame[3] if self.frame else self.pending[0][1] if self.pending else None
                if pending_at is not None and self.monotonic() - pending_at > self.timeout:
                    return events + self._lost('metadata_timeout')
                if self.dirty and self.snapshot is not None and not self.pending and self.frame is None:
                    self._request_snapshot()
                ready = self.selector.select(max(0., end - self.monotonic()))
                if not ready:
                    break
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    return events + self._lost('control_disconnected')
                read_bytes += len(chunk)
                self.buffer += chunk
                if read_bytes > self.MAX_BYTES or len(self.buffer) > self.MAX_BYTES:
                    return events + self._lost('control_read_limit')
                while b'\n' in self.buffer:
                    line, self.buffer = self.buffer.split(b'\n', 1)
                    events.extend(self._line(line.decode('utf-8', errors='strict')))
                if events or self.monotonic() >= end:
                    break
            return events
        except (OSError, ValueError, TabError, subprocess.SubprocessError) as exc:
            return events + self._lost(str(exc) if isinstance(exc, ValueError) else 'control_unavailable')

    def status(self):
        return dict(source_id=self.source_id, source_kind='tmux', state=self.state,
                    reason=self.reason, epoch=self.epoch, sequence=self.sequence,
                    startup_seconds=self.startup_seconds, owned_pid=self.process.pid if self.process else None,
                    pending_commands=len(self.pending) + (self.frame is not None),
                    buffered_bytes=len(self.buffer), metadata_only=True)

    def close(self):
        self.closed = True
        self._dispose()
        self.state = 'closed'
