from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import threading
import unittest
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from codex_wake import cli
from codex_wake.event_wake import EventWake
from codex_wake.daemon import default_signal_runners, poll_once
from codex_wake.http_json_signals import (
    HTTPJSONDocument,
    HTTPJSONClient,
    HTTPJSONSignalAdapter,
    HTTPJSONSignalRunner,
)
from codex_wake.http_json_source_config import HTTPJSONSourceConfig, HTTPJSONSourceStore
from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher, signal_journal_path
from codex_wake.signal_store import SQLiteSignalModule
from codex_wake.signal_support import signal_readiness
from codex_wake.signals import EvaluationLimits, Registration, Resume, WakeIntent


NOW = datetime(2026, 9, 27, 18, 0, tzinfo=UTC)


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1/escaped")
            self.end_headers()
            return
        if self.path == "/big":
            body = json.dumps({"value": "x" * 2000}).encode()
        else:
            body = json.dumps({"id": "job-42", "status": "succeeded"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


def config(**changes) -> HTTPJSONSourceConfig:
    values = {
        "source_instance": "example-job",
        "url": "http://127.0.0.1:8080/v1/jobs/job-42/status",
        "state_pointer": "/status",
        "event_id_pointer": "/id",
        "terminal_values": frozenset({"succeeded", "failed", "cancelled"}),
        "selectors": (("/kind", "response"),),
        "completed_at_pointer": "/completedAt",
    }
    values.update(changes)
    return HTTPJSONSourceConfig(**values)


class ScriptedClient:
    def __init__(self, *documents: HTTPJSONDocument | Exception) -> None:
        self.documents = list(documents)
        self.calls = 0

    def read(self) -> HTTPJSONDocument:
        self.calls += 1
        item = self.documents[min(self.calls - 1, len(self.documents) - 1)]
        if isinstance(item, Exception):
            raise item
        return item


class HTTPJSONSignalTests(unittest.TestCase):
    def runtime(self, root: Path) -> SQLiteSignalModule:
        return SQLiteSignalModule(
            signal_journal_path(root),
            record_publisher=WakeRecordPublisher(
                root,
                ManagedReaderCapability(root, "reader", 1, frozenset({1, 2}), True),
            ),
        )

    def arm(self, root: Path, adapter: HTTPJSONSignalAdapter, wake_id: str = "wake_http"):
        runtime = self.runtime(root)
        result = EventWake(
            runtime,
            adapters=(adapter,),
            clock=lambda: NOW,
            id_factory=lambda: wake_id,
        ).register(
            WakeIntent(
                adapter.request(),
                Resume(
                    "Inspect the authoritative job result.",
                    root,
                    MappingProxyType({"transport": "tmux", "tmux_socket": "/tmp/tmux", "pane": "%1"}),
                ),
            ),
            idempotency_key=f"http-json:{wake_id}",
        )
        self.assertIsInstance(result, Registration)
        armed = runtime.load_armed_signal(result.wake_id)
        self.assertIsNotNone(armed)
        return runtime, armed

    def test_auracall_status_envelope_is_an_ordinary_compatible_document(self) -> None:
        source = config(url="http://127.0.0.1:8080/v1/runs/resp_123/status")
        client = ScriptedClient(HTTPJSONDocument({
            "object": "auracall_run_status",
            "id": "resp_123",
            "kind": "response",
            "status": "succeeded",
            "completedAt": "2026-09-27T18:00:00Z",
            "artifacts": [{"private": "not-ingested"}],
        }))
        adapter = HTTPJSONSignalAdapter(source, client)

        document = adapter.observe(NOW)

        self.assertEqual(document.event_id, "resp_123")
        self.assertEqual(document.state, "succeeded")
        self.assertEqual(document.occurred_at, NOW)
        self.assertNotIn("artifacts", document.attributes)
        self.assertEqual(document.attributes, {"state": "succeeded", "event_id": "resp_123"})

    def test_nonterminal_or_selector_mismatch_yields_no_observation(self) -> None:
        source = config()
        running = HTTPJSONSignalAdapter(
            source,
            ScriptedClient(HTTPJSONDocument({"id": "job-42", "kind": "response", "status": "running"})),
        )
        wrong_kind = HTTPJSONSignalAdapter(
            source,
            ScriptedClient(HTTPJSONDocument({"id": "job-42", "kind": "media", "status": "succeeded"})),
        )

        self.assertIsNone(running.observe(NOW))
        self.assertIsNone(wrong_kind.observe(NOW))

    def test_repeated_poll_and_fresh_runner_converge_to_one_occurrence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            source = config(selectors=())
            terminal = HTTPJSONDocument({
                "id": "job-42", "status": "succeeded",
                "completedAt": "2026-09-27T18:00:00Z",
            })
            adapter = HTTPJSONSignalAdapter(source, ScriptedClient(terminal))
            runtime, armed = self.arm(root, adapter)

            first = HTTPJSONSignalRunner((adapter,), armed_signals=(armed,))
            first_result = first.reconcile(runtime, NOW, EvaluationLimits(100))
            second = HTTPJSONSignalRunner(
                (HTTPJSONSignalAdapter(source, ScriptedClient(terminal)),),
                armed_signals=(armed,),
            )
            second_result = second.reconcile(
                runtime, datetime(2026, 9, 27, 18, 0, 5, tzinfo=UTC), EvaluationLimits(100)
            )
            match = runtime.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(100))

            self.assertEqual((first_result.observed, first_result.degraded), (1, 0))
            self.assertEqual((second_result.observed, second_result.degraded), (0, 0))
            self.assertEqual(match.outcome, "matched")
            self.assertEqual(match.receipt.attributes, {"state": "succeeded", "event_id": "job-42"})

    def test_closed_registry_reconstructs_source_and_daemon_fires_without_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            source = config(selectors=())
            HTTPJSONSourceStore(root).configure(source)
            registration_adapter = HTTPJSONSignalAdapter(
                source,
                ScriptedClient(HTTPJSONDocument({"id": "job-42", "status": "running"})),
            )
            runtime, _armed = self.arm(root, registration_adapter)
            terminal = HTTPJSONDocument({
                "id": "job-42", "status": "succeeded",
                "completedAt": "2026-09-27T18:00:00Z",
            })
            runners = default_signal_runners(
                root,
                runtime,
                http_json_client_factory=lambda _source: ScriptedClient(terminal),
            )

            result = poll_once(
                root,
                now=NOW,
                dispatch=False,
                signal_runtime=runtime,
                signal_runners=runners,
            )

            self.assertEqual((result.fired, result.dispatched), (1, 0))
            self.assertTrue((root / "firing" / "wake_http.json").is_file())

    def test_transport_or_json_contract_failure_is_degraded_without_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            source = config(selectors=())
            adapter = HTTPJSONSignalAdapter(source, ScriptedClient(ValueError("unsafe response")))
            runtime, armed = self.arm(root, adapter)

            result = HTTPJSONSignalRunner((adapter,), armed_signals=(armed,)).reconcile(
                runtime, NOW, EvaluationLimits(100)
            )

            self.assertEqual((result.observed, result.degraded), (0, 1))
            self.assertEqual(result.instances[0].health_code, "HTTP_JSON_SOURCE_UNAVAILABLE")

    def test_production_client_reads_json_and_rejects_redirects_and_oversized_bodies(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            origin = f"http://127.0.0.1:{server.server_port}"
            document = HTTPJSONClient(config(url=origin + "/ok", selectors=())).read()
            self.assertEqual(document.payload["status"], "succeeded")
            with self.assertRaises(ValueError):
                HTTPJSONClient(config(url=origin + "/redirect", selectors=())).read()
            with self.assertRaises(ValueError):
                HTTPJSONClient(config(url=origin + "/big", selectors=(), max_response_bytes=1024)).read()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class HTTPJSONSourceStoreTests(unittest.TestCase):
    def test_store_is_owner_only_sorted_and_supports_remove(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = HTTPJSONSourceStore(Path(tmp) / "wake")
            second = config(source_instance="z-source")
            first = config(source_instance="a-source", url="http://localhost:8080/jobs/7")
            store.configure(second)
            store.configure(first)

            self.assertEqual([item.source_instance for item in store.sources()], ["a-source", "z-source"])
            self.assertEqual(store.path.stat().st_mode & 0o777, 0o600)
            self.assertTrue(store.remove("a-source"))
            self.assertFalse(store.remove("missing"))
            self.assertEqual([item.source_instance for item in store.sources()], ["z-source"])

    def test_configuration_rejects_unsafe_or_executable_shapes(self) -> None:
        invalid = (
            {"url": "file:///tmp/status.json"},
            {"url": "http://user:secret@127.0.0.1/status"},
            {"url": "http://127.0.0.1/status?token=secret"},
            {"state_pointer": "$.status"},
            {"event_id_pointer": "/" + "x" * 300},
            {"terminal_values": frozenset()},
        )
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                config(**changes)

    def test_readiness_lists_source_separately_without_polling_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            store = HTTPJSONSourceStore(root)
            store.configure(config(credential_ref=None))

            readiness = signal_readiness(root, http_json_store=store, now=NOW)

            self.assertEqual(readiness["status"], "ready")
            self.assertEqual(len(readiness["sources"]), 1)
            source = readiness["sources"][0]
            self.assertEqual((source["source"], source["source_instance"]), ("http-json", "example-job"))
            self.assertEqual(source["active_arms"], 0)
            self.assertEqual(source["support"]["credential_capability"]["status"], "not_applicable")


class HTTPJSONCliTests(unittest.TestCase):
    def run_cli(self, root: Path, *argv: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        environment = {**os.environ, "TMUX_PANE": "%11", "TMUX": "/tmp/tmux/default,1,0"}
        with patch.dict(os.environ, environment, clear=False):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(["--wake-root", str(root), *argv])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_configure_show_arm_and_remove_are_generic_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            configure = self.run_cli(
                root,
                "http-json", "source", "configure",
                "--source", "auracall-run",
                "--url", "http://127.0.0.1:8080/v1/runs/resp_123/status",
                "--state-pointer", "/status",
                "--event-id-pointer", "/id",
                "--completed-at-pointer", "/completedAt",
                "--terminal-value", "succeeded",
                "--terminal-value", "failed",
                "--selector", "/kind=response",
                "--credential-ref", "AURACALL_API_TOKEN",
                "--enabled",
            )
            self.assertEqual(configure[0], 0, configure[2])

            shown = self.run_cli(root, "http-json", "source", "show", "auracall-run", "--json")
            self.assertEqual(shown[0], 0, shown[2])
            summary = json.loads(shown[1])
            self.assertEqual(summary["state_pointer"], "/status")
            self.assertEqual(summary["terminal_values"], ["failed", "succeeded"])
            self.assertTrue(summary["credential_configured"])
            self.assertNotIn("AURACALL_API_TOKEN", shown[1])

            publisher = WakeRecordPublisher(
                root,
                ManagedReaderCapability(root, "reader", 1, frozenset({1, 2}), True),
            )
            with patch(
                "codex_wake.signal_records.WakeRecordPublisher.for_managed_reader",
                return_value=publisher,
            ):
                armed = self.run_cli(
                    root,
                    "http-json", "completed", "--source", "auracall-run",
                    "--idempotency-key", "run-123",
                )
            self.assertEqual(armed[0], 0, armed[2])
            wake_id = armed[1].split()[0]
            record = json.loads((root / "pending" / f"{wake_id}.json").read_text())
            self.assertEqual(record["predicate"]["source"], "http-json")
            self.assertEqual(record["target"]["transport"], "tmux")
            self.assertIn("Verify the authoritative status", record["prompt"])
            self.assertNotIn("AURACALL_API_TOKEN", json.dumps(record))

            with patch(
                "codex_wake.signal_records.WakeRecordPublisher.for_managed_reader",
                return_value=publisher,
            ):
                app_armed = self.run_cli(
                    root,
                    "http-json", "completed", "--source", "auracall-run",
                    "--idempotency-key", "run-123-app",
                    "--app-server-thread-id", "019abcde-1234-7000-8000-123456789abc",
                )
            self.assertEqual(app_armed[0], 0, app_armed[2])
            app_wake_id = app_armed[1].split()[0]
            app_record = json.loads((root / "pending" / f"{app_wake_id}.json").read_text())
            self.assertEqual(app_record["target"]["transport"], "app-server")
            self.assertNotIn("ack", app_record)
            self.assertNotIn("visible", app_record)

            blocked_remove = self.run_cli(root, "http-json", "source", "remove", "auracall-run")
            self.assertEqual(blocked_remove[0], 2)
            self.assertIn("active wakes", blocked_remove[2])
            self.assertEqual(self.run_cli(root, "cancel", wake_id)[0], 0)
            self.assertEqual(self.run_cli(root, "cancel", app_wake_id)[0], 0)
            removed = self.run_cli(root, "http-json", "source", "remove", "auracall-run")
            self.assertEqual(removed[0], 0, removed[2])
            self.assertEqual(HTTPJSONSourceStore(root).sources(), ())


if __name__ == "__main__":
    unittest.main()
