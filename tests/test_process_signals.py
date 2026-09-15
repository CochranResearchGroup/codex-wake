from __future__ import annotations

import sqlite3
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from codex_wake.event_wake import EventWake
from codex_wake.process_signals import (
    ProcessExitAdapter,
    ProcessExitSample,
    observe_process_exit,
    production_process_exit_adapter,
)
from codex_wake.records import cancel_record
from codex_wake.runtime_signals import RuntimeSourceDescriptor, RuntimeSourceRegistry
from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher, signal_journal_path
from codex_wake.signal_store import SQLiteSignalModule
from codex_wake.signals import Degraded, EvaluationLimits, Registration, Resume, WakeIntent


NOW = datetime(2026, 9, 15, tzinfo=UTC)
BOOT_ID = "01234567-89ab-cdef-0123-456789abcdef"
IDENTITY = {"boot_id": BOOT_ID, "pid": 123, "start_time_ticks": 456, "owner_uid": 1000}


class ProcessExitAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.allowed = True
        self.uid = 1000
        self.calls = 0
        self.sample: ProcessExitSample | Exception = ProcessExitSample.alive(**IDENTITY)
        self.descriptor = RuntimeSourceDescriptor.parse(
            {"version": 1, "kind": "process.exit", "resource": IDENTITY, "target_state": "terminated"}
        )
        self.registry = RuntimeSourceRegistry(
            {"process.exit": lambda descriptor: self.allowed and descriptor == self.descriptor}
        )
        self.adapter = ProcessExitAdapter(self.descriptor, self.registry, self.observe, lambda: self.uid)
        self.module = self.runtime()

    def runtime(self, checkpoint=None):
        return SQLiteSignalModule(
            signal_journal_path(self.root), checkpoint=checkpoint,
            record_publisher=WakeRecordPublisher(
                self.root, ManagedReaderCapability(self.root, "reader", 1, frozenset({1, 2}), True),
            ),
        )

    def observe(self) -> ProcessExitSample:
        self.calls += 1
        if isinstance(self.sample, Exception):
            raise self.sample
        return self.sample

    def register(self, *, expires_at=None):
        result = EventWake(
            self.module,
            adapters=(self.adapter,),
            clock=lambda: NOW,
            id_factory=lambda: "wake_process",
        ).register(
            WakeIntent(
                self.adapter.request(),
                Resume("continue", self.root, {"transport": "tmux", "tmux_socket": "/tmp/fixture", "pane": "%1"}),
                expires_at=expires_at,
            ),
            idempotency_key="process-registration",
        )
        self.assertIsInstance(result, Registration)
        return self.module.load_armed_signal(result.wake_id)

    def counts(self):
        with sqlite3.connect(signal_journal_path(self.root)) as connection:
            return tuple(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("receipts", "match_reservations")
            )

    def test_exact_alive_baseline_zombie_restart_and_one_publication(self) -> None:
        armed = self.register()
        self.assertEqual(self.adapter.runner((armed,)).reconcile(self.module, NOW, EvaluationLimits(8)).observed, 0)
        self.sample = ProcessExitSample.zombie(**IDENTITY)
        self.assertEqual(self.adapter.reconcile(self.module, (armed,), NOW, EvaluationLimits(8)).observed, 1)
        fresh = self.runtime()
        restored = ProcessExitAdapter.restore(armed, self.registry, self.observe, lambda: self.uid)
        self.assertEqual(
            restored.reconcile(fresh, (armed,), NOW + timedelta(seconds=1), EvaluationLimits(8)).observed,
            0,
        )
        first = restored.evaluate(fresh, armed, NOW, EvaluationLimits(8))
        second = restored.evaluate(fresh, armed, NOW, EvaluationLimits(8))
        self.assertEqual(first, second)
        self.assertEqual(first.outcome, "matched")
        self.assertEqual(dict(first.receipt.attributes), {"state": "terminated"})
        self.assertEqual(self.counts(), (1, 1))

    def test_registration_requires_same_uid_and_exact_alive_identity(self) -> None:
        for sample, uid, expected in (
            (ProcessExitSample.zombie(**IDENTITY), 1000, "RUNTIME_BASELINE_MATCHES"),
            (ProcessExitSample.alive(**{**IDENTITY, "start_time_ticks": 457}), 1000, "RUNTIME_OBSERVATION_AMBIGUOUS"),
            (ProcessExitSample.alive(**IDENTITY), 1001, "RUNTIME_AUTHORIZATION_DENIED"),
        ):
            with self.subTest(expected=expected):
                self.sample, self.uid = sample, uid
                result = self.adapter.establish_anchor(self.adapter.request(), NOW)
                self.assertEqual(result.code, expected)

    def test_disappearance_during_registration_creates_no_arm_or_receipt(self) -> None:
        self.sample = ProcessExitSample.disappeared(boot_id=BOOT_ID)
        result = EventWake(
            self.module,
            adapters=(self.adapter,),
            clock=lambda: NOW,
            id_factory=lambda: "wake_disappeared",
        ).register(
            WakeIntent(
                self.adapter.request(),
                Resume("continue", self.root, {"transport": "tmux", "tmux_socket": "/tmp/fixture", "pane": "%1"}),
            ),
            idempotency_key="disappeared-registration",
        )
        self.assertIsInstance(result, Degraded)
        self.assertEqual(result.code, "RUNTIME_OBSERVATION_AMBIGUOUS")
        with sqlite3.connect(signal_journal_path(self.root)) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM arms WHERE state IN ('prepared', 'published')"
                ).fetchone()[0],
                0,
            )
        self.assertEqual(self.counts(), (0, 0))

    def test_matched_observation_is_bounded_and_timestamped_at_sampling(self) -> None:
        armed = self.register()
        sampled_at = NOW + timedelta(seconds=3)
        self.sample = ProcessExitSample.zombie(**IDENTITY)
        self.assertEqual(self.adapter.reconcile(self.module, (armed,), sampled_at, EvaluationLimits(8)).observed, 1)
        self.assertEqual(self.adapter.evaluate(self.module, armed, sampled_at, EvaluationLimits(8)).outcome, "matched")
        with sqlite3.connect(signal_journal_path(self.root)) as connection:
            raw = connection.execute("SELECT observation_json FROM receipts").fetchone()[0]
        observation = json.loads(raw)
        self.assertEqual(observation["attributes"], {"state": "terminated"})
        self.assertEqual(datetime.fromisoformat(observation["observed_at"]), sampled_at)
        self.assertFalse(
            {"exit_code", "exit_at", "exit_time", "exact_exit_at", "exact_exit_time"}
            & (set(observation) | set(observation["attributes"]))
        )

    def test_disappearance_requires_positive_classification(self) -> None:
        armed = self.register()
        self.sample = ProcessExitSample.disappeared(boot_id=BOOT_ID)
        self.assertEqual(self.adapter.reconcile(self.module, (armed,), NOW, EvaluationLimits(8)).observed, 1)
        self.assertEqual(self.adapter.evaluate(self.module, armed, NOW, EvaluationLimits(8)).outcome, "matched")

        self.root = self.root / "invalid-disappearance"
        self.root.mkdir()
        self.module = self.runtime()
        self.sample = ProcessExitSample.alive(**IDENTITY)
        armed = self.register()
        self.sample = ProcessExitSample("disappeared", None, None, None, None, None)
        report = self.adapter.reconcile(self.module, (armed,), NOW, EvaluationLimits(8))
        self.assertEqual(report.degraded, 1)
        self.assertEqual(self.adapter.diagnostic.code, "RUNTIME_OBSERVATION_UNAVAILABLE")
        self.assertEqual(self.counts(), (0, 0))

    def test_disappearance_after_a_boot_change_is_ambiguous(self) -> None:
        armed = self.register()
        self.sample = ProcessExitSample.disappeared(boot_id="fedcba98-7654-3210-fedc-ba9876543210")
        report = self.adapter.reconcile(self.module, (armed,), NOW, EvaluationLimits(8))
        self.assertEqual(report.degraded, 1)
        self.assertEqual(self.adapter.diagnostic.code, "RUNTIME_OBSERVATION_AMBIGUOUS")
        self.assertEqual(self.counts(), (0, 0))

    def test_replacement_and_permission_fail_closed_without_a_receipt(self) -> None:
        armed = self.register()
        for sample, expected in (
            (ProcessExitSample.alive(**{**IDENTITY, "start_time_ticks": 457}), "RUNTIME_OBSERVATION_AMBIGUOUS"),
            (
                ProcessExitSample.alive(
                    **{**IDENTITY, "boot_id": "fedcba98-7654-3210-fedc-ba9876543210"}
                ),
                "RUNTIME_OBSERVATION_AMBIGUOUS",
            ),
            (ProcessExitSample.alive(**{**IDENTITY, "owner_uid": 1001}), "RUNTIME_OBSERVATION_AMBIGUOUS"),
            (PermissionError(), "RUNTIME_OBSERVATION_UNAVAILABLE"),
        ):
            with self.subTest(expected=expected):
                self.sample = sample
                report = self.adapter.reconcile(self.module, (armed,), NOW, EvaluationLimits(8))
                self.assertEqual(report.degraded, 1)
                self.assertEqual(self.adapter.diagnostic.code, expected)
                self.assertEqual(self.counts(), (0, 0))

    def test_authorization_revocation_cancellation_and_expiry_do_not_sample_or_publish(self) -> None:
        armed = self.register(expires_at=NOW + timedelta(seconds=1))
        before = self.calls
        self.adapter.reconcile(self.module, (armed,), NOW + timedelta(seconds=2), EvaluationLimits(8))
        self.assertEqual(self.calls, before)
        self.assertEqual(
            self.adapter.evaluate(self.module, armed, NOW + timedelta(seconds=2), EvaluationLimits(8)).outcome,
            "expired",
        )
        cancel_record(self.root, "wake_process", now=NOW)
        self.adapter.reconcile(self.module, (armed,), NOW, EvaluationLimits(8))
        self.assertEqual(self.calls, before)

        self.root = self.root / "revocation"
        self.root.mkdir()
        self.module = self.runtime()
        self.sample = ProcessExitSample.alive(**IDENTITY)
        armed = self.register()
        self.sample = ProcessExitSample.zombie(**IDENTITY)
        self.allowed = False
        report = self.adapter.reconcile(self.module, (armed,), NOW, EvaluationLimits(8))
        self.assertEqual(report.degraded, 1)
        self.assertEqual(self.counts(), (0, 0))

    def test_resource_limit_and_bad_checkpoint_degrade_without_observing(self) -> None:
        armed = self.register()
        before = self.calls
        self.assertEqual(self.adapter.reconcile(self.module, (armed,), NOW, EvaluationLimits(0)).degraded, 1)
        self.assertEqual(self.calls, before)
        self.module.ingest((), self.adapter._checkpoint("alive", None, NOW))
        with sqlite3.connect(signal_journal_path(self.root)) as connection:
            connection.execute("UPDATE source_state SET checkpoint = 'not-json'")
            connection.commit()
        self.assertEqual(self.adapter.reconcile(self.module, (armed,), NOW, EvaluationLimits(8)).degraded, 1)
        self.assertEqual(self.adapter.diagnostic.code, "RUNTIME_CHECKPOINT_INVALID")

    def test_journal_crash_boundaries_recover_the_one_stable_occurrence(self) -> None:
        for boundary in ("before_ingest_commit", "after_ingest_commit"):
            with self.subTest(boundary=boundary):
                self.root = Path(self.tmp.name) / boundary
                self.root.mkdir()
                self.module = self.runtime()
                self.sample = ProcessExitSample.alive(**IDENTITY)
                armed = self.register()
                self.sample = ProcessExitSample.zombie(**IDENTITY)

                def crash(name):
                    if name == boundary:
                        raise RuntimeError("simulated crash")

                failed = self.adapter.reconcile(self.runtime(crash), (armed,), NOW, EvaluationLimits(8))
                self.assertEqual(failed.degraded, 1)
                fresh = self.runtime()
                restored = ProcessExitAdapter.restore(armed, self.registry, self.observe, lambda: self.uid)
                restored.reconcile(fresh, (armed,), NOW + timedelta(seconds=1), EvaluationLimits(8))
                self.assertEqual(restored.evaluate(fresh, armed, NOW, EvaluationLimits(8)).outcome, "matched")
                self.assertEqual(self.counts(), (1, 1))

    def test_fixed_field_proc_observer_classifies_alive_zombie_and_absence(self) -> None:
        proc_root = self.root / "proc"
        boot_path = proc_root / "sys/kernel/random"
        process_path = proc_root / "123"
        boot_path.mkdir(parents=True)
        process_path.mkdir()
        (boot_path / "boot_id").write_text(BOOT_ID, encoding="utf-8")

        def write_stat(state: str) -> None:
            fields = [state, *(["0"] * 18), "456"]
            (process_path / "stat").write_text(
                "123 (fixture name) " + " ".join(fields), encoding="utf-8"
            )

        write_stat("S")
        alive = observe_process_exit(123, proc_root=proc_root)
        self.assertEqual(alive.state, "alive")
        self.assertEqual(alive.identity()["start_time_ticks"], 456)
        self.assertEqual(alive.identity()["owner_uid"], process_path.stat().st_uid)

        write_stat("Z")
        self.assertEqual(observe_process_exit(123, proc_root=proc_root).state, "zombie")
        (process_path / "stat").unlink()
        process_path.rmdir()
        disappeared = observe_process_exit(123, proc_root=proc_root)
        self.assertEqual(disappeared, ProcessExitSample.disappeared(boot_id=BOOT_ID))

    def test_fixed_field_proc_observer_rejects_unknown_state_and_oversized_fields(self) -> None:
        proc_root = self.root / "proc"
        boot_path = proc_root / "sys/kernel/random"
        process_path = proc_root / "123"
        boot_path.mkdir(parents=True)
        process_path.mkdir()
        boot_file = boot_path / "boot_id"
        stat_file = process_path / "stat"
        boot_file.write_text(BOOT_ID, encoding="utf-8")
        fields = ["Q", *(["0"] * 18), "456"]
        stat_file.write_text("123 (fixture) " + " ".join(fields), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unsupported state"):
            observe_process_exit(123, proc_root=proc_root)

        stat_file.write_text("x" * 4097, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exceeds its bound"):
            observe_process_exit(123, proc_root=proc_root)

        boot_file.write_text("x" * 65, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exceeds its bound"):
            observe_process_exit(123, proc_root=proc_root)

    def test_production_factory_rechecks_the_exact_identity_at_registration(self) -> None:
        proc_root = self.root / "proc"
        boot_path = proc_root / "sys/kernel/random"
        process_path = proc_root / "123"
        boot_path.mkdir(parents=True)
        process_path.mkdir()
        (boot_path / "boot_id").write_text(BOOT_ID, encoding="utf-8")
        fields = ["S", *(["0"] * 18), "456"]
        (process_path / "stat").write_text(
            "123 (fixture) " + " ".join(fields), encoding="utf-8"
        )
        uid = process_path.stat().st_uid
        adapter = production_process_exit_adapter(
            123, proc_root=proc_root, effective_uid=lambda: uid
        )
        self.assertEqual(dict(adapter.descriptor.resource), {
            "boot_id": BOOT_ID,
            "pid": 123,
            "start_time_ticks": 456,
            "owner_uid": uid,
        })
        self.assertEqual(adapter.establish_anchor(adapter.request(), NOW).baseline["state"], "alive")


if __name__ == "__main__":
    unittest.main()
