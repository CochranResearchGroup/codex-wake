from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.app_server import discover_local_thread_candidates, dispatch_app_server_record, read_app_server_thread_status
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
        return {"thread": {"id": thread_id, "status": {"type": "idle"}}}

    def read_thread(self, thread_id: str, include_turns: bool = False) -> dict:
        self.calls.append(("thread/read", {"thread_id": thread_id, "include_turns": include_turns}))
        return {
            "thread": {
                "id": thread_id,
                "status": {"type": "idle"},
                "cwd": "/tmp/repo",
                "sessionId": "session_123",
            }
        }

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
            self.assertEqual(data["events"][-2]["type"], "app_server_preflight")
            self.assertEqual(data["events"][-3]["type"], "dispatch_attempt")
            self.assertEqual(data["app_server_preflight"]["status"], {"type": "idle"})
            self.assertEqual(data["dispatch_result"], {"thread_id": "thread_abc", "turn_id": "turn_123"})
            self.assertEqual(data["events"][-1]["turn_id"], "turn_123")

    def test_dispatch_app_server_record_requeues_active_thread_without_starting_turn(self) -> None:
        class ActiveClient(FakeAppServerClient):
            def resume_thread(self, thread_id: str, cwd: str | None = None) -> dict:
                self.calls.append(("thread/resume", {"thread_id": thread_id, "cwd": cwd}))
                return {"thread": {"id": thread_id, "status": {"type": "active", "activeFlags": ["waitingOnApproval"]}}}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_record(root, Path(tmp))
            client = ActiveClient()

            result = dispatch_app_server_record(root, found, client=client, now=datetime(2026, 5, 18, 21, 0, tzinfo=UTC))

            self.assertEqual(result.status, "requeued")
            self.assertEqual([call[0] for call in client.calls], ["initialize", "thread/resume"])
            data = json.loads((root / "pending" / "wake_app.json").read_text())
            self.assertEqual(data["status"], "pending")
            self.assertEqual(data["attempts"], 1)
            self.assertEqual(data["next_attempt_at"], "2026-05-18T21:01:00Z")
            self.assertEqual(data["events"][-1]["type"], "requeued")
            self.assertFalse((root / "firing" / "wake_app.json").exists())

    def test_read_app_server_thread_status_summarizes_thread_status(self) -> None:
        client = FakeAppServerClient()

        summary = read_app_server_thread_status("thread_abc", client=client)

        self.assertEqual([call[0] for call in client.calls], ["initialize", "thread/read"])
        self.assertEqual(
            summary,
            {
                "thread_id": "thread_abc",
                "status": {"type": "idle"},
                "status_type": "idle",
                "cwd": "/tmp/repo",
                "sessionId": "session_123",
            },
        )

    def test_read_app_server_thread_status_can_resume_for_status(self) -> None:
        client = FakeAppServerClient()

        summary = read_app_server_thread_status("thread_abc", client=client, resume=True, cwd="/tmp/repo")

        self.assertEqual([call[0] for call in client.calls], ["initialize", "thread/resume"])
        self.assertEqual(summary["thread_id"], "thread_abc")
        self.assertEqual(summary["status_type"], "idle")

    def test_discover_local_thread_candidates_reads_session_meta_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex"
            session_dir = codex_home / "sessions" / "2026" / "05" / "21"
            session_dir.mkdir(parents=True)
            rollout = session_dir / "rollout-2026-05-21T01-00-00-thread_abc.jsonl"
            rollout.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "timestamp": "2026-05-21T01:00:00.000Z",
                                "type": "session_meta",
                                "payload": {
                                    "id": "thread_abc",
                                    "timestamp": "2026-05-21T01:00:00.000Z",
                                    "cwd": "/tmp/repo",
                                    "originator": "codex-tui",
                                    "cli_version": "0.131.0",
                                    "model_provider": "openai",
                                    "agent_nickname": "Ada",
                                    "agent_role": "worker",
                                },
                            }
                        ),
                        json.dumps({"type": "response_item", "payload": {"private": "not surfaced"}}),
                    ]
                ),
                encoding="utf-8",
            )

            candidates = discover_local_thread_candidates(codex_home=codex_home, limit=10)

            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].thread_id, "thread_abc")
            self.assertEqual(candidates[0].cwd, "/tmp/repo")
            self.assertEqual(candidates[0].originator, "codex-tui")
            self.assertEqual(candidates[0].agent_nickname, "Ada")
            self.assertEqual(candidates[0].agent_role, "worker")

    def test_discover_local_thread_candidates_can_filter_by_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex"
            session_dir = codex_home / "sessions" / "2026" / "05" / "21"
            session_dir.mkdir(parents=True)
            for thread_id, cwd in (("thread_keep", str(Path(tmp).resolve())), ("thread_skip", "/other")):
                (session_dir / f"rollout-{thread_id}.jsonl").write_text(
                    json.dumps({"type": "session_meta", "payload": {"id": thread_id, "cwd": cwd}}),
                    encoding="utf-8",
                )

            candidates = discover_local_thread_candidates(codex_home=codex_home, limit=10, cwd=Path(tmp))

            self.assertEqual([candidate.thread_id for candidate in candidates], ["thread_keep"])

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
