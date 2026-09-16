"""Public listener contract exercised over ephemeral loopback sockets."""
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
import json
import socket
import threading
import time
import unittest

from codex_wake.github_webhooks import WebhookResult
from codex_wake.webhook_http import WebhookHTTPConfig, WebhookHTTPServer


def request(body=b'{"exact": true}', *, target=b'/github/webhook', method=b'POST',
            version=b'HTTP/1.1', media=b'application/json', extra=b''):
    return (method + b' ' + target + b' ' + version + b'\r\nHost: localhost\r\n'
            b'Content-Type: ' + media + b'\r\nContent-Length: ' + str(len(body)).encode()
            + b'\r\n' + extra + b'\r\n' + body)


def receive(sock):
    chunks = []
    while True:
        try:
            chunk = sock.recv(4096)
        except ConnectionResetError:
            break
        if not chunk:
            break
        chunks.append(chunk)
    raw = b''.join(chunks)
    head, body = raw.split(b'\r\n\r\n', 1)
    status = int(head.split(b' ', 2)[1])
    headers = dict(line.split(b': ', 1) for line in head.split(b'\r\n')[1:])
    assert int(headers[b'Content-Length']) == len(body)
    assert headers[b'Connection'] == b'close'
    assert headers[b'Cache-Control'] == b'no-store'
    return status, json.loads(body)['code']


