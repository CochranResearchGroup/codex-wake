import json
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import timedelta
from http.client import HTTPConnection
from pathlib import Path

from codex_wake.github_client import GitHubRestClient, _absolute_deadline
from codex_wake.github_polling import GitHubPollingAdapter, GitHubReadError, PollBatch
from codex_wake.signals import ArmContext, Ingested, WakeId
from tests.test_github_polling import NOW, config
from tests.test_signal_store import make_module
from tests.test_signals import make_intent


def payload(**changes):
    return {"id": 101, "run_attempt": 1, "repository": {"id": 42, "full_name": "example/project"},
            "head_repository": {"id": 42, "full_name": "example/project"},
            "workflow_id": 7, "head_branch": "main", "head_sha": "a" * 40,
            "status": "completed", "conclusion": "success", "run_started_at": NOW.isoformat(),
            "updated_at": (NOW + timedelta(days=5)).isoformat(), **changes}


def terminal_responses():
    run = payload(run_started_at=(NOW + timedelta(seconds=1)).isoformat())
    return [Response({"workflow_runs": [run], "total_count": 1}), Response(run),
            Response({"jobs": [], "total_count": 0})]


class Response:
    def __init__(self, body, status=200, headers=None):
        self.status = status
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.headers = headers or {}
        self.closed = False

    def read(self, limit):
        chunk, self.body = self.body[:limit], self.body[limit:]
        return chunk

    read1 = read

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def close(self):
        self.closed = True


class FixtureHTTPS:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.origins = []
        self.closes = 0

    def __call__(self, host, timeout):
        self.origins.append((host, timeout))
        return self

    def request(self, method, path, headers):
        self.requests.append((method, path, headers))

    def getresponse(self):
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        self.closes += 1


