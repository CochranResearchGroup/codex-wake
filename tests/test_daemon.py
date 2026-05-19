from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

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
