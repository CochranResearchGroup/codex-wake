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
    classify_record,
    capture_tmux_target,
    format_utc,
    iter_records,
    parse_duration,
    parse_timestamp,
    schema_summary,
    status_summary,
    write_record,
)
from codex_wake.signal_records import build_signal_record
from codex_wake.signals import ArmedSignal, Eq, Resume, SignalRequest, SourceAnchor


class RecordTests(unittest.TestCase):
    def test_signal_cleanup_requires_durable_terminal_fence_and_released_pins(self) -> None:
        from codex_wake.event_wake import EventWake
        from codex_wake.signal_records import (
            ManagedReaderCapability,
            WakeRecordPublisher,
            signal_journal_path,
        )
        from codex_wake.signal_store import SQLiteSignalModule
        from tests.test_signals import make_adapter, make_intent

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            runtime = SQLiteSignalModule(
                signal_journal_path(root),
                record_publisher=WakeRecordPublisher(
                    root,
                    ManagedReaderCapability(root, "reader", 1, frozenset({1, 2}), True),
                ),
            )
            EventWake(
                runtime,
                adapters=[make_adapter()],
                clock=lambda: datetime(2026, 9, 14, 14, 0, tzinfo=UTC),
                id_factory=lambda: "wake_signal",
            ).register(make_intent(), idempotency_key="job-42")
            pending = root / "pending" / "wake_signal.json"
            archived_record = json.loads(pending.read_text())
            archived_record.update(
                {
                    "status": "archived",
                    "record_revision": 2,
                    "archived_at": "2026-09-14T14:00:00Z",
                    "updated_at": "2026-09-14T14:00:00Z",
                }
            )
            archive_path = root / "archive" / "wake_signal.json"
            archive_path.parent.mkdir(parents=True)
            archive_path.write_text(json.dumps(archived_record) + "\n")
            pending.unlink()

            refused = cleanup_archived_records(
                root,
                older_than=timedelta(seconds=1),
                now=datetime(2026, 9, 14, 14, 1, tzinfo=UTC),
                delete=True,
            )
            self.assertEqual(refused, [])
            self.assertTrue(archive_path.exists())

            self.assertTrue(
                runtime.retire_terminal_record(
                    archived_record,
                    now=datetime(2026, 9, 14, 14, 1, tzinfo=UTC),
                )
            )
            deleted = cleanup_archived_records(
                root,
                older_than=timedelta(seconds=1),
                now=datetime(2026, 9, 14, 14, 2, tzinfo=UTC),
                delete=True,
            )
            self.assertEqual(len(deleted), 1)
            self.assertFalse(archive_path.exists())

    def test_multi_version_classification_is_pure_and_fail_closed(self) -> None:
        v1 = build_record(
            predicate={"type": "not_before", "due_at": "2026-05-18T21:15:00Z"},
            prompt="continue",
            cwd=Path("/tmp"),
            target={"transport": "tmux", "tmux_socket": "/tmp/tmux", "pane": "%1"},
            now=datetime(2026, 5, 18, 20, 30, tzinfo=UTC),
        )
        armed = ArmedSignal(
            wake_id="wake_signal",
            arm_id="arm_wake_signal",
            spec=SignalRequest(
                1, "memory", "source-1", "occurrence", "job.completed", "job:1",
                "occurs", (Eq("result", "ready"),), "required",
            ),
            anchor=SourceAnchor(0, "memory:0", {}, "local_journal"),
            registered_at=datetime(2026, 5, 18, 20, 30, tzinfo=UTC),
            expires_at=None,
        )
        signal_json, _digest = build_signal_record(
            armed,
            Resume("continue", Path("/tmp"), {"transport": "tmux"}),
            journal_uuid="journal-1",
            revision=1,
        )
        v2 = json.loads(signal_json)

        self.assertEqual(classify_record(v1), "v1")
        self.assertEqual(classify_record(v2), "signal_v2")
        self.assertEqual(classify_record({**v1, "predicate": {"type": "signal"}}), "hold")
        self.assertEqual(classify_record({**v2, "record_revision": "1"}), "hold")
        self.assertEqual(classify_record({**v2, "schema_version": 99}), "hold")
        self.assertEqual(classify_record({"schema_version": 2}), "hold")

    def test_record_scanning_ignores_non_object_json_without_hiding_valid_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = build_record(
                predicate={"type": "not_before", "due_at": "2026-05-18T21:15:00Z"},
                prompt="continue",
                cwd=root,
                target={"transport": "tmux", "tmux_socket": "/tmp/tmux", "pane": "%1"},
                now=datetime(2026, 5, 18, 20, 30, tzinfo=UTC),
            )
            write_record(root, valid)
            (root / "pending" / "array.json").write_text("[]\n", encoding="utf-8")

            records = iter_records(root)

            self.assertEqual([item.record["id"] for item in records], [valid["id"]])

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

    def test_schema_summary_documents_version_and_compatibility(self) -> None:
        summary = schema_summary()

        self.assertEqual(summary["schema_version"], 1)
        self.assertEqual(summary["compatibility"], "additive_optional_fields")
        self.assertIn("schema_version", summary["required_fields"])
        self.assertIn("process_done", summary["predicate_types"])
        self.assertIn("openclaw_gateway", summary["target_transports"])
        self.assertIn("dispatch_result", summary["optional_fields"])
        self.assertIn("visibility_result", summary["optional_fields"])
        self.assertIn("incompatible_predicate_semantics_change", summary["schema_bump_required_for"])

    def test_status_summary_counts_records(self) -> None:
        now = datetime(2026, 5, 18, 20, 30, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pending = build_record(
                predicate={"type": "not_before", "due_at": "2026-05-18T21:15:00Z"},
                prompt="continue",
                cwd=Path(tmp),
                target={"transport": "tmux", "tmux_socket": "/tmp/tmux/default", "pane": "%1"},
                now=now,
            )
            pending["id"] = "wake_pending"
            write_record(root, pending)
            failed = build_record(
                predicate={"type": "file_exists", "path": "done"},
                prompt="check",
                cwd=Path(tmp),
                target={"transport": "app-server", "endpoint": "stdio://", "thread_id": "thread_1"},
                now=now,
            )
            failed["id"] = "wake_failed"
            failed["status"] = "failed"
            failed["next_attempt_at"] = "2026-05-18T22:00:00Z"
            failed["visibility_result"] = {"classification": "visible_prompt_observed"}
            write_record(root, failed)
            openclaw = build_record(
                predicate={"type": "not_before", "due_at": "2026-05-18T21:15:00Z"},
                prompt="openclaw",
                cwd=Path(tmp),
                target={
                    "transport": "openclaw_gateway",
                    "openclaw": {"agent_id": "main", "session_key": "agent:main:slack:channel:c0ahqqcg7j4"},
                    "dispatch": {"deliver": False, "timeout_seconds": 120, "gateway_timeout_ms": 10000},
                    "gateway": {},
                },
                now=now,
            )
            openclaw["id"] = "wake_openclaw"
            openclaw["status"] = "cancelled"
            write_record(root, openclaw)
            archived = archive_record(root, "wake_failed", now=now)
            self.assertTrue(archived.exists())

            summary = status_summary(root)

            self.assertEqual(summary["total"], 3)
            self.assertEqual(summary["active_total"], 1)
            self.assertEqual(summary["terminal_total"], 1)
            self.assertEqual(summary["archived_total"], 1)
            self.assertEqual(summary["counts_by_status"]["pending"], 1)
            self.assertEqual(summary["counts_by_status"]["cancelled"], 1)
            self.assertEqual(summary["counts_by_status"]["archived"], 1)
            self.assertEqual(summary["counts_by_predicate"], {"file_exists": 1, "not_before": 2})
            self.assertEqual(summary["counts_by_target_transport"], {"app-server": 1, "openclaw_gateway": 1, "tmux": 1})
            self.assertEqual(summary["counts_by_visibility_classification"], {"visible_prompt_observed": 1})
            self.assertEqual(summary["earliest_next_attempt_at"], "2026-05-18T21:15:00Z")

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
