"""Bounded, one-request HTTP/1.1 transport; no provider or dispatch ownership.

The callable receives exact bytes and lowercase, unique ASCII header names.
It owns authentication and durable commit; the listener never acknowledges
success before it returns. Callback work must supply its own execution bound.
An overdue callback retains its admission slot even after its socket expires.
"""
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from ipaddress import ip_address
import json
import math
import re
import socket
import threading
import time

from .github_webhooks import WebhookResult


# Exact ingress and transport outcomes; codes cannot change HTTP semantics.
_RESULTS = frozenset({
    (200, 'COMMITTED'), (200, 'DUPLICATE'), (503, 'BUSY'),
    (503, 'CLOCK_UNAVAILABLE'), (400, 'CLOCK_INVALID'), (429, 'RATE_LIMITED'),
    (503, 'INGRESS_UNAVAILABLE'), (400, 'PAYLOAD_INVALID'),
    (413, 'BODY_TOO_LARGE'), (413, 'BODY_READ_LIMIT'), (400, 'HEADERS_INVALID'),
    (401, 'SIGNATURE_INVALID'), (503, 'SECRET_UNAVAILABLE'),
    (403, 'EVENT_NOT_ALLOWED'), (400, 'DELIVERY_INVALID'), (422, 'EVENT_STALE'),
    (409, 'DELIVERY_CONFLICT'), (503, 'VERIFICATION_UNAVAILABLE'),
    (422, 'VERIFICATION_FAILED'), (503, 'STORE_UNAVAILABLE'), (503, 'COMMIT_FAILED'),
    (404, 'ROUTE'), (405, 'METHOD'), (505, 'VERSION'), (400, 'FRAMING'),
    (413, 'SIZE'), (414, 'SIZE'), (431, 'SIZE'), (415, 'MEDIA_TYPE'),
    (408, 'TIMEOUT'), (503, 'ADMISSION'), (503, 'UNAVAILABLE'),
})


class _Rejected(Exception):
    def __init__(self, status, code):
        self.result = WebhookResult(status, code)


@dataclass(frozen=True, slots=True)
class WebhookHTTPConfig:
    """Immutable budgets. Bind hosts are IP literals; port zero is ephemeral."""
    host: str = '127.0.0.1'
    port: int = 0
    path: str = '/github/webhook'
    max_request_line_bytes: int = 4096
    max_header_line_bytes: int = 8192
    max_header_bytes: int = 16384
    max_headers: int = 64
    max_body_bytes: int = 262144
    request_timeout: float = 10.0
    max_connections: int = 8
    max_workers: int = 1
    shutdown_timeout: float = 5.0
    allow_non_loopback: bool = False

    def __post_init__(self):
        invalid = 'webhook HTTP configuration is invalid'
        if type(self.host) is not str or '%' in self.host:
            raise ValueError(invalid)
        try:
            address = ip_address(self.host)
        except ValueError:
            raise ValueError(invalid) from None
        if (type(self.allow_non_loopback) is not bool
                or (not address.is_loopback and not self.allow_non_loopback)
                or type(self.path) is not str or self.path != '/github/webhook'):
            raise ValueError(invalid)
        for value, low, high in (
            (self.port, 0, 65535), (self.max_request_line_bytes, 1, 16384),
            (self.max_header_line_bytes, 1, 16384), (self.max_header_bytes, 1, 65536),
            (self.max_headers, 1, 256), (self.max_body_bytes, 1, 1048576),
            (self.max_connections, 1, 256), (self.max_workers, 1, self.max_connections),
        ):
            if type(value) is not int or not low <= value <= high:
                raise ValueError(invalid)
        for value in (self.request_timeout, self.shutdown_timeout):
            if type(value) not in (int, float) or not math.isfinite(value) or not .01 <= value <= 300:
                raise ValueError(invalid)


