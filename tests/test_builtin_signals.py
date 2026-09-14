from __future__ import annotations

import unittest
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.builtin_signals import BuiltinPredicateSignals
from codex_wake.records import build_record


class BuiltinPredicateSignalTests(unittest.TestCase):
    def make_record(self, predicate: dict) -> dict:
        record = build_record(
            predicate=predicate,
            prompt="continue",
            cwd=Path("/tmp/project"),
            target={"transport": "tmux", "tmux_socket": "/tmp/tmux", "pane": "%1"},
            now=datetime(2026, 5, 18, 20, 30, tzinfo=UTC),
        )
        record["id"] = "wake_builtin"
        return record

    def test_not_before_uses_shared_signal_contract_with_restart_stable_identity(self) -> None:
        record = self.make_record(
            {"type": "not_before", "due_at": "2026-05-18T21:15:00Z"}
        )
        now = datetime(2026, 5, 18, 21, 15, tzinfo=UTC)

        first = BuiltinPredicateSignals().evaluate(record, now)
        restarted = BuiltinPredicateSignals().evaluate(record, now)

        self.assertTrue(first.ready)
        self.assertEqual(
            first.message,
            "not_before due_at 2026-05-18T21:15:00Z matched",
        )
        self.assertEqual(first.logical_identity, restarted.logical_identity)
        self.assertEqual(first.signal.source, "codex_wake.builtin")
        self.assertEqual(first.signal.kind, "predicate.not_before")

    def test_file_exists_preserves_relative_cwd_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            record = self.make_record({"type": "file_exists", "path": "done.flag"})
            record["cwd"] = str(cwd)
            pending = BuiltinPredicateSignals().evaluate(
                record, datetime(2026, 5, 18, 21, 14, tzinfo=UTC)
            )
            (cwd / "done.flag").write_text("", encoding="utf-8")

            matched = BuiltinPredicateSignals().evaluate(
                record, datetime(2026, 5, 18, 21, 15, tzinfo=UTC)
            )

        self.assertFalse(pending.ready)
        self.assertTrue(matched.ready)
        self.assertEqual(
            matched.message,
            f"file_exists path {cwd / 'done.flag'} matched",
        )
        self.assertEqual(matched.signal.condition, "holds")

    def test_file_changed_preserves_creation_and_metadata_change_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            watched = cwd / "watched.log"
            created_record = self.make_record(
                {
                    "type": "file_changed",
                    "path": "watched.log",
                    "registered_exists": False,
                    "registered_mtime_ns": None,
                    "registered_size": None,
                }
            )
            created_record["cwd"] = str(cwd)
            before_create = BuiltinPredicateSignals().evaluate(
                created_record, datetime(2026, 5, 18, 21, 14, tzinfo=UTC)
            )
            watched.write_text("before", encoding="utf-8")
            created = BuiltinPredicateSignals().evaluate(
                created_record, datetime(2026, 5, 18, 21, 15, tzinfo=UTC)
            )
            stat = watched.stat()
            changed_record = self.make_record(
                {
                    "type": "file_changed",
                    "path": "watched.log",
                    "registered_exists": True,
                    "registered_mtime_ns": stat.st_mtime_ns,
                    "registered_size": stat.st_size,
                }
            )
            changed_record["cwd"] = str(cwd)
            unchanged = BuiltinPredicateSignals().evaluate(
                changed_record, datetime(2026, 5, 18, 21, 16, tzinfo=UTC)
            )
            watched.write_text("after value", encoding="utf-8")
            changed = BuiltinPredicateSignals().evaluate(
                changed_record, datetime(2026, 5, 18, 21, 17, tzinfo=UTC)
            )

        self.assertFalse(before_create.ready)
        self.assertTrue(created.ready)
        self.assertEqual(created.message, f"file_changed path {watched} was created")
        self.assertFalse(unchanged.ready)
        self.assertTrue(changed.ready)
        self.assertEqual(changed.message, f"file_changed path {watched} changed")
        self.assertEqual(changed.signal.condition, "becomes")

    def test_process_done_preserves_identity_and_reboot_semantics(self) -> None:
        record = self.make_record(
            {
                "type": "process_done",
                "pid": 123,
                "registered_start_time_ticks": 456,
                "registered_boot_id": "boot-abc",
            }
        )
        now = datetime(2026, 5, 18, 21, 15, tzinfo=UTC)
        matching = BuiltinPredicateSignals(
            process_exists_fn=lambda _pid: True,
            boot_id_fn=lambda: "boot-abc",
            process_identity_fn=lambda _pid: {"start_time_ticks": 456, "boot_id": "boot-abc"},
        ).evaluate(record, now)
        reused = BuiltinPredicateSignals(
            process_exists_fn=lambda _pid: True,
            boot_id_fn=lambda: "boot-abc",
            process_identity_fn=lambda _pid: {"start_time_ticks": 789, "boot_id": "boot-abc"},
        ).evaluate(record, now)
        rebooted = BuiltinPredicateSignals(
            process_exists_fn=lambda _pid: True,
            boot_id_fn=lambda: "boot-def",
            process_identity_fn=lambda _pid: {"start_time_ticks": 456, "boot_id": "boot-def"},
        ).evaluate(record, now)

        self.assertFalse(matching.ready)
        self.assertTrue(reused.ready)
        self.assertEqual(reused.message, "process_done pid 123 no longer matches registered process")
        self.assertTrue(rebooted.ready)
        self.assertEqual(rebooted.message, "process_done pid 123 was from previous boot")
        self.assertEqual(reused.signal.condition, "becomes")


if __name__ == "__main__":
    unittest.main()
