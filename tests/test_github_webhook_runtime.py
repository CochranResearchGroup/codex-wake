from __future__ import annotations

import hashlib
import hmac
import json
import socket
import tempfile
import threading
import time
import unittest
from datetime import timedelta
from pathlib import Path

from codex_wake.github_client import GitHubRestClient
from codex_wake.github_polling import GitHubPollingAdapter
from codex_wake.github_webhook_runtime import GitHubWebhookRuntime
from codex_wake.github_webhooks import WebhookConfig
from codex_wake.signals import ArmContext, EvaluationLimits, Matched, WakeId
from codex_wake.webhook_http import WebhookHTTPConfig
from tests.test_github_polling import NOW, FixtureClient, config, run
from tests.test_github_client import FixtureHTTPS, Response, payload as rest_payload
from tests.test_signal_store import make_module
from tests.test_signals import make_intent


SECRET = b"fixture-only-webhook-key-32-bytes!"


def signed_body(value=None):
    value = value or run()
    body = json.dumps({
        "action": "completed",
        "repository": {"id": value.repository_id, "full_name": value.repository},
        "workflow_run": {
            "id": value.run_id, "run_attempt": value.run_attempt,
            "workflow_id": value.workflow_id, "head_branch": "main",
            "head_sha": value.head_sha, "status": value.status,
            "conclusion": value.conclusion, "updated_at": value.completed_at.isoformat(),
        },
    }).encode()
    signature = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return body, signature


def exchange(address, body, signature, delivery="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"):
    request = (
        b"POST /github/webhook HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(body)}\r\n".encode()
        + f"X-Hub-Signature-256: sha256={signature}\r\n".encode()
        + b"X-GitHub-Event: workflow_run\r\n"
        + f"X-GitHub-Delivery: {delivery}\r\n\r\n".encode()
        + body
    )
    with socket.create_connection(address, timeout=2) as connection:
        connection.sendall(request)
        response = bytearray()
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
    status = int(bytes(response).split(b" ", 2)[1])
    code = json.loads(bytes(response).split(b"\r\n\r\n", 1)[1])["code"]
    return status, code