class _Reader:
    def __init__(self, connection, deadline):
        self.connection = connection
        self.deadline = deadline
        self.buffer = bytearray()

    def _recv(self, limit):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        self.connection.settimeout(remaining)
        chunk = self.connection.recv(limit)
        if not chunk:
            raise _Rejected(400, 'FRAMING')
        self.buffer.extend(chunk)

    def line(self, limit, status):
        while True:
            end = self.buffer.find(b'\n')
            if end >= 0:
                if end + 1 > limit:
                    raise _Rejected(status, 'SIZE')
                result = bytes(self.buffer[:end + 1])
                del self.buffer[:end + 1]
                return result
            if len(self.buffer) >= limit:
                raise _Rejected(status, 'SIZE')
            self._recv(min(4096, limit - len(self.buffer)))

    def body(self, length):
        while len(self.buffer) < length:
            self._recv(min(4096, length - len(self.buffer)))
        result = bytes(self.buffer[:length])
        del self.buffer[:length]
        return result

    def reject_observable_suffix(self):
        """Inspect only bytes present now; never wait for or predict a later write."""
        if self.buffer:
            raise _Rejected(400, 'FRAMING')
        previous_timeout = self.connection.gettimeout()
        try:
            self.connection.setblocking(False)
            if self.connection.recv(1, socket.MSG_PEEK):
                raise _Rejected(400, 'FRAMING')
        except BlockingIOError:
            pass
        finally:
            self.connection.settimeout(previous_timeout)


class _Request:
    def __init__(self, connection, deadline):
        self.connection = connection
        self.deadline = deadline
        self.lock = threading.Lock()
        self.responded = False

    def close(self):
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.connection.close()