class GitHubClientTests(unittest.TestCase):
    def test_delivery_client_reuses_the_main_thread_deadline_without_replacing_it(self):
        selected = config(evidence_mode="positive_only")
        http = FixtureHTTPS([Response(payload()), Response({"jobs": [], "total_count": 0})])
        original_handler = signal.getsignal(signal.SIGALRM)
        original_timer = signal.getitimer(signal.ITIMER_REAL)
        try:
            with _absolute_deadline(1) as deadline:
                client = GitHubRestClient(selected, credential_resolver=lambda ref: "fixture-secret",
                                          connection_factory=http, deadline=deadline)
                verified = client.get_run_attempt(selected.repository, 101, 1)
                self.assertEqual((verified.run_id, verified.run_attempt), (101, 1))
                self.assertNotEqual(signal.getsignal(signal.SIGALRM), original_handler)
                self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 0)
            self.assertIs(signal.getsignal(signal.SIGALRM), original_handler)
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL), original_timer)
        finally:
            signal.signal(signal.SIGALRM, original_handler)
            signal.setitimer(signal.ITIMER_REAL, *original_timer)

    def test_delivery_deadline_cannot_be_reused_after_its_owner_exits(self):
        selected = config(evidence_mode="positive_only")
        with _absolute_deadline(1) as deadline:
            pass
        with self.assertRaisesRegex(ValueError, "deadline is invalid"):
            GitHubRestClient(selected, credential_resolver=lambda ref: "fixture-secret", deadline=deadline)

    def test_deadline_restores_handler_and_timer_after_success_and_failure(self):
        original = signal.getsignal(signal.SIGALRM)
        def previous_handler(signum, frame):
            self.fail("unrelated alarm handler ran")
        signal.signal(signal.SIGALRM, previous_handler)
        try:
            for response in (Response({"workflow_runs": [], "total_count": 0}), Response(b"private", 401)):
                http = FixtureHTTPS([response])
                selected = config(evidence_mode="positive_only")
                adapter = GitHubPollingAdapter(selected, GitHubRestClient(
                    selected, credential_resolver=lambda ref: "fixture-secret", connection_factory=http))
                anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
                adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
                self.assertIs(signal.getsignal(signal.SIGALRM), previous_handler)
                self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
                self.assertTrue(response.closed)
                self.assertEqual(http.closes, 1)
        finally:
            signal.signal(signal.SIGALRM, original)

    def test_existing_alarm_and_non_main_thread_fail_before_credentials_or_network(self):
        credentials = []
        http = FixtureHTTPS([])
        selected = config(evidence_mode="positive_only")
        def observe():
            adapter = GitHubPollingAdapter(selected, GitHubRestClient(
                selected, credential_resolver=lambda ref: credentials.append(ref), connection_factory=http))
            anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
            return adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))

        original_handler = signal.getsignal(signal.SIGALRM)
        original_timer = signal.getitimer(signal.ITIMER_REAL)
        self.assertEqual(original_timer, (0.0, 0.0))
        signal.setitimer(signal.ITIMER_REAL, 60, 7)
        try:
            before = signal.getitimer(signal.ITIMER_REAL)
            result = observe()
            after = signal.getitimer(signal.ITIMER_REAL)
            self.assertEqual(result.code, "GITHUB_SOURCE_UNAVAILABLE")
            self.assertIs(signal.getsignal(signal.SIGALRM), original_handler)
            self.assertEqual(after[1], 7)
            self.assertLessEqual(after[0], before[0])
            self.assertGreater(after[0], before[0] - 1)
        finally:
            signal.setitimer(signal.ITIMER_REAL, *original_timer)
        results = []
        thread = threading.Thread(target=lambda: results.append(observe()))
        thread.start()
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results[0].code, "GITHUB_SOURCE_UNAVAILABLE")
        self.assertEqual(credentials, [])
        self.assertEqual(http.requests, [])
        self.assertEqual(http.origins, [])

    def test_header_trickle_stops_at_absolute_deadline_and_closes_resources(self):
        reader, writer = socket.socketpair()
        stop = threading.Event()
        old_handler = signal.getsignal(signal.SIGALRM)
        old_timer = signal.getitimer(signal.ITIMER_REAL)

        def send_headers():
            try:
                writer.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 39\r\nX-Slow: ")
                # Activity stays below the one-second socket inactivity limit,
                # while completing the headers takes two seconds.
                for _ in range(100):
                    if stop.wait(0.02):
                        return
                    writer.sendall(b"x")
                writer.sendall(b'\r\n\r\n{"workflow_runs": [], "total_count": 0}')
            except OSError:
                pass
            finally:
                writer.close()

        connections = []
        def connect(host, timeout):
            connection = HTTPConnection(host, timeout=timeout)
            reader.settimeout(timeout)
            connection.sock = reader
            connections.append(connection)
            return connection

        thread = threading.Thread(target=send_headers)
        thread.start()
        started = time.monotonic()
        try:
            selected = config(evidence_mode="positive_only", poll_timeout_seconds=1)
            adapter = GitHubPollingAdapter(selected, GitHubRestClient(
                selected, credential_resolver=lambda ref: "fixture-secret", connection_factory=connect))
            anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
            result = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
            elapsed = time.monotonic() - started
            self.assertEqual(result.code, "GITHUB_POLL_BUDGET_EXHAUSTED")
            self.assertLess(elapsed, 1.6)
            self.assertEqual(reader.fileno(), -1)
            self.assertTrue(all(connection.sock is None for connection in connections))
            self.assertIs(signal.getsignal(signal.SIGALRM), old_handler)
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL), old_timer)
        finally:
            stop.set()
            reader.close()
            writer.close()
            thread.join(timeout=1)
        self.assertFalse(thread.is_alive())

    def test_positive_batch_requires_exact_head_repository_origin(self):
        for origin in (None, {}, {"id": 99, "full_name": "fork/project"},
                       {"id": 42, "full_name": "fork/project"},
                       {"id": True, "full_name": "example/project"}):
            for stage in ("list", "attempt"):
                with self.subTest(origin=origin, stage=stage):
                    trusted = payload(run_started_at=(NOW + timedelta(seconds=1)).isoformat())
                    untrusted = {**trusted, "head_repository": origin}
                    http = FixtureHTTPS([
                        Response({"workflow_runs": [untrusted if stage == "list" else trusted], "total_count": 1}),
                        Response(untrusted), Response({"jobs": [], "total_count": 0}),
                    ])
                    selected = config(evidence_mode="positive_only")
                    adapter = GitHubPollingAdapter(selected, GitHubRestClient(
                        selected, credential_resolver=lambda ref: "fixture-secret", connection_factory=http))
                    anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
                    result = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
                    self.assertNotIsInstance(result, PollBatch)
                    self.assertEqual(result.code, "GITHUB_RESPONSE_INVALID")

    def test_late_visible_positive_replays_in_fresh_process_with_one_receipt(self):
        selected = config(evidence_mode="positive_only")
        http = FixtureHTTPS([Response({"workflow_runs": [], "total_count": 0}), *terminal_responses()])
        adapter = GitHubPollingAdapter(selected, GitHubRestClient(
            selected, credential_resolver=lambda ref: "fixture-secret", connection_factory=http))
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            module = make_module(database)
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("wake_positive_restart"), spec,
                               ArmContext("restart", "restart", NOW, None, make_intent().resume, adapter))
            empty = adapter.observe(armed.anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
            self.assertIsInstance(module.ingest(empty.observations, empty.commit), Ingested)
            late = adapter.observe(armed.anchor, checkpoint=empty.commit, now=NOW + timedelta(seconds=5))
            first = module.ingest(late.observations, late.commit)
            self.assertIsInstance(first, Ingested)
            script = '''
import json, sys
from pathlib import Path
from datetime import timedelta
from codex_wake.github_client import GitHubRestClient
from codex_wake.github_polling import GitHubPollingAdapter
from codex_wake.signals import EvaluationLimits
from tests.test_github_client import FixtureHTTPS, terminal_responses
from tests.test_github_polling import config, NOW
from tests.test_signal_store import make_module
selected = config(evidence_mode="positive_only")
adapter = GitHubPollingAdapter(selected, GitHubRestClient(selected, credential_resolver=lambda ref: "fixture-secret", connection_factory=FixtureHTTPS(terminal_responses())))
module = make_module(Path(sys.argv[1]))
armed = module.load_armed_signal("wake_positive_restart")
checkpoint = module.source_checkpoint("github", "github-ci")
batch = adapter.observe(armed.anchor, checkpoint=checkpoint, now=NOW + timedelta(seconds=10))
ingested = module.ingest(batch.observations, batch.commit)
matched = module.evaluate(armed.wake_id, armed, NOW + timedelta(seconds=10), EvaluationLimits(20))
print(json.dumps({"duplicate": ingested.receipts[0].duplicate, "receipt": ingested.receipts[0].receipt_id, "match": matched.receipt.receipt_id, "order": batch.commit.checkpoint_order}))
'''
            result = subprocess.run([sys.executable, "-c", script, str(database)],
                                    capture_output=True, text=True, check=True, timeout=10)
            replay = json.loads(result.stdout)
            self.assertTrue(replay["duplicate"])
            self.assertEqual(replay["receipt"], first.receipts[0].receipt_id)
            self.assertEqual(replay["match"], first.receipts[0].receipt_id)
            self.assertEqual(replay["order"], 0)

    def test_missing_attempt_and_incomplete_jobs_preserve_journal_atomically(self):
        latest = payload(run_attempt=2)
        for final_response in (Response(b"private", 404),
                               Response({"jobs": [], "total_count": 1})):
            http = FixtureHTTPS([Response({"workflow_runs": [latest], "total_count": 1}),
                                Response(payload()), final_response])
            selected = config(evidence_mode="positive_only")
            adapter = GitHubPollingAdapter(selected, GitHubRestClient(
                selected, credential_resolver=lambda ref: "fixture-secret", connection_factory=http))
            with tempfile.TemporaryDirectory() as tmp:
                module = make_module(Path(tmp) / "signals.sqlite3")
                spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
                armed = module.arm(WakeId("wake_atomic"), spec,
                                   ArmContext("atomic", "atomic", NOW, None, make_intent().resume, adapter))
                result = adapter.poll_into(module, armed.anchor, checkpoints=module, now=NOW + timedelta(seconds=5))
                self.assertNotIsInstance(result, Ingested)
                self.assertIsNone(module.source_checkpoint("github", "github-ci"))

    def test_old_proof_never_matches_even_when_updated_at_is_post_anchor(self):
        run = payload(run_started_at=(NOW - timedelta(days=1)).isoformat())
        http = FixtureHTTPS([Response({"workflow_runs": [run], "total_count": 1}),
                            Response(run), Response({"jobs": [], "total_count": 0})])
        selected = config(evidence_mode="positive_only")
        adapter = GitHubPollingAdapter(selected, GitHubRestClient(
            selected, credential_resolver=lambda ref: "fixture-secret", connection_factory=http))
        anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
        batch = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.commit.checkpoint_order, 0)

    def test_total_byte_budget_covers_list_attempt_and_jobs(self):
        run = payload()
        response = {"workflow_runs": [run], "total_count": 1, "ignored": "x" * 600}
        http = FixtureHTTPS([Response(response), Response(run), Response({"jobs": [], "total_count": 0})])
        selected = config(evidence_mode="positive_only", max_poll_bytes=1024)
        adapter = GitHubPollingAdapter(selected, GitHubRestClient(
            selected, credential_resolver=lambda ref: "fixture-secret", connection_factory=http))
        anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
        result = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
        self.assertEqual(result.code, "GITHUB_POLL_BUDGET_EXHAUSTED")

    def test_failures_are_sanitized_and_do_not_emit_partial_evidence(self):
        cases = (
            (Response(b"private-token", 401), "GITHUB_AUTH_UNAVAILABLE"),
            (Response(b"private-token", 429), "GITHUB_RATE_LIMITED"),
            (Response(b"private-token", 302, {"Location": "https://evil.example/private-token"}), "GITHUB_SOURCE_UNAVAILABLE"),
            (Response(b"not json private-token"), "GITHUB_RESPONSE_INVALID"),
            (Response(b'{"workflow_runs": [], "total_count": 0, "total_count": 1}'), "GITHUB_RESPONSE_INVALID"),
            (Response(b"x" * 1025), "GITHUB_POLL_BUDGET_EXHAUSTED"),
        )
        for response, code in cases:
            with self.subTest(code=code):
                http = FixtureHTTPS([response])
                selected = config(evidence_mode="positive_only", max_response_bytes=1024)
                adapter = GitHubPollingAdapter(selected, GitHubRestClient(
                    selected, credential_resolver=lambda ref: "private-token", connection_factory=http))
                anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
                result = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
                self.assertEqual(result.code, code)
                self.assertNotIn("private-token", repr(result))
                self.assertEqual(len(http.requests), 1)

    def test_terminal_jobs_prove_old_started_run_after_anchor_without_updated_at(self):
        run = payload()
        http = FixtureHTTPS([Response({"workflow_runs": [run], "total_count": 1}), Response(run),
                            Response({"jobs": [{"id": 8, "run_id": 101, "run_attempt": 1,
                                                "status": "completed", "completed_at": (NOW + timedelta(seconds=1)).isoformat()}],
                                      "total_count": 1})])
        selected = config(evidence_mode="positive_only")
        client = GitHubRestClient(selected, credential_resolver=lambda ref: "fixture-secret", connection_factory=http)
        adapter = GitHubPollingAdapter(selected, client)
        anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
        batch = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
        self.assertIsInstance(batch, PollBatch)
        self.assertEqual(len(batch.observations), 1)
        self.assertEqual(batch.observations[0].occurred_at, NOW + timedelta(seconds=1))
        self.assertEqual(batch.commit.checkpoint_order, 0)
        self.assertEqual([row[0] for row in http.requests], ["GET"] * 3)
        self.assertTrue(all(host == "api.github.com" for host, _ in http.origins))
        self.assertNotIn("created", http.requests[0][1])
        self.assertNotIn("fixture-secret", repr(batch))
