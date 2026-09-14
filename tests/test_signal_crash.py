from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.daemon import poll_once
from codex_wake.event_wake import EventWake
from codex_wake.records import archive_record
from codex_wake.signal_records import (
    ManagedReaderCapability,
    WakeRecordPublisher,
    signal_journal_path,
)
from codex_wake.signal_store import SQLiteSignalModule
from codex_wake.signals import Ingested, Registration, SourceCommit
from tests.test_signal_store import make_observation
from tests.test_signals import make_adapter, make_intent


NOW = datetime(2026, 9, 14, 14, 3, tzinfo=UTC)


class SignalFreshProcessCrashTests(unittest.TestCase):
    def crash(self, root: Path, mode: str) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "tests.signal_crash_helper", str(root), mode],
            check=False,
        )
        self.assertEqual(completed.returncode, 91, mode)

    def runtime(self, root: Path) -> SQLiteSignalModule:
        runtime = SQLiteSignalModule.open_existing(signal_journal_path(root))
        self.assertIsNotNone(runtime)
        return runtime

    def recover_registration(self, root: Path) -> Registration:
        runtime = SQLiteSignalModule(
            signal_journal_path(root),
            record_publisher=WakeRecordPublisher(
                root,
                ManagedReaderCapability(root, "recovery", 1, frozenset({1, 2}), True),
            ),
            lease_clock=lambda: datetime(2027, 1, 1, tzinfo=UTC),
        )
        adapter = make_adapter()
        result = EventWake(
            runtime,
            adapters=[adapter],
            clock=lambda: datetime(2027, 1, 1, tzinfo=UTC),
            id_factory=lambda: "wake_unused",
        ).register(make_intent(), idempotency_key="job-42")
        self.assertIsInstance(result, Registration)
        self.assertEqual(result.wake_id, "wake_signal")
        return result

    def test_fresh_process_commit_and_cross_store_crashes_recover_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            before = Path(tmp) / "ingest-before"
            self.crash(before, "ingest_before")
            accepted = self.runtime(before).ingest(
                [make_observation()],
                SourceCommit("memory", "contract-test", "checkpoint-1", 1, NOW),
            )
            self.assertIsInstance(accepted, Ingested)
            self.assertFalse(accepted.receipts[0].duplicate)
            self.assertEqual(accepted.receipts[0].local_sequence, 1)

            after = Path(tmp) / "ingest-after"
            self.crash(after, "ingest_after")
            replay = self.runtime(after).ingest(
                [make_observation()],
                SourceCommit("memory", "contract-test", "checkpoint-1", 1, NOW),
            )
            self.assertIsInstance(replay, Ingested)
            self.assertTrue(replay.receipts[0].duplicate)
            self.assertEqual(replay.receipts[0].local_sequence, 1)

            reservation = Path(tmp) / "reservation"
            self.crash(reservation, "reservation_after")
            recovered = poll_once(reservation, now=NOW, dispatch=False)
            self.assertEqual((recovered.fired, recovered.dispatched), (1, 0))
            state = self.runtime(reservation).inspect_signal_state("wake_signal")
            self.assertEqual([row["revision"] for row in state["outbox"]], [1, 2])
            self.assertIsNotNone(state["reservation"])

            firing = Path(tmp) / "firing"
            self.crash(firing, "firing_after_replace")
            self.assertTrue((firing / "firing" / "wake_signal.json").exists())
            self.assertTrue((firing / "pending" / "wake_signal.json").exists())
            poll_once(firing, now=NOW, dispatch=False)
            self.assertTrue((firing / "firing" / "wake_signal.json").exists())
            self.assertFalse((firing / "pending" / "wake_signal.json").exists())

            terminal = Path(tmp) / "terminal"
            self.crash(terminal, "terminal_after")
            poll_once(terminal, now=NOW, dispatch=False)
            self.assertTrue((terminal / "cancelled" / "wake_signal.json").exists())
            self.assertFalse((terminal / "pending" / "wake_signal.json").exists())
            terminal_runtime = self.runtime(terminal)
            self.assertEqual(terminal_runtime.terminal_status("wake_signal"), "cancelled")
            self.assertEqual(terminal_runtime.retention_pins("wake_signal"), ())

            expiry = Path(tmp) / "expiry"
            self.crash(expiry, "expiry_after")
            poll_once(expiry, now=NOW, dispatch=False)
            self.assertTrue((expiry / "expired" / "wake_signal.json").exists())
            self.assertFalse((expiry / "pending" / "wake_signal.json").exists())

    def test_fresh_process_registration_and_maintenance_crashes_leave_no_eligible_orphan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for mode in (
                "prepared_before",
                "prepared_after",
                "temp_write",
                "registration_replace",
                "before_published",
                "published_after",
            ):
                with self.subTest(mode=mode):
                    root = base / mode
                    self.crash(root, mode)
                    self.recover_registration(root)
                    self.assertTrue((root / "pending" / "wake_signal.json").exists())
                    self.assertIsNotNone(self.runtime(root).load_armed_signal("wake_signal"))

            archive = base / "archive"
            self.crash(archive, "archive_after")
            self.assertTrue((archive / "archive" / "wake_signal.json").exists())
            self.assertTrue((archive / "cancelled" / "wake_signal.json").exists())
            archive_record(archive, "wake_signal", now=NOW)
            self.assertFalse((archive / "cancelled" / "wake_signal.json").exists())

            cleanup = base / "cleanup"
            self.crash(cleanup, "cleanup_after")
            self.assertFalse((cleanup / "archive" / "wake_signal.json").exists())

            retention = base / "retention"
            self.crash(retention, "retention_after")
            replay = self.runtime(retention).ingest(
                [make_observation()],
                SourceCommit("memory", "contract-test", "checkpoint-1", 1, NOW),
            )
            self.assertFalse(replay.receipts[0].duplicate)
            self.assertEqual(replay.receipts[0].local_sequence, 2)

            migration = base / "migration"
            self.crash(migration, "migration_before")
            migrated = self.runtime(migration)
            self.assertEqual(migrated.journal_status().schema_version, 2)


if __name__ == "__main__":
    unittest.main()