class WebhookHTTPServer:
    """Bind on construction, serve once, then shut down from the lifecycle owner.

    ``address`` is the actual (IP, port) pair. ``max_connections`` bounds parsing
    threads and retained requests; ``max_workers`` separately bounds concurrent
    ingest calls. Neither limit has an application queue. The kernel listen
    backlog is bounded by max_connections. Responses are best-effort fixed-size
    writes with a 10 ms cap; deadline observation has a 10 ms accept tick.
    """
    def __init__(self, config: WebhookHTTPConfig,
                 ingest: Callable[[bytes, Mapping[str, str]], WebhookResult]):
        if type(config) is not WebhookHTTPConfig or not callable(ingest):
            raise ValueError('webhook HTTP configuration is invalid')
        self.config = config
        self._ingest = ingest
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._active = {}
        self._threads = set()
        self._serve_thread = None
        self._workers = threading.BoundedSemaphore(config.max_workers)
        family = socket.AF_INET6 if ip_address(config.host).version == 6 else socket.AF_INET
        self._socket = socket.socket(family, socket.SOCK_STREAM)
        try:
            # Permit a clean fixed-port restart through TIME_WAIT. Do not enable
            # SO_REUSEPORT, which would allow a second live listener to share it.
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET6:
                self._socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            self._socket.bind((config.host, config.port))
            self._socket.listen(config.max_connections)
            self._socket.settimeout(.01)
            self.address = self._socket.getsockname()[:2]
        except OSError:
            self._socket.close()
            raise OSError('webhook listener unavailable') from None

    def serve(self) -> None:
        """Block until shutdown; reject a second concurrent serving owner."""
        with self._lock:
            if self._stop.is_set():
                return
            if self._serve_thread is not None:
                raise RuntimeError('webhook listener already serving')
            self._serve_thread = threading.current_thread()
        while not self._stop.is_set():
            with self._lock:
                expired = [item for item in self._active.values()
                           if time.monotonic() >= item.deadline]
                self._threads = {thread for thread in self._threads if thread.is_alive()}
            for item in expired:
                self._respond(item, WebhookResult(408, 'TIMEOUT'))
            try:
                connection, _ = self._socket.accept()
            except socket.timeout:
                continue
            except OSError:
                if self._stop.is_set():
                    break
                raise
            with self._lock:
                if self._stop.is_set() or len(self._active) >= self.config.max_connections:
                    accepted = False
                else:
                    item = _Request(connection, time.monotonic() + self.config.request_timeout)
                    worker = threading.Thread(target=self._run, args=(item,),
                                              name='webhook-http-request', daemon=True)
                    self._active[worker] = item
                    self._threads.add(worker)
                    worker.start()
                    accepted = True
            if not accepted:
                item = _Request(connection, time.monotonic() + self.config.request_timeout)
                self._respond(item, WebhookResult(503, 'ADMISSION'))

    def _run(self, item):
        try:
            self._handle(item)
        finally:
            item.close()
            with self._lock:
                self._active.pop(threading.current_thread(), None)

    def shutdown(self) -> None:
        """Stop admission and close sockets; raise if callbacks cannot drain in time.

        An injected callable must bound its own work. Python cannot forcibly
        terminate it. A timeout is unsuccessful shutdown and may be retried
        after the callback exits. Successful return proves all workers exited.
        Call from the lifecycle owner, never from the ingest callable.
        """
        deadline = time.monotonic() + self.config.shutdown_timeout
        with self._lock:
            self._stop.set()
            active = list(self._active.values())
            threads = list(self._threads)
            serving = self._serve_thread
        self._socket.close()
        for item in active:
            item.close()
        if serving is not None:
            threads.append(serving)
        for thread in threads:
            if thread is threading.current_thread():
                raise RuntimeError('webhook shutdown requires lifecycle owner')
            thread.join(max(0, deadline - time.monotonic()))
        if any(thread.is_alive() for thread in threads):
            raise TimeoutError('webhook shutdown deadline exceeded')

    def _handle(self, item):
        deadline = item.deadline
        stream = _Reader(item.connection, deadline)
        try:
            line = stream.line(self.config.max_request_line_bytes, 414)
            if not line.endswith(b'\r\n'):
                raise _Rejected(400, 'FRAMING')
            parts = line[:-2].split(b' ')
            if len(parts) != 3:
                raise _Rejected(400, 'FRAMING')
            method, target, version = parts
            if version != b'HTTP/1.1':
                raise _Rejected(505, 'VERSION')
            if method != b'POST':
                raise _Rejected(405, 'METHOD')
            if target != self.config.path.encode('ascii'):
                raise _Rejected(404, 'ROUTE')
            headers = {}
            header_bytes = 0
            while True:
                line = stream.line(self.config.max_header_line_bytes, 431)
                header_bytes += len(line)
                if header_bytes > self.config.max_header_bytes:
                    raise _Rejected(431, 'SIZE')
                if line == b'\r\n':
                    break
                if len(headers) >= self.config.max_headers:
                    raise _Rejected(431, 'SIZE')
                if not line.endswith(b'\r\n') or b':' not in line:
                    raise _Rejected(400, 'FRAMING')
                name, value = line[:-2].split(b':', 1)
                if (not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name)
                        or any(byte < 32 or byte > 126 for byte in value)):
                    raise _Rejected(400, 'FRAMING')
                name = name.decode('ascii').lower()
                if name in headers or name in ('transfer-encoding', 'te', 'trailer', 'expect', 'content-encoding'):
                    raise _Rejected(400, 'FRAMING')
                headers[name] = value.decode('ascii').strip(' ')
            length = headers.get('content-length', '')
            if not headers.get('host') or not re.fullmatch('[0-9]{1,10}', length):
                raise _Rejected(400, 'FRAMING')
            if int(length) > self.config.max_body_bytes:
                raise _Rejected(413, 'SIZE')
            if headers.get('content-type') not in ('application/json', 'application/json; charset=utf-8'):
                raise _Rejected(415, 'MEDIA_TYPE')
            body = stream.body(int(length))
            if time.monotonic() >= deadline:
                raise TimeoutError()
            # Serialize the nonblocking peek's socket mode with response writes.
            with item.lock:
                if item.responded:
                    raise TimeoutError()
                stream.reject_observable_suffix()
            with self._lock:
                if self._stop.is_set() or not self._workers.acquire(blocking=False):
                    raise _Rejected(503, 'ADMISSION')
            try:
                result = self._ingest(body, headers)
            finally:
                self._workers.release()
            self._respond(item, result)
        except _Rejected as exc:
            self._respond(item, exc.result)
        except TimeoutError:
            self._respond(item, WebhookResult(408, 'TIMEOUT'))
        except Exception:
            self._respond(item, WebhookResult(503, 'UNAVAILABLE'))

    @staticmethod
    def _respond(item, result):
        if (type(result) is not WebhookResult or type(result.status) is not int
                or type(result.code) is not str or (result.status, result.code) not in _RESULTS):
            result = WebhookResult(503, 'UNAVAILABLE')
        with item.lock:
            if item.responded:
                return
            item.responded = True
            if time.monotonic() >= item.deadline:
                result = WebhookResult(408, 'TIMEOUT')
            body = json.dumps({'code': result.code}, separators=(',', ':')).encode('ascii')
            try:
                item.connection.settimeout(.01)
                item.connection.sendall((f'HTTP/1.1 {result.status} Result\r\nContent-Length: {len(body)}\r\n'
                                         'Content-Type: application/json\r\nConnection: close\r\n'
                                         'Cache-Control: no-store\r\n\r\n').encode('ascii') + body)
            except OSError:
                pass
            finally:
                item.close()
