from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.app_server import dispatch_app_server_record
from codex_wake.injector import canonical_prompt, dispatch_firing_record
from codex_wake.records import WakePath, build_record, write_record


class FakeAppServerClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def initialize(self) -> dict:
        self.calls.append(("initialize", None))
        return {"userAgent": "fake", "codexHome": "/tmp/codex", "platformFamily": "unix", "platformOs": "linux"}

    def resume_thread(self, thread_id: str, cwd: str | None = None) -> dict:
        self.calls.append(("thread/resume", {"thread_id": thread_id, "cwd": cwd}))
        return {"thread": {"id": thread_id}}

    def start_turn(self, thread_id: str, prompt: str, cwd: str | None = None) -> dict:
        self.calls.append(("turn/start", {"thread_id": thread_id, "prompt": prompt, "cwd": cwd}))
        return {"turn": {"id": "turn_123"}}

    def close(self) -> None:
        self.calls.append(("close", None))


class AppServerTests(unittest.TestCase):
    def make_record(self, root: Path, cwd: Path) -> WakePath:
        record = build_record(
            predicate={"type": "not_before", "due_at": "2026-05-18T21:15:00Z"},
            prompt="full prompt must not be sent",
            cwd=cwd,
            target={"transport": "app-server", "endpoint": "stdio://", "thread_id": "thread_abc"},
            now=datetime(2026, 5, 18, 20, 30, tzinfo=UTC),
        )
        record["id"] = "wake_app"
        record["status"] = "firing"
        path = write_record(root, record)
        return WakePath(path=path, record=record)

    def test_dispatch_app_server_record_starts_turn_with_canonical_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_record(root, Path(tmp))
            client = FakeAppServerClient()

            result = dispatch_app_server_record(root, found, client=client, now=datetime(2026, 5, 18, 21, 0, tzinfo=UTC))

            self.assertEqual(result.status, "submitted")
            self.assertEqual([call[0] for call in client.calls], ["initialize", "thread/resume", "turn/start"])
            turn_call = client.calls[-1][1]
            self.assertEqual(turn_call["prompt"], canonical_prompt("wake_app"))
            self.assertNotIn("full prompt", turn_call["prompt"])
            data = json.loads((root / "submitted" / "wake_app.json").read_text())
            self.assertEqual(data["status"], "submitted")
            self.assertEqual(data["events"][-1]["type"], "ack_observed")

    def test_unsupported_endpoint_fails_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_record(root, Path(tmp))
            found.record["target"]["endpoint"] = "ws://127.0.0.1:4500"
            write_record(root, found.record)

            result = dispatch_app_server_record(root, found, client=FakeAppServerClient())

            self.assertEqual(result.status, "failed")
            data = json.loads((root / "failed" / "wake_app.json").read_text())
            self.assertIn("only app-server stdio:// transport is implemented", data["last_error"])

    def test_generic_dispatcher_routes_app_server_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_record(root, Path(tmp))
            # Exercise only target routing and validation failure path; full app-server dispatch is
            # covered above with an injected client.
            found.record["target"]["endpoint"] = "ws://127.0.0.1:4500"
            write_record(root, found.record)

            result = dispatch_firing_record(root, found)

            self.assertEqual(result.status, "failed")


if __name__ == "__main__":
    unittest.main()
