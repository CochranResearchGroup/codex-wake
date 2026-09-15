from __future__ import annotations

import unittest
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from codex_wake.runtime_signals import RuntimeSourceRegistry
from codex_wake.signals import (
    ArmId,
    ArmContext,
    ArmedSignal,
    Degraded,
    EvaluationLimits,
    Expired,
    InMemorySignalModule,
    Invalid,
    Matched,
    SignalRequest,
    WakeId,
)
from codex_wake.systemd_signals import (
    SystemdReadError,
    SystemdReadCapability,
    SystemdSignalAdapter,
    SystemdSignalRunner,
    SystemdUnitState,
)
from codex_wake.systemd_source_config import SystemdSourceConfig
from codex_wake.records import cancel_record
from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher, signal_journal_path
from codex_wake.signal_store import SQLiteSignalModule
from tests.test_signals import make_intent
from tests.test_signal_store import make_module


NOW = datetime(2026, 9, 15, 15, 0, tzinfo=UTC)


class FakeUserManager:
    def __init__(self, state: SystemdUnitState | None) -> None:
        self.state = state
        self.aliases = {"build.service": "build.service"}
        self.calls: list[tuple[str, str]] = []

    def resolve_unit(self, unit: str, *, timeout_seconds: int) -> str:
        self.calls.append(("resolve", unit))
        return self.aliases[unit]

    def read_unit(self, unit: str, *, timeout_seconds: int) -> SystemdUnitState | None:
        self.calls.append(("read", unit))
        return self.state


def adapter(manager: FakeUserManager, *, authorizer=None,
            capability: SystemdReadCapability | None = None) -> SystemdSignalAdapter:
    source = SystemdSourceConfig(
        "build-state", "build.service", 1000, frozenset({"active", "inactive", "failed"})
    )
    descriptor_authorizer = authorizer or (lambda descriptor: True)
    return SystemdSignalAdapter(
        source,
        manager,
        RuntimeSourceRegistry({"systemd.unit": descriptor_authorizer}),
        capability or SystemdReadCapability("user", 1000),
    )


def arm(module, selected: SystemdSignalAdapter, name: str = "wake", *, expires_at=None) -> ArmedSignal:
    spec = selected.request("active")
    result = module.arm(
        WakeId(name), spec,
        ArmContext(name, name, NOW, expires_at, make_intent().resume, selected),
    )
    assert isinstance(result, ArmedSignal)
    return result


def module_at_wake_root(wake_root: Path) -> SQLiteSignalModule:
    return SQLiteSignalModule(
        signal_journal_path(wake_root),
        record_publisher=WakeRecordPublisher(
            wake_root,
            ManagedReaderCapability(wake_root, "systemd-test", 1, frozenset({1, 2}), True),
        ),
    )


