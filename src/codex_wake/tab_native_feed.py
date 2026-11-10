"""Bounded passive status connection to an existing same-user Codex server.

This adapter owns a connection, never the server or a conversation. Metadata is
allowlisted before entering the event queue. No transcript subscription exists.
"""
from __future__ import annotations

from collections import deque
import json
import math
import os
from pathlib import Path
import socket
import stat
import struct
import time
import uuid

from . import __version__
from .process import process_identity


class NativeStatusFeed:
    """Poll metadata-only native events, reconnecting after bounded backoff."""

    MAX_THREADS = 1000
    MAX_EVENTS = 2048
    MAX_FRAME = 256 * 1024
    ALLOWED_METHODS = frozenset({'initialize', 'thread/loaded/list', 'thread/read'})

    def __init__(self, endpoint, *, clock=time.time, monotonic=time.monotonic,
                 timeout=2, connector=None):
        if (not isinstance(endpoint, str) or not endpoint.startswith('unix:///')
                or not endpoint[7:] or not math.isfinite(timeout) or not 0 < timeout <= 30):
            raise ValueError('An absolute Unix endpoint and timeout in (0,30] are required.')
        self.endpoint = endpoint
        self.clock, self.monotonic, self.timeout = clock, monotonic, timeout
        self.connector = connector
        self.connection = None
        self.epoch = uuid.uuid4().hex
        self.sequence = self.request_sequence = 0
        self.events = deque()
        self.closed = False
        self.state, self.reason = 'disconnected', None
        self.retry_at, self.failures = 0.0, 0
        self.peer = None
        self.socket_identity = None
        self.startup_seconds = None
        self.last_event_at = None

    def _event(self, kind, data):
        if len(self.events) >= self.MAX_EVENTS:
            raise ValueError('event_backlog_exceeded')
        self.sequence += 1
        self.last_event_at = self.clock()
        self.events.append(dict(source_id=self.endpoint, source_kind='native',
                                epoch=self.epoch, sequence=self.sequence, kind=kind,
                                observed_at=self.last_event_at, data=data))

    @staticmethod
    def _status(value):
        if not isinstance(value, dict) or value.get('type') not in ('active', 'idle', 'notLoaded', 'systemError'):
            raise ValueError('invalid_thread_status')
        result = dict(type=value['type'])
        if 'activeFlags' in value:
            flags = value['activeFlags']
            if (not isinstance(flags, list) or len(flags) > 16 or
                    any(v not in ('waitingOnApproval', 'waitingOnUserInput') for v in flags)):
                raise ValueError('invalid_active_flags')
            result['activeFlags'] = flags[:]
        return result

    def _receive(self, timeout):
        raw = self.connection.recv(timeout=max(0, timeout))
        if not isinstance(raw, (str, bytes)) or len(raw) > self.MAX_FRAME:
            raise ValueError('native_frame_exceeded')
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError('invalid_native_frame')
        return value

    def _notification(self, message):
        # Server requests, detailed thread events and unknown methods are ignored.
        if 'id' in message or message.get('method') != 'thread/status/changed':
            return
        params = message.get('params')
        if not isinstance(params, dict) or not isinstance(params.get('threadId'), str) or not 0 < len(params['threadId']) <= 256:
            raise ValueError('invalid_thread_identity')
        self._event('update', dict(thread_id=params['threadId'], status=self._status(params.get('status'))))

    def _request(self, method, params, deadline):
        if method not in self.ALLOWED_METHODS:
            raise ValueError('method_not_allowed')
        if method == 'thread/read' and params.get('includeTurns') is not False:
            raise ValueError('history_not_allowed')
        self.request_sequence += 1
        request_id = self.request_sequence
        self.connection.send(json.dumps(dict(id=request_id, method=method, params=params)))
        for _ in range(self.MAX_EVENTS):
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                raise TimeoutError('bootstrap_deadline')
            message = self._receive(remaining)
            if 'method' in message:
                self._notification(message)
                continue
            if message.get('id') != request_id or 'error' in message or not isinstance(message.get('result'), dict):
                raise ValueError('invalid_native_response')
            return message['result']
        raise ValueError('bootstrap_notification_overflow')

    @staticmethod
    def _identity(path):
        info = path.stat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid():
            raise ValueError('endpoint_not_owned_socket')
        return (info.st_dev, info.st_ino, info.st_ctime_ns)

    def _connect(self):
        started = self.monotonic()
        deadline = started + self.timeout
        path = Path(self.endpoint[7:])
        if path.is_symlink():
            from .strict_runtime import resolve_executor_endpoint
            path = Path(resolve_executor_endpoint(self.endpoint)[7:])
        path = path.resolve(strict=True)
        self.socket_identity = (str(path), self._identity(path))
        connector = self.connector
        if connector is None:
            from websockets.sync.client import unix_connect
            connector = unix_connect
        self.connection = connector(str(path), open_timeout=max(.001, deadline - self.monotonic()),
                                    close_timeout=.1, compression=None, max_size=self.MAX_FRAME,
                                    max_queue=16, legacy=True)
        pid, uid, _ = struct.unpack('3i', self.connection.socket.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        identity = process_identity(pid)
        if uid != os.geteuid() or not identity or self._identity(path) != self.socket_identity[1]:
            raise ValueError('native_peer_unverified')
        self.peer = dict(pid=pid, start_ticks=identity['start_time_ticks'], boot_id=identity.get('boot_id'))
        self.epoch, self.sequence = uuid.uuid4().hex, 0
        server = self._request('initialize', dict(clientInfo=dict(name='codex_wake_status', version=__version__),
                                                 capabilities=dict(experimentalApi=True)), deadline)
        self.connection.send(json.dumps(dict(method='initialized')))
        self._baseline(deadline, server, reset_sequence=True)
        self.server_metadata = {key:server[key] for key in ('codexHome','userAgent','platformFamily','platformOs')
                                if isinstance(server.get(key),str) and len(server[key])<=8192}
        self.startup_seconds = self.monotonic() - started
        self.state, self.reason, self.failures = 'connected', None, 0

    def _baseline(self, deadline, server, *, reset_sequence=False):
        threads, seen, cursors, cursor = [], set(), set(), None
        while True:
            page = self._request('thread/loaded/list', dict(cursor=cursor, limit=100), deadline)
            ids = page.get('data')
            if not isinstance(ids, list):
                raise ValueError('invalid_loaded_threads')
            for thread_id in ids:
                if not isinstance(thread_id, str) or not 0 < len(thread_id) <= 256 or thread_id in seen:
                    raise ValueError('invalid_loaded_thread_identity')
                seen.add(thread_id)
                if len(seen) > self.MAX_THREADS:
                    raise ValueError('thread_population_exceeded')
                value = self._request('thread/read', dict(threadId=thread_id, includeTurns=False), deadline).get('thread')
                if not isinstance(value, dict) or value.get('id') != thread_id:
                    raise ValueError('thread_identity_mismatch')
                row = {key: value[key] for key in ('id', 'name', 'cwd', 'modelProvider')
                       if isinstance(value.get(key), str) and len(value[key]) <= 8192}
                row['status'] = self._status(value.get('status'))
                # A later metadata response supersedes earlier notifications for
                # this thread; replay only deltas subsequent to its snapshot.
                self.events = deque(event for event in self.events
                                    if event['data'].get('thread_id') != thread_id)
                threads.append(row)
            cursor = page.get('nextCursor')
            if cursor is None:
                break
            if not isinstance(cursor, str) or not 0 < len(cursor) <= 4096 or cursor in cursors:
                raise ValueError('invalid_loaded_thread_cursor')
            cursors.add(cursor)
        # Updates received while reading bootstrap are replayed after baseline.
        pending = list(self.events)
        self.events.clear()
        if reset_sequence:
            self.sequence = 0
        metadata = {key: server[key] for key in ('codexHome', 'userAgent', 'platformFamily', 'platformOs')
                    if isinstance(server.get(key), str) and len(server[key]) <= 8192}
        self._event('baseline', dict(threads=threads, server=metadata, peer=self.peer))
        for event in pending:
            self._event('update', event['data'])

    def refresh_metadata(self):
        """Complete bounded metadata rebaseline over the same read-only connection."""
        if self.closed or self.connection is None:
            return []
        try:
            self._baseline(self.monotonic()+self.timeout, self.server_metadata)
        except Exception as exc:
            self._lost('metadata_' + type(exc).__name__)
        events = list(self.events)
        self.events.clear()
        return events

    def _lost(self, reason):
        connection, self.connection = self.connection, None
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
        self.events.clear()  # An incomplete batch cannot establish current state.
        self.state, self.reason = 'unavailable', reason
        self.failures = min(6, self.failures + 1)
        self.retry_at = self.monotonic() + min(30, .25 * 2 ** self.failures)
        self._event('unavailable', dict(reason=reason))

    def poll(self, timeout=0.0):
        if not math.isfinite(timeout) or not 0 <= timeout <= 30:
            raise ValueError('poll timeout must be between0and30seconds')
        if self.closed:
            return []
        if self.connection is None:
            if self.monotonic() < self.retry_at:
                return []
            try:
                self._connect()
            except Exception as exc:
                self._lost('bootstrap_' + type(exc).__name__)
            result = list(self.events)
            self.events.clear()
            return result
        deadline = self.monotonic() + timeout
        try:
            path, identity = self.socket_identity
            if str(Path(self.endpoint[7:]).resolve(strict=True)) != path:
                raise ValueError('endpoint_generation_changed')
            if self._identity(Path(path)) != identity:
                raise ValueError('socket_generation_changed')
            current = process_identity(self.peer['pid'])
            if not current or str(current.get('start_time_ticks')) != str(self.peer['start_ticks']) or current.get('boot_id') != self.peer['boot_id']:
                raise ValueError('peer_generation_changed')
            for _ in range(self.MAX_EVENTS):
                try:
                    message = self._receive(max(0, deadline - self.monotonic()))
                except TimeoutError:
                    break
                self._notification(message)
            else:
                raise ValueError('event_batch_exceeded')
        except Exception as exc:
            self._lost('connection_' + type(exc).__name__)
        result = list(self.events)
        self.events.clear()
        return result

    def status(self):
        return dict(source_id=self.endpoint, source_kind='native', state=self.state,
                    reason=self.reason, epoch=self.epoch, sequence=self.sequence,
                    peer=self.peer, backlog=len(self.events), startup_seconds=self.startup_seconds,
                    last_event_at=self.last_event_at, retry_at=self.retry_at)

    def close(self):
        self.closed = True
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass
        self.connection = None
        self.events.clear()
        self.state = 'closed'
