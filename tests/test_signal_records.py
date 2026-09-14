from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.event_wake import EventWake
from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher
from codex_wake.signal_store import SQLiteSignalModule, SignalStoreError
from codex_wake.signals import Degraded, Registration
from tests.test_signals import make_adapter, make_intent


NOW = datetime(2026, 9, 14, 14, 0, tzinfo=UTC)


class SignalRecordPublicationTests(unittest.TestCase):
    @staticmethod
    def _downgrade_empty_journal_to_v1(database: Path) -> None:
        with sqlite3.connect(database) as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DROP TABLE record_outbox")
            connection.execute("DROP TABLE wake_lifecycle")
            connection.execute("DROP TABLE registration_tombstones")
            connection.execute(
                """
                CREATE TABLE journal_meta_v1 (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    schema_version INTEGER NOT NULL,
                    next_sequence INTEGER NOT NULL CHECK(next_sequence >= 1),
                    created_at TEXT NOT NULL,
                    migrated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO journal_meta_v1
                SELECT singleton, 1, next_sequence, created_at, migrated_at
                FROM journal_meta
                """
            )
            connection.execute("DROP TABLE journal_meta")
            connection.execute("ALTER TABLE journal_meta_v1 RENAME TO journal_meta")
            connection.execute(
                """
                CREATE TABLE arms_v1 (
                    arm_id TEXT PRIMARY KEY,
                    wake_id TEXT NOT NULL UNIQUE,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    intent_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('preparing', 'published')),
                    contract_version INTEGER NOT NULL CHECK(contract_version = 1),
                    source TEXT NOT NULL,
                    source_instance TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    resume_json TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    expires_at TEXT,
                    local_after_sequence INTEGER,
                    source_anchor TEXT,
                    baseline_json TEXT,
                    recovery TEXT,
                    preparer_token TEXT,
                    preparation_expires_at TEXT,
                    published_at TEXT,
                    FOREIGN KEY(source, source_instance)
                      REFERENCES source_instances(source, source_instance)
                )
                """
            )
            connection.execute(
                """
                INSERT INTO arms_v1
                SELECT arm_id, wake_id, idempotency_key, intent_fingerprint,
                       state, contract_version, source, source_instance, kind,
                       subject, spec_json, resume_json, registered_at,
                       expires_at, local_after_sequence, source_anchor,
                       baseline_json, recovery, preparer_token,
                       preparation_expires_at, published_at
                FROM arms
                """
            )
            connection.execute("DROP TABLE arms")
            connection.execute("ALTER TABLE arms_v1 RENAME TO arms")
            connection.execute("PRAGMA user_version = 1")
            connection.commit()

    def test_registration_requires_an_active_reader_capability_for_the_exact_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base / "signals.sqlite3"
            wake_root = base / "wake"
            facade = EventWake(
                SQLiteSignalModule(database),
                adapters=[make_adapter()],
                clock=lambda: NOW,
                id_factory=lambda: "wake_1",
            )

            unavailable = facade.register(make_intent(), idempotency_key="job-42")

            self.assertIsInstance(unavailable, Degraded)
            self.assertEqual(unavailable.code, "WAKE_RECORD_PUBLISHER_UNAVAILABLE")
            self.assertEqual(list(wake_root.glob("pending/*.json")), [])

            publisher = WakeRecordPublisher(
                wake_root,
                ManagedReaderCapability(
                    wake_root=wake_root,
                    reader_id="managed-reader-1",
                    generation=1,
                    schema_versions=frozenset({1, 2}),
                    active=True,
                ),
            )
            recovered = EventWake(
                SQLiteSignalModule(database, record_publisher=publisher),
                adapters=[make_adapter()],
                clock=lambda: NOW,
                id_factory=lambda: "wake_unused",
            ).register(make_intent(), idempotency_key="job-42")

            self.assertIsInstance(recovered, Registration)
            self.assertEqual(recovered.wake_id, "wake_1")
            record_path = wake_root / "pending" / "wake_1.json"
            raw_record = record_path.read_text(encoding="utf-8")
            record = json.loads(raw_record)
            self.assertEqual(record["schema_version"], 2)
            self.assertEqual(record["arm_id"], "arm_wake_1")
            self.assertEqual(record["record_revision"], 1)
            self.assertTrue(record["journal_uuid"])
            self.assertEqual(record["status"], "pending")
            self.assertEqual(record["predicate"]["type"], "signal")
            self.assertEqual(record["predicate"]["contract_version"], 1)
            self.assertEqual(record["predicate"]["source"], "memory")
            self.assertEqual(record["predicate"]["source_instance"], "contract-test")
            self.assertEqual(
                raw_record,
                json.dumps(
                    record,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n",
            )

    def test_registration_orders_prepared_commit_before_durable_file_and_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base / "signals.sqlite3"
            wake_root = base / "wake"
            observed: list[str] = []
            capability = ManagedReaderCapability(
                wake_root=wake_root,
                reader_id="managed-reader-1",
                generation=7,
                schema_versions=frozenset({1, 2}),
                active=True,
            )
            publisher = WakeRecordPublisher(
                wake_root,
                capability,
                checkpoint=observed.append,
            )

            result = EventWake(
                SQLiteSignalModule(
                    database,
                    record_publisher=publisher,
                    checkpoint=observed.append,
                ),
                adapters=[make_adapter()],
                clock=lambda: NOW,
                id_factory=lambda: "wake_1",
            ).register(make_intent(), idempotency_key="job-42")

            self.assertIsInstance(result, Registration)
            self.assertEqual(
                observed,
                [
                    "after_prepared_commit",
                    "after_temp_write",
                    "after_file_fsync",
                    "after_replace",
                    "after_directory_fsync",
                    "after_published_commit",
                ],
            )

    def test_reader_capability_is_bound_to_root_identity_generation_and_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "wake"
            cases = {
                "wrong_root": ManagedReaderCapability(
                    base / "other", "reader", 1, frozenset({2}), True
                ),
                "missing_identity": ManagedReaderCapability(
                    wake_root, "", 1, frozenset({2}), True
                ),
                "missing_generation": ManagedReaderCapability(
                    wake_root, "reader", 0, frozenset({2}), True
                ),
                "inactive": ManagedReaderCapability(
                    wake_root, "reader", 1, frozenset({2}), False
                ),
                "unsupported_schema": ManagedReaderCapability(
                    wake_root, "reader", 1, frozenset({1}), True
                ),
            }
            for name, capability in cases.items():
                with self.subTest(name=name):
                    publisher = WakeRecordPublisher(wake_root, capability)
                    self.assertEqual(
                        publisher.capability_code(),
                        "READER_CAPABILITY_UNAVAILABLE",
                    )

    def test_registration_reconciles_an_exact_record_left_after_replace(self) -> None:
        class SimulatedProcessCrash(BaseException):
            pass

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base / "signals.sqlite3"
            wake_root = base / "wake"
            capability = ManagedReaderCapability(
                wake_root=wake_root,
                reader_id="managed-reader-1",
                generation=1,
                schema_versions=frozenset({1, 2}),
                active=True,
            )

            def crash_after_replace(name: str) -> None:
                if name == "after_replace":
                    raise SimulatedProcessCrash()

            interrupted = EventWake(
                SQLiteSignalModule(
                    database,
                    record_publisher=WakeRecordPublisher(
                        wake_root,
                        capability,
                        checkpoint=crash_after_replace,
                    ),
                ),
                adapters=[make_adapter()],
                clock=lambda: NOW,
                id_factory=lambda: "wake_1",
            )
            with self.assertRaises(SimulatedProcessCrash):
                interrupted.register(make_intent(), idempotency_key="job-42")

            replay_adapter = make_adapter()
            recovered = EventWake(
                SQLiteSignalModule(
                    database,
                    record_publisher=WakeRecordPublisher(wake_root, capability),
                ),
                adapters=[replay_adapter],
                clock=lambda: NOW,
                id_factory=lambda: "wake_unused",
            ).register(make_intent(), idempotency_key="job-42")

            self.assertIsInstance(recovered, Registration)
            self.assertEqual(recovered.wake_id, "wake_1")
            self.assertEqual(replay_adapter.anchor_calls, 0)

    def test_registration_replays_after_published_commit_without_a_new_anchor(self) -> None:
        class SimulatedProcessCrash(BaseException):
            pass

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base / "signals.sqlite3"
            wake_root = base / "wake"
            capability = ManagedReaderCapability(
                wake_root=wake_root,
                reader_id="managed-reader-1",
                generation=1,
                schema_versions=frozenset({1, 2}),
                active=True,
            )

            def crash_after_published_commit(name: str) -> None:
                if name == "after_published_commit":
                    raise SimulatedProcessCrash()

            interrupted = EventWake(
                SQLiteSignalModule(
                    database,
                    record_publisher=WakeRecordPublisher(wake_root, capability),
                    checkpoint=crash_after_published_commit,
                ),
                adapters=[make_adapter()],
                clock=lambda: NOW,
                id_factory=lambda: "wake_1",
            )
            with self.assertRaises(SimulatedProcessCrash):
                interrupted.register(make_intent(), idempotency_key="job-42")

            replay_adapter = make_adapter()
            recovered = EventWake(
                SQLiteSignalModule(
                    database,
                    record_publisher=WakeRecordPublisher(wake_root, capability),
                ),
                adapters=[replay_adapter],
                clock=lambda: NOW,
                id_factory=lambda: "wake_unused",
            ).register(make_intent(), idempotency_key="job-42")

            self.assertIsInstance(recovered, Registration)
            self.assertEqual(recovered.wake_id, "wake_1")
            self.assertEqual(replay_adapter.anchor_calls, 0)

    def test_registration_never_overwrites_a_conflicting_final_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base / "signals.sqlite3"
            wake_root = base / "wake"
            prepared = EventWake(
                SQLiteSignalModule(database),
                adapters=[make_adapter()],
                clock=lambda: NOW,
                id_factory=lambda: "wake_1",
            ).register(make_intent(), idempotency_key="job-42")
            self.assertIsInstance(prepared, Degraded)

            final_path = wake_root / "pending" / "wake_1.json"
            final_path.parent.mkdir(parents=True)
            conflicting_bytes = b'{"schema_version":2,"id":"wake_1","corrupt":true}\n'
            final_path.write_bytes(conflicting_bytes)
            capability = ManagedReaderCapability(
                wake_root=wake_root,
                reader_id="managed-reader-1",
                generation=1,
                schema_versions=frozenset({1, 2}),
                active=True,
            )
            replay_adapter = make_adapter()

            result = EventWake(
                SQLiteSignalModule(
                    database,
                    record_publisher=WakeRecordPublisher(wake_root, capability),
                ),
                adapters=[replay_adapter],
                clock=lambda: NOW,
                id_factory=lambda: "wake_unused",
            ).register(make_intent(), idempotency_key="job-42")

            self.assertIsInstance(result, Degraded)
            self.assertEqual(result.code, "WAKE_RECORD_CONFLICT")
            self.assertEqual(final_path.read_bytes(), conflicting_bytes)
            self.assertEqual(replay_adapter.anchor_calls, 0)

    def test_v1_to_v2_migration_is_atomic_and_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            SQLiteSignalModule(database)
            self._downgrade_empty_journal_to_v1(database)

            def fail_before_commit(name: str) -> None:
                if name == "before_migration_commit":
                    raise RuntimeError("simulated migration interruption")

            with self.assertRaises(SignalStoreError):
                SQLiteSignalModule(database, checkpoint=fail_before_commit)
            with sqlite3.connect(database) as connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
                columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(journal_meta)")
                }
                self.assertNotIn("journal_uuid", columns)

            migrated = SQLiteSignalModule(database)
            status = migrated.journal_status()
            self.assertEqual(status.schema_version, 2)
            self.assertTrue(status.journal_uuid)
            with sqlite3.connect(database) as connection:
                states_sql = connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'arms'"
                ).fetchone()[0]
                self.assertIn("'prepared'", states_sql)
                self.assertIn("'tombstoned'", states_sql)
                self.assertIsNotNone(
                    connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'record_outbox'"
                    ).fetchone()
                )

    def test_migrated_v1_published_arm_republishes_without_reanchoring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base / "signals.sqlite3"
            wake_root = base / "wake"
            capability = ManagedReaderCapability(
                wake_root=wake_root,
                reader_id="managed-reader-1",
                generation=1,
                schema_versions=frozenset({1, 2}),
                active=True,
            )
            publisher = WakeRecordPublisher(wake_root, capability)
            original = EventWake(
                SQLiteSignalModule(database, record_publisher=publisher),
                adapters=[make_adapter()],
                clock=lambda: NOW,
                id_factory=lambda: "wake_1",
            ).register(make_intent(), idempotency_key="job-42")
            self.assertIsInstance(original, Registration)
            (wake_root / "pending" / "wake_1.json").unlink()
            self._downgrade_empty_journal_to_v1(database)

            replay_adapter = make_adapter()
            replay = EventWake(
                SQLiteSignalModule(database, record_publisher=publisher),
                adapters=[replay_adapter],
                clock=lambda: NOW,
                id_factory=lambda: "wake_unused",
            ).register(make_intent(), idempotency_key="job-42")

            self.assertEqual(replay, original)
            self.assertEqual(replay_adapter.anchor_calls, 0)
            self.assertTrue((wake_root / "pending" / "wake_1.json").exists())


if __name__ == "__main__":
    unittest.main()
