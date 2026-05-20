from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from codex_wake.records import (
    archive_record,
    archive_terminal_records,
    build_record,
    cancel_record,
    cleanup_archived_records,
    capture_tmux_target,
    format_utc,
    parse_duration,
    parse_timestamp,
    write_record,
)


class RecordTests(unittest.TestCase):
    def test_parse_duration_supports_compound_values(self) -> None:
        self.assertEqual(parse_duration("1h30m"), timedelta(minutes=90))
        self.assertEqual(parse_duration("2d3h4m5s"), timedelta(days=2, hours=3, minutes=4, seconds=5))

    def test_parse_duration_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            parse_duration("45")
        with self.assertRaises(ValueError):
            parse_duration("m45")

    def test_parse_timestamp_requires_timezone_and_normalizes_utc(self) -> None:
        self.assertEqual(format_utc(parse_timestamp("2026-05-18T17:30:00-05:00")), "2026-05-18T22:30:00Z")
        self.assertEqual(format_utc(parse_timestamp("2026-05-18T22:30:00Z")), "2026-05-18T22:30:00Z")
        with self.assertRaises(ValueError):
            parse_timestamp("2026-05-18T17:30:00")

    def test_capture_tmux_target_from_environment(self) -> None:
        target = capture_tmux_target({"TMUX_PANE": "%11", "TMUX": "/tmp/tmux-1000/default,123,0"})
        self.assertEqual(target["transport"], "tmux")
        self.assertEqual(target["pane"], "%11")
        self.assertEqual(target["tmux_socket"], "/tmp/tmux-1000/default")

    def test_write_and_cancel_record(self) -> None:
        now = datetime(2026, 5, 18, 20, 30, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = build_record(
                predicate={"type": "not_before", "due_at": "2026-05-18T21:15:00Z"},
                prompt="continue",
                cwd=Path(tmp),
                target={"transport": "tmux", "tmux_socket": "/tmp/tmux/default", "pane": "%1"},
                now=now,
            )
            with patch("codex_wake.records.secrets.token_hex", return_value="9f3a"):
                record["id"] = "wake_20260518_203000_9f3a"
            path = write_record(root, record)
            self.assertTrue(path.exists())
            cancelled = cancel_record(root, record["id"], now=now)
            data = json.loads(cancelled.read_text())
            self.assertEqual(data["status"], "cancelled")
            self.assertFalse(path.exists())

    def test_archive_record_only_allows_terminal_status(self) -> None:
        now = datetime(2026, 5, 18, 20, 30, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = build_record(
                predicate={"type": "not_before", "due_at": "2026-05-18T21:15:00Z"},
                prompt="continue",
                cwd=Path(tmp),
                target={"transport": "tmux", "tmux_socket": "/tmp/tmux/default", "pane": "%1"},
                now=now,
            )
            record["id"] = "wake_archive"
            active_path = write_record(root, record)
            with self.assertRaises(ValueError):
                archive_record(root, "wake_archive", now=now)
            record["status"] = "cancelled"
            terminal_path = write_record(root, record)
            active_path.unlink(missing_ok=True)

            archived = archive_record(root, "wake_archive", now=now)

            self.assertFalse(terminal_path.exists())
            data = json.loads(archived.read_text())
            self.assertEqual(data["status"], "archived")
            self.assertEqual(data["previous_status"], "cancelled")
            self.assertEqual(data["events"][-1]["type"], "archived")

    def test_archive_terminal_records_skips_active_records(self) -> None:
        now = datetime(2026, 5, 18, 20, 30, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pending = build_record(
                predicate={"type": "not_before", "due_at": "2026-05-18T21:15:00Z"},
                prompt="pending",
                cwd=Path(tmp),
                target={"transport": "tmux", "tmux_socket": "/tmp/tmux/default", "pane": "%1"},
                now=now,
            )
            pending["id"] = "wake_pending"
            write_record(root, pending)
            failed = dict(pending)
            failed["id"] = "wake_failed"
            failed["status"] = "failed"
            write_record(root, failed)

            paths = archive_terminal_records(root, now=now)

            self.assertEqual([path.name for path in paths], ["wake_failed.json"])
            self.assertTrue((root / "pending" / "wake_pending.json").exists())

    def test_cleanup_archived_records_is_dry_run_by_default(self) -> None:
        old = datetime(2026, 5, 1, 20, 30, tzinfo=UTC)
        current = datetime(2026, 5, 19, 20, 30, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = build_record(
                predicate={"type": "not_before", "due_at": "2026-05-01T21:15:00Z"},
                prompt="old",
                cwd=Path(tmp),
                target={"transport": "tmux", "tmux_socket": "/tmp/tmux/default", "pane": "%1"},
                now=old,
            )
            record["id"] = "wake_old"
            record["status"] = "cancelled"
            write_record(root, record)
            archived = archive_record(root, "wake_old", now=old)

            results = cleanup_archived_records(root, older_than=timedelta(days=7), now=current)

            self.assertEqual([result.wake_id for result in results], ["wake_old"])
            self.assertFalse(results[0].deleted)
            self.assertTrue(archived.exists())

    def test_cleanup_archived_records_deletes_only_old_archived_records(self) -> None:
        old = datetime(2026, 5, 1, 20, 30, tzinfo=UTC)
        fresh = datetime(2026, 5, 18, 20, 30, tzinfo=UTC)
        current = datetime(2026, 5, 19, 20, 30, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = build_record(
                predicate={"type": "not_before", "due_at": "2026-05-01T21:15:00Z"},
                prompt="wake",
                cwd=Path(tmp),
                target={"transport": "tmux", "tmux_socket": "/tmp/tmux/default", "pane": "%1"},
                now=old,
            )
            old_record = dict(base)
            old_record["id"] = "wake_old"
            old_record["status"] = "cancelled"
            write_record(root, old_record)
            old_path = archive_record(root, "wake_old", now=old)

            fresh_record = dict(base)
            fresh_record["id"] = "wake_fresh"
            fresh_record["status"] = "cancelled"
            write_record(root, fresh_record)
            fresh_path = archive_record(root, "wake_fresh", now=fresh)

            pending = dict(base)
            pending["id"] = "wake_pending"
            pending["status"] = "pending"
            write_record(root, pending)

            results = cleanup_archived_records(root, older_than=timedelta(days=7), now=current, delete=True)

            self.assertEqual([result.wake_id for result in results], ["wake_old"])
            self.assertTrue(results[0].deleted)
            self.assertFalse(old_path.exists())
            self.assertTrue(fresh_path.exists())
            self.assertTrue((root / "pending" / "wake_pending.json").exists())


if __name__ == "__main__":
    unittest.main()