class SystemdSignalTests(unittest.TestCase):
    def test_already_matching_registration_is_rejected_without_a_baseline(self) -> None:
        manager = FakeUserManager(SystemdUnitState("build.service", "active", "boot-a"))
        selected = adapter(manager)
        result = selected.establish_anchor(selected.request("active"), NOW)

        self.assertEqual(result, Degraded(None, "SYSTEMD_BASELINE_MATCHES", None))
        self.assertEqual(manager.calls, [("resolve", "build.service"), ("read", "build.service")])

    def test_nonmatching_baseline_then_real_transition_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
            selected = adapter(manager)
            module = make_module(Path(tmp) / "signals.sqlite3")
            armed = arm(module, selected)
            runner = SystemdSignalRunner((selected,), armed_signals=(armed,))

            first = runner.reconcile(module, NOW, EvaluationLimits(10))
            self.assertEqual((first.observed, first.degraded), (0, 0))
            manager.state = SystemdUnitState("build.service", "active", "boot-a")
            final = runner.reconcile(module, NOW, EvaluationLimits(10))
            outcome = module.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10))

            self.assertEqual((final.observed, final.degraded), (1, 0))
            self.assertIsInstance(outcome, Matched)
            self.assertEqual(outcome.receipt.attributes["active_state"], "active")

    def test_alias_resolution_precedes_exact_canonical_authorization(self) -> None:
        manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
        manager.aliases["build.service"] = "other.service"
        selected = adapter(manager)
        outcome = selected.establish_anchor(selected.request("active"), NOW)

        self.assertIsInstance(outcome, Invalid)
        self.assertEqual(outcome.code, "SYSTEMD_SIGNAL_NOT_ALLOWED")
        self.assertEqual(manager.calls, [("resolve", "build.service")])

    def test_missing_is_unavailable_not_inactive_and_read_errors_are_sanitized(self) -> None:
        manager = FakeUserManager(None)
        selected = adapter(manager)
        result = selected.establish_anchor(selected.request("inactive"), NOW)
        self.assertEqual(result, Degraded(None, "SYSTEMD_UNIT_UNAVAILABLE", None))

        with tempfile.TemporaryDirectory() as tmp:
            manager.state = SystemdUnitState("build.service", "inactive", "boot-a")
            selected = adapter(manager)
            module = make_module(Path(tmp) / "signals.sqlite3")
            armed = arm(module, selected)
            manager.state = None
            report = SystemdSignalRunner((selected,), armed_signals=(armed,)).reconcile(module, NOW, EvaluationLimits(10))
            self.assertEqual((report.observed, report.degraded), (0, 1))

    def test_gap_and_boot_change_rebaseline_without_claiming_a_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
            selected = adapter(manager)
            module = make_module(Path(tmp) / "signals.sqlite3")
            armed = arm(module, selected)
            runner = SystemdSignalRunner((selected,), armed_signals=(armed,))
            runner.reconcile(module, NOW, EvaluationLimits(10))
            manager.state = SystemdUnitState("build.service", "active", "boot-a")
            runner.observation_gap()
            gap = runner.reconcile(module, NOW, EvaluationLimits(10))
            manager.state = SystemdUnitState("build.service", "failed", "boot-b")
            boot = runner.reconcile(module, NOW, EvaluationLimits(10))

            self.assertEqual((gap.observed, gap.degraded), (0, 0))
            self.assertEqual((boot.observed, boot.degraded), (0, 0))
            self.assertNotIsInstance(module.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10)), Matched)

    def test_reconnect_rebaselines_without_claiming_a_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
            selected = adapter(manager)
            module = make_module(Path(tmp) / "signals.sqlite3")
            armed = arm(module, selected)
            runner = SystemdSignalRunner((selected,), armed_signals=(armed,))
            runner.reconcile(module, NOW, EvaluationLimits(10))
            manager.state = SystemdUnitState("build.service", "active", "boot-a")
            runner.reconnect()

            report = runner.reconcile(module, NOW, EvaluationLimits(10))

            self.assertEqual((report.observed, report.degraded), (0, 0))
            self.assertNotIsInstance(module.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10)), Matched)

    def test_persisted_checkpoint_makes_restart_and_repeated_reconcile_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
            selected = adapter(manager)
            module = make_module(Path(tmp) / "signals.sqlite3")
            armed = arm(module, selected)
            SystemdSignalRunner((selected,), armed_signals=(armed,)).reconcile(module, NOW, EvaluationLimits(10))
            manager.state = SystemdUnitState("build.service", "active", "boot-a")
            restarted = SystemdSignalRunner((selected,), armed_signals=(armed,), initial_reason="startup")
            first = restarted.reconcile(module, NOW, EvaluationLimits(10))
            second = restarted.reconcile(module, NOW, EvaluationLimits(10))
            result = module.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10))

            self.assertEqual((first.observed, second.observed), (1, 0))
            self.assertIsInstance(result, Matched)

    def test_sqlite_commit_then_crash_boundary_recovers_without_duplicate_observation(self) -> None:
        class CrashAfterCommit:
            def __init__(self, inner):
                self.inner = inner

            def source_checkpoint(self, source, source_instance):
                return self.inner.source_checkpoint(source, source_instance)

            def load_armed_signal(self, wake_id):
                return self.inner.load_armed_signal(wake_id)

            def ingest(self, observations, source_commit):
                self.inner.ingest(observations, source_commit)
                raise RuntimeError("simulated post-commit crash")

            def evaluate(self, wake_id, armed_signal, now, limits):
                return self.inner.evaluate(wake_id, armed_signal, now, limits)

        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
            selected = adapter(manager)
            module = make_module(database)
            armed = arm(module, selected)
            SystemdSignalRunner((selected,), armed_signals=(armed,)).reconcile(module, NOW, EvaluationLimits(10))
            manager.state = SystemdUnitState("build.service", "active", "boot-a")
            with self.assertRaisesRegex(RuntimeError, "post-commit"):
                SystemdSignalRunner((selected,), armed_signals=(armed,)).reconcile(CrashAfterCommit(module), NOW, EvaluationLimits(10))

            recovered = make_module(database)
            restored = recovered.load_armed_signal(armed.wake_id)
            assert isinstance(restored, ArmedSignal)
            replay = SystemdSignalRunner((selected,), armed_signals=(restored,), initial_reason="startup")
            result = replay.reconcile(recovered, NOW, EvaluationLimits(10))

            self.assertEqual((result.observed, result.degraded), (0, 0))
            self.assertIsInstance(recovered.evaluate(restored.wake_id, restored, NOW, EvaluationLimits(10)), Matched)

    def test_cancelled_or_expired_arms_do_not_create_a_live_adapter_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wake_root = Path(tmp) / "wake"
            manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
            selected = adapter(manager)
            module = module_at_wake_root(wake_root)
            cancelled_arm = arm(module, selected, "cancelled")
            cancel_record(wake_root, str(cancelled_arm.wake_id), now=NOW)
            manager.calls.clear()
            cancelled = SystemdSignalRunner((selected,), armed_signals=(cancelled_arm,)).reconcile(
                module, NOW, EvaluationLimits(10)
            )
            self.assertEqual((cancelled.scanned, cancelled.observed, cancelled.degraded), (0, 0, 0))
            self.assertEqual(module.terminal_status(cancelled_arm.wake_id), "cancelled")
            self.assertEqual(manager.calls, [])

            expiring = arm(module, selected, "expired", expires_at=NOW)
            manager.calls.clear()
            unreaped = SystemdSignalRunner((selected,), armed_signals=(expiring,)).reconcile(
                module, NOW, EvaluationLimits(10)
            )
            self.assertEqual((unreaped.scanned, unreaped.observed, unreaped.degraded), (0, 0, 0))
            self.assertEqual(manager.calls, [])
            self.assertTrue(module.expire_unreserved(expiring.wake_id, now=NOW))
            expired = SystemdSignalRunner((selected,), armed_signals=(expiring,)).reconcile(
                module, NOW, EvaluationLimits(10)
            )
            self.assertEqual((expired.scanned, expired.observed, expired.degraded), (0, 0, 0))
            self.assertEqual(module.terminal_status(expiring.wake_id), "expired")
            self.assertEqual(manager.calls, [])

    def test_revocation_and_hostile_or_wrong_unit_observation_fail_closed(self) -> None:
        permitted = {"yes"}
        with tempfile.TemporaryDirectory() as tmp:
            manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
            selected = adapter(manager, authorizer=lambda descriptor: bool(permitted))
            module = make_module(Path(tmp) / "signals.sqlite3")
            armed = arm(module, selected)
            permitted.clear()
            report = SystemdSignalRunner((selected,), armed_signals=(armed,)).reconcile(module, NOW, EvaluationLimits(10))
            self.assertEqual(report.degraded, 1)
            self.assertEqual(manager.calls[-1], ("resolve", "build.service"))

            valid = selected.request("active")
            self.assertIsInstance(selected.establish_anchor(replace(valid, subject="unit:other.service"), NOW), Invalid)

    def test_capability_denies_foreign_uid_without_calling_the_backend(self) -> None:
        manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
        with patch("codex_wake.systemd_signals.os.geteuid", return_value=1001):
            selected = adapter(manager)
            denied = selected.establish_anchor(selected.request("active"), NOW)

        self.assertEqual(denied, Degraded(None, "SYSTEMD_CAPABILITY_DENIED", None))
        self.assertEqual(manager.calls, [])
        with self.assertRaisesRegex(ValueError, "capability is invalid"):
            SystemdReadCapability("system", 1000)

    def test_read_unit_timeout_and_unavailable_are_sanitized_degradations(self) -> None:
        manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
        selected = adapter(manager)

        def timeout(unit: str, *, timeout_seconds: int):
            raise SystemdReadError("timeout")

        manager.read_unit = timeout  # type: ignore[method-assign]
        result = selected.establish_anchor(selected.request("active"), NOW)
        self.assertEqual(result, Degraded(None, "SYSTEMD_OBSERVATION_TIMEOUT", None))

        def unavailable(unit: str, *, timeout_seconds: int):
            raise SystemdReadError("unavailable")

        manager.read_unit = unavailable  # type: ignore[method-assign]
        result = selected.establish_anchor(selected.request("active"), NOW)
        self.assertEqual(result, Degraded(None, "SYSTEMD_OBSERVATION_UNAVAILABLE", None))

    def test_runner_without_durable_loader_fails_closed_without_backend_reads(self) -> None:
        manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
        selected = adapter(manager)
        module = InMemorySignalModule()
        armed = arm(module, selected)
        manager.calls.clear()

        result = SystemdSignalRunner((selected,), armed_signals=(armed,)).reconcile(
            module, NOW, EvaluationLimits(10)
        )

        self.assertEqual((result.scanned, result.observed, result.degraded), (0, 0, 1))
        self.assertEqual(manager.calls, [])

    def test_runner_rejects_a_stale_arm_identity_before_backend_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = FakeUserManager(SystemdUnitState("build.service", "inactive", "boot-a"))
            selected = adapter(manager)
            module = make_module(Path(tmp) / "signals.sqlite3")
            armed = arm(module, selected)
            stale = replace(armed, arm_id=ArmId("arm_stale"))
            manager.calls.clear()

            result = SystemdSignalRunner((selected,), armed_signals=(stale,)).reconcile(
                module, NOW, EvaluationLimits(10)
            )

            self.assertEqual((result.scanned, result.observed, result.degraded), (0, 0, 1))
            self.assertEqual(manager.calls, [])
