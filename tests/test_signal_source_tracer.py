from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from codex_wake.event_wake import EventWake
from codex_wake.records import cancel_record
from codex_wake.runtime_signals import RuntimeSourceDescriptor, RuntimeSourceRegistry
from codex_wake.runtime_signal_tracer import RuntimeSignalTracer, TracerSample
from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher, signal_journal_path
from codex_wake.signal_store import SQLiteSignalModule
from codex_wake.signals import EvaluationLimits, Registration, Resume, WakeIntent


NOW = datetime(2026, 9, 15, tzinfo=UTC)


class RuntimeTracerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.allowed = True
        self.sample = TracerSample("waiting", 0)
        self.calls = 0
        self.descriptor = RuntimeSourceDescriptor.parse({"version": 1, "kind": "tracer.state",
            "resource": {"identity": "test-resource"}, "target_state": "ready"})
        self.registry = RuntimeSourceRegistry({"tracer.state": lambda d: self.allowed and d == self.descriptor})
        self.tracer = RuntimeSignalTracer(self.descriptor, self.registry, self.observe)
        self.module = self.runtime()

    def runtime(self, checkpoint=None):
        return SQLiteSignalModule(signal_journal_path(self.root), checkpoint=checkpoint,
            record_publisher=WakeRecordPublisher(self.root,
                ManagedReaderCapability(self.root, "reader", 1, frozenset({1, 2}), True)))

    def observe(self):
        self.calls += 1
        return self.sample

    def register(self, expires_at=None):
        result = EventWake(self.module, adapters=(self.tracer,), clock=lambda: NOW,
            id_factory=lambda: "wake_tracer").register(WakeIntent(self.tracer.request(),
                Resume("continue", self.root, {"transport": "tmux", "tmux_socket": "/tmp/fixture", "pane": "%1"}),
                expires_at=expires_at), idempotency_key="tracer-registration")
        self.assertIsInstance(result, Registration)
        return self.module.load_armed_signal(result.wake_id)

    def counts(self):
        with sqlite3.connect(signal_journal_path(self.root)) as db:
            return tuple(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                         for table in ("receipts", "match_reservations"))

    def test_nonmatching_baseline_transition_restart_and_one_publication(self):
        armed = self.register()
        self.assertEqual(self.tracer.runner((armed,)).reconcile(self.module, NOW, EvaluationLimits(8)).observed, 0)
        self.sample = TracerSample("ready", 1)
        self.assertEqual(self.tracer.reconcile(self.module, (armed,), NOW, EvaluationLimits(8)).observed, 1)
        fresh = self.runtime()
        restored = RuntimeSignalTracer.restore(armed, self.registry, self.observe)
        report = restored.reconcile(fresh, (armed,), NOW + timedelta(seconds=1), EvaluationLimits(8))
        self.assertEqual((report.observed, report.degraded), (0, 0))
        first = restored.evaluate(fresh, armed, NOW, EvaluationLimits(8))
        second = restored.evaluate(fresh, armed, NOW, EvaluationLimits(8))
        self.assertEqual(first, second)
        self.assertEqual(first.outcome, "matched")
        self.assertEqual(self.counts(), (1, 1))
        record = json.loads((self.root / "firing/wake_tracer.json").read_text())
        self.assertEqual(record["trigger_match"]["attributes"]["state"], "ready")

    def test_revocation_blocks_sampling_and_prior_receipt_publication(self):
        armed = self.register()
        self.sample = TracerSample("ready", 1)
        self.tracer.reconcile(self.module, (armed,), NOW, EvaluationLimits(8))
        calls = self.calls
        self.allowed = False
        report = self.tracer.reconcile(self.module, (armed,), NOW, EvaluationLimits(8))
        outcome = self.tracer.evaluate(self.module, armed, NOW, EvaluationLimits(8))
        self.assertEqual(self.calls, calls)
        self.assertEqual(report.degraded, 1)
        self.assertEqual(outcome.code, "RUNTIME_AUTHORIZATION_DENIED")
        self.assertEqual(self.counts(), (1, 0))
        self.assertFalse((self.root / "firing/wake_tracer.json").exists())

    def test_revocation_during_observation_prevents_ingestion(self):
        armed = self.register()
        def revoke():
            self.allowed = False
            return TracerSample("ready", 1)
        tracer = RuntimeSignalTracer(self.descriptor, self.registry, revoke)
        self.assertEqual(tracer.reconcile(self.module, (armed,), NOW, EvaluationLimits(8)).degraded, 1)
        self.assertEqual(self.counts(), (0, 0))

    def test_revocation_after_reservation_blocks_publication_and_preserves_reservation(self):
        armed = self.register()
        self.sample = TracerSample("ready", 1)
        self.tracer.runner((armed,)).reconcile(self.module, NOW, EvaluationLimits(8))
        evaluate = self.module.evaluate
        def reserve_then_revoke(*args):
            outcome = evaluate(*args)
            self.allowed = False
            return outcome
        with patch.object(self.module, "evaluate", side_effect=reserve_then_revoke):
            outcome = self.tracer.evaluate(self.module, armed, NOW, EvaluationLimits(8))
        self.assertEqual(outcome.code, "RUNTIME_AUTHORIZATION_DENIED")
        self.assertEqual(self.counts(), (1, 1))
        self.assertFalse((self.root / "firing/wake_tracer.json").exists())
        self.allowed = True
        self.assertEqual(self.tracer.evaluate(self.module, armed, NOW, EvaluationLimits(8)).outcome, "matched")
        self.assertEqual(self.counts(), (1, 1))

    def test_revocation_during_authorized_ingest_takes_effect_at_next_guard(self):
        armed = self.register()
        self.sample = TracerSample("ready", 1)
        ingest = self.module.ingest
        def ingest_then_revoke(*args):
            # The successful pre-ingest guard authorized this operation. Later
            # revocation does not retract its committed occurrence.
            outcome = ingest(*args)
            self.allowed = False
            return outcome
        with patch.object(self.module, "ingest", side_effect=ingest_then_revoke):
            report = self.tracer.runner((armed,)).reconcile(self.module, NOW, EvaluationLimits(8))
        self.assertEqual((report.observed, report.degraded), (1, 0))
        self.assertEqual(self.counts(), (1, 0))
        self.assertEqual(self.tracer.evaluate(self.module, armed, NOW, EvaluationLimits(8)).code,
            "RUNTIME_AUTHORIZATION_DENIED")
        self.assertEqual(self.counts(), (1, 0))
        self.assertFalse((self.root / "firing/wake_tracer.json").exists())
        self.allowed = True
        self.assertEqual(self.tracer.evaluate(self.module, armed, NOW, EvaluationLimits(8)).outcome, "matched")
        self.assertEqual(self.counts(), (1, 1))

    def test_initial_match_ambiguity_and_budget_exhaustion_fail_closed(self):
        self.sample = TracerSample("ready", 0)
        self.assertEqual(self.tracer.establish_anchor(self.tracer.request(), NOW).code, "RUNTIME_BASELINE_MATCHES")
        self.sample = TracerSample("waiting", 0)
        armed = self.register()
        before = self.calls
        report = self.tracer.reconcile(self.module, (armed,), NOW, EvaluationLimits(0))
        self.assertEqual((report.degraded, self.calls), (1, before))
        self.assertEqual(self.tracer.diagnostic.code, "RUNTIME_RESOURCE_LIMIT")
        self.sample = {"state": "ready", "generation": 1, "env": "private"}
        self.assertEqual(self.tracer.reconcile(self.module, (armed,), NOW, EvaluationLimits(8)).degraded, 1)
        self.assertEqual(self.tracer.diagnostic.code, "RUNTIME_OBSERVATION_UNAVAILABLE")
        self.assertEqual(self.counts(), (0, 0))

    def test_cancelled_and_expired_arms_are_not_sampled(self):
        # "Timeout" here is durable wake expiry. The trusted fixture callback
        # is synchronous; real adapters must bound their own backend calls.
        armed = self.register(expires_at=NOW + timedelta(seconds=1))
        before = self.calls
        self.tracer.reconcile(self.module, (armed,), NOW + timedelta(seconds=2), EvaluationLimits(8))
        self.assertEqual(self.calls, before)
        self.assertEqual(self.tracer.evaluate(self.module, armed, NOW + timedelta(seconds=2), EvaluationLimits(8)).outcome, "expired")
        cancel_record(self.root, "wake_tracer", now=NOW)
        self.tracer.reconcile(self.module, (armed,), NOW, EvaluationLimits(8))
        self.assertEqual(self.calls, before)
        self.assertEqual(self.counts(), (0, 0))

    def test_crashes_before_and_after_ingest_commit_recover_one_occurrence(self):
        for boundary in ("before_ingest_commit", "after_ingest_commit"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as tmp:
                self.root = Path(tmp)
                self.module = self.runtime()
                self.sample = TracerSample("waiting", 0)
                armed = self.register()
                self.sample = TracerSample("ready", 1)
                def crash(name):
                    if name == boundary:
                        raise RuntimeError("simulated crash")
                failed = self.tracer.reconcile(self.runtime(crash), (armed,), NOW, EvaluationLimits(8))
                self.assertEqual(failed.degraded, 1)
                fresh = self.runtime()
                restored = RuntimeSignalTracer.restore(armed, self.registry, self.observe)
                restored.reconcile(fresh, (armed,), NOW + timedelta(seconds=1), EvaluationLimits(8))
                self.assertEqual(restored.evaluate(fresh, armed, NOW, EvaluationLimits(8)).outcome, "matched")
                self.assertEqual(self.counts(), (1, 1))

    def test_ambiguous_generation_and_forged_anchor_never_match(self):
        from dataclasses import replace
        armed = self.register()
        self.sample = TracerSample("ready", 0)
        self.assertEqual(self.tracer.reconcile(self.module, (armed,), NOW, EvaluationLimits(8)).degraded, 1)
        self.assertEqual(self.tracer.diagnostic.code, "RUNTIME_OBSERVATION_AMBIGUOUS")
        forged = replace(armed, anchor=replace(armed.anchor, source_anchor="runtime:other"))
        with self.assertRaises(ValueError):
            RuntimeSignalTracer.restore(forged, self.registry, self.observe)
        self.assertEqual(self.counts(), (0, 0))

    def test_fresh_process_crash_reconstructs_identity_and_recovers_publication(self):
        # A real process exit skips Python rollback/finally cleanup at the journal boundary.
        child = r'''
import os, sys
from pathlib import Path
from datetime import UTC, datetime
from codex_wake.runtime_signals import RuntimeSourceRegistry
from codex_wake.runtime_signal_tracer import RuntimeSignalTracer, TracerSample
from codex_wake.signal_store import SQLiteSignalModule
from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher, signal_journal_path
from codex_wake.signals import EvaluationLimits
root = Path(sys.argv[1])
def crash(name):
    if name == sys.argv[2]:
        os._exit(91)
module = SQLiteSignalModule(signal_journal_path(root), checkpoint=crash,
    record_publisher=WakeRecordPublisher(root, ManagedReaderCapability(root, "child", 1, frozenset({1, 2}), True)))
armed = module.load_armed_signal("wake_tracer")
tracer = RuntimeSignalTracer.restore(armed, RuntimeSourceRegistry({"tracer.state": lambda d: d.resource["identity"] == "test-resource"}), lambda: TracerSample("ready", 1))
now = datetime(2026, 9, 15, tzinfo=UTC)
tracer.runner((armed,)).reconcile(module, now, EvaluationLimits(8))
tracer.evaluate(module, armed, now, EvaluationLimits(8))
'''
        for boundary in ("before_ingest_commit", "after_ingest_commit", "after_match_reservation_commit"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as tmp:
                self.root = Path(tmp)
                self.module = self.runtime()
                self.sample = TracerSample("waiting", 0)
                armed = self.register()
                completed = subprocess.run([sys.executable, "-c", child, str(self.root), boundary],
                    check=False, capture_output=True, text=True, timeout=10)
                self.assertEqual(completed.returncode, 91, completed.stderr)
                self.sample = TracerSample("ready", 1)
                fresh = self.runtime()
                restored = RuntimeSignalTracer.restore(fresh.load_armed_signal(armed.wake_id), self.registry, self.observe)
                restored.runner((armed,)).reconcile(fresh, NOW + timedelta(seconds=1), EvaluationLimits(8))
                self.assertEqual(restored.evaluate(fresh, armed, NOW, EvaluationLimits(8)).outcome, "matched")
                self.assertEqual(self.counts(), (1, 1))
                state = fresh.inspect_signal_state(armed.wake_id)
                self.assertEqual([row["revision"] for row in state["outbox"]], [1, 2])
