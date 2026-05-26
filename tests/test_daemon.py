from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from codex_wake.daemon import PollResult, format_poll_result, poll_once, poll_result_has_activity
from codex_wake.records import build_record, write_record


class DaemonTests(unittest.TestCase):
    def make_record(self, tmp: str, predicate: dict) -> dict:
        now = datetime(2026, 5, 18, 20, 30, tzinfo=UTC)
        record = build_record(
            predicate=predicate,
            prompt="continue",
            cwd=Path(tmp),
            target={"transport": "tmux", "tmux_socket": "/tmp/tmux/default", "pane": "%1"},
            now=now,
        )
        record["id"] = f"wake_{len(predicate)}"
        return record

    def test_not_before_moves_ready_record_to_firing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            record = self.make_record(tmp, {"type": "not_before", "due_at": "2026-05-18T21:15:00Z"})
            write_record(root, record)

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.fired, 1)
            self.assertFalse((root / "pending" / f"{record['id']}.json").exists())
            firing = root / "firing" / f"{record['id']}.json"
            self.assertTrue(firing.exists())
            data = json.loads(firing.read_text())
            self.assertEqual(data["status"], "firing")
            self.assertEqual(data["events"][-1]["type"], "predicate_matched")

    def test_not_before_leaves_future_record_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            record = self.make_record(tmp, {"type": "not_before", "due_at": "2026-05-18T21:15:00Z"})
            write_record(root, record)

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 14, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.pending, 1)
            self.assertTrue((root / "pending" / f"{record['id']}.json").exists())

    def test_pending_record_respects_future_next_attempt_backoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            record = self.make_record(tmp, {"type": "not_before", "due_at": "2026-05-18T21:15:00Z"})
            record["next_attempt_at"] = "2026-05-18T21:30:00Z"
            write_record(root, record)

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 16, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.pending, 1)
            self.assertEqual(result.fired, 0)
            self.assertTrue((root / "pending" / f"{record['id']}.json").exists())

    def test_file_exists_relative_to_record_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            event_path = Path(tmp) / ".codex" / "events" / "pytest.done"
            event_path.parent.mkdir(parents=True)
            event_path.write_text("", encoding="utf-8")
            record = self.make_record(tmp, {"type": "file_exists", "path": ".codex/events/pytest.done"})
            record["id"] = "wake_file"
            write_record(root, record)

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.fired, 1)
            self.assertTrue((root / "firing" / "wake_file.json").exists())

    def test_file_changed_waits_for_mtime_or_size_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            watched = Path(tmp) / "watched.log"
            watched.write_text("before", encoding="utf-8")
            stat = watched.stat()
            record = self.make_record(
                tmp,
                {
                    "type": "file_changed",
                    "path": "watched.log",
                    "registered_exists": True,
                    "registered_mtime_ns": stat.st_mtime_ns,
                    "registered_size": stat.st_size,
                },
            )
            record["id"] = "wake_changed"
            write_record(root, record)

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.pending, 1)
            watched.write_text("after value", encoding="utf-8")

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 16, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.fired, 1)
            self.assertTrue((root / "firing" / "wake_changed.json").exists())

    def test_file_changed_fires_when_missing_file_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            watched = Path(tmp) / "created.log"
            record = self.make_record(
                tmp,
                {
                    "type": "file_changed",
                    "path": "created.log",
                    "registered_exists": False,
                    "registered_mtime_ns": None,
                    "registered_size": None,
                },
            )
            record["id"] = "wake_created"
            write_record(root, record)

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.pending, 1)
            watched.write_text("created", encoding="utf-8")

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 16, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.fired, 1)
            self.assertTrue((root / "firing" / "wake_created.json").exists())

    def test_process_done_waits_for_pid_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            proc = subprocess.Popen(["sleep", "0.2"])
            self.addCleanup(lambda: proc.poll() is None and proc.kill())
            record = self.make_record(tmp, {"type": "process_done", "pid": proc.pid})
            record["id"] = "wake_pid"
            write_record(root, record)

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.pending, 1)
            proc.wait(timeout=2)

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 16, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.fired, 1)
            self.assertTrue((root / "firing" / "wake_pid.json").exists())

    def test_process_done_waits_for_matching_process_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            record = self.make_record(
                tmp,
                {
                    "type": "process_done",
                    "pid": 123,
                    "registered_start_time_ticks": 456,
                    "registered_boot_id": "boot-abc",
                },
            )
            record["id"] = "wake_pid_identity"
            write_record(root, record)

            with patch("codex_wake.daemon.process_exists", return_value=True):
                with patch("codex_wake.daemon.boot_id_value", return_value="boot-abc"):
                    with patch(
                        "codex_wake.daemon.process_identity",
                        return_value={"start_time_ticks": 456, "boot_id": "boot-abc"},
                    ):
                        result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.pending, 1)
            self.assertTrue((root / "pending" / "wake_pid_identity.json").exists())

    def test_process_done_fires_when_pid_identity_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            record = self.make_record(
                tmp,
                {
                    "type": "process_done",
                    "pid": 123,
                    "registered_start_time_ticks": 456,
                    "registered_boot_id": "boot-abc",
                },
            )
            record["id"] = "wake_pid_reused"
            write_record(root, record)

            with patch("codex_wake.daemon.process_exists", return_value=True):
                with patch("codex_wake.daemon.boot_id_value", return_value="boot-abc"):
                    with patch(
                        "codex_wake.daemon.process_identity",
                        return_value={"start_time_ticks": 789, "boot_id": "boot-abc"},
                    ):
                        result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.fired, 1)
            data = json.loads((root / "firing" / "wake_pid_reused.json").read_text())
            self.assertIn("no longer matches", data["events"][-1]["message"])

    def test_process_done_fires_when_boot_id_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            record = self.make_record(
                tmp,
                {
                    "type": "process_done",
                    "pid": 123,
                    "registered_start_time_ticks": 456,
                    "registered_boot_id": "boot-abc",
                },
            )
            record["id"] = "wake_pid_boot"
            write_record(root, record)

            with patch("codex_wake.daemon.process_exists", return_value=True):
                with patch("codex_wake.daemon.boot_id_value", return_value="boot-def"):
                    result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.fired, 1)
            data = json.loads((root / "firing" / "wake_pid_boot.json").read_text())
            self.assertIn("previous boot", data["events"][-1]["message"])

    def test_process_done_rejects_invalid_registered_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            record = self.make_record(tmp, {"type": "process_done", "pid": 123, "registered_start_time_ticks": "bad"})
            record["id"] = "wake_bad_pid_identity"
            write_record(root, record)

            with patch("codex_wake.daemon.process_exists", return_value=True):
                result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.failed, 1)
            data = json.loads((root / "failed" / "wake_bad_pid_identity.json").read_text())
            self.assertIn("registered_start_time_ticks", data["last_error"])

    def test_process_done_rejects_invalid_pid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            record = self.make_record(tmp, {"type": "process_done", "pid": "nope"})
            record["id"] = "wake_bad_pid"
            write_record(root, record)

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.failed, 1)
            data = json.loads((root / "failed" / "wake_bad_pid.json").read_text())
            self.assertIn("process_done predicate requires", data["last_error"])

    def test_invalid_predicate_moves_to_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            record = self.make_record(tmp, {"type": "command", "cmd": "pytest"})
            record["id"] = "wake_bad"
            write_record(root, record)

            result = poll_once(root, now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC), dispatch=False)

            self.assertEqual(result.failed, 1)
            failed = root / "failed" / "wake_bad.json"
            self.assertTrue(failed.exists())
            data = json.loads(failed.read_text())
            self.assertEqual(data["status"], "failed")
            self.assertIn("unsupported predicate type", data["last_error"])

    def test_poll_result_format_and_activity(self) -> None:
        empty = PollResult()
        active = PollResult(checked=1, fired=1, dispatched=1, submitted=1)

        self.assertFalse(poll_result_has_activity(empty))
        self.assertTrue(poll_result_has_activity(active))
        self.assertEqual(
            format_poll_result(active),
            "checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0",
        )


if __name__ == "__main__":
    unittest.main()