class GitHubWebhookRuntimeTests(unittest.TestCase):
    def test_rotation_callbacks_cross_the_runtime_boundary_after_durable_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = make_module(Path(tmp) / "signals.sqlite3")
            adapter = GitHubPollingAdapter(config(), FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("runtime-rotation"), spec,
                               ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            admissions, commits = [], []
            runtime = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1), adapter=adapter,
                module=module, checkpoints=module, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",), secret_generations=(8,)),
                resolve_secret=lambda ref: SECRET,
                attempt_client_factory=lambda deadline: FixtureClient([run()]),
                operation_timeout=1, now=lambda: NOW + timedelta(seconds=2),
                admitted_generations=lambda now: admissions.append(now) or (8,),
                committed_delivery=lambda generation, receipt: commits.append((generation, receipt)),
            )
            body, signature = signed_body()
            result = []

            def deliver():
                result.append(exchange(runtime.address, body, signature))
                runtime.shutdown()

            client = threading.Thread(target=deliver)
            client.start()
            runtime.serve()
            client.join(2)
            self.assertFalse(client.is_alive())
            self.assertEqual(result, [(200, "COMMITTED")])
            self.assertEqual(admissions, [NOW + timedelta(seconds=2)])
            self.assertEqual(len(commits), 1)
            self.assertEqual(commits[0][0], 8)
            self.assertIsNotNone(module.source_checkpoint("github", "github-ci"))

    def test_signed_loopback_delivery_commits_before_committed_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = make_module(Path(tmp) / "signals.sqlite3")
            adapter = GitHubPollingAdapter(config(), FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("runtime-hook"), spec,
                               ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            clients = []

            def attempt_client(deadline):
                client = FixtureClient([run()])
                clients.append((deadline, client))
                return client

            runtime = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1), adapter=adapter,
                module=module, checkpoints=module, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: SECRET, attempt_client_factory=attempt_client,
                operation_timeout=1, now=lambda: NOW + timedelta(seconds=2),
            )
            body, signature = signed_body()
            result = []

            def deliver():
                result.append(exchange(runtime.address, body, signature))
                runtime.shutdown()

            client = threading.Thread(target=deliver)
            client.start()
            runtime.serve()
            client.join(2)
            self.assertFalse(client.is_alive())
            self.assertEqual(result, [(200, "COMMITTED")])
            self.assertEqual(len(clients), 1)
            matched = module.evaluate(armed.wake_id, armed, NOW + timedelta(seconds=2), EvaluationLimits(1))
            self.assertIsInstance(matched, Matched)

    def test_replayed_delivery_ids_converge_to_one_durable_occurrence(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = make_module(Path(tmp) / "signals.sqlite3")
            adapter = GitHubPollingAdapter(config(), FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("runtime-replay"), spec,
                               ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            clients = []
            def attempt_client(deadline):
                client = FixtureClient([run()])
                clients.append(client)
                return client
            runtime = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1), adapter=adapter,
                module=module, checkpoints=module, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: SECRET, attempt_client_factory=attempt_client,
                operation_timeout=1, now=lambda: NOW + timedelta(seconds=2),
            )
            body, signature = signed_body()
            result = []
            def deliver():
                result.append(exchange(runtime.address, body, signature))
                result.append(exchange(runtime.address, body, signature))
                result.append(exchange(runtime.address, body, signature,
                                       "11111111-2222-3333-4444-555555555555"))
                runtime.shutdown()
            client = threading.Thread(target=deliver)
            client.start()
            runtime.serve()
            client.join(2)
            self.assertFalse(client.is_alive())
            self.assertEqual(result, [(200, "COMMITTED"), (200, "DUPLICATE"), (200, "DUPLICATE")])
            self.assertEqual(len(clients), 3)
            matched = module.evaluate(armed.wake_id, armed, NOW + timedelta(seconds=2), EvaluationLimits(1))
            self.assertIsInstance(matched, Matched)

    def test_provider_timeout_runs_on_main_thread_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = make_module(Path(tmp) / "signals.sqlite3")
            adapter = GitHubPollingAdapter(config(), FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("runtime-timeout"), spec,
                               ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            factory_threads = []
            class SlowClient:
                def get_run_attempt(self, *args):
                    time.sleep(1)
            def attempt_client(deadline):
                factory_threads.append(threading.current_thread())
                return SlowClient() if len(factory_threads) == 1 else FixtureClient([run()])
            runtime = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=.3, shutdown_timeout=.2), adapter=adapter,
                module=module, checkpoints=module, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: SECRET, attempt_client_factory=attempt_client,
                operation_timeout=.05, now=lambda: NOW + timedelta(seconds=2),
            )
            body, signature = signed_body()
            result = []
            def deliver():
                result.append(exchange(runtime.address, body, signature))
                result.append(exchange(runtime.address, body, signature,
                                       "11111111-2222-3333-4444-555555555555"))
                runtime.shutdown()
            client = threading.Thread(target=deliver)
            client.start()
            started = time.monotonic()
            runtime.serve()
            elapsed = time.monotonic() - started
            client.join(2)
            self.assertFalse(client.is_alive())
            self.assertLess(elapsed, .6)
            self.assertEqual(result, [(503, "VERIFICATION_UNAVAILABLE"), (200, "COMMITTED")])
            self.assertEqual(factory_threads, [threading.main_thread(), threading.main_thread()])
            self.assertIsNotNone(module.source_checkpoint("github", "github-ci"))

    def test_poll_first_and_restart_both_preserve_the_durable_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            module = make_module(database)
            adapter = GitHubPollingAdapter(config(), FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("runtime-poll-first"), spec,
                               ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            observation = adapter.normalize_verified_attempt(run())
            checkpoint = adapter.checkpoint_for_anchor(armed.anchor)
            self.assertFalse(module.ingest((observation,), checkpoint).receipts[0].duplicate)
            factories = []
            def attempt_client(deadline):
                factories.append(deadline)
                return FixtureClient([run()])
            body, signature = signed_body()
            first = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1), adapter=adapter,
                module=module, checkpoints=module, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: SECRET, attempt_client_factory=attempt_client,
                operation_timeout=1, now=lambda: NOW + timedelta(seconds=2),
            )
            first_result = []
            def deliver_first():
                first_result.append(exchange(first.address, body, signature))
                first.shutdown()
            thread = threading.Thread(target=deliver_first)
            thread.start()
            first.serve()
            thread.join(2)
            self.assertEqual(first_result, [(200, "DUPLICATE")])

            reopened = make_module(database)
            second = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1), adapter=adapter,
                module=reopened, checkpoints=reopened, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: SECRET, attempt_client_factory=attempt_client,
                operation_timeout=1, now=lambda: NOW + timedelta(seconds=2),
            )
            second_result = []
            def deliver_second():
                second_result.append(exchange(second.address, body, signature,
                                              "11111111-2222-3333-4444-555555555555"))
                second.shutdown()
            thread = threading.Thread(target=deliver_second)
            thread.start()
            second.serve()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(second_result, [(200, "DUPLICATE")])
            self.assertEqual(len(factories), 2)

    def test_disconnect_after_admission_can_commit_before_shutdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = make_module(Path(tmp) / "signals.sqlite3")
            adapter = GitHubPollingAdapter(config(), FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("runtime-disconnect"), spec,
                               ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            entered, release = threading.Event(), threading.Event()
            class BlockingClient:
                def get_run_attempt(self, *args):
                    entered.set()
                    release.wait(1)
                    return run()
            runtime = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1), adapter=adapter,
                module=module, checkpoints=module, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: SECRET, attempt_client_factory=lambda deadline: BlockingClient(),
                operation_timeout=.5, now=lambda: NOW + timedelta(seconds=2),
            )
            body, signature = signed_body()
            request = (
                b"POST /github/webhook HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
                + f"Content-Length: {len(body)}\r\n".encode()
                + f"X-Hub-Signature-256: sha256={signature}\r\n".encode()
                + b"X-GitHub-Event: workflow_run\r\n"
                + b"X-GitHub-Delivery: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\r\n\r\n" + body
            )
            def disconnect():
                with socket.create_connection(runtime.address, timeout=2) as connection:
                    connection.sendall(request)
                self.assertTrue(entered.wait(1))
                release.set()
                runtime.shutdown()
            client = threading.Thread(target=disconnect)
            client.start()
            runtime.serve()
            client.join(2)
            self.assertFalse(client.is_alive())
            matched = module.evaluate(armed.wake_id, armed, NOW + timedelta(seconds=2), EvaluationLimits(1))
            self.assertIsInstance(matched, Matched)

    def test_secret_failure_returns_a_stable_response_without_provider_or_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = make_module(Path(tmp) / "signals.sqlite3")
            adapter = GitHubPollingAdapter(config(), FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("runtime-secret"), spec,
                               ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            factories = []
            runtime = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1), adapter=adapter,
                module=module, checkpoints=module, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: (_ for _ in ()).throw(OSError("secret unavailable")),
                attempt_client_factory=lambda deadline: factories.append(deadline),
                operation_timeout=1, now=lambda: NOW + timedelta(seconds=2),
            )
            body, signature = signed_body()
            result = []
            def deliver():
                result.append(exchange(runtime.address, body, signature))
                runtime.shutdown()
            client = threading.Thread(target=deliver)
            client.start()
            runtime.serve()
            client.join(2)
            self.assertFalse(client.is_alive())
            self.assertEqual(result, [(503, "SECRET_UNAVAILABLE")])
            self.assertEqual(factories, [])
            self.assertIsNone(module.source_checkpoint("github", "github-ci"))

    def test_bridge_rejects_a_second_delivery_without_queuing_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = make_module(Path(tmp) / "signals.sqlite3")
            adapter = GitHubPollingAdapter(config(), FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("runtime-bridge"), spec,
                               ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            entered, release = threading.Event(), threading.Event()
            clients = []
            class BlockingClient:
                def get_run_attempt(self, *args):
                    entered.set()
                    release.wait(1)
                    return run()
            def attempt_client(deadline):
                clients.append(deadline)
                return BlockingClient()
            runtime = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1, max_connections=2, max_workers=2),
                adapter=adapter, module=module, checkpoints=module, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: SECRET, attempt_client_factory=attempt_client,
                operation_timeout=.5, now=lambda: NOW + timedelta(seconds=2),
            )
            body, signature = signed_body()
            first, second = [], []
            def deliver_first():
                first.append(exchange(runtime.address, body, signature))
                runtime.shutdown()
            def deliver_second():
                self.assertTrue(entered.wait(1))
                second.append(exchange(runtime.address, body, signature,
                                       "11111111-2222-3333-4444-555555555555"))
                release.set()
            one = threading.Thread(target=deliver_first)
            two = threading.Thread(target=deliver_second)
            one.start()
            two.start()
            runtime.serve()
            one.join(2)
            two.join(2)
            self.assertFalse(one.is_alive())
            self.assertFalse(two.is_alive())
            self.assertEqual(first, [(200, "COMMITTED")])
            self.assertEqual(second, [(503, "BUSY")])
            self.assertEqual(len(clients), 1)

    def test_store_failure_never_acknowledges_a_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_module(Path(tmp) / "signals.sqlite3")
            adapter = GitHubPollingAdapter(config(), FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = store.arm(WakeId("runtime-store-failure"), spec,
                              ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            class FailingStore:
                def ingest(self, observations, checkpoint):
                    raise OSError("database unavailable")
            runtime = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1), adapter=adapter,
                module=FailingStore(), checkpoints=store, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: SECRET, attempt_client_factory=lambda deadline: FixtureClient([run()]),
                operation_timeout=1, now=lambda: NOW + timedelta(seconds=2),
            )
            body, signature = signed_body()
            result = []
            def deliver():
                result.append(exchange(runtime.address, body, signature))
                runtime.shutdown()
            client = threading.Thread(target=deliver)
            client.start()
            runtime.serve()
            client.join(2)
            self.assertFalse(client.is_alive())
            self.assertEqual(result, [(503, "COMMIT_FAILED")])
            self.assertIsNone(store.source_checkpoint("github", "github-ci"))

    def test_second_listener_owner_is_rejected_at_the_bound_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = make_module(Path(tmp) / "signals.sqlite3")
            adapter = GitHubPollingAdapter(config(), FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("runtime-owner"), spec,
                               ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            common = dict(
                adapter=adapter, module=module, checkpoints=module, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: SECRET, attempt_client_factory=lambda deadline: FixtureClient([run()]),
                operation_timeout=1, now=lambda: NOW + timedelta(seconds=2),
            )
            first = GitHubWebhookRuntime(WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1), **common)
            try:
                occupied = WebhookHTTPConfig(host=first.address[0], port=first.address[1],
                                             request_timeout=2, shutdown_timeout=1)
                with self.assertRaisesRegex(OSError, "listener unavailable"):
                    GitHubWebhookRuntime(occupied, **common)
            finally:
                first.shutdown()

    def test_runtime_uses_a_fresh_production_rest_client_under_its_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = make_module(Path(tmp) / "signals.sqlite3")
            selected = config(evidence_mode="positive_only")
            adapter = GitHubPollingAdapter(selected, FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("runtime-production-client"), spec,
                               ArmContext("runtime", "runtime", NOW, None, make_intent().resume, adapter))
            clients = []
            def attempt_client(deadline):
                http = FixtureHTTPS([Response(rest_payload()), Response({"jobs": [], "total_count": 0})])
                client = GitHubRestClient(selected, credential_resolver=lambda ref: "fixture-secret",
                                          connection_factory=http, deadline=deadline)
                clients.append((client, http))
                return client
            runtime = GitHubWebhookRuntime(
                WebhookHTTPConfig(request_timeout=2, shutdown_timeout=1), adapter=adapter,
                module=module, checkpoints=module, anchor=armed.anchor,
                webhook_config=WebhookConfig(secret_refs=("current",)),
                resolve_secret=lambda ref: SECRET, attempt_client_factory=attempt_client,
                operation_timeout=1, now=lambda: NOW + timedelta(seconds=2),
            )
            body, signature = signed_body()
            result = []
            def deliver():
                result.append(exchange(runtime.address, body, signature))
                runtime.shutdown()
            thread = threading.Thread(target=deliver)
            thread.start()
            runtime.serve()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(result, [(200, "COMMITTED")])
            self.assertEqual(len(clients), 1)
            self.assertEqual(len(clients[0][1].requests), 2)


if __name__ == "__main__":
    unittest.main()