class WebhookHTTPTests(unittest.TestCase):
    @contextmanager
    def listener(self, callback=None, **config):
        calls = []
        def ingest(body, headers):
            calls.append((body, headers))
            return WebhookResult(200, 'COMMITTED')
        server = WebhookHTTPServer(WebhookHTTPConfig(**config), callback or ingest)
        thread = threading.Thread(target=server.serve, name='test-webhook-serve')
        thread.start()
        try:
            yield server, calls
        finally:
            server.shutdown()
            thread.join(2)
            self.assertFalse(thread.is_alive())

    def exchange(self, server, raw):
        with socket.create_connection(server.address, timeout=2) as sock:
            sock.sendall(raw)
            sock.shutdown(socket.SHUT_WR)
            return receive(sock)

    def test_exact_body_and_committed_result_cross_public_seam(self):
        with self.listener() as (server, calls):
            self.assertEqual(self.exchange(server, request()), (200, 'COMMITTED'))
            self.assertEqual(calls[0][0], b'{"exact": true}')
            self.assertEqual(calls[0][1]['content-type'], 'application/json')
            self.assertEqual(len(calls), 1)

    def test_route_method_version_and_media_are_exact(self):
        cases = [(dict(target=value), (404, 'ROUTE')) for value in (
            b'/github/webhook?x=1', b'/github/webhook#x', b'/github/webhook/',
            b'/github/%77ebhook', b'http://localhost/github/webhook', b'*')]
        cases += [(dict(method=b'GET'), (405, 'METHOD')),
                  (dict(version=b'HTTP/1.0'), (505, 'VERSION')),
                  (dict(media=b'text/plain'), (415, 'MEDIA_TYPE')),
                  (dict(media=b'application/json; charset=latin1'), (415, 'MEDIA_TYPE'))]
        with self.listener() as (server, calls):
            for overrides, expected in cases:
                with self.subTest(overrides=overrides):
                    self.assertEqual(self.exchange(server, request(**overrides)), expected)
            self.assertEqual(calls, [])
            self.assertEqual(self.exchange(server, request(media=b'application/json; charset=utf-8')),
                             (200, 'COMMITTED'))

    def test_ambiguous_framing_never_reaches_ingest(self):
        raw = request()
        cases = [request(extra=extra) for extra in (
            b'Content-Length: 15\r\n', b'CONTENT-LENGTH: 99\r\n',
            b'Transfer-Encoding: chunked\r\n', b'Expect: 100-continue\r\n',
            b'Content-Encoding: identity\r\n', b'Host: duplicate\r\n',
            b' X-Folded: yes\r\n', b'Bad Name: value\r\n', b'X-Value: a\x00b\r\n')]
        cases += [raw.replace(b'Content-Length: 15\r\n', value) for value in (
            b'', b'Content-Length: +15\r\n', b'Content-Length: 1, 15\r\n',
            b'Content-Length: -1\r\n', b'Content-Length: 1.5\r\n')]
        cases += [raw[:-1], raw.replace(b'\r\n', b'\n')]
        for malformed in cases:
            with self.subTest(raw=malformed), self.listener() as (server, calls):
                self.assertEqual(self.exchange(server, malformed), (400, 'FRAMING'))
                self.assertEqual(calls, [])

    def test_observable_suffix_is_rejected_before_ingest(self):
        # Queue bytes before starting serve: suffix presence is deterministic.
        # The large body also leaves suffix bytes beyond the parser read buffer.
        for body in (b'{}', b' ' * 8192):
            for suffix in (b'X', request()):
                with self.subTest(body_size=len(body), suffix=suffix):
                    calls = []
                    def ingest(body, headers):
                        calls.append(body)
                        return WebhookResult(200, 'COMMITTED')
                    server = WebhookHTTPServer(WebhookHTTPConfig(), ingest)
                    serving = threading.Thread(target=server.serve)
                    try:
                        with socket.create_connection(server.address, timeout=2) as sock:
                            sock.sendall(request(body) + suffix)
                            serving.start()
                            self.assertEqual(receive(sock), (400, 'FRAMING'))
                            self.assertEqual(calls, [])
                    finally:
                        server.shutdown()
                        serving.join(2)

    def test_later_write_cannot_become_a_second_request(self):
        entered, release = threading.Event(), threading.Event()
        calls = []
        def ingest(body, headers):
            calls.append(body)
            entered.set()
            release.wait(2)
            return WebhookResult(200, 'COMMITTED')
        with self.listener(ingest) as (server, _):
            with socket.create_connection(server.address, timeout=2) as sock:
                sock.sendall(request())
                self.assertTrue(entered.wait(1))
                try:
                    sock.sendall(request())
                finally:
                    release.set()
                self.assertEqual(receive(sock), (200, 'COMMITTED'))
                self.assertEqual(len(calls), 1)

    def test_clean_shutdown_allows_immediate_fixed_port_restart(self):
        with self.listener() as (server, _):
            host, port = server.address
            with socket.create_connection(server.address, timeout=2) as sock:
                # Let the server close first so its local socket enters TIME_WAIT.
                sock.sendall(request())
                self.assertEqual(receive(sock), (200, 'COMMITTED'))
            with self.assertRaises(OSError):
                WebhookHTTPServer(WebhookHTTPConfig(host=host, port=port),
                                  lambda b, h: WebhookResult(200, 'COMMITTED'))
        with self.listener(host=host, port=port) as (restarted, calls):
            self.assertEqual(restarted.address, (host, port))
            self.assertEqual(self.exchange(restarted, request()), (200, 'COMMITTED'))
            self.assertEqual(len(calls), 1)

    def test_size_budgets_reject_before_ingest(self):
        cases = [({'max_request_line_bytes': 16}, request(), (414, 'SIZE')),
                 ({'max_header_line_bytes': 16}, request(), (431, 'SIZE')),
                 ({'max_header_bytes': 40}, request(), (431, 'SIZE')),
                 ({'max_headers': 2}, request(), (431, 'SIZE')),
                 ({'max_body_bytes': 10}, request(), (413, 'SIZE'))]
        for config, raw, expected in cases:
            with self.subTest(config=config), self.listener(**config) as (server, calls):
                self.assertEqual(self.exchange(server, raw), expected)
                self.assertEqual(calls, [])

    def test_absolute_deadline_limits_slow_and_incomplete_requests(self):
        for prefix in (b'P', request().split(b'\r\n\r\n')[0] + b'\r\n\r\n{'):
            with self.subTest(prefix=prefix), self.listener(request_timeout=.2) as (server, calls):
                with socket.create_connection(server.address, timeout=2) as sock:
                    started = time.monotonic()
                    sock.sendall(prefix)
                    self.assertEqual(receive(sock), (408, 'TIMEOUT'))
                    self.assertLess(time.monotonic() - started, 1)
                    self.assertEqual(calls, [])

    def test_connection_and_ingest_capacity_reject_without_queue(self):
        entered, release = threading.Event(), threading.Event()
        calls = []
        def blocked(body, headers):
            calls.append(body)
            entered.set()
            release.wait(2)
            return WebhookResult(200, 'COMMITTED')
        for limits in ({'max_connections': 1, 'max_workers': 1},
                       {'max_connections': 2, 'max_workers': 1}):
            entered.clear()
            release.clear()
            calls.clear()
            with self.subTest(limits=limits), self.listener(blocked, **limits) as (server, _):
                with socket.create_connection(server.address, timeout=2) as first:
                    first.sendall(request())
                    self.assertTrue(entered.wait(1))
                    try:
                        self.assertEqual(self.exchange(server, request()), (503, 'ADMISSION'))
                        self.assertEqual(len(calls), 1)
                    finally:
                        release.set()
                    self.assertEqual(receive(first), (200, 'COMMITTED'))

    def test_shutdown_is_truthful_about_blocked_callback(self):
        entered, release = threading.Event(), threading.Event()
        def blocked(body, headers):
            entered.set()
            release.wait(2)
            return WebhookResult(200, 'COMMITTED')
        server = WebhookHTTPServer(WebhookHTTPConfig(shutdown_timeout=.1), blocked)
        serving = threading.Thread(target=server.serve)
        serving.start()
        with socket.create_connection(server.address, timeout=2) as sock:
            sock.sendall(request())
            self.assertTrue(entered.wait(1))
            try:
                started = time.monotonic()
                with self.assertRaisesRegex(TimeoutError, '^webhook shutdown deadline exceeded$'):
                    server.shutdown()
                self.assertLess(time.monotonic() - started, .5)
                self.assertEqual(sock.recv(1024), b'')
                with self.assertRaises(OSError):
                    socket.create_connection(server.address, timeout=.2)
            finally:
                release.set()
                server.shutdown()
                serving.join(1)
        self.assertFalse(serving.is_alive())
        self.assertFalse(any(t.name == 'webhook-http-request' for t in threading.enumerate()))

    def test_bind_and_limit_configuration_fails_closed(self):
        for values in ({'host': '0.0.0.0'}, {'host': '192.0.2.1'}, {'host': 'localhost'},
                       {'host': '::ffff:192.0.2.1'}, {'port': True}, {'port': 65536},
                       {'max_connections': 0}, {'max_workers': 9}, {'max_headers': 0},
                       {'max_body_bytes': -1}, {'request_timeout': float('nan')},
                       {'shutdown_timeout': float('inf')}, {'path': '/another'},
                       {'allow_non_loopback': 1}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                WebhookHTTPConfig(**values)
        allowed = WebhookHTTPConfig(host='0.0.0.0', allow_non_loopback=True)
        self.assertEqual(allowed.host, '0.0.0.0')
        with self.assertRaises(FrozenInstanceError):
            allowed.port = 1

    def test_forwarding_headers_and_host_do_not_change_behavior(self):
        with self.listener() as (server, calls):
            raw = request(extra=b'Forwarded: for=192.0.2.1;host=evil\r\n'
                          b'X-Forwarded-For: 192.0.2.2\r\nX-Forwarded-Proto: https\r\n')
            raw = raw.replace(b'Host: localhost', b'Host: attacker.example')
            self.assertEqual(self.exchange(server, raw), (200, 'COMMITTED'))
            self.assertEqual(len(calls), 1)

    def test_callback_failures_and_invalid_results_are_sanitized(self):
        def fail(body, headers):
            raise RuntimeError('credential-secret-do-not-echo')
        for callback in (fail, lambda b, h: WebhookResult(200, 'credential-secret-do-not-echo'),
                         lambda b, h: WebhookResult('200\r\nInjected: bad', 'COMMITTED'),
                         lambda b, h: WebhookResult(302, 'COMMITTED'),
                         lambda b, h: WebhookResult(599, 'COMMITTED'),
                         lambda b, h: WebhookResult(200, 'SIGNATURE_INVALID'),
                         lambda b, h: None):
            with self.subTest(callback=callback), self.listener(callback) as (server, _):
                self.assertEqual(self.exchange(server, request()), (503, 'UNAVAILABLE'))
        with self.listener(lambda b, h: WebhookResult(401, 'SIGNATURE_INVALID')) as (server, _):
            self.assertEqual(self.exchange(server, request()), (401, 'SIGNATURE_INVALID'))

    def test_legitimate_ingress_status_code_pairs_are_preserved(self):
        pairs = {
            200: ('COMMITTED', 'DUPLICATE'),
            400: ('CLOCK_INVALID', 'PAYLOAD_INVALID', 'HEADERS_INVALID', 'DELIVERY_INVALID'),
            401: ('SIGNATURE_INVALID',), 403: ('EVENT_NOT_ALLOWED',),
            409: ('DELIVERY_CONFLICT',), 413: ('BODY_TOO_LARGE', 'BODY_READ_LIMIT'),
            422: ('EVENT_STALE', 'VERIFICATION_FAILED'), 429: ('RATE_LIMITED',),
            503: ('BUSY', 'CLOCK_UNAVAILABLE', 'INGRESS_UNAVAILABLE', 'SECRET_UNAVAILABLE',
                  'VERIFICATION_UNAVAILABLE', 'STORE_UNAVAILABLE', 'COMMIT_FAILED'),
        }
        for status, codes in pairs.items():
            for code in codes:
                with self.subTest(status=status, code=code):
                    result = WebhookResult(status, code)
                    with self.listener(lambda b, h: result) as (server, _):
                        self.assertEqual(self.exchange(server, request()), (status, code))

    def test_request_deadline_closes_response_even_if_callback_is_still_busy(self):
        entered, release = threading.Event(), threading.Event()
        def blocked(body, headers):
            entered.set()
            release.wait(2)
            return WebhookResult(200, 'COMMITTED')
        with self.listener(blocked, request_timeout=.1) as (server, _):
            with socket.create_connection(server.address, timeout=1) as sock:
                sock.sendall(request())
                self.assertTrue(entered.wait(1))
                try:
                    self.assertEqual(receive(sock), (408, 'TIMEOUT'))
                    self.assertEqual(self.exchange(server, request()), (503, 'ADMISSION'))
                finally:
                    release.set()

    def test_http11_requires_host_and_rejects_transfer_negotiation(self):
        with self.listener() as (server, calls):
            for raw in (request().replace(b'Host: localhost\r\n', b''),
                        request(extra=b'TE: trailers\r\n'),
                        request(extra=b'Trailer: X-Signature\r\n')):
                with self.subTest(raw=raw):
                    self.assertEqual(self.exchange(server, raw), (400, 'FRAMING'))
            self.assertEqual(calls, [])

    def test_shutdown_interrupts_a_partial_request_without_ingest(self):
        with self.listener(max_connections=1, shutdown_timeout=.5) as (server, calls):
            with socket.create_connection(server.address, timeout=1) as sock:
                sock.sendall(b'POST /github/webhook HTTP/1.1\r\n')
                # Seeing admission rejection proves the first socket is owned.
                self.assertEqual(self.exchange(server, request()), (503, 'ADMISSION'))
                server.shutdown()
                self.assertEqual(sock.recv(1024), b'')
                self.assertEqual(calls, [])
        self.assertFalse(any(t.name == 'webhook-http-request' for t in threading.enumerate()))

    def test_trickled_bytes_do_not_reset_absolute_request_deadline(self):
        with self.listener(request_timeout=.15) as (server, calls):
            with socket.create_connection(server.address, timeout=1) as sock:
                stopped = threading.Event()
                def trickle():
                    for byte in request():
                        try:
                            sock.sendall(bytes([byte]))
                        except OSError:
                            return
                        if stopped.wait(.03):
                            return
                writer = threading.Thread(target=trickle)
                writer.start()
                started = time.monotonic()
                try:
                    self.assertEqual(receive(sock), (408, 'TIMEOUT'))
                    self.assertLess(time.monotonic() - started, .75)
                    self.assertEqual(calls, [])
                finally:
                    stopped.set()
                    writer.join(1)


if __name__ == '__main__':
    unittest.main()
